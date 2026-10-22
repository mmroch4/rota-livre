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
| Porquê Coreflux e não um script/servidor normal? | `TODO` |
| O que é real e o que é simulado? | `TODO` |
| Como escalaria para N utilizadores/dispositivos? | `TODO` |
| E a segurança (quem pode publicar/alterar config)? | `TODO`: Rules |
| Quanto custa implementar? Quem pagaria? | `TODO` |
| O que fariam a seguir com mais tempo? | `TODO` |

## Papéis no dia

Sem papéis fixos na equipa. Decidir **até à hora de almoço** quem apresenta cada bloco e quem
"conduz" a demo enquanto outro fala.

## Slides

`TODO`: link para os slides (Google Slides/Canva) e para o vídeo de backup.
