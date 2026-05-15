# Gerenciador de Bookmarks do Chrome

Ferramenta em Python (stdlib apenas) para leitura, análise e reorganização
automática dos bookmarks do Google Chrome.

## Recursos

- **Leitura** automática do arquivo `Bookmarks` do Chrome (Linux, macOS, Windows)
- **Análise estatística**: total de bookmarks, pastas, profundidade,
  duplicados, URLs inválidas e top domínios
- **Categorização** em dois modos:
  - **Heurístico** (default): 13 categorias fixas (Desenvolvimento, Aprendizado,
    IA e Pesquisa, Redes Sociais, Notícias, Entretenimento, Compras, Email e
    Comunicação, Trabalho e Produtividade, Documentos e Armazenamento, Finanças,
    Viagens, Outros). Sem dependências externas.
  - **Via IA** (`--ai`): a Claude propõe uma taxonomia de 2 níveis
    (categoria > subcategoria) adaptada *aos seus* bookmarks, e em seguida
    classifica cada item nessa árvore. Requer `ANTHROPIC_API_KEY`.
- **Reorganização segura**: gera um novo arquivo `Bookmarks` em formato
  compatível com o Chrome, sem nunca sobrescrever o original automaticamente

## Requisitos

- Python 3.11+
- Modo heurístico: **sem dependências externas** (apenas biblioteca padrão)
- Modo IA: `pip install -r requirements.txt` (instala `anthropic`) e
  `export ANTHROPIC_API_KEY=sk-ant-...`
- `pytest` para rodar os testes

## Localização do arquivo `Bookmarks` do Chrome

| Sistema  | Caminho                                                                   |
|----------|---------------------------------------------------------------------------|
| Linux    | `~/.config/google-chrome/Default/Bookmarks`                               |
| macOS    | `~/Library/Application Support/Google/Chrome/Default/Bookmarks`           |
| Windows  | `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Bookmarks`                |

Para outros perfis, troque `Default` por `Profile 1`, `Profile 2`, etc.

## Uso (CLI)

Rode a partir desta pasta (`bookmarks/`):

```bash
python -m bookmarks_manager <comando> [opções]
```

### Comandos disponíveis

#### `path` — mostra o caminho padrão do arquivo Bookmarks

```bash
python -m bookmarks_manager path
python -m bookmarks_manager path --profile "Profile 1"
```

#### `analyze` — estatísticas sobre seus bookmarks

```bash
python -m bookmarks_manager analyze
python -m bookmarks_manager analyze --path /caminho/para/Bookmarks
python -m bookmarks_manager analyze --top 20
```

Saída de exemplo:

```
=== Relatório de Bookmarks ===
Total de bookmarks: 10
Total de pastas:    6
Profundidade máxima: 2
Pastas vazias:      1

Top 10 domínios:
     2  github.com
     1  stackoverflow.com
     ...

URLs duplicadas: 1
  https://github.com
    - GitHub
    - GitHub Duplicado
```

#### `suggest` — sugestão de reorganização por categoria

```bash
python -m bookmarks_manager suggest
python -m bookmarks_manager suggest --detailed
python -m bookmarks_manager suggest --detailed --sample 10
python -m bookmarks_manager suggest --keep-duplicates
```

#### `reorganize` — gera novo arquivo Bookmarks reorganizado

```bash
python -m bookmarks_manager reorganize -o /tmp/Bookmarks
python -m bookmarks_manager reorganize -o /tmp/Bookmarks --target-root other
python -m bookmarks_manager reorganize -o /tmp/Bookmarks --force
```

> **Importante:** o comando **não sobrescreve** o arquivo do Chrome.
> Ele apenas escreve um novo arquivo no caminho indicado por `-o`.
> Para aplicar a reorganização:
>
> 1. Feche o Google Chrome **completamente**
> 2. Faça backup do arquivo `Bookmarks` original
> 3. Copie o arquivo gerado para o local original
> 4. Abra o Chrome novamente

## Modo IA: taxonomia adaptativa

A IA é usada em **duas etapas separadas**:

1. **Propor a árvore** (1 chamada Opus 4.7): a Claude lê uma amostra dos
   seus bookmarks (nome + domínio, **sem path nem query** para preservar
   privacidade) e propõe uma árvore de 2 níveis adaptada ao seu perfil.
   Salva em `taxonomy.json` — editável a mão.
2. **Classificar** (N batches Haiku 4.5 em paralelo): com a taxonomia em
   mãos, cada bookmark recebe um par `(categoria, subcategoria)`. Paths
   inválidos caem em `Outros`.

### Workflow recomendado

