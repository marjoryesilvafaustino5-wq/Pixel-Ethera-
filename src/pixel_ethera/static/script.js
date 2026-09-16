/* =========================================================
   PIXEL ETHERA — SCRIPT PRINCIPAL (INTEGRADO COM FLASK)
   ========================================================= */

// Variáveis globais para controle
let currentUser = null;
let currentProfile = null;
let allArtworks = [];
let activeSpace = "Todos";
let searchQuery = "";
let editingArtworkId = null;
let selectedArtworkId = null;

/* =========================================================
   MODAIS (COMPRA, VENDA, LOGIN, PERFIL)
   ========================================================= */

function openBuyModal(space, title, artist, price, imageUrl, artworkId) {
    const modal = document.getElementById("buy-modal");
    if (!modal) return;
    selectedArtworkId = artworkId;

    document.getElementById("buy-art-space").textContent = space;
    document.getElementById("buy-art-title").textContent = title;
    document.getElementById("buy-art-artist").textContent = artist;
    document.getElementById("buy-art-price").textContent = price;
    document.getElementById("buy-art-summary").textContent = title;
    document.getElementById("buy-art-space-summary").textContent = space;
    
    const imgEl = document.getElementById("buy-art-image");
    if (imgEl && imageUrl) {
        imgEl.src = imageUrl;
    }

    modal.classList.add("active");
}

function closeBuyModal() {
    const modal = document.getElementById("buy-modal");
    if (modal) modal.classList.remove("active");
}

function openSellModal() {
    if (!currentUser) {
        alert("Você precisa entrar em uma conta para publicar uma obra.");
        openLoginModal();
        return;
    }
    const modal = document.getElementById("sell-modal");
    if (modal) modal.classList.add("active");
}

function closeSellModal() {
    const modal = document.getElementById("sell-modal");
    if (modal) modal.classList.remove("active");
}

function openLoginModal() {
    const modal = document.getElementById("login-modal");
    if (modal) modal.classList.add("active");
}

function closeLoginModal() {
    const modal = document.getElementById("login-modal");
    if (modal) modal.classList.remove("active");
}

function updateAuthUI() {
    const authButton = document.getElementById("auth-button");
    if (!authButton) return;

    if (currentUser) {
        authButton.textContent = `Sair (${currentUser.name})`;
        authButton.onclick = logout;
    } else {
        authButton.textContent = "Entrar";
        authButton.onclick = openLoginModal;
    }
}

async function logout() {
    try {
        const response = await fetch("/api/logout", { method: "POST" });
        if (!response.ok) throw new Error("Falha ao sair");
        currentUser = null;
        updateAuthUI();
        alert("Você saiu da sua conta.");
    } catch (error) {
        alert("Não foi possível sair da conta.");
    }
}

function openRegisterModal() {
    const modal = document.getElementById("register-modal");
    if (modal) modal.classList.add("active");
}

function closeRegisterModal() {
    const modal = document.getElementById("register-modal");
    if (modal) modal.classList.remove("active");
}

function openArtistProfile() {
    if (!currentUser) {
        alert("Você precisa entrar ou criar uma conta primeiro.");
        openLoginModal();
        return;
    }
    const modal = document.getElementById("artist-profile-modal");
    if (modal) {
        modal.classList.add("active");
        loadCurrentProfile();
        loadMyArtworks();
    }
}

function closeArtistProfile() {
    const modal = document.getElementById("artist-profile-modal");
    if (modal) modal.classList.remove("active");
}

function closeArtistPage() {
    const artistPage = document.getElementById("artist-page");
    if (artistPage) artistPage.classList.remove("visible");
}

// Fechar modais ao clicar fora ou apertar ESC
document.addEventListener("click", function (event) {
    if (event.target.classList.contains("modal-overlay")) {
        event.target.classList.remove("active");
    }
});

document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
        document.querySelectorAll(".modal-overlay").forEach(m => m.classList.remove("active"));
        closeArtistPage();
    }
});

/* =========================================================
   COMUNICAÇÃO COM O SERVIDOR FLASK (API)
   ========================================================= */

