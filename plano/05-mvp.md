# MVP e produto

> v2 (2026-10-17). Definido com o fundador. Substitui a v1, que assumia reaproveitar o backend do Rio Manager e o modelo de roteamento (ambos descartados). Sistema **novo e independente**; a documentação da Inside é só referência de domínio.

## Objetivo
Colocar no ar um marketplace onde as operadoras da rede do sócio vendem seus passeios no Rio diretamente para turistas, com pagamento na plataforma, e medir H1, H2, H5 e H9.

## Pendências de definição (aguardando o fundador)
| Tema | Recomendação | Status |
|---|---|---|
| Plataforma | **Site responsivo e instalável (PWA) primeiro**; apps iOS/Android (Expo/React Native, mesma API) na fase 2 | ✅ decidido (2026-10-18) |
| Confirmação | **Reserva instantânea como padrão** (vaga na agenda = voucher na hora). Confirmação manual só como exceção, com prazo de 15-30 min | ✅ decidido (2026-10-18) |
| Comissão da plataforma | **10% padrão**, editável por operadora no painel admin | ✅ decidido (2026-10-18) |
| Promotores de praia | Fora do escopo por enquanto | ✅ decidido (2026-10-18) |

## Escopo

### Turista
| Prioridade | Funcionalidade |
|---|---|
| Must | Catálogo aberto, sem login, em PT/ES/EN |
| Must | Busca e filtros: nome, categoria, preço, data, horário, disponibilidade |
| Must | **Mapa** com passeios próximos da localização do turista ou de um endereço informado |
| Must | Página do passeio: fotos, descrição, inclui/não inclui, ponto de encontro, horários, preço por adulto e criança, operadora, política de cancelamento |
| Must | Reserva: escolher horário e nº de pessoas; ver total |
| Must | **Login obrigatório para reservar**: "Entrar com Google" ou código por e-mail (sem senha); WhatsApp pedido uma vez |
| Must | Pagamento do **valor total** por Pix ou cartão |
| Must | **Reserva instantânea**: pagou com vaga na agenda → voucher na hora (tela, e-mail e WhatsApp) |
| Must | Disponibilidade exibida como "disponível" / "últimas vagas" (não o número exato) |
| Should | Passeios sob consulta (confirmação manual): prazo curto e reembolso automático se não confirmados; não aparecem na busca para o mesmo dia |
| Must | "Minhas reservas": status, voucher, cancelamento conforme a política |
| Should | Avaliação depois do passeio (pedido por e-mail) e filtro por avaliação |
| Could | Favoritos, sugestão de outros passeios |

### Operadora
| Prioridade | Funcionalidade |
|---|---|
| Must | Acesso por convite (onboarding das operadoras da rede do sócio) |
| Must | Cadastro de passeios: textos em PT/ES/EN, fotos, categoria, preço por faixa etária, local no mapa, ponto de encontro, política de cancelamento |
| Must | **Agenda**: horários recorrentes, vagas por horário, bloqueio de datas, **fechamento de vendas X horas antes da saída** |
| Must | Notificação de nova reserva (e-mail e WhatsApp via link) |
| Should | Para passeios sob consulta: aceitar/recusar no prazo |
| Must | Lista de reservas por dia (lista de embarque) |
| Must | Extrato: reservas, comissão e repasses |

### Admin (interno)
| Prioridade | Funcionalidade |
|---|---|
| Must | Aprovar operadoras e passeios |
| Must | Comissão padrão de 10%, editável individualmente por operadora |
| Must | Ver reservas, cancelar e reembolsar |
| Must | Controle de repasses às operadoras |
| Must | Painel de métricas (ver abaixo) |

## Fluxo da reserva
1. O turista escolhe passeio, data, horário e pessoas; a vaga é **reservada temporariamente** durante o checkout (ex.: 10-15 min).
2. Ele faz login e paga o total (Pix ou cartão).
3. Pagamento aprovado → reserva **confirmada na hora**, vaga descontada, voucher enviado, operadora notificada.
4. Exceção (passeio sob consulta): reserva aguardando confirmação por 15-30 min; sem resposta ou recusa → **reembolso automático**.
5. O passeio acontece → o valor fica liberado para repasse (menos a comissão).

Operadoras com muitas recusas ou cancelamentos perdem posição na busca.

## Proteção contra desintermediação
Risco: o turista vê o passeio na plataforma e compra direto com a operadora. É menor que em serviços recorrentes (o turista fica poucos dias e compra 1-2 passeios), mas precisa de cuidado desde o MVP.

**A. Esconder o caminho até a operadora (produto, Must)**
- Antes da reserva, não exibir telefone, site, redes sociais nem nome comercial completo da operadora.
- Mapa com **região aproximada**; ponto de encontro exato só no voucher.
- Moderação de descrições e fotos para barrar contatos (telefone, @, QR, links).
- Vagas como "disponível" / "últimas vagas", não o número exato.

**B. Valer a pena para o turista**
- **Paridade de preço** no contrato com a operadora (não vender mais barato direto a quem veio da plataforma). Validar com advogado.
- Garantias da plataforma: reembolso por clima ou cancelamento, suporte no idioma do turista, cartão internacional, avaliações.

**C. Valer a pena para a operadora**
- Pagamento antecipado (fim do no-show), agenda e lista de embarque organizadas, clientes novos.
- Comissão justa (comissão alta incentiva o desvio).
- Termos de uso: aliciar cliente da plataforma para venda por fora gera punição ou remoção.

## Fora do MVP
Apps nativos (se confirmado site primeiro), chat, cupons, preço dinâmico, módulo de promotores, outras cidades, carrinho com vários passeios, integração com agendas externas, repasse 100% automático (se o gateway não oferecer).

## Arquitetura (proposta)
- **Backend:** Python (FastAPI), PostgreSQL (com PostGIS para busca por proximidade).
- **Redis:** fila de tarefas e cache (expirar reservas temporárias e prazos de confirmação, enviar notificações, processar reembolsos e repasses). **As reservas ficam no Postgres**, não no Redis.
- **Frontend web:** React Router v7 em modo framework (Vite), com a fundação do Rio Manager (shadcn, Tailwind, TanStack Query). SSR nas páginas públicas; painel e admin só no navegador. Detalhes em `spec.md` §3.
- **Mapa:** MapLibre GL JS + OpenFreeMap; geocodificação via Photon/Nominatim (100% gratuito).
- **Login:** Google OAuth e código por e-mail.
- **Pagamentos:** gateway com **contas de marketplace / split e repasse sob demanda** (candidatos: Pagar.me, Mercado Pago, Asaas, Iugu, Stripe Connect). Validar: Pix, cartões estrangeiros (Chile, Argentina etc.), retenção até o passeio, taxas.
- **Fase 2 (apps):** Expo/React Native consumindo a mesma API; build de iOS na nuvem (EAS), sem Mac.

## Métricas desde o primeiro dia
- Oferta (H1): operadoras ativas, passeios publicados, % de agendas atualizadas.
- Demanda (H2, H9): visitas, buscas, visitas por passeio, início de checkout, login concluído, pagamento aprovado, conversão por etapa.
- Operação (H1, H5): % de reservas instantâneas, cancelamentos pela operadora, reembolsos, agendas atualizadas.
- Desintermediação (H10): recompra na plataforma, denúncias, queda de vendas por operadora sem motivo aparente.
- Negócio: vendas por semana, ticket, comissão, recompra.

## Critério de lançamento
- Operadoras da rede do sócio cadastradas com os passeios mais vendidos (Arraial, Um Dia no Rio, SUP, Favela, Angra, City Tour) e agendas preenchidas.
- Compra real ponta a ponta em produção (pagamento, confirmação, voucher, reembolso).
- Primeiras reservas pagas por turistas reais.

## Estimativa (1 dev em tempo integral, só web)
> Estimativa grosseira, para planejamento. Em meio período, multiplicar por ~2. Revisar depois da escolha do gateway.

| Fase | Semanas | Entregas | Pronto quando |
|---|---|---|---|
| **0. Decisões e conteúdo** (em paralelo, com o sócio) | — | Escolha e teste do gateway (Pix, cartões estrangeiros, marketplace); contrato com operadoras (comissão, paridade, termos); Cadastur das operadoras; fotos, textos e preços dos primeiros passeios | Gateway testado com pagamento real; operadoras iniciais com contrato |
| **1. Fundação** | 2 | Repositório, FastAPI, Postgres + PostGIS, Redis + worker de tarefas, login (Google + código por e-mail), modelo de dados (operadora, passeio, traduções, horários e vagas, reserva, pagamento, repasse), deploy inicial | API no ar com login funcionando |
| **2. Painel da operadora** | 2-3 | Convite e onboarding, cadastro de passeios com fotos e textos PT/ES/EN, local no mapa, agenda recorrente com vagas, bloqueios e fechamento antes da saída, lista de reservas | Uma operadora real cadastra um passeio completo sozinha |
| **3. Site do turista** | 3-4 | Catálogo trilíngue com renderização no servidor (SEO), busca e filtros, **mapa com busca por proximidade**, página do passeio, seleção de horário e pessoas com vaga reservada temporariamente | Turista encontra e escolhe um passeio no celular, em 3 idiomas |
| **4. Pagamento e reserva** | 2-3 | Checkout no gateway (Pix e cartão), webhooks idempotentes, reserva instantânea, voucher (PDF/QR), e-mails e WhatsApp, cancelamento conforme política, reembolso, retenção e repasse | Compra real ponta a ponta, com reembolso testado |
| **5. Admin, proteção e lançamento** | 2 | Aprovação de operadoras e passeios, comissão editável, controle de repasses, painel de métricas, moderação de contatos, termos de uso e privacidade (LGPD), monitoramento de erros, backups | Lançamento com as operadoras da rede |
| **Folga** | 2 | Ajustes e imprevistos | — |
| **Total** | **≈ 13-16 semanas** | | |

**Fase 2 do produto (depois do MVP):** apps iOS/Android com Expo consumindo a mesma API; avaliações com filtro; confirmação manual para passeios sob consulta, se ainda não feita.

## Riscos
- As operadoras não manterem a agenda atualizada (H1) → overbooking, cancelamentos e reembolsos. Com reserva instantânea, esse é o risco operacional nº 1.
- Desintermediação: turistas e operadoras fechando por fora (H10).
- Falta de canal de aquisição de turistas (H3).
- Gateway não aceitar bem cartões estrangeiros ou não suportar marketplace como precisamos (H8).
- Regulação: operadoras sem Cadastur (H6).
