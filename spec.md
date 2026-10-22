# Spec — Marketplace de passeios (MVP)

**Versão:** 0.4 · **Data:** 2026-10-18 · **Estado:** proposta para o MVP
**Base:** visão em [plano/00-ideia.md](plano/00-ideia.md), escopo em [plano/05-mvp.md](plano/05-mvp.md), riscos em [plano/gargalos.md](plano/gargalos.md). Tarefas em [tasks.md](tasks.md).

Itens marcados com ⏳ dependem de uma decisão ainda aberta.

---

## 1. Visão geral

Marketplace aberto onde turistas encontram, reservam e pagam passeios oferecidos diretamente por operadoras, começando pelo Rio de Janeiro. Três interfaces: **turista** (site público), **operadora** (painel) e **admin** (painel interno).

### 1.1 Princípios
1. **Valores congelados na reserva.** Preço, comissão e repasse calculados no momento da reserva ficam gravados; mudanças posteriores de preço ou comissão não alteram reservas existentes.
2. **O servidor calcula tudo.** O frontend nunca envia preço, comissão ou repasse.
3. **Dinheiro em centavos** (inteiros, BRL).
4. **Nada financeiro é apagado.** Cancelamentos e estornos mudam status e ficam no histórico.
5. **Toda alteração sensível é auditada** (quem, quando, valor antigo e novo).
6. **Reserva instantânea por padrão.** Se há vaga, a reserva paga é confirmada na hora.
7. **Contato da operadora só depois da reserva** (proteção contra desintermediação).
8. **Trilíngue:** português, espanhol e inglês em toda a interface do turista e no conteúdo público.

---

## 2. Atores e papéis

| Papel | Quem | Acesso |
|---|---|---|
| `tourist` | Turista | Site público; reservar exige login |
| `operator` | Usuário vinculado a uma operadora | Painel da operadora (só dados da própria operadora) |
| `admin` | Equipe da plataforma | Painel admin (tudo) |

Um usuário pode ser membro de uma operadora (`operator_members`). Turistas não precisam de vínculo.

---

## 3. Arquitetura

| Camada | Tecnologia |
|---|---|
| API | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic |
| Banco | PostgreSQL 16 + PostGIS |
| Fila, cache e rate limit | Redis + worker de tarefas com agendamento (proposta: Celery + Celery Beat, compatível com o SQLAlchemy síncrono da fundação) |
| Frontend | **React Router v7 em modo framework (sobre Vite) + React + TypeScript**, reaproveitando a fundação do Rio Manager (configs de Vite, TypeScript, Tailwind v4, shadcn/ui, alias `@/`, ESLint). Um único app: site do turista em `/{locale}/...` **renderizado no servidor (SSR)**; painel da operadora em `/painel` e admin em `/admin` **só no navegador** (como o Rio Manager). Depois da primeira carga, a navegação é no navegador, sem recarregar. Estado do servidor com TanStack Query; formulários com React Hook Form + Zod; i18n com i18next (PT/ES/EN) |
| SEO | SSR das páginas públicas com metadados, Open Graph e `hreflang` por idioma; sitemap gerado a partir da API. Componentes só de navegador (mapa, `localStorage`) carregados apenas no cliente |
| Servidor do frontend | Node (servidor do React Router) para as rotas públicas; repassa cookies à API quando necessário. A API Python continua sendo a única dona da autenticação e das regras |
| PWA | Manifest + service worker (instalável na tela inicial) |
| Arquivos | Armazenamento compatível com S3 (ex.: Cloudflare R2) com upload por URL pré-assinada |
| E-mail | SMTP configurável por variáveis de ambiente (qualquer provedor: SES, Resend, Brevo etc.) |
| Mapa | Proposta: **MapLibre GL JS** (biblioteca gratuita, código aberto) com tiles do **OpenFreeMap** ou **Protomaps** hospedado no armazenamento de objetos; geocodificação gratuita via **Photon** (komoot, sem chave) com fallback no **Nominatim** (respeitando o limite de 1 req/s), chamada pelo backend e com cache no Redis. **Decisão: solução 100% gratuita por enquanto.** Provedor isolado atrás de um componente/adaptador para poder trocar. "Perto de mim" usa a geolocalização do navegador; a distância é calculada no PostGIS |
| Pagamentos | Gateway com contas de marketplace, Pix e cartão ⏳ (G3, G7) |
| Analytics | PostHog (funil do turista) |
| Erros | Sentry |

