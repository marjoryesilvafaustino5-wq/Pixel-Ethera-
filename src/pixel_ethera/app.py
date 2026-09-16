from flask import Flask, render_template, request, jsonify, send_from_directory, session
from pathlib import Path
import json
import hashlib
import hmac
import math
import os
import time
import uuid
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent.parent

load_dotenv(PROJECT_DIR / ".env")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "pixel-ethera-development-key")

MP_API_URL = "https://api.mercadopago.com"
MP_CLIENT_ID = os.environ.get("MP_CLIENT_ID")
MP_CLIENT_SECRET = os.environ.get("MP_CLIENT_SECRET")
MP_REDIRECT_URI = os.environ.get("MP_REDIRECT_URI")
MP_WEBHOOK_SECRET = os.environ.get("MP_WEBHOOK_SECRET")

DATA_FILE = PROJECT_DIR / "artworks.json"
PROFILES_FILE = PROJECT_DIR / "artist_profiles.json"
USERS_FILE = PROJECT_DIR / "users.json"
PURCHASES_FILE = PROJECT_DIR / "purchases.json"

UPLOAD_FOLDER = BASE_DIR / "static" / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024


def load_json(file_path, default):
    if not file_path.exists():
        return default

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return default


def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_artworks():
    data = load_json(DATA_FILE, [])
    return data if isinstance(data, list) else []


def save_artworks(artworks):
    save_json(DATA_FILE, artworks)


def load_profiles():
    data = load_json(PROFILES_FILE, [])
    return data if isinstance(data, list) else []


def save_profiles(profiles):
    save_json(PROFILES_FILE, profiles)


def load_users():
    data = load_json(USERS_FILE, [])
    return data if isinstance(data, list) else []


def save_users(users):
    save_json(USERS_FILE, users)


def load_purchases():
    data = load_json(PURCHASES_FILE, [])
    return data if isinstance(data, list) else []


def save_purchases(purchases):
    save_json(PURCHASES_FILE, purchases)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def get_logged_user():
    user_id = session.get("user_id")

    if not user_id:
        return None

    users = load_users()
    for user in users:
        if user.get("id") == user_id:
            return user

    return None


def get_user_profile(user_id):
    profiles = load_profiles()

    for profile in profiles:
        if profile.get("user_id") == user_id:
            return profile

    return None


def save_profile(profile):
    profiles = load_profiles()
    for index, item in enumerate(profiles):
        if item.get("id") == profile.get("id"):
            profiles[index] = profile
            break
    else:
        profiles.append(profile)
    save_profiles(profiles)


def has_artwork_id(artwork, artwork_id):
    try:
        return int(artwork.get("id", 0)) == artwork_id
    except (AttributeError, TypeError, ValueError):
        return False


@app.route("/")
def home():
    return render_template("index.html")


# =====================================================
# CONTA
# =====================================================

@app.post("/api/register")
def register():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name:
        return jsonify({
            "error": "Informe seu nome artístico."
        }), 400

    if not email:
        return jsonify({
            "error": "Informe seu e-mail."
        }), 400

    if "@" not in email:
        return jsonify({
            "error": "Informe um e-mail válido."
        }), 400

    if len(password) < 6:
        return jsonify({
            "error": "A senha precisa ter pelo menos 6 caracteres."
        }), 400

    users = load_users()

    for user in users:
        if user.get("email") == email:
            return jsonify({
                "error": "Este e-mail já possui uma conta."
            }), 409

    user = {
        "id": str(uuid.uuid4()),
        "name": name,
        "email": email,
        "password": generate_password_hash(password)
    }

    users.append(user)
    save_users(users)

    profiles = load_profiles()

    profiles.append({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "name": name,
        "bio": "",
        "space": "Ethera"
    })

    save_profiles(profiles)

    session["user_id"] = user["id"]

    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "email": user["email"]
    }), 201


@app.post("/api/login")
def login():

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    users = load_users()

    for user in users:

        if user.get("email") == email:

            if check_password_hash(
                user.get("password", ""),
                password
            ):

                session["user_id"] = user["id"]

                return jsonify({
                    "id": user["id"],
                    "name": user["name"],
                    "email": user["email"]
                })

            break

    return jsonify({
        "error": "E-mail ou senha incorretos."
    }), 401


