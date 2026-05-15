"""Geração de sugestões de reorganização e construção de nova árvore.

Dois caminhos de uso:

1. Heurístico (sem IA): ``suggest_reorganization`` + ``build_reorganized_tree``
   usam ``categorizer.py`` (regras de domínio fixas, 1 nível).
2. Via IA: ``ai_suggest_reorganization`` + ``build_reorganized_tree_from_assignments``
   usam uma ``Taxonomy`` hierárquica (2 níveis) e categorização por LLM.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bookmarks_manager.ai_categorizer import ai_categorize, group_by_path
from bookmarks_manager.categorizer import (
    CATEGORY_OTHER,
    categorize_bookmarks,
)
from bookmarks_manager.reader import Bookmark, BookmarkFile, Folder
from bookmarks_manager.taxonomy import CATEGORY_OTHER as TAXONOMY_OTHER, Taxonomy


@dataclass
class ReorganizationSuggestion:
    """Sugestão de reorganização heurística (1 nível)."""

    categories: dict[str, list[Bookmark]] = field(default_factory=dict)
    duplicates_removed: int = 0
    total_original: int = 0

    @property
    def total_categorized(self) -> int:
        return sum(len(bms) for bms in self.categories.values())

    def format_report(self) -> str:
        lines = [
            "=== Sugestão de Reorganização ===",
            f"Bookmarks originais: {self.total_original}",
            f"Duplicados removidos: {self.duplicates_removed}",
            f"Bookmarks categorizados: {self.total_categorized}",
            "",
            "Distribuição por categoria:",
        ]
        sorted_cats = sorted(
            self.categories.items(), key=lambda x: (-len(x[1]), x[0])
        )
        for category, bookmarks in sorted_cats:
            lines.append(f"  [{len(bookmarks):4d}] {category}")
        return "\n".join(lines)

    def format_detailed_report(self, limit_per_category: int = 5) -> str:
        lines = [self.format_report(), "", "=== Amostras por Categoria ==="]
        sorted_cats = sorted(
            self.categories.items(), key=lambda x: (-len(x[1]), x[0])
        )
        for category, bookmarks in sorted_cats:
            count = len(bookmarks)
            noun = "item" if count == 1 else "itens"
            lines.append(f"\n[{category}] ({count} {noun})")
            for bm in bookmarks[:limit_per_category]:
                name = bm.name or "(sem título)"
                lines.append(f"  - {name}  →  {bm.url}")
            if len(bookmarks) > limit_per_category:
                lines.append(f"  ... e mais {len(bookmarks) - limit_per_category}")
        return "\n".join(lines)


@dataclass
class AIReorganizationSuggestion:
    """Sugestão de reorganização via IA (2 níveis, taxonomia)."""

    taxonomy: Taxonomy
    groups: dict[tuple[str, str], list[Bookmark]] = field(default_factory=dict)
    duplicates_removed: int = 0
    total_original: int = 0

    @property
    def total_categorized(self) -> int:
        return sum(len(bms) for bms in self.groups.values())

    def _category_totals(self) -> list[tuple[str, int]]:
        totals: dict[str, int] = {}
        for (cat, _sub), bms in self.groups.items():
            totals[cat] = totals.get(cat, 0) + len(bms)
        return sorted(totals.items(), key=lambda x: (-x[1], x[0]))

    def format_report(self) -> str:
        lines = [
            "=== Sugestão de Reorganização (IA) ===",
            f"Bookmarks originais: {self.total_original}",
            f"Duplicados removidos: {self.duplicates_removed}",
            f"Bookmarks categorizados: {self.total_categorized}",
            f"Taxonomia: {len(self.taxonomy.categories)} categorias",
            "",
            "Distribuição por categoria:",
        ]
        for cat_name, total in self._category_totals():
            lines.append(f"  [{total:4d}] {cat_name}")
        return "\n".join(lines)

    def format_detailed_report(self, limit_per_category: int = 5) -> str:
        lines = [self.format_report(), "", "=== Distribuição por subcategoria ==="]
        # Agrupar por categoria preservando ordem da taxonomia.
        for cat in self.taxonomy.categories:
            cat_total = sum(
                len(bms) for (c, _s), bms in self.groups.items() if c == cat.name
            )
            if cat_total == 0:
                continue
            lines.append(f"\n[{cat.name}] ({cat_total} itens)")
            if cat.subcategories:
                for sub in cat.subcategories:
                    bms = self.groups.get((cat.name, sub.name), [])
                    if not bms:
                        continue
                    lines.append(f"  → {sub.name} ({len(bms)})")
                    for bm in bms[:limit_per_category]:
                        name = bm.name or "(sem título)"
                        lines.append(f"      - {name}  →  {bm.url}")
                    if len(bms) > limit_per_category:
                        lines.append(f"      ... e mais {len(bms) - limit_per_category}")
            else:
                bms = self.groups.get((cat.name, ""), [])
                for bm in bms[:limit_per_category]:
                    name = bm.name or "(sem título)"
                    lines.append(f"  - {name}  →  {bm.url}")
                if len(bms) > limit_per_category:
                    lines.append(f"  ... e mais {len(bms) - limit_per_category}")
        return "\n".join(lines)


def _dedupe(bookmarks: list[Bookmark]) -> tuple[list[Bookmark], int]:
    seen: set[str] = set()
    unique: list[Bookmark] = []
    removed = 0
    for bm in bookmarks:
        key = bm.url.strip().lower()
        if not key:
            unique.append(bm)
            continue
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        unique.append(bm)
    return unique, removed


def suggest_reorganization(
    file: BookmarkFile, *, remove_duplicates: bool = True
) -> ReorganizationSuggestion:
    """Gera uma sugestão de reorganização heurística (1 nível)."""
    all_bookmarks = list(file.iter_bookmarks())
    total_original = len(all_bookmarks)

    if remove_duplicates:
        unique, removed = _dedupe(all_bookmarks)
    else:
        unique, removed = all_bookmarks, 0

    result = categorize_bookmarks(unique)

    return ReorganizationSuggestion(
        categories=result.categories,
        duplicates_removed=removed,
        total_original=total_original,
    )


def build_reorganized_tree(
    file: BookmarkFile,
    *,
    remove_duplicates: bool = True,
    target_root: str = "bookmark_bar",
) -> BookmarkFile:
    """Constrói um novo BookmarkFile com a estrutura reorganizada (heurística, 1 nível)."""
    suggestion = suggest_reorganization(file, remove_duplicates=remove_duplicates)
    sorted_cats = sorted(
        suggestion.categories.items(), key=lambda x: (-len(x[1]), x[0])
    )

    folders: list[Folder] = []
    for category, bookmarks in sorted_cats:
        bookmarks_sorted = sorted(bookmarks, key=lambda b: b.name.lower())
        folders.append(Folder(name=category, children=list(bookmarks_sorted)))

    folders.sort(key=lambda f: (f.name == CATEGORY_OTHER, -len(f.children), f.name))

    return _wrap_folders(file, folders, target_root)


def ai_suggest_reorganization(
    file: BookmarkFile,
    taxonomy: Taxonomy,
    *,
    remove_duplicates: bool = True,
) -> AIReorganizationSuggestion:
    """Gera sugestão via IA usando a taxonomia fornecida."""
    all_bookmarks = list(file.iter_bookmarks())
    total_original = len(all_bookmarks)

    if remove_duplicates:
        unique, removed = _dedupe(all_bookmarks)
    else:
        unique, removed = all_bookmarks, 0

    assignments = ai_categorize(unique, taxonomy)
    groups = group_by_path(unique, assignments)

    return AIReorganizationSuggestion(
        taxonomy=taxonomy,
        groups=groups,
        duplicates_removed=removed,
        total_original=total_original,
    )


def build_reorganized_tree_from_assignments(
    file: BookmarkFile,
    taxonomy: Taxonomy,
    *,
    remove_duplicates: bool = True,
    target_root: str = "bookmark_bar",
) -> BookmarkFile:
    """Categoriza via IA e constrói árvore hierárquica de 2 níveis."""
    suggestion = ai_suggest_reorganization(
        file, taxonomy, remove_duplicates=remove_duplicates
    )
    return build_tree_from_suggestion(suggestion, file, target_root=target_root)


def build_tree_from_suggestion(
    suggestion: AIReorganizationSuggestion,
    file: BookmarkFile,
    *,
    target_root: str = "bookmark_bar",
) -> BookmarkFile:
    """Monta a árvore Chrome a partir de uma AIReorganizationSuggestion já calculada."""
    folders: list[Folder] = []
    for cat in suggestion.taxonomy.categories:
        if cat.subcategories:
            sub_folders: list[Folder] = []
            for sub in cat.subcategories:
                bms = suggestion.groups.get((cat.name, sub.name), [])
                if not bms:
                    continue
                bms_sorted = sorted(bms, key=lambda b: b.name.lower())
                sub_folders.append(Folder(name=sub.name, children=list(bms_sorted)))
            if not sub_folders:
                continue
            folders.append(Folder(name=cat.name, children=sub_folders))
        else:
            bms = suggestion.groups.get((cat.name, ""), [])
            if not bms:
                continue
            bms_sorted = sorted(bms, key=lambda b: b.name.lower())
            folders.append(Folder(name=cat.name, children=list(bms_sorted)))

    # Outros sempre no fim (mantendo o nome da taxonomia, não o do categorizer).
    folders.sort(
        key=lambda f: (f.name == TAXONOMY_OTHER, -_count_leaves(f), f.name.lower())
    )

    return _wrap_folders(file, folders, target_root)


def _count_leaves(folder: Folder) -> int:
    return sum(1 for _ in folder.iter_bookmarks())


def _wrap_folders(
    file: BookmarkFile, folders: list[Folder], target_root: str
) -> BookmarkFile:
    empty_bar = Folder(name=file.bookmark_bar.name)
    empty_other = Folder(name=file.other.name)
    empty_synced = Folder(name=file.synced.name)

    if target_root == "bookmark_bar":
        empty_bar.children = folders
    elif target_root == "other":
        empty_other.children = folders
    elif target_root == "synced":
        empty_synced.children = folders
    else:
        raise ValueError(f"target_root inválido: {target_root!r}")

    return BookmarkFile(
        bookmark_bar=empty_bar,
        other=empty_other,
        synced=empty_synced,
        version=file.version,
        checksum="",
    )