Autenticação: Google OAuth (fluxo *authorization code* inteiramente no backend: o frontend só redireciona) e código de 6 dígitos por e-mail. Sessão com access token curto (JWT, em memória no frontend) e refresh token rotativo em cookie `httpOnly`, `Secure`, `SameSite=Lax`, com proteção CSRF na rota de refresh.

**Modo sem login (desenvolvimento):** toda a infraestrutura de autenticação existe, mas fica **desligada** por padrão com `AUTH_ENABLED=false`. Nesse modo:
- o backend aceita o header `X-Dev-User-Role` (`tourist`/`operator`/`admin`) e, opcionalmente, `X-Dev-Operator-Id`, e injeta um **usuário de desenvolvimento** fixo por papel (criado pelo seed);
- o frontend mostra um **seletor de papel** fixo no topo e envia esses headers;
- todas as regras de autorização (papéis, escopo por operadora) continuam sendo aplicadas sobre o usuário de desenvolvimento, para que nada mude ao ligar o login;
- a API **se recusa a subir** se `APP_ENV=production` e `AUTH_ENABLED=false`, e loga um aviso em todas as requisições nesse modo.

Ao ligar (`AUTH_ENABLED=true`), os headers de desenvolvimento são ignorados e as rotas passam a exigir sessão real.

**Integrações externas** (Google, SMTP, gateway, armazenamento, Sentry, mapa) são configuradas só por variáveis de ambiente no backend; nenhum segredo vai para o frontend. Guia em `docs/integracoes.md`.

**Ambiente local:** Postgres (com PostGIS) e Redis em Docker Compose, mais um servidor SMTP de teste (Mailpit).

---

## 4. Modelo de dados

Todas as tabelas têm `id`, `created_at` e `updated_at`. Valores monetários em `*_cents` (inteiro).

### 4.1 Pessoas e acesso
- **users**: `email` (único), `name`, `phone_e164` (obrigatório antes da primeira reserva), `role` (`tourist`/`operator`/`admin`), `google_sub` (único, opcional), `locale` (`pt`/`es`/`en`), `is_active`.
- **email_login_codes**: `email`, `code_hash`, `expires_at` (10 min), `attempts`, `used_at`.
- **refresh_tokens**: `user_id`, `token_hash`, `expires_at`, `revoked_at`.

### 4.2 Operadoras
- **operators**: `trade_name`, `legal_name`, `document` (CNPJ ou CPF), `cadastur_number`, `status` (`invited`/`pending_review`/`active`/`suspended`), `commission_rate` (decimal, **nulo = usar o padrão**), `contact_phone`, `contact_email` (privados), `gateway_recipient_id` ⏳, `cancellations_count`, `notes` (admin).
- **operator_members**: `operator_id`, `user_id`, `role` (`owner`/`staff`).
- **operator_invites**: `operator_id`, `email`, `token_hash`, `expires_at`, `accepted_at`.

### 4.3 Catálogo
- **categories**: `slug`, `name_pt`, `name_es`, `name_en`, `icon`, `position`.
- **tours**:
  - `operator_id`, `category_id`, `slug` (único), `status` (`draft`/`pending_review`/`published`/`paused`/`rejected`)
  - `duration_minutes`, `min_pax_per_booking`, `max_pax_per_booking`
  - `public_location` (PostGIS `POINT`, **aproximado**: região), `public_area_label` (ex.: "Copacabana")
  - `meeting_point_location` (`POINT`, exato, **privado**), `meeting_point_details` (privado, por idioma em `tour_translations`)
  - `booking_cutoff_minutes` (fechamento antes da saída), `instant_booking` (padrão `true`)
  - `cancellation_policy` (`flexible`/`moderate`/`strict`, ver RN06)
  - `on_site_fees_note` (taxas pagas no local, ex.: acesso a Arraial/Angra) ⏳ G8
  - `rating_avg`, `rating_count` (pós-MVP)