@app.post("/api/logout")
def logout():

    session.clear()

    return jsonify({
        "message": "Logout realizado."
    })


@app.get("/api/me")
def current_user():

    user = get_logged_user()

    if not user:
        return jsonify({
            "logged_in": False
        })

    return jsonify({
        "logged_in": True,
        "id": user["id"],
        "name": user["name"],
        "email": user["email"]
    })


# =====================================================
# PERFIS
# =====================================================

@app.get("/api/profiles")
def get_profiles():

    return jsonify(load_profiles())


@app.get("/api/profile")
def get_profile():

    user = get_logged_user()

    if not user:
        return jsonify({})

    profile = get_user_profile(user["id"])

    return jsonify(profile or {})


@app.post("/api/profile")
def update_profile():

    user = get_logged_user()

    if not user:
        return jsonify({
            "error": "Você precisa entrar em uma conta."
        }), 401

    name = request.form.get("name", "").strip()
    bio = request.form.get("bio", "").strip()
    space = request.form.get("space", "").strip()

    if not name:
        return jsonify({
            "error": "Informe seu nome artístico."
        }), 400

    if space not in ["Ethera", "Pixel Dreams"]:
        return jsonify({
            "error": "Escolha um espaço válido."
        }), 400

    profiles = load_profiles()

    for profile in profiles:

        if (
            profile.get("name", "").lower() == name.lower()
            and profile.get("user_id") != user["id"]
        ):
            return jsonify({
                "error": "Esse nome artístico já está sendo usado."
            }), 409

    profile = get_user_profile(user["id"])

    if profile:

        profile["name"] = name
        profile["bio"] = bio
        profile["space"] = space

    else:

        profile = {
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "name": name,
            "bio": bio,
            "space": space
        }

        profiles.append(profile)

    users = load_users()

    for account in users:

        if account.get("id") == user["id"]:
            account["name"] = name
            break

    save_users(users)
    save_profiles(profiles)

    return jsonify(profile)


# =====================================================
# OBRAS
# =====================================================

@app.get("/api/artworks")
def get_artworks():

    return jsonify(load_artworks())


@app.post("/api/mercadopago/connect")
def mercadopago_connect():
    user = get_logged_user()
    if not user:
        return jsonify({"error": "Você precisa entrar em uma conta."}), 401
    if not MP_CLIENT_ID or not MP_REDIRECT_URI:
        return jsonify({"error": "Configure MP_CLIENT_ID e MP_REDIRECT_URI."}), 503

    profile = get_user_profile(user["id"])
    if not profile:
        return jsonify({"error": "Crie seu perfil de artista primeiro."}), 400

    state = str(uuid.uuid4())
    session["mercadopago_oauth_state"] = state
    authorization_url = "https://auth.mercadopago.com.br/authorization?" + urlencode({
        "client_id": MP_CLIENT_ID,
        "response_type": "code",
        "platform_id": "mp",
        "redirect_uri": MP_REDIRECT_URI,
        "state": state
    })
    return jsonify({"url": authorization_url}), 201


@app.get("/oauth/mercadopago/callback")
def mercadopago_callback():
    state = request.args.get("state")
    code = request.args.get("code")
    if not code or state != session.pop("mercadopago_oauth_state", None):
        return render_template("index.html", payment_status="connect_error")
    if not MP_CLIENT_ID or not MP_CLIENT_SECRET or not MP_REDIRECT_URI:
        return render_template("index.html", payment_status="connect_error")

    try:
        response = requests.post(
            f"{MP_API_URL}/oauth/token",
            json={
                "client_id": MP_CLIENT_ID,
                "client_secret": MP_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": MP_REDIRECT_URI
            },
            timeout=15
        )
    except requests.RequestException:
        return render_template("index.html", payment_status="connect_error")
    if not response.ok or not get_logged_user():
        return render_template("index.html", payment_status="connect_error")

    token = response.json()
    if not token.get("access_token"):
        return render_template("index.html", payment_status="connect_error")
    profile = get_user_profile(get_logged_user()["id"])
    profile["mercadopago_access_token"] = token.get("access_token")
    profile["mercadopago_refresh_token"] = token.get("refresh_token")
    profile["mercadopago_user_id"] = token.get("user_id")
    save_profile(profile)
    return render_template("index.html", payment_status="connect_return")