// Verificar usuário logado ao carregar a página
async function checkAuth() {
    try {
        const response = await fetch("/api/me");
        const data = await response.json();
        if (data.logged_in) {
            currentUser = data;
        }
        updateAuthUI();
    } catch (error) {
        console.error("Erro ao verificar autenticação:", error);
    }
}

async function loadCurrentProfile() {
    try {
        const response = await fetch("/api/profile");
        const profile = await response.json();
        const nameInput = document.getElementById("artist-profile-name");
        const bioInput = document.getElementById("artist-profile-bio");
        const spaceInput = document.getElementById("artist-profile-space");

        if (nameInput) nameInput.value = profile.name || currentUser.name || "";
        if (bioInput) bioInput.value = profile.bio || "";
        if (spaceInput) spaceInput.value = profile.space || "";
    } catch (error) {
        console.error("Erro ao carregar perfil:", error);
    }
    loadConnectStatus();
}

async function loadConnectStatus() {
    const status = document.getElementById("connect-status");
    const button = document.getElementById("connect-button");
    if (!status || !button) return;
    try {
        const response = await fetch("/api/mercadopago/status");
        const data = await response.json();
        if (data.ready) {
            status.textContent = "Recebimentos configurados: você recebe 95% de cada venda.";
            button.textContent = "Atualizar dados de recebimento";
        } else {
            status.textContent = "Configure sua conta para receber 95% de cada venda.";
        }
    } catch (error) {
        status.textContent = "Não foi possível verificar o status dos recebimentos.";
    }
}

async function startConnectOnboarding() {
    const button = document.getElementById("connect-button");
    if (button) {
        button.disabled = true;
        button.textContent = "Abrindo cadastro...";
    }
    try {
        const response = await fetch("/api/mercadopago/connect", { method: "POST" });
        const data = await response.json();
        if (!response.ok) {
            alert(data.error || "Não foi possível configurar os recebimentos.");
            return;
        }
        window.location.assign(data.url);
    } catch (error) {
        alert("Erro de conexão ao configurar os recebimentos.");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Configurar recebimentos";
        }
    }
}

// Carregar obras do servidor
async function loadArtworksFromServer() {
    const gallery = document.getElementById("gallery-grid");
    if (gallery) gallery.textContent = "Carregando obras...";

    try {
        const response = await fetch("/api/artworks");
        const data = await response.json();
        if (!response.ok || !Array.isArray(data)) {
            throw new Error("Resposta inválida da galeria");
        }
        allArtworks = data;
        applyGalleryFilters();
    } catch (error) {
        console.error("Erro ao carregar obras:", error);
        if (gallery) {
            gallery.textContent = "Não foi possível carregar as obras.";
            const retry = document.createElement("button");
            retry.type = "button";
            retry.className = "secondary-button";
            retry.textContent = "Tentar novamente";
            retry.addEventListener("click", loadArtworksFromServer);
            gallery.appendChild(retry);
        }
    }
}

async function loadMyArtworks() {
    const list = document.getElementById("my-artworks-list");
    if (!list || !currentUser) return;

    try {
        const response = await fetch("/api/my-artworks");
        const artworks = await response.json();
        list.innerHTML = "";

        if (!response.ok || artworks.length === 0) {
            const message = document.createElement("p");
            message.className = "empty-gallery";
            message.textContent = response.ok ? "Você ainda não publicou obras." : (artworks.error || "Não foi possível carregar suas obras.");
            list.appendChild(message);
            return;
        }

        artworks.forEach(function (artwork) {
            const item = document.createElement("div");
            item.className = "my-artwork-item";

            const info = document.createElement("div");
            const title = document.createElement("strong");
            title.textContent = artwork.title;
            const details = document.createElement("span");
            details.textContent = `${artwork.space} - R$ ${Number(artwork.price).toFixed(2).replace(".", ",")}`;
            info.append(title, details);

            const actions = document.createElement("div");
            actions.className = "my-artwork-actions";

            const editButton = document.createElement("button");
            editButton.type = "button";
            editButton.className = "text-button";
            editButton.textContent = "Editar";
            editButton.addEventListener("click", () => startArtworkEdit(artwork));

            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "text-button danger-button";
            deleteButton.textContent = "Excluir";
            deleteButton.addEventListener("click", () => deleteArtwork(artwork.id));

            actions.append(editButton, deleteButton);
            item.append(info, actions);
            list.appendChild(item);
        });
    } catch (error) {
        list.textContent = "Não foi possível carregar suas obras.";
    }
}

function startArtworkEdit(artwork) {
    const form = document.getElementById("sell-form");
    const title = document.getElementById("title");
    const space = document.getElementById("space");
    const price = document.getElementById("price");
    const image = document.getElementById("image");
    const submitButton = form && form.querySelector("button[type=submit]");
    const cancelButton = document.getElementById("cancel-edit-button");

    if (!form || !title || !space || !price || !image || !submitButton) return;
    editingArtworkId = artwork.id;
    title.value = artwork.title || "";
    space.value = artwork.space || "";
    price.value = artwork.price || "";
    image.required = false;
    submitButton.textContent = "Salvar alterações";
    if (cancelButton) cancelButton.hidden = false;
    closeArtistProfile();
    openSellModal();
}

function cancelArtworkEdit() {
    editingArtworkId = null;
    const form = document.getElementById("sell-form");
    const image = document.getElementById("image");
    const submitButton = form && form.querySelector("button[type=submit]");
    const cancelButton = document.getElementById("cancel-edit-button");
    if (form) form.reset();
    if (image) image.required = true;
    if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
    imagePreviewUrl = null;
    const preview = document.getElementById("image-preview");
    if (preview) {
        preview.hidden = true;
        preview.removeAttribute("src");
    }
    if (submitButton) submitButton.textContent = "Publicar obra";
    if (cancelButton) cancelButton.hidden = true;
}

async function deleteArtwork(artworkId) {
    if (!window.confirm("Excluir esta obra permanentemente?")) return;

    try {
        const response = await fetch(`/api/artworks/${artworkId}`, { method: "DELETE" });
        const result = await response.json();
        if (!response.ok) {
            alert(result.error || "Não foi possível excluir a obra.");
            return;
        }
        await loadArtworksFromServer();
        await loadMyArtworks();
    } catch (error) {
        alert("Erro de conexão ao excluir a obra.");
    }
}

// Renderizar obras na galeria e destaques
function createArtworkCard(artwork, showPurchaseButton) {
    const card = document.createElement("article");
    card.className = "art-card";
    card.dataset.space = artwork.space || "";

    const imageWrapper = document.createElement("div");
    imageWrapper.className = "art-card-image";

    const image = document.createElement("img");
    image.src = artwork.image || "";
    image.alt = artwork.title || "Obra digital";
    imageWrapper.appendChild(image);

    const content = document.createElement("div");
    content.className = "art-card-content";

    const space = document.createElement("span");
    space.className = "art-card-space";
    space.textContent = artwork.space || "Sem espaço";

    const title = document.createElement("h3");
    title.textContent = artwork.title || "Obra sem título";

    const artist = document.createElement("button");
    artist.type = "button";
    artist.className = "artist-name-button";
    artist.textContent = `por ${artwork.artist || "Artista desconhecido"}`;
    artist.addEventListener("click", function () {
        viewArtistProfile(artwork.artist || "Artista desconhecido");
    });

    const price = document.createElement("div");
    price.className = "art-card-price";
    price.textContent = `R$ ${Number(artwork.price || 0).toFixed(2).replace(".", ",")}`;

    content.append(space, title, artist, price);

    if (showPurchaseButton) {
        const purchase = document.createElement("button");
        purchase.type = "button";
        purchase.className = "primary-button";
        purchase.textContent = "Comprar";
        purchase.addEventListener("click", function () {
            openBuyModal(
                artwork.space,
                artwork.title,
                artwork.artist,
                `R$ ${Number(artwork.price || 0).toFixed(2).replace(".", ",")}`,
                artwork.image,
                artwork.id
            );
        });
        content.appendChild(purchase);
    }

    card.append(imageWrapper, content);
    return card;
}

