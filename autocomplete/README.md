# Autocomplete demo — distribuição da próxima palavra

Script que faz 30.000 chamadas paralelas ao Claude (10k por prompt,
3 prompts) com prefill para mostrar empiricamente como adicionar
contexto numa frase incompleta concentra a distribuição da próxima
palavra gerada pelo modelo.

Usado em aula introdutória de LLMs para advogados.

## Como funciona

Para cada uma de 3 frases incompletas com nível crescente de contexto,
o script envia a frase como mensagem `assistant` (prefill) e pede ao
modelo que continue. Roda 10k chamadas por frase com temperatura 1.0,
extrai a primeira palavra de cada resposta, conta frequências e gera
gráficos comparativos.

As 3 frases:

| Nível | Prefill |
|-------|---------|
| Pouco contexto | "A ação foi" |
| Contexto médio | "A ação de despejo foi" |
| Muito contexto | "Após o inquilino purgar a mora dentro do prazo legal, a ação de despejo foi" |

O efeito esperado (confirmado na última rodada): conforme aumenta o
contexto jurídico, a distribuição da próxima palavra fica mais
concentrada. Com a frase completa em Q3, 41% das respostas começam
com "arquivada" — comportamento que reflete a doutrina processual
civil sobre purga da mora em ação de despejo.

## Pré-requisitos

- Python 3.10+
- Chave da API Anthropic em `ANTHROPIC_API_KEY`

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Como rodar

```bash
python autocomplete_simulation.py
```

Os artefatos saem em `output/` (script-relative — não depende de onde
você roda):

- `output/raw_results.json` — 30k respostas brutas (auditoria)
- `output/distribuicao.xlsx` — uma aba por pergunta + aba resumo
- `output/distribuicao.html` — 3 gráficos de barras horizontais com
  Chart.js, abre em qualquer browser

## Parâmetros

Editáveis no topo do script:

| Variável | Default | O quê |
|----------|---------|-------|
| `N_PER_QUESTION` | 10000 | Chamadas por pergunta |
| `CONCURRENCY` | 50 | Tarefas simultâneas (semáforo asyncio) |
| `TEMPERATURE` | 1.0 | Temperatura — 1.0 mostra distribuição natural |
| `MAX_TOKENS` | 5 | Janela de saída — apertado pra "primeira palavra" |
| `PRIMARY_MODEL` | claude-haiku-4-5 | Modelo principal |
| `FALLBACK_MODEL` | claude-haiku-4-5 | Fallback se o primário não responder |

## Custo e tempo

Com `N_PER_QUESTION=10000` (30k calls totais) no Haiku 4.5:
~US$ 1-2, ~30 min (limitado por rate limit do tier).

Para subir pra Opus 4.7 mantendo 10k: troque `PRIMARY_MODEL`
para `claude-opus-4-7`. Custo sobe pra ~US$ 20-25.

## Limitações conhecidas

- `MAX_TOKENS=5` pode truncar palavras longas. Na rodada do Haiku,
  "arquivada" aparece em parte como "arquiv" (~10% em Q3).
  Bumpar pra 8 resolve mas pode misturar primeira+segunda palavra
  no `extract_first_word`.
- Sem prompt caching. Cada chamada manda a instrução de novo.
  Para Haiku custa pouco, mas se rodar com Opus vale acrescentar.
