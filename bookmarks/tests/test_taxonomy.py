"""Testes para taxonomy.py (estrutura, I/O, validação de paths)."""

import json
from pathlib import Path

import pytest

from bookmarks_manager.taxonomy import (
    CATEGORY_OTHER,
    Category,
    Subcategory,
    Taxonomy,
    load_taxonomy,
    save_taxonomy,
)


def _sample_tax() -> Taxonomy:
    return Taxonomy(
        categories=[
            Category(
                name="Tech",
                description="Coisas de tecnologia",
                subcategories=[
                    Subcategory(name="Python", description="Linguagem Python"),
                    Subcategory(name="Frontend", description="JS, CSS, etc."),
                ],
            ),
            Category(name="Notícias", subcategories=[]),
        ],
        model="claude-opus-4-7",
        generated_at="2026-01-01T00:00:00+00:00",
        n_bookmarks_sampled=100,
    )


def test_category_names():
    tax = _sample_tax()
    assert tax.category_names() == ["Tech", "Notícias"]


def test_find_category_case_insensitive():
    tax = _sample_tax()
    assert tax.find_category("tech").name == "Tech"
    assert tax.find_category("NOTÍCIAS").name == "Notícias"
    assert tax.find_category("inexistente") is None


def test_has_path():
    tax = _sample_tax()
    assert tax.has_path("Tech", "Python")
    assert tax.has_path("tech", "python")  # case-insensitive
    assert not tax.has_path("Tech", "Rust")
    # Categoria sem subs: subcategory deve ser vazio/None
    assert tax.has_path("Notícias", "")
    assert tax.has_path("Notícias", None)
    assert not tax.has_path("Notícias", "Alguma")


def test_ensure_other_adds_if_missing():
    tax = _sample_tax()
    assert tax.find_category(CATEGORY_OTHER) is None
    tax.ensure_other()
    assert tax.find_category(CATEGORY_OTHER) is not None
    # Idempotente
    tax.ensure_other()
    assert sum(1 for c in tax.categories if c.name == CATEGORY_OTHER) == 1


def test_flatten_paths():
    tax = _sample_tax()
    paths = tax.flatten_paths()
    assert "Tech > Python" in paths
    assert "Tech > Frontend" in paths
    assert "Notícias" in paths


def test_save_and_load_roundtrip(tmp_path: Path):
    tax = _sample_tax()
    path = tmp_path / "tax.json"
    save_taxonomy(tax, path)

    loaded = load_taxonomy(path)
    assert loaded.category_names()[:2] == ["Tech", "Notícias"]
    assert loaded.model == "claude-opus-4-7"
    assert loaded.find_category("Tech").subcategories[0].name == "Python"
    # load_taxonomy chama ensure_other
    assert loaded.find_category(CATEGORY_OTHER) is not None


def test_from_dict_ignores_empty_names():
    data = {
        "version": 1,
        "categories": [
            {"name": "", "subcategories": []},  # ignorado
            {"name": "Valida", "subcategories": [{"name": ""}, {"name": "X"}]},
        ],
    }
    tax = Taxonomy.from_dict(data)
    names = tax.category_names()
    assert "Valida" in names
    assert "" not in names
    valid = tax.find_category("Valida")
    assert valid.subcategory_names() == ["X"]


def test_load_taxonomy_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_taxonomy(tmp_path / "missing.json")


def test_format_report_has_structure():
    tax = _sample_tax()
    report = tax.format_report()
    assert "Tech" in report
    assert "Python" in report
    assert "Notícias" in report