- **tour_translations**: `tour_id`, `locale`, `title`, `summary`, `description`, `includes`, `excludes`, `what_to_bring`, `meeting_point_details` (privado). Único por (`tour_id`, `locale`).
- **tour_photos**: `tour_id`, `storage_key`, `position`, `alt`.
- **tour_price_categories**: `tour_id`, `code` (`adult`/`child`/`infant`/`senior`), `min_age`, `max_age`, `label_pt/es/en`.
- **tour_prices**: `price_category_id`, `price_cents`, `valid_from`, `valid_to` (nulo = sem fim). Permite **preço por temporada** (G8). Não pode haver sobreposição de vigência na mesma categoria.

### 4.4 Agenda
- **tour_schedules** (regra de recorrência): `tour_id`, `weekdays` (array 0-6), `start_time`, `capacity`, `valid_from`, `valid_to`.
- **departures** (saídas concretas, geradas a partir das regras): `tour_id`, `schedule_id` (opcional), `starts_at` (timestamp com fuso `America/Sao_Paulo`), `capacity`, `seats_held`, `seats_booked`, `status` (`open`/`closed`/`cancelled`), `cancel_reason` (`weather`/`operator`/`other`).
  - Vagas disponíveis = `capacity - seats_held - seats_booked`.
  - Exceções (bloquear um dia, mudar capacidade, saída extra) são edições diretas em `departures`.
  - Único por (`tour_id`, `starts_at`).

### 4.5 Reservas e dinheiro
- **bookings**:
  - `code` (curto e legível, ex.: `RJ-7K3P9Q`), `user_id`, `departure_id`, `operator_id`, `tour_id`
  - `status` (ver §5), `locale`, `contact_name`, `contact_phone_e164`, `pax_total`
  - Valores congelados: `subtotal_cents`, `commission_rate`, `commission_cents`, `operator_amount_cents`, `service_fee_cents` (0 no MVP; reservado para G2)
  - `hold_expires_at`, `paid_at`, `confirmed_at`, `cancelled_at`, `cancelled_by` (`tourist`/`operator`/`admin`/`system`), `cancel_reason`, `completed_at`
  - `refund_amount_cents`, `source` (UTM/ref), `checked_in_at` (pós-MVP)
- **booking_items**: `booking_id`, `price_category_code`, `quantity`, `unit_price_cents`.
- **booking_passengers** (opcional no MVP): `booking_id`, `name`, `age`.
- **payments**: `booking_id`, `gateway`, `gateway_charge_id` (único), `method` (`pix`/`card`), `status` (`pending`/`approved`/`failed`/`refunded`/`partially_refunded`/`chargeback`), `amount_cents`, `fee_cents`, `pix_qr_code`, `pix_expires_at`, `raw` (JSON).
- **refunds**: `payment_id`, `amount_cents`, `reason`, `gateway_refund_id`, `status`.
- **payouts**: `operator_id`, `period_start`, `period_end`, `amount_cents`, `status` (`pending`/`paid`/`failed`), `paid_at`, `gateway_transfer_id`, `notes`.
- **payout_items**: `payout_id`, `booking_id`, `amount_cents`.
- **webhook_events**: `gateway`, `event_id` (único, para idempotência), `payload`, `processed_at`, `error`.

### 4.6 Plataforma
- **settings**: chave/valor (`default_commission_rate = 0.10`, `hold_minutes = 15`, `payout_delay_days` ⏳).
- **audit_logs**: `user_id`, `entity`, `entity_id`, `action`, `old_values`, `new_values`.
- **reviews** (pós-MVP): `booking_id` (único), `rating` 1-5, `comment`, `status`.

---

## 5. Ciclo de vida da reserva

