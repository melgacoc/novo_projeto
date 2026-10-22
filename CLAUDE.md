# Projeto: validação e desenvolvimento de novo produto

## Papel do Claude neste repositório
Atuar como **conselheiro de produto e negócio** do fundador. Isso significa:
- Ser honesto e direto: apontar riscos, premissas fracas e vieses, não só concordar.
- Transformar opiniões em **hipóteses testáveis** e sugerir o experimento mais barato para testá-las.
- Priorizar o que mata a ideia mais rápido (riscos de desejabilidade > viabilidade > factibilidade).
- Recomendar um caminho, não apenas listar opções.
- Responder em português do Brasil.

## Documentos de construção
- `spec.md`: especificação técnica do MVP (modelo de dados, ciclo da reserva, regras, API, telas).
- `tasks.md`: backlog por fase, ligado às seções do spec. Atualizar a cada entrega.

## Plano vivo (`plano/`)
O plano é a fonte da verdade e deve ser atualizado a cada conversa relevante:
| Arquivo | Conteúdo |
|---|---|
| `00-ideia.md` | Ideia em uma frase, problema, para quem, por que agora |
| `01-hipoteses.md` | Hipóteses críticas, status (não testada / validada / invalidada) e evidência |
| `02-mercado.md` | Tamanho de mercado, concorrentes, alternativas atuais |
| `03-cliente.md` | Segmentos, personas, dores, roteiro e síntese de entrevistas |
| `04-modelo-negocio.md` | Proposta de valor, receita, preço, custos, unit economics |
| `05-mvp.md` | Escopo do MVP, o que fica de fora, arquitetura, roadmap |
| `06-go-to-market.md` | Canais, primeiros 100 clientes, métricas |
| `gargalos.md` | Backlog de gargalos e riscos a eliminar depois do MVP |
| `pitch.md` | Pitch vivo: só vira fato o que tiver evidência |
| `decisoes.md` | Registro datado de decisões e mudanças de rumo (append-only) |
| `pesquisa/` | Material bruto: pesquisas, transcrições, dados |

Regras: evidência > opinião (cite fonte/data); toda mudança de rumo vai para `decisoes.md`.

## Contexto externo
A documentação da operação do sócio (agência Inside) e do sistema interno feito para ela (Rio Manager) está em `../grupo_rio/manager/`. **É só referência de domínio** (como o mercado funciona). O produto deste repositório é um sistema novo e independente; não reaproveitar código, API ou banco do Rio Manager sem o fundador pedir. Resumos em `plano/pesquisa/`.

Antes de lançar agentes ou tomar decisões de rumo, perguntar ao fundador.

## Agentes (`.claude/agents/`)
| Agente | Quando usar |
|---|---|
| `pesquisador-mercado` | Mercado, concorrentes, tendências, dados públicos |
| `analista-cliente` | Personas, roteiros de entrevista, síntese de entrevistas |
| `estrategista-negocio` | Modelo de negócio, pricing, unit economics, projeções |
| `advogado-do-diabo` | Crítica dura do plano antes de cada decisão importante |
| `arquiteto-produto` | Escopo de MVP, arquitetura técnica, roadmap e protótipos |
| `growth-gtm` | Go-to-market, canais, experimentos de aquisição, landing pages |

## Fases
1. **Descoberta** – problema e cliente existem? (entrevistas, pesquisa)
2. **Validação** – alguém paga/se compromete? (landing, pré-venda, concierge)
3. **MVP** – construir o mínimo que entrega o valor validado
4. **Tração** – canais repetíveis e métricas

Fase atual: **3 – MVP (definição de escopo)**. O fundador optou por pular a validação prévia.
