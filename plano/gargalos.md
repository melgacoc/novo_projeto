# Gargalos e riscos a resolver

> Criado em 2026-10-18 a partir da revisão crítica do MVP (agente `advogado-do-diabo`) e da leitura do conselheiro.
> Decisão do fundador: **construir o MVP primeiro para ter noção do produto e depois eliminar os gargalos um a um.** Este documento é o backlog desses gargalos. Atualize o status de cada item conforme for resolvido.

Veredito da revisão: **ajustar, à beira de repensar**. Oferta e tecnologia não são o gargalo; demanda e economia são.

## Resumo
| # | Gargalo | Gravidade | Status |
|---|---|---|---|
| G1 | Não há canal de demanda definido | 🔴 Crítico | Aberto |
| G2 | Economia apertada com 10% de comissão | 🔴 Crítico | Aberto |
| G3 | Tributação sobre o GMV se não houver split real | 🔴 Crítico | Aberto |
| G4 | Estimativa de prazo otimista | 🟠 Alto | Aberto |
| G5 | Turista comprar sozinho pagando 100% antecipado | 🟠 Alto | Aberto |
| G6 | Agenda desatualizada + reserva instantânea = overbooking | 🟠 Alto | Aberto |
| G7 | Gateway: cartões estrangeiros, KYC/CNPJ das operadoras | 🟠 Alto | Aberto |
| G8 | Itens essenciais faltando no escopo | 🟡 Médio | Aberto |
| G9 | Itens subestimados no escopo | 🟡 Médio | Aberto |
| G10 | Premissas sem evidência | 🟡 Médio | Aberto |
| G11 | Relação com o negócio do sócio | 🟡 Médio | Aberto |

---

## G1. Não há canal de demanda definido 🔴
**Problema:** os ≈ R$ 90 mil/mês de hoje são vendidos por pessoas (vendedores da Inside, promotores, recepção do hostel Che Lagarto). A plataforma nasce com oferta (operadoras), mas sem nenhum caminho definido para o turista chegar. O `06-go-to-market.md` está vazio. SEO contra Civitatis/GetYourGuide leva de 6 a 12 meses.

**Leitura do conselheiro:** é o ponto mais importante. Inside e promotores estão fora do modelo por decisão do fundador, mas a plataforma precisa de canais de distribuição, que podem existir sem fazer parte do modelo.

**Caminhos possíveis:**
- Parcerias com hostels e hotéis (link/QR de indicação, comissão para quem indica).
- Instagram e conteúdo em espanhol/português/inglês.
- Google (SEO de longo prazo; anúncios só se a economia permitir, ver G2).
- Teste barato de demanda: link de pagamento para os 6 passeios mais vendidos + R$ 500 de anúncios em espanhol, medindo o custo por reserva.

**Próxima ação:** escrever o `06-go-to-market.md` com os canais iniciais.

---

## G2. Economia apertada com 10% de comissão 🔴
**Estimativa por reserva** (ticket R$ 723; 65% Pix e 35% cartão; plataforma absorve as taxas; valores aproximados, não verificados):

| Item | R$ |
|---|---|
| Comissão de 10% | +72 |
| Gateway (Pix ≈ 1%, cartão estrangeiro ≈ 5%) | −16 |
| Antecipação do cartão (repasse antes do recebimento) | −5 |
| Chargebacks (≈ 1% do volume de cartão) | −3 |
| Taxas perdidas em reembolsos | −1 |
| Impostos sobre a comissão (Simples ≈ 6-10%) | −6 |
| **Margem por reserva** | **≈ +41** |

**Por mês:** mesmo que toda a rede migre (≈ 120 reservas), ≈ R$ 4,9 mil de margem, menos suporte trilíngue (≈ R$ 3 mil) e infraestrutura (≈ R$ 1,2 mil) = **≈ R$ 700/mês**, sem salário.
**Aquisição paga:** CPC de R$ 2-5 com conversão de 1-2% → R$ 100-500 por reserva. A margem de R$ 41 não paga isso.

**Saídas compatíveis com as decisões do fundador:**
- **Taxa de serviço cobrada do turista** (5-8%, como Airbnb e Booking), mantendo 10% da operadora.
- **Comissão padrão de 15%**, ainda editável por operadora (a operadora fica com 85%, contra ≈ 78% hoje).
- Manter 10% sabendo que a margem é apertada e que só canais gratuitos funcionam.

**Próxima ação:** fundador decidir o modelo de receita.

---

## G3. Tributação sobre o GMV 🔴
**Problema:** se o dinheiro passar pela conta da plataforma sem split real no gateway, o imposto pode incidir sobre o valor total vendido, não só sobre a comissão. Isso quebra o modelo.

**Próxima ação:** 1 hora de consulta com contador **antes de escolher o gateway**. Confirmar também a emissão de NFS-e sobre a comissão.

---