```
          criar (vaga retida)
               │
               ▼
   ┌────────  held  ────────┐
   │  pagamento aprovado     │ prazo expirou
   ▼                         ▼
confirmed ◄── (instantânea)  expired
   │
   ├── turista cancela ────────► cancelled (reembolso conforme RN06)
   ├── operadora cancela ──────► cancelled (reembolso integral; conta para a operadora)
   ├── saída cancelada (clima) ► cancelled (reembolso integral)
   ├── admin cancela ──────────► cancelled (reembolso definido pelo admin)
   ├── operadora marca no-show ► no_show (sem reembolso)
   └── saída aconteceu ────────► completed ──► repasse (payout)
```

Pós-MVP (passeios sob consulta): `held → awaiting_operator → confirmed | cancelled` (prazo de 15-30 min, reembolso automático).

### 5.1 Regras de transição
- **Criar (held):** em uma transação, `UPDATE departures SET seats_held = seats_held + :pax WHERE id = :id AND status = 'open' AND capacity - seats_held - seats_booked >= :pax`. Se nenhuma linha for afetada, não há vaga. Grava `hold_expires_at = agora + hold_minutes`.
- **Pagamento aprovado** (webhook): `seats_held -= pax`, `seats_booked += pax`, status `confirmed`, gera voucher, notifica turista e operadora.
- **Pagamento aprovado depois de expirar** (comum com Pix): se ainda houver vaga, confirma; se não, status `cancelled` com `cancel_reason = 'no_availability'` e **reembolso integral automático**.
- **Expirar:** job libera `seats_held` e marca `expired`.
- **Cancelar:** libera `seats_booked`, calcula reembolso, cria `refunds`, atualiza contadores.
- **Completar:** job marca `completed` as reservas `confirmed` cuja saída terminou (`starts_at + duration`), exceto `no_show`.

---

## 6. Regras de negócio

| # | Regra |
|---|---|
| RN01 | **Comissão:** padrão de 10% (`settings.default_commission_rate`); o admin pode definir outra taxa por operadora (`operators.commission_rate`). A taxa vigente é congelada na reserva. |
| RN02 | **Preço:** total = Σ (quantidade × preço da categoria etária). A idade define a categoria. Calculado pelo servidor. |
| RN03 | **Temporada:** usa o preço vigente **na data da saída**, consultado no momento da reserva, e congela. |
| RN04 | **Fechamento:** não se vende uma saída a menos de `booking_cutoff_minutes` do início. Saídas passadas ou fechadas não aparecem. |
| RN05 | **Retenção da vaga:** 15 minutos para concluir o pagamento (`hold_minutes`). O QR do Pix expira no mesmo prazo. |
| RN06 | **Cancelamento pelo turista** ⏳ (proposta): `flexible` = reembolso integral até 24 h antes; `moderate` = integral até 48 h antes; `strict` = sem reembolso. Depois do prazo, sem reembolso. Taxas do gateway: ⏳ G2. |
| RN07 | **Cancelamento por clima ou pela operadora:** cancelar uma saída cancela todas as reservas dela com **reembolso integral** e aviso ao turista (G8). |
| RN08 | **Penalidade:** cada cancelamento pela operadora soma em `cancellations_count`; operadoras com taxa alta perdem posição na busca. |
| RN09 | **Disponibilidade exibida:** "disponível" ou "últimas vagas" (quando vagas ≤ max(3, 20% da capacidade)); nunca o número exato. |
| RN10 | **Desintermediação:** antes da reserva, não exibir `trade_name` completo, telefone, e-mail, site, redes sociais nem localização exata. Esses dados vão só no voucher. Textos e fotos passam por aprovação do admin; o sistema sinaliza padrões de contato (telefone, @, URL) nos textos. |
| RN11 | **Repasse:** valor da operadora (`operator_amount_cents`) liberado `payout_delay_days` depois de `completed` ⏳ (G3, G7). Repasse por período, gerado pelo admin no MVP. |
| RN12 | **Login para reservar:** catálogo aberto; reservar exige login e telefone (pedido uma vez). |
| RN13 | **Publicação:** um passeio só é publicado com os 3 idiomas preenchidos, pelo menos 1 foto, 1 categoria de preço vigente e agenda. O admin aprova. Cadastro inicial pode ser feito pela equipe (concierge, G9). |
| RN14 | **Mudança no tamanho do grupo** ⏳ (G8): no MVP, só pelo admin (cancelar e refazer, ou ajuste manual). |
| RN15 | **No-show:** a operadora pode marcar até 24 h depois da saída; sem reembolso. |

