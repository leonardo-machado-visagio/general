"""Proposta de taxonomia via LLM (1 chamada, modelo forte).

Recebe uma lista de bookmarks, monta amostra estratificada por domínio
(para representatividade quando a lista é grande), e pede ao modelo que
proponha uma árvore de 2 níveis (categoria > subcategoria) adaptada ao
conjunto.

A saída é forçada via tool_use para garantir formato.
"""

from __future__ import annotations

import asyncio
import random
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

from bookmarks_manager.ai_client import (
    UsageTracker,
    call_tool_use,
    get_client,
)
from bookmarks_manager.reader import Bookmark
from bookmarks_manager.taxonomy import (
    Category,
    Subcategory,
    Taxonomy,
)

TAXONOMY_MODEL = "claude-opus-4-7"
TAXONOMY_SAMPLE_MAX = 500
TAXONOMY_MAX_TOKENS = 4000
TAXONOMY_TEMPERATURE = 0.3

_SYSTEM = (
    "Você é um organizador especialista em curadoria de bookmarks. "
    "Dada uma lista de bookmarks (nome + domínio), proponha uma árvore "
    "de organização de até 2 níveis (categoria > subcategoria) que seja "
    "específica e útil para ESSE conjunto, não uma taxonomia genérica. "
    "Diretrizes:\n"
    "- Entre 6 e 12 categorias de nível 1.\n"
    "- Cada categoria deve ter entre 2 e 6 subcategorias, exceto quando "
    "  for muito específica e não comportar subdivisão (deixe lista vazia).\n"
    "- Nomes curtos (1-3 palavras), em português brasileiro.\n"
    "- Descrições de 1 frase explicando o escopo de cada categoria.\n"
    "- Inclua 'Outros' como última categoria, sem subcategorias.\n"
    "- Evite sobreposição entre categorias."
)

_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "categories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "subcategories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    },
                },
                "required": ["name", "subcategories"],
            },
        }
    },
    "required": ["categories"],
}


def _domain_of(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def stratified_sample(
    bookmarks: list[Bookmark],
    *,
    max_size: int = TAXONOMY_SAMPLE_MAX,
    seed: int = 42,
) -> list[Bookmark]:
    """Amostra estratificada por domínio.

    Preserva variedade: pega no máximo K itens por domínio antes de
    cortar no tamanho máximo. Se a lista couber inteira, retorna ela.
    """
    if len(bookmarks) <= max_size:
        return list(bookmarks)

    rng = random.Random(seed)
    by_domain: dict[str, list[Bookmark]] = defaultdict(list)
    for bm in bookmarks:
        by_domain[_domain_of(bm.url)].append(bm)

    # Round-robin entre domínios para garantir cobertura.
    domains = list(by_domain.keys())
    rng.shuffle(domains)
    for d in domains:
        rng.shuffle(by_domain[d])

    sample: list[Bookmark] = []
    while len(sample) < max_size:
        progressed = False
        for d in domains:
            if by_domain[d]:
                sample.append(by_domain[d].pop())
                progressed = True
                if len(sample) >= max_size:
                    break
        if not progressed:
            break
    return sample


def _format_bookmark_list(bookmarks: list[Bookmark]) -> str:
    lines = []
    for bm in bookmarks:
        domain = _domain_of(bm.url) or "(sem domínio)"
        name = (bm.name or "(sem título)").strip()
        lines.append(f"- {name} :: {domain}")
    return "\n".join(lines)


def _parse_response(data: dict) -> list[Category]:
    cats: list[Category] = []
    for raw in data.get("categories", []):
        name = (raw.get("name") or "").strip()
        if not name:
            continue
        subs = []
        for s in raw.get("subcategories") or []:
            sub_name = (s.get("name") or "").strip()
            if sub_name:
                subs.append(
                    Subcategory(
                        name=sub_name,
                        description=(s.get("description") or "").strip(),
                    )
                )
        cats.append(
            Category(
                name=name,
                description=(raw.get("description") or "").strip(),
                subcategories=subs,
            )
        )
    return cats


async def _propose_async(
    bookmarks: list[Bookmark],
    *,
    model: str,
    sample_size: int,
) -> Taxonomy:
    sample = stratified_sample(bookmarks, max_size=sample_size)
    user_content = (
        "Bookmarks (nome :: domínio):\n\n"
        + _format_bookmark_list(sample)
        + "\n\nProponha agora a taxonomia."
    )

    usage = UsageTracker()
    client = get_client()
    try:
        data = await call_tool_use(
            client,
            model=model,
            system=_SYSTEM,
            user_content=user_content,
            tool_name="propose_taxonomy",
            tool_schema=_TOOL_SCHEMA,
            max_tokens=TAXONOMY_MAX_TOKENS,
            temperature=TAXONOMY_TEMPERATURE,
            usage=usage,
        )
    finally:
        await client.close()

    categories = _parse_response(data)
    tax = Taxonomy(
        categories=categories,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        model=model,
        n_bookmarks_sampled=len(sample),
    )
    tax.ensure_other()
    cost = usage.cost_usd(model)
    cost_str = f"  custo: US$ {cost:.4f}" if cost is not None else ""
    print(f"Taxonomia gerada: {len(tax.categories)} categorias.{cost_str}")
    return tax


def propose_taxonomy(
    bookmarks: list[Bookmark],
    *,
    model: str = TAXONOMY_MODEL,
    sample_size: int = TAXONOMY_SAMPLE_MAX,
) -> Taxonomy:
    """Versão síncrona — embrulha a chamada asyncio internamente."""
    return asyncio.run(
        _propose_async(bookmarks, model=model, sample_size=sample_size)
    )