## G4. Estimativa de prazo otimista 🟠
**Problema:** a estimativa do MVP (13-16 semanas) é otimista. Para 1 dev solo, o mais provável é **22-30 semanas**.

| Onde estoura | Previsto | Provável |
|---|---|---|
| Pagamento e reserva (marketplace, webhooks, estorno, repasse) | 2-3 sem | 5-6 sem |
| Agenda (recorrência, exceções, retenção de vaga, concorrência) | — | +1-2 sem |
| Site trilíngue com SEO e mapa | — | +1-2 sem |
| Admin, LGPD e lançamento | 2 sem | 3-4 sem |

Também: a fase 0 (gateway, contratos) bloqueia a fase de pagamento, e o fundador divide o tempo com o Rio Manager.

**Saídas:** aceitar 20-26 semanas, ou cortar escopo para 10-12 semanas (catálogo, checkout, voucher e reembolso para os 6 passeios principais, com o admin fazendo o resto à mão).

---

## G5. Turista comprar sozinho pagando 100% antecipado 🟠
**Problema:** hoje o turista paga um sinal médio de 43%, sempre com uma pessoa ao lado. Não há evidência de compra autônoma com pagamento total (hipótese H2).

**Próxima ação:** medir no MVP (conversão do checkout, abandono no pagamento). Se a conversão for baixa, considerar sinal + saldo no embarque.

---

## G6. Overbooking 🟠
**Problema:** hoje a disponibilidade é resolvida por WhatsApp. Com reserva instantânea, agenda desatualizada vira overbooking, reembolso, suporte e avaliação ruim (hipóteses H1 e H5).

**Ação barata:** pedir a 3 operadoras que atualizem uma planilha compartilhada de vagas todo dia por 2 semanas e medir quantas cumprem.

---

## G7. Gateway de pagamento 🟠
**Problemas:**
- Gateways brasileiros podem recusar cartões do Chile e da Argentina.
- Pix de apps argentinos precisa ser testado.
- Subcontas exigem KYC e possivelmente CNPJ; operadoras informais (pessoas físicas) podem não passar.

**Ação barata:** prova técnica de 1 semana com 2 gateways (transação real com cartão chileno e argentino, Pix, split e estorno). Checar CNPJ e Cadastur das operadoras em 1 dia.

---

## G8. Itens essenciais faltando no escopo 🟡
- Busca no hotel e ponto de encontro por zona.
- Taxas de acesso de Arraial e Angra (incluídas ou à parte).
- Preço por temporada.
- Cancelamento de uma saída inteira por clima, com reembolso em massa.
- Mudança no tamanho do grupo depois da reserva.
- Emissão de NFS-e sobre a comissão.
- Antifraude no cartão (voucher instantâneo atrai cartão roubado).
- Suporte por WhatsApp a partir de cedo (passeios saem às 6-7h).
- Check-in por QR no embarque.

---

## G9. Itens subestimados ou que podem ser simplificados 🟡
**Subestimados:** agenda recorrente com exceções e concorrência; integração de marketplace no gateway; tradução do conteúdo; manter duas bases de frontend (site com SSR + painel).

**Sugestões de simplificação da revisão** (algumas vão contra decisões do fundador e ficam só registradas):
- Mapa: simplificar (exibir os passeios, sem busca por raio na primeira versão). *Fundador quer o mapa; não remover.*
- Login com Google: código por e-mail bastaria. *Fundador quer o Google; manter.*
- Passeios sob consulta, avaliações e moderação automática: adiar.
- Painel de métricas próprio: usar uma ferramenta pronta (PostHog, Metabase).
- **Cadastro inicial concierge:** vocês cadastram os passeios (3 idiomas, fotos) em vez de cada operadora fazer sozinha.

---

## G10. Premissas sem evidência 🟡
- O volume da rede atual migra para a plataforma.
- As operadoras mantêm a agenda atualizada.
- O turista paga 100% online, sozinho.
- 10% de comissão cobre os custos.
- Gateways brasileiros aceitam cartões estrangeiros.
- As operadoras têm CNPJ e Cadastur.
- A paridade de preço pode ser imposta.
- SEO traz tráfego no curto prazo.
- Mapa e inglês são diferenciais (inglês é ≈ 1% da demanda atual).

Observação da revisão: o modelo mudou várias vezes em 2 dias e a lista de "Must" cresce. Vale manter o escopo sob controle.

---

## G11. Relação com o negócio do sócio 🟡
**Problema:** hoje a Inside fica com ≈ 15% e o promotor com ≈ 6%. Uma operadora na plataforma a 10% pode vender mais barato que a própria Inside, e a plataforma passa a competir com o negócio do sócio. Também não está escrito o que o sócio ganha com a plataforma.

**Próxima ação:** acordo escrito com o sócio (papel, participação, o que acontece com as vendas da Inside). Carta de intenção das maiores operadoras, começando pela Alegria (≈ 35% do volume atual).
