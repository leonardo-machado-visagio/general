"""Testes de ai_categorizer.py com cliente AsyncAnthropic mockado."""

from unittest.mock import patch

import pytest

from bookmarks_manager.ai_categorizer import (
    _build_tool_schema,
    _format_taxonomy_for_prompt,
    _resolve_path,
    ai_categorize,
    group_by_path,
)
from bookmarks_manager.reader import Bookmark
from bookmarks_manager.taxonomy import (
    CATEGORY_OTHER,
    Category,
    Subcategory,
    Taxonomy,
)


def _tax() -> Taxonomy:
    return Taxonomy(
        categories=[
            Category(
                name="Tech",
                subcategories=[
                    Subcategory(name="Python"),
                    Subcategory(name="Frontend"),
                ],
            ),
            Category(name="Notícias", subcategories=[]),
            Category(name=CATEGORY_OTHER, subcategories=[]),
        ]
    )


def _bm(name: str, url: str) -> Bookmark:
    return Bookmark(name=name, url=url)


def test_resolve_path_valid():
    tax = _tax()
    assert _resolve_path(tax, "Tech", "Python") == ("Tech", "Python")
    assert _resolve_path(tax, "tech", "frontend") == ("Tech", "Frontend")


def test_resolve_path_category_without_subs_ignores_sub():
    tax = _tax()
    assert _resolve_path(tax, "Notícias", "Qualquer") == ("Notícias", "")
    assert _resolve_path(tax, "Notícias", "") == ("Notícias", "")


def test_resolve_path_invalid_subcategory_falls_back():
    tax = _tax()
    # Sub inexistente: cai na primeira da categoria
    cat, sub = _resolve_path(tax, "Tech", "Rust")
    assert cat == "Tech"
    assert sub == "Python"


def test_resolve_path_invalid_category_goes_to_other():
    tax = _tax()
    assert _resolve_path(tax, "Inexistente", "X") == (CATEGORY_OTHER, "")


def test_resolve_path_empty_sub_on_category_with_subs():
    tax = _tax()
    cat, sub = _resolve_path(tax, "Tech", "")
    assert cat == "Tech"
    assert sub == "Python"


def test_format_taxonomy_for_prompt():
    tax = _tax()
    txt = _format_taxonomy_for_prompt(tax)
    assert "Tech > Python" in txt
    assert "Tech > Frontend" in txt
    assert "Notícias" in txt
    assert "Tech > Notícias" not in txt  # não mistura


def test_build_tool_schema_enum_has_category_names():
    tax = _tax()
    schema = _build_tool_schema(tax)
    enum = schema["properties"]["assignments"]["items"]["properties"]["category"]["enum"]
    assert set(enum) == {"Tech", "Notícias", CATEGORY_OTHER}


def test_group_by_path():
    bms = [
        _bm("a", "https://a.com"),
        _bm("b", "https://b.com"),
        _bm("c", "https://c.com"),
    ]
    assignments = {
        0: ("Tech", "Python"),
        1: ("Tech", "Python"),
        2: ("Notícias", ""),
    }
    groups = group_by_path(bms, assignments)
    assert len(groups[("Tech", "Python")]) == 2
    assert len(groups[("Notícias", "")]) == 1


def test_group_by_path_default_other_for_missing():
    bms = [_bm("a", "https://a.com")]
    groups = group_by_path(bms, {})  # sem assignment
    assert (CATEGORY_OTHER, "") in groups
    assert len(groups[(CATEGORY_OTHER, "")]) == 1


# -- Integração com client mockado ------------------------------------------


class _MockUsage:
    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0


class _MockBlock:
    def __init__(self, name, input_):
        self.type = "tool_use"
        self.name = name
        self.input = input_


class _MockResponse:
    def __init__(self, name, input_):
        self.content = [_MockBlock(name, input_)]
        self.stop_reason = "tool_use"
        self.usage = _MockUsage()


class _MockMessages:
    def __init__(self, responder):
        self._responder = responder

    async def create(self, **kwargs):
        return self._responder(**kwargs)


class _MockClient:
    def __init__(self, responder):
        self.messages = _MockMessages(responder)

    async def close(self):
        pass


def _build_responder(items_per_batch_response):
    """items_per_batch_response: callable(batch_user_content) -> list of assignment dicts."""

    def responder(**kwargs):
        # Pega o user_content do último message
        messages = kwargs.get("messages", [])
        user_content = messages[-1]["content"] if messages else ""
        items = items_per_batch_response(user_content)
        return _MockResponse(name="assign_categories", input_={"assignments": items})

    return responder


def test_ai_categorize_uses_taxonomy(monkeypatch):
    tax = _tax()
    bms = [
        _bm("Pandas", "https://pandas.pydata.org"),
        _bm("React", "https://react.dev"),
        _bm("G1", "https://g1.globo.com"),
        _bm("Aleatório", "https://random.com"),
    ]

    def respond(user_content):
        # Estratégia tonta: tudo Tech > Python, exceto G1 (Notícias) e Aleatório (Outros).
        out = []
        for line in user_content.splitlines():
            if line.startswith("[") and "]" in line:
                idx = int(line[1 : line.index("]")])
                name = line.split("] ", 1)[1].split(" ::", 1)[0]
                if "G1" in name:
                    out.append({"idx": idx, "category": "Notícias", "subcategory": ""})
                elif "Aleatório" in name:
                    out.append({"idx": idx, "category": "Inexistente", "subcategory": "x"})
                else:
                    out.append(
                        {"idx": idx, "category": "Tech", "subcategory": "Python"}
                    )
        return out

    responder = _build_responder(respond)

    with patch(
        "bookmarks_manager.ai_categorizer.get_client",
        return_value=_MockClient(responder),
    ):
        assignments = ai_categorize(bms, tax, batch_size=10, concurrency=1)

    assert assignments[0] == ("Tech", "Python")
    assert assignments[1] == ("Tech", "Python")
    assert assignments[2] == ("Notícias", "")
    # Categoria inexistente → Outros
    assert assignments[3] == (CATEGORY_OTHER, "")


def test_ai_categorize_handles_missing_indices(monkeypatch):
    """Se o modelo esquecer de retornar índices, eles caem em Outros."""
    tax = _tax()
    bms = [_bm(f"n{i}", f"https://x{i}.com") for i in range(5)]

    def respond(user_content):
        # Só retorna o primeiro item; outros 4 ficam órfãos
        return [{"idx": 0, "category": "Tech", "subcategory": "Python"}]

    responder = _build_responder(respond)
    with patch(
        "bookmarks_manager.ai_categorizer.get_client",
        return_value=_MockClient(responder),
    ):
        assignments = ai_categorize(bms, tax, batch_size=10, concurrency=1)

    assert assignments[0] == ("Tech", "Python")
    for i in range(1, 5):
        assert assignments[i] == (CATEGORY_OTHER, "")


def test_ai_categorize_empty_input_short_circuits():
    """Lista vazia não deve chamar o cliente."""
    tax = _tax()
    with patch("bookmarks_manager.ai_categorizer.get_client") as mock_get:
        result = ai_categorize([], tax)
    assert result == {}
    mock_get.assert_not_called()
