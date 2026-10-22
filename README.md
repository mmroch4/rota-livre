# O(1/n) — SciTeCh '26

Repositório de código e desenvolvimento da equipa **O(1/n)** no
[SciTeCh '26](https://scitech.bestporto.org/index.html) (Science and Technology Challenge),
organizado pelo BEST Porto na FCUP, a **24 e 25 de outubro de 2026**.

| Equipa |
|--------|
| Miguel |
| Victor |
| Ben    |
| Pedro  |

## As duas modalidades

O SciTeCh tem duas provas, cada uma num dia, com **6 horas de trabalho** seguidas de avaliação.
Cada pasta deste repo corresponde a uma modalidade:

| Dia | Pasta | Modalidade | O que é | Estado |
|-----|-------|------------|---------|--------|
| **Sáb. 24/10** | [`hackathon/`](hackathon/) | **Hackathon** | Solução de automação para um **problema real escolhido por nós**, construída sobre a plataforma **Coreflux** (broker MQTT + LoT). Avaliada por um pitch de 5 min com demo (até 8 min com perguntas do júri). | Tema aberto: ideia em brainstorming, setup do broker pronto. |
| **Dom. 25/10** | [`team-design/`](team-design/) | **Team Design** | Protótipo físico funcional com materiais simples e de baixo custo, que responde ao guião revelado no dia. | Esqueleto de treino (Arduino Uno + ponte H + servo), pronto a adaptar. |

## Estrutura do repositório

```text
scitech-2026/
├── README.md           # este ficheiro
├── CLAUDE.md           # contexto e convenções para agentes de IA
├── regulamento.pdf     # regulamento oficial do SciTeCh '26
├── team-design/        # firmware PlatformIO (Arduino Uno) + simulação Wokwi
└── hackathon/          # solução Coreflux: broker, código LoT, serviços, dashboard e pitch
```

## Começar

Pré-requisitos comuns (Linux ou macOS): `git`, `python3`, **Docker + Docker Compose v2** (hackathon)
e VS Code (recomendado).

```bash
git clone git@github.com:mmroch4/scitech-2026.git
cd scitech-2026
```

Depois seguir o README da modalidade:
- **Team Design:** [`team-design/README.md`](team-design/README.md)
- **Hackathon:** [`hackathon/README.md`](hackathon/README.md)

## Como trabalhamos

- **Documentação em português (PT-PT); código em inglês.** Identificadores, nomes de ficheiros,
  mensagens Serial/MQTT e tópicos ficam em inglês. Os comentários explicativos podem ficar em PT-PT.
- **Git trunk-based:** todos fazem push diretamente para `main`, com commits pequenos e frequentes.
  Antes de cada push: `git pull --rebase`. No dia da prova não há PRs (não há tempo).
- **Nunca fazer commit de segredos** (token Wokwi, código de licença Coreflux, chaves de API).
  Ficam em `.env`, que está no `.gitignore`.

## Regras do regulamento que afetam o código

Resumo do [`regulamento.pdf`](regulamento.pdf), apenas os pontos que influenciam o trabalho técnico:

- **Team Design (Art. 5.º):** só se podem usar **os materiais e ferramentas fornecidos pela organização**,
  à exceção dos computadores. As ferramentas não podem fazer parte do protótipo. Os componentes eletrónicos
  ficam com a organização no fim. Os critérios de teste só são revelados no guião, no início da prova.
- **Hackathon (Art. 1.º, 6.º):** a avaliação é feita por uma **apresentação** que cobre:
  1. a exposição do **problema**;
  2. a **demonstração** da solução;
  3. a **arquitetura** desenvolvida;
  4. a **maturidade** da solução.

  As soluções passam por **software de deteção de plágio**: não copiar código dos labs da formação
  Coreflux; escrever o nosso.
- **Creditação (Art. 13.º):** 1,5 ECTS exige participar nas **duas** modalidades com nota ≥ 10.
