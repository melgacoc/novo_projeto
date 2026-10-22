# Decisões técnicas do MVP (para revisão do fundador)

> Tomadas durante o desenvolvimento de 2026-10-18, seguindo `spec.md` e `tasks.md`. Cada item diz **o que** foi decidido, **por quê** e **como mudar**. Marque o que quiser rever.

## Arquitetura e fundação

| # | Decisão | Por quê | Como mudar |
|---|---|---|---|
| D1 | Reaproveitada do Rio Manager só a **fundação**: configs de Vite, TypeScript, Tailwind v4, ESLint, `components.json` (shadcn), `index.css`, componentes `ui/*`, versões das libs Python e o `env.py` do Alembic. Nenhum código de domínio. | Pedido do fundador. | — |
| D2 | Frontend em **React Router 7.18 (modo framework)** sobre Vite: páginas públicas com SSR; `/painel` e `/admin` só no navegador (`clientLoader.hydrate` + `HydrateFallback`). | SEO e 4G nas páginas públicas; painel igual a uma SPA. O React Router 8 exige Node 22 (a máquina tem Node 20). | Ao atualizar o Node, migrar para RR 8. |
| D3 | `npm` com `legacy-peer-deps` (arquivo `web/.npmrc`). | O npm 10 tem um bug ao resolver os peers opcionais do `@react-router/dev` (wrangler, rsc). | Remover quando o npm/React Router corrigir. |
| D4 | Um único app web (site, painel e admin), e o painel/admin só em **português**. | Equipe das operadoras fala PT/ES; reduz 3× o trabalho de tradução do painel. O site do turista é PT/ES/EN. | Extrair os textos do painel para `lib/i18n.ts`. |
| D5 | Traduções do site em um dicionário próprio (`web/src/lib/i18n.ts`), sem i18next. | i18next com SSR exige configuração extra; o dicionário é tipado e funciona no servidor e no navegador. | Trocar por i18next se o volume de textos crescer muito. |
| D6 | Backend **sem camada `repositories`** (o Rio Manager tem): endpoints → services → models. | Menos código para o MVP; os services concentram as regras. | Criar `repositories` se as consultas começarem a se repetir. |
| D7 | Fila e agendador com **Celery + Celery Beat** (Redis). | Compatível com o SQLAlchemy síncrono da fundação; o `arq` exige código assíncrono. | — |
| D8 | IDs internos são inteiros; o turista vê só o **slug** do passeio e o **código da reserva** (`RJ-XXXXXX`). | Simplicidade sem expor sequências sensíveis. | — |
| D9 | Respostas montadas em `services/serializers.py` (dicionários por público: turista, operadora, admin) em vez de schemas Pydantic de saída. | Garante num só lugar que dados privados nunca saem nas visões públicas (RN10). | Criar schemas de saída se quiser a documentação OpenAPI mais rica. |
| D10 | Portas locais diferentes das do Rio Manager: Postgres **5433**, Redis **6380**, Mailpit **1026/8026**. | Os dois projetos rodam juntos. | `docker-compose.yml` e `.env`. |

## Regras de negócio implementadas com escolhas minhas

