# Integrações externas

Todas as chaves ficam **só no backend** (`api/.env`). O frontend tem uma única variável (`VITE_API_URL`).
Sem as variáveis preenchidas, cada integração funciona em modo "desligado" ou simulado, e o sistema roda inteiro localmente.

| Integração | Sem configurar | Variáveis |
|---|---|---|
| Login com Google | Botão não aparece | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` |
| E-mail (SMTP) | Mailpit local (ou só log) | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS` |
| Gateway de pagamento | Gateway `fake` (simulador) | `PAYMENT_GATEWAY`, `PAYMENT_API_KEY`, `PAYMENT_WEBHOOK_SECRET`, `PAYMENT_ENV` |
| Armazenamento de fotos | Disco local (`api/media`) | `STORAGE_ENDPOINT`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_PUBLIC_URL` |
| Geocodificação | Photon/Nominatim (grátis, sem chave) | `GEOCODING_PROVIDER`, `GEOCODING_USER_AGENT` |
| Mapa (tiles) | OpenFreeMap (grátis, sem chave) | — (no frontend, em `src/components/MapView.tsx`) |
| Erros | Só log | `SENTRY_DSN` |

Depois de mudar o `.env`, reinicie a API e o worker.

---

## 1. Ligar o login (`AUTH_ENABLED`)

Hoje o login está **desligado** (`AUTH_ENABLED=false`): o site mostra uma barra amarela para escolher o papel (turista, operadora, admin) e a API usa usuários de desenvolvimento.

Para ligar:
1. Configure o SMTP (seção 3) e, se quiser, o Google (seção 2).
2. Em `api/.env`: `AUTH_ENABLED=true`.
3. Garanta um admin real: `ADMIN_EMAIL=seu@email.com` e rode `make seed` (cria o usuário admin; o login é pelo código enviado a esse e-mail).
4. Reinicie API e worker.

Com o login ligado, os headers de desenvolvimento são ignorados e os usuários de desenvolvimento não conseguem entrar.
A API **se recusa a subir** com `APP_ENV=production` e `AUTH_ENABLED=false`.

Como funciona a sessão: o access token (15 min) fica em memória no navegador; o refresh token fica num cookie `httpOnly` e é trocado a cada uso (reutilizar um token antigo revoga todas as sessões daquela família). O refresh exige o header `X-CSRF-Token` igual ao cookie `tur_csrf`.

## 2. Login com Google

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/) e crie (ou escolha) um projeto.
2. **APIs e serviços → Tela de consentimento OAuth**: tipo "Externo", nome do app, e-mail de suporte, domínio. Escopos: `openid`, `email`, `profile`.
3. **Credenciais → Criar credenciais → ID do cliente OAuth → Aplicativo da Web**.
   - **URIs de redirecionamento autorizados**: `http://localhost:8000/api/v1/auth/google/callback` (desenvolvimento) e `https://api.SEU-DOMINIO/api/v1/auth/google/callback` (produção).
   - Origens JavaScript não são necessárias (o fluxo é todo no backend).
4. Copie o ID e a chave secreta para `api/.env`:
   ```
   GOOGLE_CLIENT_ID=...apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=...
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/google/callback
   ```
5. `FRONTEND_URL` precisa conter a URL do site: depois do login a API redireciona para `FRONTEND_URL/auth/callback`.

Teste: com `AUTH_ENABLED=true`, abra `/pt/entrar` e clique em "Continuar com Google".

**Quando houver app iOS (fase 2):** a Apple exige "Entrar com Apple" se o app oferecer login com Google.

## 3. E-mail (SMTP)

Qualquer provedor SMTP serve (Amazon SES, Resend, Brevo, Postmark, Google Workspace…).

```
SMTP_HOST=smtp.provedor.com
SMTP_PORT=587
SMTP_USER=usuario
SMTP_PASSWORD=senha-ou-api-key
SMTP_FROM=Nome da Plataforma <reservas@seu-dominio.com>
SMTP_TLS=true
```

- Configure SPF, DKIM e DMARC do domínio no provedor (senão os e-mails caem no spam).
- Desenvolvimento: o `docker compose` sobe o **Mailpit**; tudo que a API envia aparece em http://localhost:8026.
- Os e-mails são enviados pelo **worker** (fila no Redis). Sem o worker rodando, ficam na fila.

E-mails enviados hoje: código de login, reserva confirmada (com voucher PDF), cancelamento/reembolso, lembrete na véspera, nova reserva para a operadora, convite de operadora.

## 4. Gateway de pagamento

O sistema usa uma interface única (`api/app/services/payments.py`, classe `PaymentGateway`) com 3 operações:

| Método | O que faz |
|---|---|
| `create_charge(...)` | Cria a cobrança (Pix ou cartão) e devolve id, QR Pix ou URL do checkout |
| `refund(charge_id, amount_cents)` | Estorno total ou parcial |
| `parse_webhook(headers, body)` | Valida a assinatura e normaliza o evento (`payment.approved`, `payment.failed`, `chargeback`) |