@app.get("/api/mercadopago/status")
def mercadopago_status():
    user = get_logged_user()
    if not user:
        return jsonify({"connected": False}), 401
    profile = get_user_profile(user["id"])
    connected = bool(profile and profile.get("mercadopago_access_token"))
    if not connected:
        return jsonify({"connected": False, "ready": False})
    return jsonify({"connected": True, "ready": True})


@app.get("/payment/connect/refresh")
def connect_refresh():
    return render_template("index.html", payment_status="connect_refresh")


@app.get("/payment/connect/return")
def connect_return():
    return render_template("index.html", payment_status="connect_return")


@app.post("/api/purchases")
def create_purchase():
    user = get_logged_user()
    if not user:
        return jsonify({
            "error": "Você precisa entrar em uma conta para comprar."
        }), 401

    payload = request.get_json(silent=True) or {}
    try:
        artwork_id = int(payload.get("artwork_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "Obra inválida."}), 400

    artwork = next(
        (item for item in load_artworks() if has_artwork_id(item, artwork_id)),
        None
    )
    if not artwork:
        return jsonify({"error": "Obra não encontrada."}), 404

    seller_profile = get_user_profile(artwork.get("user_id"))
    seller_token = seller_profile.get("mercadopago_access_token") if seller_profile else None
    if not seller_token:
        return jsonify({"error": "O artista ainda não configurou o recebimento."}), 409

    if not MP_CLIENT_ID or not MP_CLIENT_SECRET or not MP_REDIRECT_URI:
        return jsonify({
            "error": "Pagamento indisponível: configure o Mercado Pago."
        }), 503

    purchases = load_purchases()
    purchase = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "artwork_id": artwork_id,
        "status": "pending",
        "title": artwork.get("title", ""),
        "price": artwork.get("price", 0),
        "commission_percent": 5,
        "artist_percent": 95
    }

    amount = float(artwork.get("price", 0))
    try:
        preference = requests.post(
            f"{MP_API_URL}/checkout/preferences",
            headers={"Authorization": f"Bearer {seller_token}"},
            json={
                "items": [{
                    "title": artwork.get("title", "Obra digital"),
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": amount
                }],
                "marketplace_fee": round(amount * 0.05, 2),
                "external_reference": purchase["id"],
                "notification_url": f"{request.host_url}webhooks/mercadopago",
                "back_urls": {
                    "success": f"{request.host_url}payment/success",
                    "failure": f"{request.host_url}payment/cancelled",
                    "pending": f"{request.host_url}payment/pending"
                },
                "auto_return": "approved"
            },
            timeout=15
        )
    except requests.RequestException:
        return jsonify({"error": "Mercado Pago está indisponível no momento."}), 503
    if not preference.ok:
        return jsonify({"error": "Não foi possível iniciar o pagamento."}), 502

    preference_data = preference.json()
    if not preference_data.get("id") or not preference_data.get("init_point"):
        return jsonify({"error": "Resposta inválida do Mercado Pago."}), 502
    platform_fee = round(amount * 0.05, 2)
    purchase["checkout_id"] = preference_data.get("id")
    purchase["gross_amount"] = amount
    purchase["platform_fee"] = platform_fee
    purchase["artist_amount"] = round(amount - platform_fee, 2)
    purchases.append(purchase)
    save_purchases(purchases)

    return jsonify({"checkout_url": preference_data.get("init_point"), "purchase_id": purchase["id"]}), 201


@app.route("/webhooks/mercadopago", methods=["POST"])
@app.route("/api/mercadopago/webhook", methods=["POST"])
def webhook_mercadopago():
    if not MP_WEBHOOK_SECRET:
        return jsonify({"error": "Webhook não configurado."}), 503

    signature = request.headers.get("x-signature", "")
    request_id = request.headers.get("x-request-id", "")
    parts = dict(
        item.split("=", 1)
        for item in signature.split(",")
        if "=" in item
    )
    payload = request.get_json(silent=True) or {}
    payment_id = (payload.get("data") or {}).get("id")
    if not payment_id:
        return jsonify({"received": True})
    timestamp = parts.get("ts")
    signature_hash = parts.get("v1")
    if not timestamp or not signature_hash:
        return jsonify({"error": "Assinatura inválida."}), 401
    try:
        timestamp_value = int(timestamp)
    except ValueError:
        return jsonify({"error": "Assinatura inválida."}), 401
    if abs(int(time.time()) - timestamp_value) > 300:
        return jsonify({"error": "Assinatura expirada."}), 401
    manifest = f"id:{payment_id};request-id:{request_id};ts:{timestamp};"
    expected_hash = hmac.new(
        MP_WEBHOOK_SECRET.encode(), manifest.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature_hash, expected_hash):
        return jsonify({"error": "Assinatura inválida."}), 401

    purchases = load_purchases()
    for purchase in purchases:
        if purchase.get("mercadopago_payment_id") == str(payment_id):
            return jsonify({"received": True})

    for purchase in purchases:
        seller_profile = get_user_profile(
            next((item.get("user_id") for item in load_artworks()
                  if has_artwork_id(item, purchase.get("artwork_id"))), None)
        )
        token = seller_profile.get("mercadopago_access_token") if seller_profile else None
        if not token:
            continue
        try:
            payment = requests.get(
                f"{MP_API_URL}/v1/payments/{payment_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=15
            )
        except requests.RequestException:
            continue
        if payment.ok:
            payment_data = payment.json()
            if payment_data.get("external_reference") == purchase.get("id"):
                purchase["mercadopago_payment_id"] = str(payment_id)
                purchase["status"] = "paid" if payment_data.get("status") == "approved" else payment_data.get("status", "pending")
                save_purchases(purchases)
                break
    return jsonify({"received": True})


@app.get("/payment/success")
def payment_success():
    return render_template("index.html", payment_status="success")


@app.get("/payment/cancelled")
def payment_cancelled():
    return render_template("index.html", payment_status="cancelled")


@app.get("/payment/pending")
def payment_pending():
    return render_template("index.html", payment_status="pending")


@app.post("/api/artworks")
def create_artwork():

    user = get_logged_user()

    if not user:
        return jsonify({
            "error": "Você precisa entrar em uma conta para publicar uma obra."
        }), 401

    profile = get_user_profile(user["id"])

    if not profile:
        return jsonify({
            "error": "Crie seu perfil de artista antes de publicar."
        }), 400
    if not profile.get("mercadopago_access_token"):
        return jsonify({
            "error": "Configure sua conta Mercado Pago antes de publicar."
        }), 409

    title = request.form.get("title", "").strip()
    space = request.form.get("space", "").strip()
    price_text = request.form.get("price", "").strip()

    if not title:
        return jsonify({
            "error": "Informe o título da obra."
        }), 400

    if space not in ["Ethera", "Pixel Dreams"]:
        return jsonify({
            "error": "Espaço inválido."
        }), 400

    try:
        price = float(price_text)
    except (ValueError, TypeError):
        return jsonify({
            "error": "Preço inválido."
        }), 400

    if not math.isfinite(price) or price < 1:
        return jsonify({
            "error": "O preço mínimo é R$ 1,00."
        }), 400

    if price > 1000000:
        return jsonify({
            "error": "O preço máximo é R$ 1.000.000,00."
        }), 400

    image = request.files.get("image")

    if image is None or image.filename == "":
        return jsonify({
            "error": "Escolha uma imagem para a obra."
        }), 400

    if not allowed_file(image.filename):
        return jsonify({
            "error": "Formato de imagem não permitido."
        }), 400

    extension = image.filename.rsplit(".", 1)[1].lower()

    unique_name = (
        f"{uuid.uuid4().hex}.{extension}"
    )

    safe_name = secure_filename(unique_name)

    image_path = UPLOAD_FOLDER / safe_name

    image.save(image_path)

    artworks = load_artworks()

    new_id = 1

    if artworks:

        ids = []

        for artwork in artworks:

            try:
                ids.append(
                    int(artwork.get("id", 0))
                )
            except (TypeError, ValueError):
                pass

        if ids:
            new_id = max(ids) + 1

    artwork = {
        "id": new_id,
        "user_id": user["id"],
        "title": title,
        "artist": profile["name"],
        "space": space,
        "price": price,
        "image": f"/static/uploads/{safe_name}"
    }

    artworks.append(artwork)

    save_artworks(artworks)

    return jsonify(artwork), 201


# =====================================================
# MINHAS OBRAS
# =====================================================

@app.get("/api/my-artworks")
def my_artworks():

    user = get_logged_user()

    if not user:
        return jsonify({
            "error": "Você precisa entrar em uma conta."
        }), 401

    artworks = load_artworks()

    mine = [
        artwork
        for artwork in artworks
        if artwork.get("user_id") == user["id"]
    ]

    return jsonify(mine)


@app.delete("/api/artworks/<int:artwork_id>")
def delete_artwork(artwork_id):

    user = get_logged_user()

    if not user:
        return jsonify({
            "error": "Você precisa entrar em uma conta."
        }), 401

    artworks = load_artworks()

    artwork = None

    for item in artworks:

        if has_artwork_id(item, artwork_id):
            artwork = item
            break

    if not artwork:
        return jsonify({
            "error": "Obra não encontrada."
        }), 404

    if artwork.get("user_id") != user["id"]:
        return jsonify({
            "error": "Você só pode remover suas próprias obras."
        }), 403

    image_url = artwork.get("image", "")

    filename = Path(image_url).name

    image_path = UPLOAD_FOLDER / filename

    if image_path.exists():
        try:
            image_path.unlink()
        except OSError:
            pass

    artworks = [
        item
        for item in artworks
        if not has_artwork_id(item, artwork_id)
    ]

    save_artworks(artworks)

    return jsonify({
        "message": "Obra removida com sucesso."
    })

@app.put("/api/artworks/<int:artwork_id>")
def update_artwork(artwork_id):

    user = get_logged_user()

    if not user:
        return jsonify({
            "error": "Você precisa entrar em uma conta."
        }), 401

    artworks = load_artworks()

    artwork = None

    for item in artworks:
        if has_artwork_id(item, artwork_id):
            artwork = item
            break

    if not artwork:
        return jsonify({
            "error": "Obra não encontrada."
        }), 404

    if artwork.get("user_id") != user["id"]:
        return jsonify({
            "error": "Você só pode editar suas próprias obras."
        }), 403

    title = request.form.get("title", "").strip()
    space = request.form.get("space", "").strip()
    price_text = request.form.get("price", "").strip()

    if not title:
        return jsonify({
            "error": "Informe o título da obra."
        }), 400

    if space not in ["Ethera", "Pixel Dreams"]:
        return jsonify({
            "error": "Escolha um espaço válido."
        }), 400

    try:
        price = float(price_text)
    except (ValueError, TypeError):
        return jsonify({
            "error": "Preço inválido."
        }), 400

    if not math.isfinite(price) or price < 1:
        return jsonify({
            "error": "O preço mínimo é R$ 1,00."
        }), 400

    if price > 1000000:
        return jsonify({
            "error": "O preço máximo é R$ 1.000.000,00."
        }), 400

    artwork["title"] = title
    artwork["space"] = space
    artwork["price"] = price

    image = request.files.get("image")

    if image and image.filename:

        if not allowed_file(image.filename):
            return jsonify({
                "error": "Formato de imagem não permitido."
            }), 400

        old_image = artwork.get("image", "")
        old_filename = Path(old_image).name
        old_path = UPLOAD_FOLDER / old_filename

        if old_path.exists():
            try:
                old_path.unlink()
            except OSError:
                pass

        extension = image.filename.rsplit(".", 1)[1].lower()

        unique_name = (
            f"{uuid.uuid4().hex}.{extension}"
        )

        safe_name = secure_filename(unique_name)

        image_path = UPLOAD_FOLDER / safe_name
        image.save(image_path)

        artwork["image"] = (
            f"/static/uploads/{safe_name}"
        )

    save_artworks(artworks)

    return jsonify(artwork)
# =====================================================
# UPLOADS
# =====================================================

@app.get("/uploads/<filename>")
def uploaded_file(filename):

    return send_from_directory(
        UPLOAD_FOLDER,
        filename
    )


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )