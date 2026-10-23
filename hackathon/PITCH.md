# Pitch e demo

> A apresentação **conta muito**: é por ela que o júri avalia a solução (Regulamento, Art. 1.º, 3).
> Reservar pelo menos **1h30 das 6h** para preparar e ensaiar o pitch e a demo.

**Formato:** pitch de **5 minutos**, que pode estender-se até **8 minutos** se o júri fizer perguntas
e quiser saber mais do projeto. Prova no **sábado, 24/10**.

## Estrutura (mapeada aos critérios do júri)

| # | Bloco | Critério do júri | Tempo (pitch de ~5 min) | Conteúdo |
|---|-------|------------------|:-----:|----------|
| 1 | Gancho | — | 0:20 | Uma frase/número que mostra a dor. |
| 2 | **Problema** | exposição do problema | 0:50 | Quem sofre, quanto custa, porque é que hoje não está resolvido. |
| 3 | Solução | — | 0:30 | O produto numa frase e o que muda para o utilizador. |
| 4 | **Demo** | demonstração | 1:40 | Ao vivo: um evento real atravessa o sistema de ponta a ponta. |
| 5 | **Arquitetura** | arquitetura desenvolvida | 0:50 | Um diagrama: fontes → Coreflux (Actions/Models/Connectors) → saídas. Destacar o que corre **dentro do broker**. |
| 6 | **Maturidade** | maturidade | 0:40 | O que é real vs. simulado, testes, segurança (Rules), escala, próximos passos. |
| 7 | Fecho | — | 0:10 | A frase do produto + nome da equipa. |

## Guião (Vale, ~5 min)

| # | Bloco | Fala / ecrã |
|---|-------|-------------|
| 1 | Gancho | *"Ontem, em Portugal, o mesmo kWh custou 1000 vezes mais às 19h do que ao meio-dia."* Gráfico real da REN de 22/10. |
| 2 | Problema | Restaurante com tarifa indexada: câmara frigorífica, máquina da loiça, carrinha elétrica. A hora mais barata desta semana foi às 12h, 13h, 11h, 11h, **1h**, 14h, 14h... Um temporizador não acompanha isto, e ninguém consulta o OMIE todos os dias às 13h. |
| 3 | Solução | *"O Vale percebe o que cada equipamento precisa, a partir de uma frase, põe o consumo nos vales do preço e liga os equipamentos sozinho, sem nunca pôr a comida em risco."* |
| 4 | Demo | Ver o guião abaixo. |
| 5 | Arquitetura | Um diagrama (README §3). Mensagem: **tudo o que decide vive no broker**: Connectors REST e LLM, Python dentro do broker, Actions, Rules. Fora dele só ficam o simulador dos equipamentos e o ecrã. |
| 6 | Maturidade | Real vs. simulado, *guardrails* acima do plano, o LLM nunca atua, modo seguro sem internet, Rules, testes (incluindo o dia de 100 quartos de hora a 25/10), auditoria em CSV. |
| 7 | Fecho | *"Vale: a energia mais barata é a que se gasta na hora certa." Equipa O(1/n).* |

## Guião da demo (1:40)

Estado inicial: `00-setup.lotnb` corrido, preços de hoje já em `copilot/market/prices`, todos os equipamentos em `advise`,
relógio parado no slot 32 (08:00), Mailpit vazio, CSV limpo.

1. **(0:15) Preços reais.** O dashboard mostra a curva de hoje vinda da REN, com o vale do meio-dia bem visível.
2. **(0:25) Frase → tarefas.** Escrever: *"A carrinha chega às 9h e tem de sair às 17h com 30 kWh. A loiça do almoço
   tem de estar lavada antes das 19h."* O JSON das 2 tarefas aparece, e os planos ficam sombreados sobre a curva:
   "poupança prevista: X €".
3. **(0:10) Aconselhar → agir.** Um conselho aparece em modo `advise`. Passar a carrinha e a loiça para `auto`.
4. **(0:25) ▶ Simular o dia** (1 s = 15 min). Os equipamentos ligam-se sozinhos nos vales, a câmara pré-arrefece antes do
   pico das 18h e o contador de € poupados sobe.
5. **(0:20) Imprevisto.** Clicar em "porta aberta" na câmara: a temperatura passa os 5 °C e o `Guard` liga a câmara **mesmo com preço alto**.
   Chega o email ao Mailpit ("Câmara 1 fora da faixa") e aparece uma linha no CSV com a razão `guardrail`.
6. **(0:05) Prova.** O HUB mostra as Actions e os Connectors a correr no broker.

**Plano B (por ordem):**
- **o LLM falha ou demora:** botões com tarefas predefinidas que publicam o mesmo `copilot/tasks/new`;
- **sem internet:** preços de 22/10 em cache (ficheiro + retained) e o LLM via predefinidas;
- **o dashboard falha:** o Panel do HUB e o MQTT Explorer;
- **falha tudo:** vídeo da demo gravado às H+4:30.

## Checklist da demo

- [ ] Um **guião escrito** da demo: cada clique e cada mensagem publicada.
- [ ] Um único caminho "feliz", ensaiado **pelo menos 3 vezes**, de preferência na máquina da apresentação.
- [ ] Estado inicial reproduzível (script ou `00-setup.lotnb` que repõe a config retained).
- [ ] Dados que provocam o evento interessante **a pedido** (botão, script Python, publish no HUB),
      em vez de esperar por um timer.