---

## 7. API (v1)

Prefixo `/api/v1`. Respostas em JSON. Erros no formato `{ "error": { "code", "message" } }`.

### 7.1 Pública
| Método | Rota | Descrição |
|---|---|---|
| GET | `/categories` | Categorias |
| GET | `/tours` | Busca. Filtros: `q`, `category`, `price_min`, `price_max`, `date`, `time_from`, `time_to`, `available` (bool), `lat`, `lng`, `radius_km`, `pax`, `sort` (`relevance`/`price`/`distance`), paginação. `locale` via header `Accept-Language` ou query |
| GET | `/tours/{slug}` | Detalhe público (sem dados privados) |
| GET | `/tours/{slug}/departures` | Saídas com disponibilidade (RN09) entre `from` e `to` |
| POST | `/quotes` | Calcula total para `departure_id` + quantidades por categoria |

### 7.2 Autenticação
| Método | Rota | Descrição |
|---|---|---|
| GET | `/auth/google/start` | Redireciona para o login do Google (com `state` anti-CSRF) |
| GET | `/auth/google/callback` | Recebe o código, cria ou vincula o usuário, abre sessão e redireciona ao frontend |
| POST | `/auth/email/request-code` | Envia código de 6 dígitos |
| POST | `/auth/email/verify` | Valida o código e abre sessão |
| POST | `/auth/refresh` | Renova o access token |
| POST | `/auth/logout` | Revoga o refresh token |
| GET / PATCH | `/me` | Perfil (nome, telefone, idioma) |

### 7.3 Turista
| Método | Rota | Descrição |
|---|---|---|
| POST | `/bookings` | Cria reserva `held` (retém vaga) |
| POST | `/bookings/{code}/payments` | Inicia pagamento (`pix` ou `card`) |
| GET | `/bookings` | Minhas reservas |
| GET | `/bookings/{code}` | Detalhe (dados privados da operadora só se `confirmed`) |
| GET | `/bookings/{code}/voucher` | Voucher (PDF) |
| POST | `/bookings/{code}/cancel` | Cancela conforme RN06 |

### 7.4 Webhooks
| Método | Rota | Descrição |
|---|---|---|
| POST | `/webhooks/payments/{gateway}` | Eventos do gateway. Valida assinatura; idempotente por `event_id` |

### 7.5 Operadora (`/operator`, só a própria operadora)
| Método | Rota | Descrição |
|---|---|---|
| POST | `/operator/invites/{token}/accept` | Aceita convite |
| GET / PATCH | `/operator/profile` | Dados da operadora |
| CRUD | `/operator/tours` | Passeios, traduções, categorias de preço e preços |
| POST | `/operator/tours/{id}/photos/upload-url` | URL pré-assinada para foto |
| POST | `/operator/tours/{id}/submit` | Envia para aprovação |
| CRUD | `/operator/tours/{id}/schedules` | Regras de agenda |
| GET / PATCH | `/operator/departures` | Lista e edita saídas (capacidade, fechar) |
| POST | `/operator/departures/{id}/cancel` | Cancela saída (clima/outro) com reembolso em massa |
| GET | `/operator/bookings` | Reservas, filtros por dia e status (lista de embarque) |
| POST | `/operator/bookings/{code}/cancel` | Cancela uma reserva (reembolso integral, RN08) |
| POST | `/operator/bookings/{code}/no-show` | Marca no-show (RN15) |
| GET | `/operator/statement` | Extrato: reservas, comissão, repasses |

### 7.6 Admin (`/admin`)
| Método | Rota | Descrição |
|---|---|---|
| CRUD | `/admin/operators` | Criar, convidar, aprovar, suspender, **comissão individual** |
| GET / POST | `/admin/tours` | Listar e **aprovar/rejeitar/pausar**; editar conteúdo (concierge) |
| CRUD | `/admin/categories` | Categorias |
| GET | `/admin/bookings` | Busca de reservas |
| POST | `/admin/bookings/{code}/cancel` | Cancela com reembolso definido |
| GET / POST | `/admin/payouts` | Gerar repasses por período, marcar como pagos |
| GET / PATCH | `/admin/settings` | Comissão padrão, prazos |
| GET | `/admin/metrics` | Números básicos (ver §10) |
| GET | `/admin/audit-logs` | Auditoria |

