"""Testes de ai_taxonomy.py (amostragem + parsing, sem chamadas reais à API)."""

from collections import Counter
from urllib.parse import urlparse

from bookmarks_manager.ai_taxonomy import (
    _format_bookmark_list,
    _parse_response,
    stratified_sample,
)
from bookmarks_manager.reader import Bookmark


def _bm(name: str, url: str) -> Bookmark:
    return Bookmark(name=name, url=url)


def test_stratified_sample_returns_all_if_small():
    bms = [_bm(f"n{i}", f"https://example.com/{i}") for i in range(10)]
    out = stratified_sample(bms, max_size=20)
    assert len(out) == 10


def test_stratified_sample_respects_max_size():
    bms = [_bm(f"n{i}", f"https://example.com/{i}") for i in range(100)]
    out = stratified_sample(bms, max_size=30)
    assert len(out) == 30


def test_stratified_sample_covers_domains():
    """Domínios menos populares devem aparecer mesmo com max_size pequeno."""
    bms = []
    # 90 do github, 10 de outros 10 domínios distintos
    bms.extend(_bm(f"gh{i}", f"https://github.com/{i}") for i in range(90))
    for i in range(10):
        bms.append(_bm(f"x{i}", f"https://site{i}.com"))

    out = stratified_sample(bms, max_size=20)
    domains = Counter(
        (urlparse(bm.url).hostname or "").replace("www.", "") for bm in out
    )
    # Espera-se que > 1 domínio apareça (estratificação funcionou)
    assert len(domains) > 1


def test_format_bookmark_list_includes_name_and_domain():
    bms = [
        _bm("GitHub", "https://github.com"),
        _bm("Pandas", "https://pandas.pydata.org/docs/"),
    ]
    txt = _format_bookmark_list(bms)
    assert "GitHub :: github.com" in txt
    assert "Pandas :: pandas.pydata.org" in txt


def test_parse_response_filters_invalid():
    data = {
        "categories": [
            {
                "name": "Tech",
                "description": "Coisas tech",
                "subcategories": [
                    {"name": "Python", "description": "linguagem"},
                    {"name": "", "description": "ignorada"},  # sem nome
                ],
            },
            {"name": "", "subcategories": []},  # sem nome → fora
            {"name": "Notícias", "subcategories": None},  # subs nulas
        ]
    }
    cats = _parse_response(data)
    names = [c.name for c in cats]
    assert names == ["Tech", "Notícias"]
    tech = cats[0]
    assert [s.name for s in tech.subcategories] == ["Python"]
