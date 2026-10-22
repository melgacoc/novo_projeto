# Tasks — MVP

**Atualizado em:** 2026-10-18 · **Spec:** [spec.md](spec.md) · **Riscos:** [plano/gargalos.md](plano/gargalos.md)

Cada tarefa indica a seção do spec que implementa (ex.: §4.4). Marque `[x]` ao concluir e atualize este arquivo a cada entrega.

**Estado em 2026-10-18:** MVP desenvolvido (Fases 1 a 5) com login desligado e gateway simulado. `[x]` = feito · `[~]` = parcial · `[ ]` = pendente. Decisões tomadas no desenvolvimento: [docs/decisoes-tecnicas.md](docs/decisoes-tecnicas.md).

**Estimativa (1 dev, tempo integral):** 13-16 semanas no plano original (a Fase 1 cresceu com segurança e integrações desde o início); a revisão crítica aponta **22-30 semanas** como mais provável (G4). As fases abaixo seguem a ordem de dependência.

---

## Fase 0 — Decisões e pré-requisitos (em paralelo, com o sócio)
Bloqueia a Fase 4 (pagamentos).

- [ ] Consulta com contador: tributação sobre comissão vs. GMV, NFS-e, estrutura jurídica (G3)
- [ ] Prova técnica com 2 gateways: Pix, cartão chileno e argentino, contas de marketplace/split, retenção, estorno, repasse (G7)
- [ ] Escolher gateway e definir `payout_delay_days` (§6 RN11)
- [ ] Definir a política de cancelamento final e quem absorve as taxas (§6 RN06, G2)
- [ ] Decidir taxa de serviço ao turista (G2)
- [ ] Verificar CNPJ/CPF e Cadastur das operadoras iniciais (G7)
- [ ] Contrato com operadoras: comissão de 10%, paridade de preço, regras contra desvio (§6 RN10)
- [ ] Juntar conteúdo dos primeiros passeios: fotos, textos, preços por faixa etária e temporada, horários, capacidade, ponto de encontro
- [ ] Criar as contas das integrações (Google, SMTP, gateway, armazenamento, Sentry) seguindo `docs/integracoes.md`
- [ ] Nome e domínio da plataforma

---

## Princípios de escalabilidade (desde o início)
Aplicar desde a Fase 1 o que é barato agora e caro de mudar depois. **Não** fazer agora: microsserviços, Kubernetes, réplicas de leitura, mensageria pesada.

- **API sem estado:** nenhuma sessão ou arquivo em memória/disco local; permite rodar várias instâncias atrás de um balanceador.
- **Estado compartilhado no Redis:** rate limit, retenções de curta duração, cache, fila.
- **Trabalho pesado fora da requisição:** e-mails, PDFs, reembolsos em massa e webhooks vão para o worker.
- **Banco:** índices nas consultas de busca e agenda, paginação em toda listagem, pool de conexões configurável, migrations versionadas.
- **Concorrência e idempotência:** retenção atômica de vagas, chaves de idempotência em pagamentos e webhooks.
- **Arquivos em armazenamento de objetos** (S3/R2), nunca no disco do servidor.
- **Observabilidade:** logs estruturados com `request_id`, health checks (`/health`, `/ready`), Sentry.
- **Configuração só por variáveis de ambiente** (12-factor).

---

## Fase 1 — Fundação (≈ 2-3 semanas)
Reaproveitar a **configuração de fundação** do Rio Manager (`../grupo_rio/manager/`), **sem trazer código de domínio** (passeios, reservas, boate etc.).

### Estrutura e ambiente
- [x] Repositório com `api/` (backend) e `web/` (frontend), `docs/` e `docker-compose.yml` na raiz
- [x] Docker Compose com **Postgres + PostGIS** (`postgis/postgis`), **Redis** e **Mailpit** (SMTP de teste com interface web), volumes persistentes e health checks
- [x] `.env.example` do backend e do frontend; `.env` no `.gitignore`
- [x] `Makefile` ou scripts: subir bancos, migrar, rodar API, worker e web, rodar testes
- [x] README com o passo a passo local