---

## 8. Telas

### 8.1 Site do turista (`/{pt|es|en}/...`)
- **Home:** busca, categorias, destaques, acesso ao mapa.
- **Busca:** lista + filtros (categoria, preço, data, horário, disponível agora) e **alternância lista/mapa**; "perto de mim" (geolocalização) ou endereço.
- **Passeio:** fotos, descrição, inclui/não inclui, região aproximada no mapa, política de cancelamento, taxas pagas no local, calendário de saídas com disponibilidade, seletor de pessoas por faixa etária, total.
- **Checkout:** login (Google ou código), telefone (uma vez), resumo, contador da retenção, pagamento Pix (QR e copia-e-cola) ou cartão.
- **Confirmação:** voucher, ponto de encontro exato, contato da operadora.
- **Minhas reservas:** lista, detalhe, voucher, cancelar.
- **Páginas legais:** termos, privacidade, política de cancelamento.

### 8.2 Painel da operadora (`/painel`)
Início (próximas saídas), passeios (cadastro em abas: conteúdo por idioma, fotos, preços, local, regras), agenda (calendário de saídas, regras de recorrência, bloqueios), reservas (lista de embarque do dia), extrato.

### 8.3 Admin (`/admin`)
Operadoras, passeios (fila de aprovação), reservas, repasses, categorias, configurações, métricas, auditoria.

---

## 9. Tarefas em segundo plano (worker)

| Tarefa | Frequência |
|---|---|
| Expirar reservas `held` vencidas e liberar vagas | A cada minuto |
| Fechar saídas no horário de corte (RN04) | A cada 5 minutos |
| Gerar `departures` a partir de `tour_schedules` para os próximos 90 dias | Diária e ao salvar uma regra |
| Marcar reservas `completed` | A cada hora |
| Enviar e-mails (fila) | Contínuo |
| Lembrete ao turista no dia anterior | Diária |
| Processar reembolsos em massa (saída cancelada) | Sob demanda |
| Reprocessar webhooks com erro | A cada 10 minutos |

---

## 10. Notificações e métricas

**E-mails ao turista (PT/ES/EN):** código de login, reserva confirmada (com voucher), cancelamento e reembolso, saída cancelada, lembrete do dia anterior.
**E-mails à operadora:** nova reserva, cancelamento pelo turista, resumo diário das saídas do dia seguinte. Link `wa.me` com texto pronto onde fizer sentido.

**Métricas:** funil no PostHog (visita → busca → passeio → início do checkout → login → pagamento aprovado). No admin: reservas e vendas por semana, comissão, operadoras e passeios ativos, cancelamentos por operadora, reembolsos, tempo de retenção expirado vs. pago.

---

## 11. Segurança e LGPD
- Senhas não existem; códigos e tokens guardados como hash.
- Rate limit em login e criação de reservas.
- Autorização por papel e por operadora em todas as rotas `/operator`.
- Validação de assinatura dos webhooks.
- Consentimento e política de privacidade; exclusão de conta sob pedido (mantendo registros financeiros exigidos por lei).
- Backups diários do banco.

---

## 12. Pendências (ligadas a `plano/gargalos.md`)
| Tema | Gargalo |
|---|---|
| Escolha do gateway, split, retenção e repasse | G3, G7 |
| Prazo de repasse (`payout_delay_days`) | G3, G7 |
| Taxa de serviço ao turista (`service_fee_cents`) | G2 |
| Política de cancelamento final e quem absorve taxas | G2 |
| Taxas pagas no local, busca no hotel, zonas de encontro | G8 |
| Antifraude no cartão | G8 |
| Emissão de NFS-e sobre a comissão | G3, G8 |
| Provedor de mapa | Custo |
