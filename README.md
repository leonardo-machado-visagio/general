# general

Repositório de utilitários e demos em Python. Cada subpasta é um
projeto independente com seu próprio README e dependências.

## Projetos

### [`bookmarks/`](./bookmarks/) — Gerenciador de bookmarks do Chrome

Ferramenta CLI em Python para ler, analisar e reorganizar os bookmarks
do Chrome. Dois modos de categorização:

- **Heurístico** (stdlib apenas): 13 categorias fixas por domínio.
- **Via IA** (`--ai`): Claude propõe taxonomia de 2 níveis adaptada aos
  seus bookmarks e classifica cada item nela.

Inclui UI standalone (`index.html`) e suíte de testes (`pytest`).
Ver [bookmarks/README.md](./bookmarks/README.md).

### [`autocomplete/`](./autocomplete/) — Demo de autocomplete LLM

Script que faz 30k chamadas paralelas ao Claude com prefill para
mostrar empiricamente como mais contexto na frase concentra a
distribuição da próxima palavra. Usado em aula de LLMs para advogados.

Ver [autocomplete/README.md](./autocomplete/README.md).

## Estrutura

```
.
├── bookmarks/
│   ├── bookmarks_manager/   # pacote Python (inclui módulos de IA opcionais)
│   ├── tests/
│   ├── index.html
│   ├── requirements.txt     # anthropic (opcional, só para modo IA)
│   └── README.md
└── autocomplete/
    ├── autocomplete_simulation.py
    ├── requirements.txt
    ├── output/              # artefatos da última rodada
    └── README.md
```
