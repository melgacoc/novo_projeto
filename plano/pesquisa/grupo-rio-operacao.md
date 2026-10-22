# Operação atual do sócio: Grupo Rio / agência Inside

Fonte: documentação do Rio Manager em `../grupo_rio/manager/` (knowladgebase.md, spec.md, dashboards.md, perguntas-cliente.md), lida em 2026-10-17.
O Rio Manager é o sistema interno (backoffice) que o fundador está desenvolvendo para o grupo. É uma prova de conceito (PoC).

## Quem é
- **Grupo Rio:** agência de passeios **Inside**, boate/festas e hostel (Che Lagarto), no Rio de Janeiro.
- A Inside é **agência intermediária**: quem executa os passeios são as operadoras parceiras (ex.: Havana, Sérgio, CM Nobre).
- Equipe fala **português e espanhol** (interface PT/ES). Clientes falam qualquer idioma.
- Promotores trabalham na praia e na recepção. Os mesmos promotores captam para a boate (diária + comissão por entrada).

## Números
Ainda não temos números reais (os valores de `dashboards.md` são mock do seed, segundo o fundador). Pedir ao sócio: volume mensal, ticket médio, % da Inside e % do promotor por passeio.

## Passeios principais (citados nas regras de preço)
Angra dos Reis, Arraial do Cabo, Um Dia no Rio (UDR), City Tour (CCV).

## Como uma venda funciona hoje
1. O promotor aborda o turista (praia/recepção) e **negocia o preço**: pode vender qualquer valor acima do piso da Inside ("neto Inside"); o que passar do piso é dele.
2. O turista paga um **sinal** (Pix para a Inside, ou Pix/dinheiro na mão do promotor) para garantir a vaga.
3. A reserva é lançada (hoje por admin, no Rio Manager) e gera um **voucher PDF** (PT/ES), compartilhado pelo celular.
4. O turista paga o **saldo à operadora no embarque**.
5. Acertos semanais: promotor (comissões + diárias + lucro − sinais retidos) e operadora (a receber/a pagar).

## Preços
- Três camadas por passeio: **neto operadora** (custo) → **neto Inside** (piso) → **preço final** (negociado pelo promotor).
- Tarifas mudam por temporada/mês; regras de criança/idoso variam por passeio e operadora.

## Dores registradas
- Planilhas duplicadas (operacional e financeiro), falta de números em tempo real, erros de digitação.
- Vendas abaixo do piso (o sistema avisa e marca).
- Regras de cancelamento/no-show ainda indefinidas.

## O que NÃO aparece na documentação
- Venda **self-service** pelo turista (página pública, QR code, pagamento online sem o promotor).
- Site/canal online próprio da Inside.
