# Pixel-Ethera-
Marketplace de artes digitais para artistas e colecionadores.

## Pagamentos

O checkout usa Mercado Pago com OAuth para conectar o artista. O artista precisa
concluir a conexão da conta no perfil antes de vender. Em cada venda, 95% são
destinados ao artista e 5% ficam com o Pixel Ethera.

A publicação também exige uma conta Mercado Pago conectada, para que nenhuma
obra seja anunciada sem um destino válido para o repasse. Em produção, a URL de
webhook precisa ser pública e usar HTTPS.

Instale as dependências e configure a chave secreta no mesmo ambiente Python
usado para executar o Flask:

```bash
python -m pip install -r requirements.txt
export MP_CLIENT_ID="seu_client_id"
export MP_CLIENT_SECRET="seu_client_secret"
export MP_REDIRECT_URI="http://localhost:5000/oauth/mercadopago/callback"
export MP_WEBHOOK_SECRET="segredo_do_webhook"
python -m src.pixel_ethera.app
```

Sem essas variáveis, a conexão e a compra são bloqueadas com uma mensagem de
configuração, sem criar pedido falso. Configure também a URL de webhook
`/webhooks/mercadopago` no painel do Mercado Pago.