- [ ] **Plano B:** vídeo da demo gravado em ecrã + dados simulados se um sensor ou API externa falhar.
- [ ] Sem internet? Saber o que deixa de funcionar (Connectors REST) e ter alternativa.
- [ ] Fonte grande no HUB/terminal; fechar notificações; separadores preparados.

## Perguntas do júri (até 3 min)

Os 3 minutos extra são uma oportunidade: as perguntas mostram interesse. Preparar respostas curtas
(≤ 30 s) e, quando fizer sentido, um **slide de reserva** para cada uma:

| Pergunta provável | Resposta / slide de reserva |
|-------------------|-----------------------------|
| Porquê Coreflux e não um script/servidor normal? | O broker já é o sítio por onde passam os dados dos equipamentos. Pôr lá a decisão (Actions, `CALL PYTHON`, `CALL LLM`) elimina um servidor intermédio, um ponto de falha e latência, e a decisão continua a funcionar perto do equipamento, mesmo com a cloud em baixo. |
| O que é real e o que é simulado? | Real: os preços da REN, o LLM, o planeamento, o despacho, os *guardrails*, os emails e a auditoria. Simulado: os equipamentos e o relógio acelerado. Para ir para o real basta pôr um relé/PLC a subscrever o mesmo `.../command`. |
| Como escalaria para N utilizadores/dispositivos? | Os equipamentos são configuração (`config/devices/<id>`) e não código. Um broker por loja, ligado a um broker central, para cadeias. O planner é puro e não tem estado. |
| E a segurança (quem pode publicar/alterar config)? | Rules: só as Actions publicam comandos para os equipamentos, o dashboard só envia pedidos e muda o modo, e cada equipamento só publica a sua telemetria. O LLM nunca atua: a tarefa é validada por um Model antes de se planear. |
| E se o LLM se enganar? | O LLM só gera uma *proposta* de tarefa. O Model valida-a, o dono vê-a e confirma-a, e o *guardrail* protege sempre a operação. No pior caso planeia-se mal, mas nunca de forma perigosa. |
| Quanto se poupa a sério? | Só a componente de energia muda (não as redes, a potência e os impostos). Na demo mostramos € poupados nessa componente, com preços reais. A afirmação honesta é: "desloca X kWh/dia do pico para o vale". |
| Quanto custa implementar? Quem pagaria? | O dono do negócio paga uma subscrição por estabelecimento, mais relés baratos ou a integração com o controlador existente. O argumento de venda é o simulador de fatura (quanto pouparia na indexada). |
| O que fariam a seguir com mais tempo? | Integração Modbus com os controladores de frio, previsão do preço de amanhã antes das 13h, otimização da potência contratada e do autoconsumo solar, e o perfil residencial (carro elétrico). |

## Papéis no dia

Sem papéis fixos na equipa. Decidir **até à hora de almoço** quem apresenta cada bloco e quem
"conduz" a demo enquanto outro fala.

Divisão de trabalho sugerida (4 frentes em paralelo, com o mapa de tópicos do README como contrato):
**A**: broker/LoT (Connectors, `ParsePrices`, `SimClock`, `Dispatch`, `Guard`, Rules) ·
**B**: Python do planner + testes · **C**: dashboard web · **D**: LLM (`ParseIntent`), simulador de equipamentos
e, a partir de H+3, os slides.

## Plano das 6 horas

| Marco | Objetivo (verificável) |
|-------|------------------------|
| **H+0:30** | Broker e licença ativos. ⚠️ Verificados: tier da licença (LLM Connector?), `CALL PYTHON`, Connector REST com a data no endpoint, porta WebSocket. Decisões de plano B tomadas **aqui**, não mais tarde. |
| **H+1** | Os preços reais chegam a `copilot/market/prices` (retained). O planner passa nos testes. O dashboard desenha a curva. O simulador publica telemetria. |
| **H+2** | **MVP de ponta a ponta sem LLM:** uma tarefa num formulário → plano → `SimClock` → `Dispatch` → o equipamento liga no vale. A partir daqui há sempre uma demo. |
| **H+3** | O LLM converte texto em `Task` (ou plano B em Python). `Guard` + email + CSV a funcionar. Almoço; decidir quem apresenta o quê. |
| **H+4** | Rules, `Meter` (contador de €), Panel do HUB, polimento do dashboard. **H+4:30: congelar as funcionalidades e gravar o vídeo de backup.** |
| **H+4:30 → H+6** | **1h30 só para o pitch:** slides, 3 ensaios cronometrados na máquina da apresentação, perguntas do júri, repor o estado inicial. Só se corrigem bugs. |

## Preparação na véspera (sem código do produto)

O regulamento não proíbe explicitamente o trabalho prévio, mas o guião da prova só é entregue no dia, e há deteção de plágio.
Por isso, na véspera só se faz **ambiente, pesquisa e decisões**:
- `docker compose pull` e um `up` de teste. Ter a licença à mão. Instalar a extensão LoT Notebooks.
- Criar uma chave da API da Anthropic (com crédito) e testá-la com um `curl`. Fica fora do git.
- Ler a documentação: [LLM Connector](https://docs.coreflux.org/latest/lot-language/routes/ai-routes.md),
  [Python integration](https://docs.coreflux.org/latest/lot-language/actions/python-integration.md), Rules, Panels e o
  Connector REST (como pôr a data do payload no endpoint).
- Guardar os preços da REN da última semana em JSON (dados, para o plano B sem internet e para os gráficos dos slides).
- Esqueleto dos slides: gancho, problema com os números, diagrama de arquitetura.
- Combinar quem fica com cada frente (A–D) e dormir.

## Slides

`TODO`: link para os slides (Google Slides/Canva) e para o vídeo de backup.