| # | Decisão | Por quê | Como mudar |
|---|---|---|---|
| R1 | **Região pública** = ponto de encontro arredondado para 2 casas decimais (~1 km). A operadora marca o ponto exato; o turista vê só a região e o nome do bairro. | RN10 (desintermediação) sem pedir dois cadastros de local. | `PUBLIC_PRECISION` em `catalog_service.py`. |
| R2 | O turista vê o **nome público** da operadora (`public_name`, controlado pelo admin), mas nunca contato, nome fantasia completo ou endereço exato antes de confirmar. | No marketplace aberto o turista escolhe a operadora, então precisa de um nome; o admin decide qual. | Campo `public_name` no admin. |
| R3 | **Fechamento de vendas** calculado na hora (`starts_at − corte > agora`), sem job que "fecha" a saída. | Sempre correto e sem atraso. | — |
| R4 | Retenção de vaga de **15 min** (configurável no admin); o QR do Pix expira junto. Pagamento que chega depois: confirma se houver vaga, senão reembolso automático. | Spec §5.1. | Admin → Configurações. |
| R5 | Política de cancelamento por passeio: flexível (24 h), moderada (48 h), rígida (sem reembolso). Reembolso **integral ou zero**, sem taxa retida. | Simples de explicar; taxa do gateway fica com a plataforma por enquanto (G2). | `tourist_refund_amount` em `booking_service.py`. |
| R6 | Cancelamento pela operadora ou clima: reembolso integral + contador de cancelamentos da operadora, que **rebaixa na busca** (ordenação por relevância). | RN07, RN08. | `catalog_service.search`. |
| R7 | **No-show**: a operadora marca entre o início da saída e +24 h; a operadora recebe normalmente. | RN15. | — |
| R8 | **Repasse**: valor da operadora liberado `payout_delay_days` (padrão 2) dias depois de `completed` ou `no_show`; o admin gera os repasses agrupados por operadora e marca como pagos. | Sem gateway real ainda (G3, G7). | Admin → Configurações; integração no gateway. |
| R9 | **Comissão** com arredondamento meio-para-cima em centavos, congelada na reserva. | RN01. | — |
| R10 | Preço por temporada usa o preço vigente **na data da saída**. No seed, alta temporada (+15%) a partir de 1º de dezembro. | RN03. | Editor de passeio → Preços. |
| R11 | **Disponibilidade** exibida como "disponível", "últimas vagas" (≤ máx(3, 20% da capacidade)) ou "esgotado". | RN09. | Admin → Configurações. |
| R12 | Passeio só é publicado com: 3 idiomas, ≥ 1 foto, preço vigente, categoria, ponto no mapa e agenda. Edições depois de publicado **não** voltam para análise. | RN13; não travar a operadora no dia a dia. | `tour_service.publication_problems` / `update`. |
| R13 | **Moderação** de contatos (telefone, e-mail, URL, @, "WhatsApp") só **sinaliza** para o admin; não bloqueia. | Evita falso positivo travando cadastro. | `services/moderation.py`. |
| R14 | Exclusão de passeio só em rascunho/rejeitado e sem reservas; publicados são pausados. | Nada financeiro é apagado. | — |
| R15 | Convite de operadora: link válido por 7 dias, enviado por e-mail e devolvido na tela do admin (para mandar por WhatsApp). | Onboarding concierge. | — |
| R16 | Usuário criado automaticamente no primeiro login (Google ou código); turista por padrão. Ao aceitar convite, vira operadora. | — | — |
| R17 | Login obrigatório para reservar; nome e WhatsApp pedidos na primeira reserva e guardados no perfil. | Decisão do fundador. | — |

## Segurança

- Sem senhas. Códigos de login e tokens guardados como HMAC-SHA256; código de 6 dígitos vale 10 min e aceita 5 tentativas.
- Refresh token rotativo com detecção de reuso (revoga a família); cookie `httpOnly`, `SameSite=Lax`, `Secure` em produção; CSRF por double submit.
- Rate limit no Redis: global por IP (600/min) e por grupo (código de login 5/10 min, verificação 10/10 min, reservas 20/10 min por usuário, busca 120/min, geocodificação 30/min). Se o Redis cair, a requisição passa (fail-open) e vai para o log.
- Headers de segurança, `TrustedHostMiddleware`, limite de corpo (8 MB), uploads validados pelo conteúdo e reprocessados (remove EXIF/GPS).
- Escopo por operadora em todas as rotas `/operator` (header `X-Operator-Id` validado contra o vínculo do usuário).
- Guardas de produção: a API não sobe com login desligado, gateway `fake` ou `SECRET_KEY` de desenvolvimento.
- Auditoria de comissão, status de passeio, cancelamentos, saídas, repasses, configurações e usuários.

## Escalabilidade (o que já está pronto)

API sem estado (pode rodar várias instâncias), rate limit/cache/fila no Redis, retenção de vagas atômica no banco, idempotência em pagamentos e webhooks, fotos em S3, índices nas buscas, paginação, health checks (`/health`, `/ready`), logs JSON com `request_id`. **Celery Beat deve rodar em uma instância só.**

## O que ficou de fora ou simplificado (próximos passos)

| Item | Situação |
|---|---|
| Gateway real | Interface pronta; só o simulador implementado (depende da escolha do gateway, G3/G7). |
| PostHog (funil do turista) | Não instalado; o admin mostra métricas do banco. |
| Avaliações | Campos no banco (`rating_avg`, `rating_count`), sem tela. Pós-MVP. |
| Passeios sob consulta (`awaiting_operator`) | Status existe; fluxo não implementado (toda reserva é instantânea). |
| Mudança no tamanho do grupo | Só cancelando e refazendo (RN14). |
| Check-in por QR | O voucher já tem QR com o código; falta a tela de leitura. |
| NFS-e, antifraude | Não implementados (G3, G8). |
| WhatsApp | Só links `wa.me`; sem API. |
| Teste ponta a ponta no navegador | Executado em 2026-10-18 com Playwright (12 cenários: busca, mapa, filtros, reserva, Pix simulado, voucher, painel, criação de passeio, admin, celular), todos ok. O roteiro não foi versionado. |
