# Tur — marketplace de passeios no Rio de Janeiro

O turista encontra, escolhe, reserva e paga passeios oferecidos diretamente pelas operadoras. Três interfaces: **site do turista** (PT/ES/EN), **painel da operadora** e **admin**.

- Visão e plano de negócio: [`plano/`](plano/) (comece por [`plano/00-ideia.md`](plano/00-ideia.md) e [`plano/05-mvp.md`](plano/05-mvp.md))
- Especificação técnica: [`spec.md`](spec.md) · Backlog: [`tasks.md`](tasks.md)
- Integrações (Google, SMTP, gateway, fotos, mapa): [`docs/integracoes.md`](docs/integracoes.md)
- Decisões técnicas tomadas no desenvolvimento: [`docs/decisoes-tecnicas.md`](docs/decisoes-tecnicas.md)

## Estrutura

```
api/    FastAPI + SQLAlchemy 2 + Alembic + PostGIS + Celery (Python 3.12)
web/    React Router 7 (modo framework, SSR) + Vite + Tailwind + shadcn/ui + TanStack Query
docs/   integrações e decisões técnicas
plano/  plano de negócio vivo
docker-compose.yml   Postgres+PostGIS, Redis, Mailpit (e, opcionalmente, api/worker/web)
```

## Rodando localmente

Pré-requisitos: Docker, Python 3.12, Node 20.

```bash
make infra     # Postgres (5433), Redis (6380), Mailpit (SMTP 1026, interface http://localhost:8026)
make setup     # venv + dependências + .env a partir dos .env.example
make migrate   # cria as tabelas
make seed      # configurações, usuários de desenvolvimento e passeios de demonstração
```

Em três terminais:

```bash
make api       # http://localhost:8000  (documentação interativa em /docs)
make worker    # fila de e-mails, expiração de reservas, geração de saídas, lembretes
make web       # http://localhost:5173
```

Ou tudo em containers: `make all-docker` (site em http://localhost:3000).

### Login desligado (padrão)

`AUTH_ENABLED=false` em `api/.env`. Uma **barra amarela** no topo do site escolhe o papel:

| Papel | Onde | O que dá para testar |
|---|---|---|
| Turista | `/pt`, `/es`, `/en` | buscar (filtros, mapa, "perto de mim"), reservar, pagar (Pix simulado), voucher, cancelar |
| Operadora | `/painel` | cadastrar passeio (textos, preços por temporada, fotos, mapa, agenda), agenda, lista de embarque, cancelar por clima, extrato |
| Admin | `/admin` | aprovar passeios, operadoras e comissão individual, reservas e reembolsos, repasses, configurações, auditoria |

O pagamento usa o gateway **simulado**: no checkout, o botão "Simular pagamento aprovado" faz o papel do webhook. Os e-mails (confirmação com voucher em PDF, cancelamentos, convites) aparecem no Mailpit: http://localhost:8026.

Para ligar o login, veja [`docs/integracoes.md`](docs/integracoes.md#1-ligar-o-login-auth_enabled).

### Dados de demonstração

4 operadoras e 8 passeios **fictícios**, inspirados nos mais vendidos do Rio (Arraial do Cabo, Um Dia no Rio, SUP na Praia Vermelha, Rocinha, Angra, Corcovado, asa-delta, Pedra do Telégrafo), com textos nos 3 idiomas, fotos geradas, preços de baixa/alta temporada e agenda para 90 dias. O turista de desenvolvimento já tem duas reservas realizadas (para testar repasses) e uma futura.

## Testes e qualidade

```bash
make test   # 24 testes do backend (Postgres de teste: tur_test)
make lint   # typecheck + ESLint do frontend
```

## Comandos úteis

```bash
cd api && ./venv/bin/alembic revision --autogenerate -m "descrição"   # nova migration
cd api && ./venv/bin/python -m app.seed --no-demo                      # seed sem dados fictícios
docker compose exec db psql -U tur -d tur                             # console do banco
```
