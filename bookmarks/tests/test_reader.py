"""Testes para o módulo reader."""

import platform
from pathlib import Path

import pytest

from bookmarks_manager.reader import (
    Bookmark,
    BookmarkFile,
    Folder,
    default_chrome_path,
    read_bookmarks,
)


def test_default_chrome_path_returns_path():
    path = default_chrome_path()
    assert isinstance(path, Path)
    assert "Bookmarks" in str(path)


def test_default_chrome_path_includes_profile():
    path = default_chrome_path(profile="Profile 1")
    assert "Profile 1" in str(path)


def test_default_chrome_path_per_os():
    system = platform.system()
    path = str(default_chrome_path())
    if system == "Linux":
        assert ".config/google-chrome" in path
    elif system == "Darwin":
        assert "Application Support/Google/Chrome" in path
    elif system == "Windows":
        assert "Google\\Chrome" in path or "Google/Chrome" in path


def test_read_bookmarks_parses_fixture(sample_file: BookmarkFile):
    assert isinstance(sample_file, BookmarkFile)
    assert sample_file.version == 1
    assert sample_file.checksum == "abc123"
    assert sample_file.bookmark_bar.name == "Barra de favoritos"
    assert sample_file.other.name == "Outros favoritos"
    assert sample_file.synced.name == "Favoritos do celular"


def test_iter_bookmarks_returns_all(sample_file: BookmarkFile):
    bookmarks = list(sample_file.iter_bookmarks())
    urls = {b.url for b in bookmarks}
    assert "https://github.com" in urls
    assert "https://stackoverflow.com/questions" in urls
    assert "https://coursera.org/learn/machine-learning" in urls
    assert "https://twitter.com/home" in urls
    assert len(bookmarks) == 10


def test_iter_bookmarks_recurses_into_subfolders(sample_file: BookmarkFile):
    bookmark_names = {b.name for b in sample_file.bookmark_bar.iter_bookmarks()}
    assert "Coursera ML" in bookmark_names
    assert "Curso de Python" in bookmark_names


def test_iter_folders_returns_nested(sample_file: BookmarkFile):
    folders = list(sample_file.iter_folders())
    names = [f.name for f in folders]
    assert "Cursos" in names
    assert "Subpasta" in names
    assert "Pasta Vazia" in names


def test_read_bookmarks_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        read_bookmarks(tmp_path / "missing.json")


def test_to_chrome_dict_roundtrip(sample_file: BookmarkFile):
    data = sample_file.to_chrome_dict()
    assert data["version"] == 1
    assert "roots" in data
    assert "bookmark_bar" in data["roots"]
    assert data["roots"]["bookmark_bar"]["type"] == "folder"


def test_bookmark_to_chrome_dict():
    bm = Bookmark(name="Test", url="https://example.com", id="99")
    data = bm.to_chrome_dict()
    assert data == {
        "type": "url",
        "name": "Test",
        "url": "https://example.com",
        "id": "99",
    }


def test_folder_to_chrome_dict_with_children():
    folder = Folder(
        name="F",
        children=[Bookmark(name="A", url="https://a.com")],
    )
    data = folder.to_chrome_dict()
    assert data["type"] == "folder"
    assert data["name"] == "F"
    assert len(data["children"]) == 1
    assert data["children"][0]["type"] == "url"
