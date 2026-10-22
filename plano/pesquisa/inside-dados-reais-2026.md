# Dados reais da Inside (planilhas do sócio)

Fontes (fora do repositório, contêm dados pessoais de clientes; **não copiar para cá**):
- `Controle de Reservas Inside 2026.xlsx - Control de Reservas.csv`: 771 reservas com passeio entre fev e out/2026
- `Controle Financeiro Inside 2026 - Outubro.csv`: custos de outubro/2026 (mês parcial)

Análise feita em 2026-10-17 (script de agregação, só números agregados aqui).

## Volume (reservas não canceladas, por mês do passeio)
| Mês | Reservas | PAX | Vendido (R$) |
|---|---|---|---|
| mar | 39 | 105 | 32.850 |
| abr | 84 | 235 | 57.785 |
| mai | 87 | 218 | 67.722 |
| jun | 103 | 319 | 101.670 |
| jul | 81 | 198 | 61.912 |
| ago | 135 | 338 | 89.484 |
| set | 144 | 373 | 86.936 |
| out (parcial) | 75 | 185 | 43.090 |
| **Total** | **750** | **1.976** | **≈ 542.500** |

- Ticket médio: **R$ 723 por reserva**, **R$ 275 por pessoa**.
- Sinal médio: **43%** do valor; o restante é pago à operadora no embarque.
- 21 canceladas, 6 no-show, 9 cortesias.
- Regime recente: ≈ 120-145 reservas e R$ 85-100 mil por mês.

## Divisão do valor (set-out/2026, 219 reservas com netos preenchidos, R$ 130 mil)
| Parte | % do vendido |
|---|---|
| Operadora (neto operadora) | **78%** |
| Inside (neto Inside − neto operadora) | **15%** |
| Promotor (preço − neto Inside) | **6%** |
→ Intermediação total ≈ **22%**.

## Quem é o cliente
- Idioma: **95% espanhol**, 4% português, 1% inglês.
- Origem (DDI do telefone): Chile 148, Argentina 137, Colômbia 83, México 78, Peru 71, Equador 23, Uruguai 19, Brasil 27, EUA/Canadá 14, Espanha 11.
- **20% dos clientes compram 2 ou mais passeios** (535 clientes únicos).

## Quando compram
- Antecedência mediana: **1 dia**.
- **75% compram até a véspera**; 9% no mesmo dia; só 11% com 3 dias ou mais.

## Como pagam o sinal
Pix 72% · cartão 11% (com acréscimo de 5%) · dinheiro ≈ 9% · sem sinal 5%.
O sinal fica com a empresa em ≈ 75% dos casos; com promotor ou parceiro no restante. Há várias contas/maquininhas (Inside Santander, "RS"/Rio Sessions, XP/Stone, Cielo link, Che Lagarto).

## Passeios e operadoras
- Mais vendidos (reservas): Arraial 134, Um Dia no Rio 112, SUP 90, Favela 70, Angra (todas as variações) ≈ 115, City Tour/Corcovado ≈ 40.
- Maior receita: Um Dia no Rio R$ 124 mil, Arraial R$ 86 mil, SUP R$ 32 mil, Helicóptero R$ 30 mil.
- Operadoras: **Alegria ≈ 35% do vendido**, Sergio 12%, Pepe 8%, Falcon 7%, Rio 40 7%. Concentração alta.
- Canais/vendedores: Sari 183 reservas, Natalia/Nati 174, Denise 51, Facu 45, **Che Lagarto (hostel) 52**, Central de Reservas 29.

## Custos (outubro/2026, mês parcial, inclui festas)
- Fixos ≈ R$ 15,3 mil (aluguel R$ 5 mil, folha R$ 5,5 mil, comissões turismo R$ 1,9 mil e festas R$ 1,5 mil, mídia R$ 1,2 mil).
- Variáveis ≈ R$ 5,3 mil (ads R$ 2,5 mil, flyer/catálogo R$ 1,3 mil).
- Total ≈ R$ 20,5 mil. "Receita Turismo" ainda não lançada no mês.

## Dores visíveis nas observações da planilha
- Dinheiro espalhado em várias contas e com promotores ("sinal com Facundo", "Rio Sessions", "XP Stone", "Cielo link").
- Taxas de acesso (Arraial/Angra) às vezes incluídas, às vezes não, descontadas da comissão.
- Acréscimo de 5% no cartão esquecido; diferenças de neto acertadas depois por Pix.
- Cancelamento por clima (SUP, barco) com devolução manual de sinal.
- Pax que não embarcam e grupos que mudam de tamanho.