```bash
# 1. Gerar a taxonomia (1 vez, ou com --refresh para regenerar)
python -m bookmarks_manager propose-tree -o taxonomy.json

# 2. Ver a distribuição sugerida antes de aplicar
python -m bookmarks_manager suggest --ai --taxonomy taxonomy.json --detailed

# 3. Aplicar
python -m bookmarks_manager reorganize --ai --taxonomy taxonomy.json -o /tmp/Bookmarks
```

### Custo estimado

Com Haiku 4.5 para classificação e Opus 4.7 para a taxonomia:

| Bookmarks | Propor árvore (Opus) | Classificar (Haiku) | **Total** |
|-----------|----------------------|---------------------|-----------|
| 500       | ~US$ 0,40            | ~US$ 0,05           | **~US$ 0,45** |
| 1.000     | ~US$ 0,60            | ~US$ 0,10           | **~US$ 0,70** |
| 5.000     | ~US$ 0,60            | ~US$ 0,50           | **~US$ 1,10** |

A taxonomia tem amostra limitada a 500 bookmarks (parâmetro `--sample-size`),
então o custo dela não cresce indefinidamente. A categorização é proporcional
ao número total.

### Privacidade

A IA recebe **apenas o nome do bookmark e o domínio** (não a URL completa,
não o path, não query strings). A chave de API é lida exclusivamente de
`ANTHROPIC_API_KEY` no ambiente, nunca persistida em disco.

## Uso (API Python)

```python
from bookmarks_manager import (
    read_bookmarks,
    analyze,
    suggest_reorganization,
    build_reorganized_tree,
)

file = read_bookmarks()  # auto-detecta perfil padrão
print(analyze(file).format_report())

suggestion = suggest_reorganization(file)
print(suggestion.format_detailed_report())

new_tree = build_reorganized_tree(file)
# new_tree.to_chrome_dict() retorna um dict pronto para serializar como JSON
```

### API com IA

```python
from bookmarks_manager import (
    read_bookmarks,
    load_taxonomy,
    save_taxonomy,
    ai_suggest_reorganization,
    build_tree_from_suggestion,
)
from bookmarks_manager.ai_taxonomy import propose_taxonomy

file = read_bookmarks()
bookmarks = list(file.iter_bookmarks())

# 1. Propor (1 chamada Opus)
taxonomy = propose_taxonomy(bookmarks)
save_taxonomy(taxonomy, "taxonomy.json")

# 2. Categorizar e ver distribuição
suggestion = ai_suggest_reorganization(file, taxonomy)
print(suggestion.format_detailed_report())

# 3. Construir nova árvore Chrome
new_tree = build_tree_from_suggestion(suggestion, file)
```

## Estrutura do projeto

```
bookmarks_manager/
├── __init__.py
├── __main__.py         # python -m bookmarks_manager
├── reader.py           # parsing do JSON do Chrome
├── analyzer.py         # estatísticas e detecção de duplicados
├── categorizer.py      # heurísticas de categorização (sem IA)
├── taxonomy.py         # tipos Taxonomy / Category / Subcategory + I/O JSON
├── ai_client.py        # AsyncAnthropic + retry + UsageTracker
├── ai_taxonomy.py      # propor árvore via Opus (tool_use)
├── ai_categorizer.py   # classificar bookmarks via Haiku em batches
├── reorganizer.py      # construção da nova árvore (heurística + IA)
└── cli.py              # argparse + subcomandos
tests/
├── fixtures/sample_bookmarks.json
├── test_reader.py
├── test_analyzer.py
├── test_categorizer.py
├── test_reorganizer.py
├── test_taxonomy.py
├── test_ai_taxonomy.py
├── test_ai_categorizer.py
├── test_ai_integration.py
└── test_cli.py
```

## Rodando os testes

A partir desta pasta (`bookmarks/`):

```bash
python -m pytest tests/
```

## Limitações conhecidas

- **Modo heurístico**: a categorização usa regras manuais (lista de
  domínios e palavras-chave). Sites desconhecidos caem em **Outros**.
  Para melhorar, edite `bookmarks_manager/categorizer.py` *ou* use
  `--ai`.
- **Modo IA**: a taxonomia depende da amostra (até 500 bookmarks por
  default). Coleções muito heterogêneas podem se beneficiar de aumentar
  `--sample-size`. O JSON gerado é editável a mão antes de classificar.
- O Chrome usa um campo `checksum` para detectar adulteração. Ao
  substituir o arquivo manualmente, o Chrome recalcula o checksum no
  próximo carregamento — não há problema em deixar esse campo vazio.
- Pastas customizadas existentes na barra de favoritos são desfeitas na
  reorganização. Faça backup se quiser preservá-las.