Hoje existe só o `FakeGateway` (desenvolvimento). Para integrar um gateway real:

1. **Escolha e teste antes** (ver `plano/gargalos.md`, G3 e G7): Pix, cartões do Chile/Argentina, contas de marketplace (split/subcontas), retenção do valor até o passeio, estorno, taxas. Candidatos: Pagar.me, Mercado Pago, Asaas, Iugu, Stripe Connect.
2. Crie `class MeuGateway(PaymentGateway)` em `payments.py` implementando os 3 métodos e registre em `_GATEWAYS = {"fake": FakeGateway, "meugateway": MeuGateway}`.
3. `api/.env`:
   ```
   PAYMENT_GATEWAY=meugateway
   PAYMENT_API_KEY=...
   PAYMENT_WEBHOOK_SECRET=...
   PAYMENT_ENV=sandbox
   ```
4. Cadastre no painel do gateway a URL de webhook: `https://api.SEU-DOMINIO/api/v1/webhooks/payments/meugateway`.
5. Se o gateway usar checkout hospedado para cartão, devolva `checkout_url` em `create_charge`: o site redireciona o turista automaticamente.
6. Repasses: hoje o admin gera os repasses e marca como pagos (`/admin/repasses`). Se o gateway fizer split/transferência, guarde o id do recebedor de cada operadora em `operators.gateway_recipient_id` (campo já existe, editável no admin) e chame a transferência em `payout_service.mark_paid`.

Regras já prontas: chave de idempotência por cobrança, webhook idempotente (`webhook_events.event_id`), pagamento que chega depois da retenção expirar (confirma se houver vaga; senão reembolsa sozinho), reembolsos por política, clima e operadora.

O simulador (`POST /api/v1/dev/payments/{charge_id}/simulate`) só existe com `PAYMENT_GATEWAY=fake` e fora de produção. A API não sobe em produção com `PAYMENT_GATEWAY=fake`.

## 5. Armazenamento de fotos (S3 / Cloudflare R2)

Sem configuração, as fotos ficam em `api/media` e a API serve em `/media` (só para desenvolvimento).

Para produção, qualquer serviço compatível com S3:
```
STORAGE_ENDPOINT=https://<conta>.r2.cloudflarestorage.com   # vazio para AWS S3
STORAGE_BUCKET=tur-fotos
STORAGE_ACCESS_KEY=...
STORAGE_SECRET_KEY=...
STORAGE_PUBLIC_URL=https://fotos.seu-dominio.com             # domínio público do bucket
```
Toda foto enviada é validada pelo conteúdo, convertida para JPEG, redimensionada (máx. 1920 px) e tem os metadados (EXIF/GPS) removidos.

## 6. Mapa e geocodificação (gratuitos)

- **Tiles:** MapLibre GL JS + [OpenFreeMap](https://openfreemap.org) (sem cadastro, sem chave, mantido por doações, sem garantia de disponibilidade). Para trocar, mude `STYLE` em `web/src/components/MapView.tsx` (ex.: Protomaps hospedado no seu bucket, MapTiler ou Mapbox).
- **Busca de endereço:** feita pelo backend (`/api/v1/geocode`), com [Photon](https://photon.komoot.io) e fallback no [Nominatim](https://nominatim.org) (limite de 1 requisição/s, respeitado por uma trava no Redis). Resultados ficam 1 dia em cache. `GEOCODING_USER_AGENT` deve ter um contato real (exigência do Nominatim).
- "Perto de mim" usa a localização do navegador; a distância é calculada no PostGIS.

## 7. Sentry (erros)

Crie um projeto Python em [sentry.io](https://sentry.io) e preencha `SENTRY_DSN`. Sem a variável, os erros vão só para o log.

## 8. Analytics (funil do turista)

O admin mostra números calculados no banco (reservas, GMV, comissão, conversão retenção→pagamento). O funil completo (visita → busca → passeio → checkout) fica para o PostHog: crie o projeto em [posthog.com](https://posthog.com) e adicione o snippet em `web/src/root.tsx` (ainda não feito, ver `docs/decisoes-tecnicas.md`).

## 9. Produção: checklist

- `APP_ENV=production`, `AUTH_ENABLED=true`, gateway real, `SECRET_KEY` aleatório (≥ 32 bytes).
- `FRONTEND_URL`, `API_PUBLIC_URL` e `ALLOWED_HOSTS` com os domínios reais.
- HTTPS na frente da API e do site (os cookies ficam `Secure` em produção).
- Banco com backup diário; Redis com persistência.
- API, worker (Celery com `--beat` em **uma** instância só) e site (`npm run start`).
- `alembic upgrade head` a cada deploy.
