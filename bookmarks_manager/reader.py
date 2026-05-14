"""Leitura e parsing do arquivo de bookmarks do Google Chrome.

O Chrome armazena bookmarks em um arquivo JSON chamado ``Bookmarks`` dentro do
diretório do perfil. A localização varia por sistema operacional:

- Linux:   ~/.config/google-chrome/<Profile>/Bookmarks
- macOS:   ~/Library/Application Support/Google/Chrome/<Profile>/Bookmarks
- Windows: %LOCALAPPDATA%\\Google\\Chrome\\User Data\\<Profile>\\Bookmarks
"""

from __future__ import annotations

import json
import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class Bookmark:
    """Um bookmark individual (folha da árvore)."""

    name: str
    url: str
    id: str = ""
    date_added: str = ""
    guid: str = ""

    @property
    def type(self) -> str:
        return "url"

    def to_chrome_dict(self) -> dict:
        data = {
            "type": "url",
            "name": self.name,
            "url": self.url,
        }
        if self.id:
            data["id"] = self.id
        if self.date_added:
            data["date_added"] = self.date_added
        if self.guid:
            data["guid"] = self.guid
        return data


@dataclass
class Folder:
    """Uma pasta de bookmarks (nó interno da árvore)."""

    name: str
    children: list = field(default_factory=list)
    id: str = ""
    date_added: str = ""
    date_modified: str = ""
    guid: str = ""

    @property
    def type(self) -> str:
        return "folder"

    def iter_bookmarks(self) -> Iterator[Bookmark]:
        """Itera recursivamente sobre todos os bookmarks desta pasta."""
        for child in self.children:
            if isinstance(child, Bookmark):
                yield child
            elif isinstance(child, Folder):
                yield from child.iter_bookmarks()

    def iter_folders(self) -> Iterator["Folder"]:
        """Itera recursivamente sobre todas as subpastas."""
        for child in self.children:
            if isinstance(child, Folder):
                yield child
                yield from child.iter_folders()

    def to_chrome_dict(self) -> dict:
        data = {
            "type": "folder",
            "name": self.name,
            "children": [c.to_chrome_dict() for c in self.children],
        }
        if self.id:
            data["id"] = self.id
        if self.date_added:
            data["date_added"] = self.date_added
        if self.date_modified:
            data["date_modified"] = self.date_modified
        if self.guid:
            data["guid"] = self.guid
        return data


@dataclass
class BookmarkFile:
    """Representação do arquivo Bookmarks do Chrome."""

    bookmark_bar: Folder
    other: Folder
    synced: Folder
    version: int = 1
    checksum: str = ""

    def iter_bookmarks(self) -> Iterator[Bookmark]:
        yield from self.bookmark_bar.iter_bookmarks()
        yield from self.other.iter_bookmarks()
        yield from self.synced.iter_bookmarks()

    def iter_folders(self) -> Iterator[Folder]:
        yield self.bookmark_bar
        yield from self.bookmark_bar.iter_folders()
        yield self.other
        yield from self.other.iter_folders()
        yield self.synced
        yield from self.synced.iter_folders()

    def to_chrome_dict(self) -> dict:
        return {
            "checksum": self.checksum,
            "roots": {
                "bookmark_bar": self.bookmark_bar.to_chrome_dict(),
                "other": self.other.to_chrome_dict(),
                "synced": self.synced.to_chrome_dict(),
            },
            "version": self.version,
        }


def default_chrome_path(profile: str = "Default") -> Path:
    """Retorna o caminho padrão do arquivo Bookmarks para o SO atual."""
    system = platform.system()
    home = Path.home()

    if system == "Linux":
        return home / ".config" / "google-chrome" / profile / "Bookmarks"
    if system == "Darwin":
        return (
            home
            / "Library"
            / "Application Support"
            / "Google"
            / "Chrome"
            / profile
            / "Bookmarks"
        )
    if system == "Windows":
        local_app = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        return Path(local_app) / "Google" / "Chrome" / "User Data" / profile / "Bookmarks"

    raise RuntimeError(f"Sistema operacional não suportado: {system}")


def _parse_node(raw: dict) -> Bookmark | Folder:
    node_type = raw.get("type")
    if node_type == "url":
        return Bookmark(
            name=raw.get("name", ""),
            url=raw.get("url", ""),
            id=raw.get("id", ""),
            date_added=raw.get("date_added", ""),
            guid=raw.get("guid", ""),
        )
    if node_type == "folder":
        children = [_parse_node(c) for c in raw.get("children", [])]
        return Folder(
            name=raw.get("name", ""),
            children=children,
            id=raw.get("id", ""),
            date_added=raw.get("date_added", ""),
            date_modified=raw.get("date_modified", ""),
            guid=raw.get("guid", ""),
        )
    raise ValueError(f"Tipo de nó desconhecido: {node_type!r}")


def _parse_root(raw: dict, fallback_name: str) -> Folder:
    parsed = _parse_node({**raw, "type": "folder"})
    if not isinstance(parsed, Folder):
        raise ValueError("Esperava uma pasta como raiz")
    if not parsed.name:
        parsed.name = fallback_name
    return parsed


def read_bookmarks(path: str | Path | None = None, profile: str = "Default") -> BookmarkFile:
    """Lê o arquivo de bookmarks do Chrome e retorna a estrutura parseada.

    Se ``path`` não for informado, o caminho padrão do SO é usado.
    """
    target = Path(path) if path else default_chrome_path(profile)
    if not target.exists():
        raise FileNotFoundError(
            f"Arquivo de bookmarks não encontrado em: {target}. "
            "Informe o caminho manualmente com --path."
        )
    with target.open("r", encoding="utf-8") as fh:
        raw = json.load(fh)

    roots = raw.get("roots", {})
    return BookmarkFile(
        bookmark_bar=_parse_root(roots.get("bookmark_bar", {}), "Barra de favoritos"),
        other=_parse_root(roots.get("other", {}), "Outros favoritos"),
        synced=_parse_root(roots.get("synced", {}), "Favoritos do celular"),
        version=raw.get("version", 1),
        checksum=raw.get("checksum", ""),
    )