function renderArtworks(artworksToRender) {
    const gallery = document.getElementById("gallery-grid");
    const featured = document.getElementById("featured-artworks");

    if (gallery) gallery.innerHTML = "";
    if (featured) featured.innerHTML = "";

    if (!artworksToRender || artworksToRender.length === 0) {
        const emptyMessage = searchQuery || activeSpace !== "Todos"
            ? "Nenhuma obra encontrada para estes filtros."
            : "Ainda não há obras publicadas.";
        if (gallery) {
            const message = document.createElement("p");
            message.className = "empty-gallery";
            message.textContent = emptyMessage;
            gallery.appendChild(message);
        }
        if (featured) {
            const message = document.createElement("p");
            message.className = "empty-gallery";
            message.textContent = "Ainda não há obras em destaque.";
            featured.appendChild(message);
        }
        return;
    }

    artworksToRender.forEach(function (artwork) {
        if (gallery) gallery.appendChild(createArtworkCard(artwork, true));
    });

    // Preencher Destaques (últimas 3 obras)
    if (featured) {
        const featuredList = [...artworksToRender].reverse().slice(0, 3);
        featuredList.forEach(function (artwork) {
            featured.appendChild(createArtworkCard(artwork, false));
        });
    }
}

/* =========================================================
   FILTROS DA GALERIA
   ========================================================= */

function filterSpace(space) {
    activeSpace = space;
    const filters = document.querySelectorAll(".filter-button");

    filters.forEach(function (filter) {
        if (filter.textContent.trim() === space || (space === "Todos" && filter.textContent.trim() === "Todas")) {
            filter.classList.add("active");
        } else {
            filter.classList.remove("active");
        }
    });

    applyGalleryFilters();
}

function applyGalleryFilters() {
    const filtered = allArtworks.filter(function (artwork) {
        const matchesSpace = activeSpace === "Todos" || artwork.space === activeSpace;
        const text = [artwork.title, artwork.artist, artwork.space]
            .map(value => String(value || "").toLowerCase())
            .join(" ");
        return matchesSpace && text.includes(searchQuery);
    });
    renderArtworks(filtered);
}

const artworkSearch = document.getElementById("artwork-search");
if (artworkSearch) {
    artworkSearch.addEventListener("input", function (event) {
        searchQuery = event.target.value.trim().toLowerCase();
        applyGalleryFilters();
    });
}

/* =========================================================
   FORMULÁRIOS (LOGIN, PUBLICAÇÃO, PERFIL)
   ========================================================= */

// Envio do formulário de Publicação
const sellForm = document.getElementById("sell-form");
if (sellForm) {
    sellForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const formData = new FormData(sellForm);
        const submitButton = sellForm.querySelector("button[type=submit]");
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.textContent = "Publicando...";
        }

        try {
            const endpoint = editingArtworkId
                ? `/api/artworks/${editingArtworkId}`
                : "/api/artworks";
            const response = await fetch(endpoint, {
                method: editingArtworkId ? "PUT" : "POST",
                body: formData
            });
            const result = await response.json();

            if (response.ok) {
                alert(`A obra "${result.title}" foi publicada com sucesso!`);
                sellForm.reset();
                cancelArtworkEdit();
                closeSellModal();
                await loadArtworksFromServer();
                await loadMyArtworks();
            } else {
                alert(result.error || "Erro ao publicar obra.");
            }
        } catch (error) {
            alert("Erro de conexão ao publicar obra.");
        } finally {
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.textContent = "Publicar obra";
            }
        }
    });
}

const imageInput = document.getElementById("image");
const imagePreview = document.getElementById("image-preview");
let imagePreviewUrl = null;
if (imageInput && imagePreview) {
    imageInput.addEventListener("change", function () {
        if (imagePreviewUrl) URL.revokeObjectURL(imagePreviewUrl);
        const [file] = imageInput.files;
        if (!file) {
            imagePreview.hidden = true;
            imagePreview.removeAttribute("src");
            return;
        }
        const allowedTypes = ["image/png", "image/jpeg", "image/gif", "image/webp"];
        if (!allowedTypes.includes(file.type) || file.size > 15 * 1024 * 1024) {
            imageInput.value = "";
            imagePreview.hidden = true;
            imagePreview.removeAttribute("src");
            alert("Escolha uma imagem PNG, JPG, GIF ou WEBP de até 15 MB.");
            return;
        }
        imagePreviewUrl = URL.createObjectURL(file);
        imagePreview.src = imagePreviewUrl;
        imagePreview.hidden = false;
    });
}

