"""Testes para o módulo reorganizer."""

import json
from pathlib import Path

from bookmarks_manager.reader import read_bookmarks
from bookmarks_manager.reorganizer import (
    build_reorganized_tree,
    suggest_reorganization,
)


def test_suggest_removes_duplicates(sample_file):
    suggestion = suggest_reorganization(sample_file, remove_duplicates=True)
    assert suggestion.duplicates_removed >= 1
    assert suggestion.total_original == 10
    assert suggestion.total_categorized == suggestion.total_original - suggestion.duplicates_removed


def test_suggest_keeps_duplicates_when_disabled(sample_file):
    suggestion = suggest_reorganization(sample_file, remove_duplicates=False)
    assert suggestion.duplicates_removed == 0
    assert suggestion.total_categorized == suggestion.total_original


def test_suggest_creates_expected_categories(sample_file):
    suggestion = suggest_reorganization(sample_file)
    assert "Desenvolvimento" in suggestion.categories
    assert "Aprendizado" in suggestion.categories
    assert "Entretenimento" in suggestion.categories


def test_build_reorganized_tree_structure(sample_file):
    new_file = build_reorganized_tree(sample_file)
    bar = new_file.bookmark_bar
    assert len(bar.children) > 0
    # Todos os filhos da barra devem ser pastas (categorias)
    for child in bar.children:
        assert child.type == "folder"


def test_build_reorganized_tree_target_root_other(sample_file):
    new_file = build_reorganized_tree(sample_file, target_root="other")
    assert len(new_file.bookmark_bar.children) == 0
    assert len(new_file.other.children) > 0


def test_build_reorganized_tree_outputs_valid_chrome_format(sample_file, tmp_path: Path):
    new_file = build_reorganized_tree(sample_file)
    data = new_file.to_chrome_dict()

    out = tmp_path / "Bookmarks"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=3), encoding="utf-8")

    reloaded = read_bookmarks(out)
    assert reloaded.version == sample_file.version
    # Mesma quantidade de bookmarks após dedup
    reloaded_count = len(list(reloaded.iter_bookmarks()))
    original_count = len(list(sample_file.iter_bookmarks()))
    assert reloaded_count <= original_count  # menor ou igual por dedup


def test_format_report_contains_summary(sample_file):
    suggestion = suggest_reorganization(sample_file)
    report = suggestion.format_report()
    assert "Sugestão de Reorganização" in report
    assert "Distribuição por categoria" in report


def test_format_detailed_report_contains_samples(sample_file):
    suggestion = suggest_reorganization(sample_file)
    report = suggestion.format_detailed_report(limit_per_category=2)
    assert "Amostras por Categoria" in report
    assert "→" in report