### Backend: base (a partir da fundação do Rio Manager)
- [x] Estrutura de pastas igual à do Rio Manager: `app/api/v1/endpoints`, `app/core`, `app/models`, `app/repositories`, `app/schemas`, `app/services`, `tests/` _(sem `repositories`: ver docs/decisoes-tecnicas.md D6)_
- [x] `requirements.txt` com a base do Rio Manager (FastAPI, Uvicorn, SQLAlchemy 2, Alembic, psycopg, Pydantic, PyJWT, python-dotenv, python-multipart, phonenumbers, pytest, httpx) + `redis`, `celery`, `geoalchemy2`, `pydantic-settings`, `sentry-sdk`, `authlib` (Google OAuth)
- [x] Configuração central com `pydantic-settings` (falha ao subir se faltar variável obrigatória)
- [x] Banco: engine com pool configurável, `get_db`, Alembic, migration inicial com extensão PostGIS
- [x] Padrão de erros `{ error: { code, message } }` e handler que nunca expõe stack trace em produção (§7)
- [x] Paginação e filtros padrão (reaproveitar `core/pagination.py` e `core/filtering.py` como referência)
- [x] Auditoria (`audit_logs`) a partir de `core/audit.py` do Rio Manager (§4.6)
- [x] `settings` da plataforma com comissão padrão de 10% e prazos (§4.6)
- [x] Worker Celery + Celery Beat ligado ao Redis; tarefa de exemplo e teste
- [x] Logs estruturados (JSON) com `request_id`
- [x] `/health` (vivo) e `/ready` (banco e Redis respondendo)
- [x] Sentry (ativo só se `SENTRY_DSN` estiver definido)

### Backend: autenticação e autorização (§3, §4.1, §7.2)
- [x] Modelos `users`, `email_login_codes`, `refresh_tokens`
- [x] Login com Google pelo fluxo *authorization code* no backend (`/auth/google/start` e `/auth/google/callback`, `state` anti-CSRF)
- [x] Login com código de 6 dígitos por e-mail (hash do código, validade de 10 min, máximo de tentativas)
- [x] Access token JWT curto (≈ 15 min) + refresh token rotativo em cookie `httpOnly`, `Secure`, `SameSite=Lax`; detecção de reuso de refresh (revoga a família)
- [x] Proteção CSRF na rota de refresh (double submit token)
- [x] Logout e "sair de todos os dispositivos"
- [x] `GET/PATCH /me` (nome, telefone E.164 com `phonenumbers`, idioma)
- [x] **Roles** (`tourist`, `operator`, `admin`) com dependências reutilizáveis: `require_user`, `require_role(...)`, `require_operator_member(operator_id)` (escopo por operadora)
- [x] Seed do primeiro admin por variável de ambiente
- [x] **Chave `AUTH_ENABLED` (padrão `false`)**: com o login desligado, dependência de usuário resolve um **usuário de desenvolvimento** pelo header `X-Dev-User-Role` (e `X-Dev-Operator-Id`); seed cria um usuário fixo por papel e uma operadora de teste
- [x] Guardas do modo sem login: API não sobe com `APP_ENV=production` e `AUTH_ENABLED=false`; aviso em log em toda requisição nesse modo
- [x] Testes rodando nos dois modos (login ligado e desligado), garantindo que a autorização por papel e por operadora vale igual
- [x] Testes de autorização: cada role acessa só o que deve; operadora não vê dados de outra

