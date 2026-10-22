# Modelo de negócio

> v2 (2026-10-17). Marketplace aberto com comissão por reserva.

## Como a plataforma ganha dinheiro
- **Comissão sobre cada reserva**, descontada antes do repasse à operadora: **10% padrão**, editável por operadora no painel admin (decidido em 2026-10-18).
- Referências: marketplaces globais cobram 20-30%; a intermediação manual atual na rede fica em ≈ 22%.

## Fluxo do dinheiro
1. O turista paga o **total** na plataforma (Pix ou cartão).
2. O gateway retém o valor até o passeio acontecer.
3. Depois do passeio: repasse à operadora (valor − comissão). Recusa, expiração ou cancelamento elegível → reembolso.

## Referência de volume (rede atual do sócio)
Dados em `pesquisa/inside-dados-reais-2026.md`: ≈ R$ 90 mil/mês vendidos, ticket R$ 275 por pessoa.
Exemplo ilustrativo: se esse volume migrar inteiro para a plataforma, a receita mensal seria:

| Comissão | Receita/mês (R$ 90 mil de vendas) |
|---|---|
| 10% | R$ 9 mil |
| 15% | R$ 13,5 mil |
| 20% | R$ 18 mil |

Menos as taxas do gateway (≈ 1% Pix, ≈ 4-5% cartão, a confirmar) e os custos de infraestrutura. Crescer além disso depende de trazer turistas novos (H3) e outras operadoras.

## Questões em aberto
- Quem absorve as taxas do gateway e do cartão.
- Política de cancelamento padrão e quem decide (plataforma ou operadora).
- Prazo de repasse (ex.: D+2 depois do passeio).
- Estrutura jurídica: empresa, sócios, Cadastur da plataforma.
