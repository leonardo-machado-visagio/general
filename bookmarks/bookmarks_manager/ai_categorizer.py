"""Categorização em lote contra uma taxonomia existente, via LLM.

Divide os bookmarks em batches, envia cada batch ao modelo (Haiku) com a
taxonomia achatada como contexto, e recebe um mapping idx → (categoria,
subcategoria) via tool_use. Paths inválidos caem em Outros > Geral.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from urllib.parse import urlparse

from bookmarks_manager.ai_client import (
    UsageTracker,
    call_tool_use,
    get_client,
)
from bookmarks_manager.reader import Bookmark
from bookmarks_manager.taxonomy import (
    CATEGORY_OTHER,
    SUBCATEGORY_GENERAL,
    Taxonomy,
)

CATEGORIZE_MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 30
CONCURRENCY = 10
CATEGORIZE_MAX_TOKENS = 1500
CATEGORIZE_TEMPERATURE = 0.1


def _domain_of(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _format_taxonomy_for_prompt(taxonomy: Taxonomy) -> str:
    lines = ["Categorias disponíveis (categoria > subcategoria):"]
    for cat in taxonomy.categories:
        if cat.subcategories:
            for sub in cat.subcategories:
                desc = f" — {sub.description}" if sub.description else ""
                lines.append(f"- {cat.name} > {sub.name}{desc}")
        else:
            desc = f" — {cat.description}" if cat.description else ""
            lines.append(f"- {cat.name}{desc}")
    return "\n".join(lines)


def _format_batch(batch: list[tuple[int, Bookmark]]) -> str:
    lines = []
    for idx, bm in batch:
        domain = _domain_of(bm.url) or "(sem domínio)"
        name = (bm.name or "(sem título)").strip()
        lines.append(f"[{idx}] {name} :: {domain}")
    return "\n".join(lines)


def _build_tool_schema(taxonomy: Taxonomy) -> dict:
    # Enum dinâmico com nomes válidos. Modelo pode escolher
    # subcategoria vazia para categorias sem filhos.
    cat_names = [c.name for c in taxonomy.categories]
    return {
        "type": "object",
        "properties": {
            "assignments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "idx": {"type": "integer"},
                        "category": {"type": "string", "enum": cat_names},
                        "subcategory": {"type": "string"},
                    },
                    "required": ["idx", "category", "subcategory"],
                },
            }
        },
        "required": ["assignments"],
    }


_SYSTEM = (
    "Você é um classificador de bookmarks. Para cada item da lista, "
    "escolha exatamente uma categoria e uma subcategoria da taxonomia "
    "fornecida. Diretrizes:\n"
    "- Use SEMPRE nomes exatos da taxonomia (categoria e subcategoria).\n"
    "- Se a categoria escolhida não tiver subcategorias, retorne "
    "  subcategory='' (string vazia).\n"
    "- Se nenhuma categoria couber, use category='Outros' com "
    "  subcategory=''.\n"
    "- Responda para TODOS os índices do batch, sem omitir nenhum."
)


async def _categorize_batch(
    client,
    model: str,
    semaphore: asyncio.Semaphore,
    batch: list[tuple[int, Bookmark]],
    taxonomy: Taxonomy,
    tool_schema: dict,
    usage: UsageTracker,
) -> list[dict]:
    async with semaphore:
        tax_block = _format_taxonomy_for_prompt(taxonomy)
        items_block = _format_batch(batch)
        user_content = (
            f"{tax_block}\n\nBookmarks para classificar:\n{items_block}\n\n"
            "Classifique todos os itens acima."
        )
        try:
            data = await call_tool_use(
                client,
                model=model,
                system=_SYSTEM,
                user_content=user_content,
                tool_name="assign_categories",
                tool_schema=tool_schema,
                max_tokens=CATEGORIZE_MAX_TOKENS,
                temperature=CATEGORIZE_TEMPERATURE,
                usage=usage,
            )
            assignments = data.get("assignments") or []
            if not isinstance(assignments, list):
                return []
            return assignments
        except RuntimeError as e:
            print(f"  batch falhou: {e}")
            return []


def _resolve_path(
    taxonomy: Taxonomy,
    category: str,
    subcategory: str,
) -> tuple[str, str]:
    """Valida o par contra a taxonomia. Caso inválido, cai em Outros > Geral."""
    cat = taxonomy.find_category(category)
    if cat is None:
        return (CATEGORY_OTHER, "")
    if not cat.subcategories:
        return (cat.name, "")
    if not subcategory:
        # Categoria tem subs mas modelo deixou vazio: usa primeira sub.
        return (cat.name, cat.subcategories[0].name)
    norm = subcategory.strip().lower()
    for s in cat.subcategories:
        if s.name.strip().lower() == norm:
            return (cat.name, s.name)
    # Sub inexistente: usa primeira como fallback.
    return (cat.name, cat.subcategories[0].name)


async def _categorize_async(
    bookmarks: list[Bookmark],
    taxonomy: Taxonomy,
    *,
    model: str,
    batch_size: int,
    concurrency: int,
) -> dict[int, tuple[str, str]]:
    if not bookmarks:
        return {}

    taxonomy.ensure_other()
    tool_schema = _build_tool_schema(taxonomy)

    indexed = list(enumerate(bookmarks))
    batches = [
        indexed[i : i + batch_size] for i in range(0, len(indexed), batch_size)
    ]
    semaphore = asyncio.Semaphore(concurrency)
    usage = UsageTracker()

    client = get_client()
    start = time.time()
    try:
        results = await asyncio.gather(
            *(
                _categorize_batch(
                    client, model, semaphore, batch, taxonomy, tool_schema, usage
                )
                for batch in batches
            )
        )
    finally:
        await client.close()

    assignments_by_idx: dict[int, tuple[str, str]] = {}
    for batch_result in results:
        for item in batch_result:
            try:
                idx = int(item.get("idx"))
                cat = item.get("category", "")
                sub = item.get("subcategory", "")
            except (TypeError, ValueError):
                continue
            if 0 <= idx < len(bookmarks):
                assignments_by_idx[idx] = _resolve_path(taxonomy, cat, sub)

    # Itens que o modelo não retornou: caem em Outros.
    for idx in range(len(bookmarks)):
        assignments_by_idx.setdefault(idx, (CATEGORY_OTHER, ""))

    elapsed = time.time() - start
    cost = usage.cost_usd(model)
    cost_str = f"  custo: US$ {cost:.4f}" if cost is not None else ""
    print(
        f"Categorização: {len(bookmarks)} bookmarks em "
        f"{len(batches)} batches, {elapsed:.1f}s.{cost_str}"
    )
    return assignments_by_idx


def ai_categorize(
    bookmarks: list[Bookmark],
    taxonomy: Taxonomy,
    *,
    model: str = CATEGORIZE_MODEL,
    batch_size: int = BATCH_SIZE,
    concurrency: int = CONCURRENCY,
) -> dict[int, tuple[str, str]]:
    """Categoriza bookmarks contra a taxonomia.

    Retorna mapping do índice na lista de entrada para um par
    ``(categoria, subcategoria)``. Subcategoria pode ser string vazia
    quando a categoria não tem subdivisões.
    """
    return asyncio.run(
        _categorize_async(
            bookmarks,
            taxonomy,
            model=model,
            batch_size=batch_size,
            concurrency=concurrency,
        )
    )


def group_by_path(
    bookmarks: list[Bookmark],
    assignments: dict[int, tuple[str, str]],
) -> dict[tuple[str, str], list[Bookmark]]:
    """Inverte o mapping: (cat, sub) → lista de bookmarks."""
    out: dict[tuple[str, str], list[Bookmark]] = defaultdict(list)
    for idx, bm in enumerate(bookmarks):
        path = assignments.get(idx, (CATEGORY_OTHER, ""))
        out[path].append(bm)
    return dict(out)