### Backend: middlewares e segurança
- [x] CORS restrito às origens do `FRONTEND_URL` (padrão do `main.py` do Rio Manager)
- [x] Middleware de autenticação por token (base: `core/auth_middleware.py`), com lista de rotas públicas _(feito como dependência FastAPI em `core/deps.py`, mais simples que middleware)_
- [x] **Rate limit no Redis** por IP e por usuário, com limites diferentes por grupo de rota (login/código, criação de reserva, busca pública, webhooks) e resposta `429` com `Retry-After`
- [x] Headers de segurança (HSTS, `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, CSP da API)
- [x] `TrustedHostMiddleware` e limite de tamanho do corpo da requisição
- [x] Validação de entrada com Pydantic em todas as rotas; sem SQL montado à mão
- [x] Hash de códigos e tokens; segredos só em variáveis de ambiente
- [x] Validação de uploads (tipo, tamanho) e URLs pré-assinadas com expiração curta _(upload pela API com reprocessamento da imagem em vez de URL pré-assinada)_
- [x] Verificação de dependências vulneráveis no CI (`pip-audit`, `npm audit`) _(só relatório, não bloqueia)_

### Integrações externas: só configuração + documentação
Todas as chaves ficam **apenas no backend**. Deixar as variáveis no `.env.example` e um cliente/adaptador com interface definida, funcionando em modo "desligado" ou fake quando a variável estiver vazia.
- [x] **Google OAuth:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`
- [x] **SMTP:** `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS` (Mailpit no ambiente local)
- [x] **Gateway de pagamento:** `PAYMENT_GATEWAY`, `PAYMENT_API_KEY`, `PAYMENT_WEBHOOK_SECRET`, `PAYMENT_ENV` (sandbox/produção); interface `PaymentGateway` (cobrar Pix, cobrar cartão, reembolsar, consultar, validar webhook) com implementação fake para desenvolvimento
- [x] **Armazenamento de arquivos:** `STORAGE_ENDPOINT`, `STORAGE_BUCKET`, `STORAGE_ACCESS_KEY`, `STORAGE_SECRET_KEY`, `STORAGE_PUBLIC_URL`
- [x] **Mapa (gratuito):** MapLibre GL JS + tiles OpenFreeMap (sem chave) no frontend; geocodificação no backend via Photon com fallback Nominatim (sem chave, com cache no Redis e limite de 1 req/s); `GEOCODING_PROVIDER` permite trocar no futuro
- [x] **Sentry:** `SENTRY_DSN`
- [x] **`docs/integracoes.md`:** para cada integração, onde criar a conta, como gerar as chaves, quais URLs de callback/webhook cadastrar, quais variáveis preencher e como testar localmente

### Frontend: base (a partir da fundação do Rio Manager)
- [x] Projeto **React Router v7 em modo framework** (Vite + React + TypeScript), copiando de `centralization-front`: `vite.config.ts` (alias `@/`, plugin Tailwind), `tsconfig*.json`, `eslint.config.js`, `components.json` (shadcn, estilo new-york, lucide), `index.css` (tema e variáveis), `lib/utils.ts`
- [~] Mesmas bibliotecas base: React Router, TanStack Query, React Hook Form + Zod, i18next, date-fns, lucide, shadcn/ui _(React Hook Form, Zod e i18next não foram usados: formulários simples e dicionário próprio de traduções, ver D5)_
- [x] Componentes shadcn base (button, input, form, dialog, select, card, table, badge, skeleton, dropdown, popover, label)
- [x] Cliente da API a partir de `lib/api.ts` do Rio Manager, adaptado: access token em memória, refresh por cookie `httpOnly` com `credentials: 'include'`, renovação única para requisições simultâneas
- [x] `AuthContext` e `useCurrentUser` a partir do Rio Manager; guards de rota por role (turista, operadora, admin)
- [x] i18n com **PT/ES/EN** (detecção pelo navegador, troca manual, prefixo de idioma nas rotas públicas)
- [x] Layouts: público (turista), painel da operadora, admin (base: `AdminLayout`/`SidebarNav`)
- [x] **SSR nas rotas públicas** (`/{locale}/...`) com dados carregados no servidor e hidratados no TanStack Query; `/painel` e `/admin` só no navegador
- [x] Repasse de cookies do servidor Node para a API nas rotas públicas que precisarem do usuário logado _(não necessário: as rotas com SSR são públicas)_
- [x] Padrão para componentes só de navegador (carregamento apenas no cliente)
- [x] Servidor Node do frontend no Docker/deploy
- [x] Telas de login (botão Google → redireciona para a API; código por e-mail) e perfil (prontas, mas escondidas enquanto o login estiver desligado)
- [x] **Seletor de papel de desenvolvimento** (turista/operadora/admin) visível só quando a API informa `auth_enabled=false` (`GET /config` público); envia os headers `X-Dev-*`
- [x] Tema claro/escuro (segue o sistema; botão no cabeçalho e no menu)
- [x] PWA: manifest e service worker (instalável)
- [x] Única variável do frontend: `VITE_API_URL`

### CI
- [x] Pipeline: lint e testes do backend, lint e build do frontend, auditoria de dependências _(`.github/workflows/ci.yml`; ainda não executado)_
- [ ] Deploy de staging (API, worker, web, Postgres, Redis)

---

## Fase 2 — Painel da operadora (≈ 2-3 semanas)

### Operadoras e convites (§4.2, §7.5, §7.6)
- [x] Modelos `operators`, `operator_members`, `operator_invites`
- [x] Admin cria operadora e envia convite; operadora aceita e vira membro
- [x] Perfil da operadora (dados privados)

### Passeios (§4.3, §6 RN13)
- [x] Modelos `categories`, `tours`, `tour_translations`, `tour_photos`, `tour_price_categories`, `tour_prices`
- [x] CRUD de passeios com conteúdo em PT/ES/EN
- [x] Upload de fotos por URL pré-assinada; ordenação _(upload pela API, conversão para JPEG e remoção de EXIF; ordenação pela API)_
- [x] Categorias etárias e preços com vigência (temporada); validação de sobreposição
- [x] Local público aproximado + ponto de encontro exato privado (mapa para marcar)
- [x] Taxas pagas no local (`on_site_fees_note`)
- [x] Política de cancelamento e corte de vendas por passeio
- [x] Envio para aprovação; validação de publicação (RN13)
- [x] Sinalização de padrões de contato nos textos (RN10)

### Agenda (§4.4, §9)
- [x] Modelos `tour_schedules` e `departures`
- [x] Regras de recorrência (dias da semana, horário, capacidade, vigência)
- [x] Geração de saídas para 90 dias (ao salvar e diariamente)
- [x] Calendário de saídas: editar capacidade, fechar, criar saída extra
- [~] Testes de geração (fuso `America/Sao_Paulo`, vigências, edições preservadas) _(parcial: geração testada; preservação de edições sem teste dedicado)_

### Telas (§8.2)
- [x] Início, passeios (abas), agenda (calendário), perfil

---

## Fase 3 — Site do turista (≈ 3-4 semanas)

### API pública (§7.1)
- [x] `GET /categories`
- [x] `GET /tours` com filtros (texto, categoria, preço, data, horário, disponível, pessoas) e paginação
- [x] Busca por proximidade com PostGIS (`lat`, `lng`, `radius_km`, ordenação por distância)
- [x] Ordenação com penalidade por cancelamentos (RN08)
- [x] `GET /tours/{slug}` sem dados privados (RN10)
- [x] `GET /tours/{slug}/departures` com disponibilidade "disponível / últimas vagas" (RN09) e corte (RN04)
- [x] `POST /quotes` (RN02, RN03)

### Telas (§8.1)
- [x] Home
- [x] Busca com filtros e alternância lista/mapa; "perto de mim" e endereço
- [x] Página do passeio com calendário de saídas e seletor de pessoas
- [x] SEO: metadados e Open Graph por idioma nas páginas renderizadas no servidor, `hreflang`, sitemap gerado a partir da API
- [x] Páginas legais (termos, privacidade, cancelamento)

---

## Fase 4 — Reserva e pagamento (≈ 2-3 semanas; G4 aponta 5-6)
Depende da Fase 0 (gateway escolhido).

### Reserva (§4.5, §5)
- [x] Modelos `bookings`, `booking_items`, `booking_passengers` _(sem `booking_passengers` no MVP)_
- [x] `POST /bookings`: retenção atômica de vagas (§5.1) e valores congelados (RN01, RN02, RN03)
- [x] Teste de concorrência: duas reservas disputando a última vaga
- [x] Job de expiração das retenções (§9)
- [x] Código legível da reserva

### Pagamento (§4.5, §7.3, §7.4)
- [x] Modelos `payments`, `refunds`, `webhook_events`
- [~] Integração com o gateway: Pix (QR, copia-e-cola, expiração) e cartão _(gateway simulado com Pix e cartão; gateway real depende da Fase 0)_
- [x] Webhook com validação de assinatura e idempotência
- [x] Pagamento aprovado → `confirmed`; pagamento após expirar → confirma se houver vaga, senão reembolso automático (§5.1)
- [x] Reembolso (total e parcial) via gateway
- [x] Job de reprocessamento de webhooks com erro

### Pós-reserva
- [x] Voucher PDF (PT/ES/EN) com ponto de encontro exato e contato da operadora
- [x] Tela de confirmação e "Minhas reservas" (§8.1)
- [x] Cancelamento pelo turista conforme RN06
- [x] Cancelamento de saída pela operadora (clima) com reembolso em massa (RN07)
- [x] Cancelamento de reserva pela operadora (RN08) e no-show (RN15)
- [x] Lista de embarque do dia no painel da operadora
- [x] Job de `completed` (§9)

### Notificações (§10)
- [x] Fila de e-mails e templates PT/ES/EN
- [x] Turista: confirmação, cancelamento/reembolso, saída cancelada, lembrete D-1 _(feito, inclusive lembrete D-1)_
- [~] Operadora: nova reserva, cancelamento, resumo diário; links `wa.me` _(parcial: e-mail de nova reserva e links `wa.me`; falta resumo diário)_

---

## Fase 5 — Admin, repasses e lançamento (≈ 2 semanas; G4 aponta 3-4)

### Admin (§7.6, §8.3)
- [x] Operadoras: aprovar, suspender, **comissão individual** (RN01)
- [x] Passeios: fila de aprovação, aprovar/rejeitar/pausar, edição concierge
- [x] Categorias
- [x] Reservas: busca, detalhe, cancelamento com reembolso definido
- [x] Configurações (comissão padrão, prazos)
- [x] Auditoria

### Repasses (§4.5, RN11)
- [x] Modelos `payouts` e `payout_items`
- [x] Gerar repasses por período a partir das reservas `completed` elegíveis
- [x] Marcar como pago (ou transferência pelo gateway, se suportado)
- [x] Extrato da operadora (§7.5)

### Métricas (§10)
- [ ] PostHog no site com eventos do funil
- [x] Números básicos no admin

### Lançamento
- [x] Termos de uso, privacidade (LGPD) e consentimento
- [ ] Backups diários e restauração testada
- [~] Cadastro concierge dos primeiros passeios (Arraial, Um Dia no Rio, SUP, Favela, Angra, City Tour) _(edição concierge pronta no admin; seed traz 8 passeios fictícios de demonstração)_
- [ ] Compra real ponta a ponta em produção (Pix e cartão estrangeiro, cancelamento, reembolso)
- [ ] Deploy de produção e domínio

---

## Pós-MVP (backlog)
- [ ] Apps iOS/Android com Expo consumindo a mesma API
- [ ] Avaliações e filtro por avaliação
- [ ] Passeios sob consulta (`awaiting_operator`, prazo de 15-30 min)
- [ ] Check-in por QR no embarque
- [ ] Mudança no tamanho do grupo pelo turista (RN14)
- [ ] Antifraude no cartão (G8)
- [ ] Busca no hotel e zonas de encontro (G8)
- [ ] Taxa de serviço ao turista (G2)
- [ ] Canais de aquisição (G1, ver `plano/06-go-to-market.md`)
