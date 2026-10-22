# Experimento 01: QR code com promotores

**Status:** ❌ não será feito (decisão do fundador em 2026-10-17). O fundador considera a demanda validada pela venda que já acontece na praia e assume o risco do tempo de desenvolvimento. A hipótese H14 passa a ser medida dentro do MVP. | **Hipóteses:** H9 (diferencial: confiança/decisão na hora), H10 (promotor leva o turista ao portal), H11 (operadoras aceitam comissão)
**Duração:** 2 semanas | **Custo estimado:** < R$ 300 (impressão + taxas de pagamento)

## Pergunta
Se o promotor, em vez de só falar e cobrar em dinheiro, mostrar um QR code que abre uma página com fotos, avaliações e pagamento online, o turista compra mais (ou pelo menos igual) e confia mais?

## Como funciona na praia
1. O promotor aborda o turista como já faz hoje.
2. Mostra um cartão/crachá com QR code ("Veja os passeios, fotos e avaliações").
3. O turista abre no celular uma página com os passeios, preço fechado, em PT/ES/EN.
4. Compra ali mesmo (Pix ou cartão) ou depois, sozinho, no hotel.
5. Recebe a confirmação/voucher no WhatsApp ou e-mail.
6. A operadora recebe a lista de reservas (manual: WhatsApp/planilha).

## O que montar (sem sistema próprio)
- **Página:** site estático simples (5-10 passeios, fotos, descrição, preço, horário, ponto de encontro, PT/ES/EN).
- **Pagamento:** links de pagamento prontos (Mercado Pago, Asaas ou Stripe), um por passeio.
- **Rastreio:** um QR code/URL por promotor (ex.: `?p=joao`) para saber quem trouxe cada venda.
- **Operação manual (concierge):** o fundador/sócio confirma cada reserva com a operadora pelo WhatsApp e manda o voucher.
- **Comissão:** acertada manualmente no fim da semana.

## Grupos
- **Teste:** 2-3 promotores com QR code.
- **Controle:** os mesmos promotores na semana anterior (ou outros promotores) vendendo do jeito tradicional.

## Métricas
| Métrica | Como medir |
|---|---|
| Abordagens por dia | Promotor anota (contador simples) |
| Escaneamentos | Analytics da página (por promotor) |
| Vendas na hora vs. vendas depois | Horário do pagamento vs. horário da abordagem |
| Taxa de fechamento (vendas / abordagens) | Comparar com o controle |
| Ticket médio | Pagamentos |
| % estrangeiros | Idioma escolhido na página |
| Objeções | Promotor anota o motivo dos "não" |
| Opinião do promotor e da operadora | Conversa no fim do teste |

## Critério de sucesso (definir antes de começar)
- Taxa de fechamento com QR **≥** taxa tradicional, **e**
- pelo menos 20% das vendas acontecem depois da abordagem (o turista volta sozinho = confiança/conveniência), **e**
- promotores querem continuar usando.

Se falhar: entender o motivo (o turista não quer escanear? prefere dinheiro? o promotor não usa?) antes de decidir o próximo passo.