const cancelEditButton = document.getElementById("cancel-edit-button");
if (cancelEditButton) cancelEditButton.addEventListener("click", cancelArtworkEdit);

const connectButton = document.getElementById("connect-button");
if (connectButton) connectButton.addEventListener("click", startConnectOnboarding);

// Envio do formulário de Login
const loginForm = document.getElementById("login-form");
if (loginForm) {
    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const formData = new FormData(loginForm);

        try {
            const response = await fetch("/api/login", {
                method: "POST",
                body: formData
            });
            const result = await response.json();

            if (response.ok) {
                currentUser = result;
                updateAuthUI();
                alert(`Bem-vinda de volta, ${result.name}!`);
                closeLoginModal();
            } else {
                alert(result.error || "E-mail ou senha incorretos.");
            }
        } catch (error) {
            alert("Erro ao fazer login.");
        }
    });
}

const registerForm = document.getElementById("register-form");
if (registerForm) {
    registerForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const formData = new FormData(registerForm);

        try {
            const response = await fetch("/api/register", {
                method: "POST",
                body: formData
            });
            const result = await response.json();

            if (response.ok) {
                currentUser = result;
                updateAuthUI();
                registerForm.reset();
                closeRegisterModal();
                alert(`Conta criada com sucesso, ${result.name}!`);
            } else {
                alert(result.error || "Erro ao criar conta.");
            }
        } catch (error) {
            alert("Erro de conexão ao criar conta.");
        }
    });
}

// Envio do formulário de Perfil
const profileForm = document.getElementById("artist-profile-form");
if (profileForm) {
    profileForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        const formData = new FormData(profileForm);

        try {
            const response = await fetch("/api/profile", {
                method: "POST",
                body: formData
            });
            const result = await response.json();

            if (response.ok) {
                alert("Perfil salvo com sucesso!");
                currentUser.name = result.name;
                closeArtistProfile();
            } else {
                alert(result.error || "Erro ao salvar perfil.");
            }
        } catch (error) {
            alert("Erro ao salvar perfil.");
        }
    });
}

// Simulação de compra
async function confirmPurchase() {
    if (!currentUser) {
        closeBuyModal();
        openLoginModal();
        return;
    }
    if (!selectedArtworkId) {
        alert("Não foi possível identificar esta obra.");
        return;
    }

    const button = document.querySelector(".purchase-button");
    if (button) {
        button.disabled = true;
        button.textContent = "Registrando pedido...";
    }
    try {
        const response = await fetch("/api/purchases", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ artwork_id: selectedArtworkId })
        });
        const result = await response.json();
        if (!response.ok) {
            alert(result.error || "Não foi possível iniciar a compra.");
            return;
        }
        if (!result.checkout_url) {
            alert("O checkout não está disponível no momento.");
            return;
        }
        window.location.assign(result.checkout_url);
    } catch (error) {
        alert("Erro de conexão ao iniciar a compra.");
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = "Continuar para confirmação";
        }
    }
}

// Visualizar página do artista
function viewArtistProfile(artistName) {
    const artistPage = document.getElementById("artist-page");
    const nameEl = document.getElementById("artist-page-name");
    const worksContainer = document.getElementById("artist-page-works");

    if (nameEl) nameEl.textContent = artistName;

    const artistWorks = allArtworks.filter(art => art.artist === artistName);
    if (worksContainer) {
        worksContainer.innerHTML = "";
        artistWorks.forEach(artwork => {
            worksContainer.appendChild(createArtworkCard(artwork, false));
        });
    }

    if (artistPage) {
        artistPage.classList.add("visible");
        artistPage.scrollIntoView({ behavior: "smooth" });
    }
}

/* =========================================================
   INICIALIZAÇÃO
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {
    checkAuth();
    loadArtworksFromServer();
});