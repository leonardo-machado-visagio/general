# Gerenciador de Bookmarks do Chrome

Ferramenta em Python (stdlib apenas) para leitura, análise e reorganização
automática dos bookmarks do Google Chrome.

## Recursos

- **Leitura** automática do arquivo `Bookmarks` do Chrome (Linux, macOS, Windows)
- **Análise estatística**: total de bookmarks, pastas, profundidade,
  duplicados, URLs inválidas e top domínios
- **Categorização** heurística em 13 categorias (Desenvolvimento, Aprendizado,
  IA e Pesquisa, Redes Sociais, Notícias, Entretenimento, Compras, Email e
  Comunicação, Trabalho e Produtividade, Documentos e Armazenamento, Finanças,
  Viagens, Outros)
- **Reorganização segura**: gera um novo arquivo `Bookmarks` em formato
  compatível com o Chrome, sem nunca sobrescrever o original automaticamente

## Requisitos

- Python 3.11+
- Sem dependências externas (apenas biblioteca padrão)
- `pytest` para rodar os testes

## Localização do arquivo `Bookmarks` do Chrome

| Sistema  | Caminho                                                                   |
|----------|---------------------------------------------------------------------------|
| Linux    | `~/.config/google-chrome/Default/Bookmarks`                               |
| macOS    | `~/Library/Application Support/Google/Chrome/Default/Bookmarks`           |
| Windows  | `%LOCALAPPDATA%\Google\Chrome\User Data\Default\Bookmarks`                |

Para outros perfis, troque `Default` por `Profile 1`, `Profile 2`, etc.

## Uso (CLI)

Execute como módulo:

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

## Estrutura do projeto

```
bookmarks_manager/
├── __init__.py
├── __main__.py        # python -m bookmarks_manager
├── reader.py          # parsing do JSON do Chrome
├── analyzer.py        # estatísticas e detecção de duplicados
├── categorizer.py     # heurísticas de categorização
├── reorganizer.py     # construção da nova árvore
└── cli.py             # argparse + subcomandos
tests/
├── fixtures/sample_bookmarks.json
├── test_reader.py
├── test_analyzer.py
├── test_categorizer.py
├── test_reorganizer.py
└── test_cli.py
```

## Rodando os testes

```bash
python -m pytest tests/
```

## Limitações conhecidas

- A categorização é baseada em regras manuais (lista de domínios e
  palavras-chave). Sites desconhecidos caem em **Outros**. Para melhorar,
  edite `bookmarks_manager/categorizer.py`.
- O Chrome usa um campo `checksum` para detectar adulteração. Ao substituir
  o arquivo manualmente, o Chrome recalcula o checksum no próximo
  carregamento — não há problema em deixar esse campo vazio.
- Pastas customizadas existentes na barra de favoritos são desfeitas na
  reorganização. Faça backup se quiser preservá-las.
