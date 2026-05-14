"""Testes para o módulo analyzer."""

from bookmarks_manager.analyzer import analyze


def test_analyze_counts(sample_file):
    stats = analyze(sample_file)
    assert stats.total_bookmarks == 10
    assert stats.total_folders >= 5  # 3 roots + Cursos + Subpasta + Pasta Vazia


def test_analyze_top_domains(sample_file):
    stats = analyze(sample_file)
    domains = dict(stats.top_domains)
    assert "github.com" in domains
    assert domains["github.com"] == 2


def test_analyze_duplicates(sample_file):
    stats = analyze(sample_file)
    duplicate_urls = [url for url, _ in stats.duplicates]
    assert "https://github.com" in duplicate_urls


def test_analyze_invalid_urls(sample_file):
    stats = analyze(sample_file)
    invalid_names = [name for name, _ in stats.invalid_urls]
    assert "Página estranha" in invalid_names


def test_analyze_max_depth(sample_file):
    stats = analyze(sample_file)
    # Subpasta dentro de Cursos = profundidade 2
    assert stats.max_depth >= 2


def test_analyze_empty_folders(sample_file):
    stats = analyze(sample_file)
    assert stats.empty_folders >= 1  # "Pasta Vazia"


def test_format_report_includes_sections(sample_file):
    stats = analyze(sample_file)
    report = stats.format_report()
    assert "Total de bookmarks" in report
    assert "Top 10 domínios" in report
    assert "URLs duplicadas" in report
    assert "URLs inválidas" in report
