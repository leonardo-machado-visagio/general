"""Análise estatística de coleções de bookmarks."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from urllib.parse import urlparse

from bookmarks_manager.reader import Bookmark, BookmarkFile, Folder


@dataclass
class BookmarkStats:
    total_bookmarks: int = 0
    total_folders: int = 0
    max_depth: int = 0
    empty_folders: int = 0
    top_domains: list[tuple[str, int]] = field(default_factory=list)
    duplicates: list[tuple[str, list[str]]] = field(default_factory=list)
    invalid_urls: list[tuple[str, str]] = field(default_factory=list)

    def format_report(self) -> str:
        lines = [
            "=== Relatório de Bookmarks ===",
            f"Total de bookmarks: {self.total_bookmarks}",
            f"Total de pastas:    {self.total_folders}",
            f"Profundidade máxima: {self.max_depth}",
            f"Pastas vazias:      {self.empty_folders}",
            "",
            "Top 10 domínios:",
        ]
        if not self.top_domains:
            lines.append("  (nenhum)")
        else:
            for domain, count in self.top_domains[:10]:
                lines.append(f"  {count:4d}  {domain}")

        lines.append("")
        lines.append(f"URLs duplicadas: {len(self.duplicates)}")
        for url, names in self.duplicates[:5]:
            lines.append(f"  {url}")
            for name in names:
                lines.append(f"    - {name}")
        if len(self.duplicates) > 5:
            lines.append(f"  ... e mais {len(self.duplicates) - 5}")

        lines.append("")
        lines.append(f"URLs inválidas: {len(self.invalid_urls)}")
        for name, url in self.invalid_urls[:5]:
            lines.append(f"  {name!r}: {url}")
        if len(self.invalid_urls) > 5:
            lines.append(f"  ... e mais {len(self.invalid_urls) - 5}")

        return "\n".join(lines)


def _extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host.lower()


def _is_valid_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return bool(parsed.scheme and parsed.netloc) or parsed.scheme in {
        "chrome",
        "chrome-extension",
        "about",
    }


def _max_depth(folder: Folder, current: int = 0) -> int:
    deepest = current
    for child in folder.children:
        if isinstance(child, Folder):
            child_depth = _max_depth(child, current + 1)
            if child_depth > deepest:
                deepest = child_depth
    return deepest


def _count_empty_folders(folder: Folder) -> int:
    count = 0
    for sub in folder.iter_folders():
        if not sub.children:
            count += 1
    if not folder.children:
        count += 1
    return count


def analyze(file: BookmarkFile, top_n: int = 10) -> BookmarkStats:
    """Gera estatísticas sobre o arquivo de bookmarks."""
    bookmarks: list[Bookmark] = list(file.iter_bookmarks())
    folders: list[Folder] = list(file.iter_folders())

    domain_counter: Counter[str] = Counter()
    url_to_names: dict[str, list[str]] = {}
    invalid: list[tuple[str, str]] = []

    for bm in bookmarks:
        if _is_valid_url(bm.url):
            domain = _extract_domain(bm.url)
            if domain:
                domain_counter[domain] += 1
        else:
            invalid.append((bm.name, bm.url))

        url_to_names.setdefault(bm.url, []).append(bm.name)

    duplicates = [(url, names) for url, names in url_to_names.items() if len(names) > 1]
    duplicates.sort(key=lambda x: -len(x[1]))

    max_depth = max(
        (_max_depth(file.bookmark_bar), _max_depth(file.other), _max_depth(file.synced)),
        default=0,
    )

    root_ids = {id(file.bookmark_bar), id(file.other), id(file.synced)}
    empty_folders = sum(
        1 for f in folders if not f.children and id(f) not in root_ids
    )

    return BookmarkStats(
        total_bookmarks=len(bookmarks),
        total_folders=len(folders),
        max_depth=max_depth,
        empty_folders=empty_folders,
        top_domains=domain_counter.most_common(top_n),
        duplicates=duplicates,
        invalid_urls=invalid,
    )
