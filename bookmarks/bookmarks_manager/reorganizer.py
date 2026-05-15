"""Geração de sugestões de reorganização e construção de nova árvore."""

from __future__ import annotations

from dataclasses import dataclass, field

from bookmarks_manager.categorizer import (
    CATEGORY_OTHER,
    categorize_bookmarks,
)
from bookmarks_manager.reader import Bookmark, BookmarkFile, Folder


@dataclass
class ReorganizationSuggestion:
    """Sugestão de reorganização com agrupamento por categoria."""

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
    """Gera uma sugestão de reorganização agrupando bookmarks por categoria."""
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
    """Constrói um novo ``BookmarkFile`` com a estrutura reorganizada.

    ``target_root`` indica em qual raiz colocar as pastas reorganizadas.
    Os outros roots ficam vazios. Categorias são ordenadas por contagem desc.
    """
    suggestion = suggest_reorganization(file, remove_duplicates=remove_duplicates)
    sorted_cats = sorted(
        suggestion.categories.items(), key=lambda x: (-len(x[1]), x[0])
    )

    folders: list[Folder] = []
    for category, bookmarks in sorted_cats:
        # Move "Outros" para o final ordenando depois.
        bookmarks_sorted = sorted(bookmarks, key=lambda b: b.name.lower())
        folders.append(Folder(name=category, children=list(bookmarks_sorted)))

    # "Outros" sempre por último, mesmo que seja grande.
    folders.sort(key=lambda f: (f.name == CATEGORY_OTHER, -len(f.children), f.name))

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
