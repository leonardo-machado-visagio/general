# general

Repositório de utilitários e demos em Python. Cada subpasta é um
projeto independente com seu próprio README e dependências.

## Projetos

### [`bookmarks/`](./bookmarks/) — Gerenciador de bookmarks do Chrome

Ferramenta CLI em Python (stdlib apenas) para ler, analisar e
reorganizar os bookmarks do Chrome em categorias. Inclui uma UI
standalone (`index.html`) e suíte de testes (`pytest`).

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
│   ├── bookmarks_manager/   # pacote Python
│   ├── tests/
│   ├── index.html
│   └── README.md
└── autocomplete/
    ├── autocomplete_simulation.py
    ├── requirements.txt
    ├── output/              # artefatos da última rodada
    └── README.md
```
