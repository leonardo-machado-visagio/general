"""Integração de IA: categorização → árvore hierárquica e CLI com mocks."""

import json
from pathlib import Path
from unittest.mock import patch

from bookmarks_manager.cli import main
from bookmarks_manager.reader import Bookmark, read_bookmarks
from bookmarks_manager.reorganizer import (
    ai_suggest_reorganization,
    build_tree_from_suggestion,
)
from bookmarks_manager.taxonomy import (
    CATEGORY_OTHER,
    Category,
    Subcategory,
    Taxonomy,
    save_taxonomy,
)


def _tax() -> Taxonomy:
    return Taxonomy(
        categories=[
            Category(
                name="Desenvolvimento",
                subcategories=[
                    Subcategory(name="Repositórios"),
                    Subcategory(name="Q&A"),
                ],
            ),
            Category(
                name="Aprendizado",
                subcategories=[Subcategory(name="Cursos")],
            ),
            Category(name="Entretenimento", subcategories=[]),
            Category(name=CATEGORY_OTHER, subcategories=[]),
        ]
    )


class _MockUsage:
    input_tokens = 0
    output_tokens = 0


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


def _make_categorize_responder(rules):
    """rules: dict[substring_no_nome -> (cat, sub)] aplicado por bookmark."""

    def responder(**kwargs):
        messages = kwargs.get("messages", [])
        user_content = messages[-1]["content"] if messages else ""
        items = []
        for line in user_content.splitlines():
            if not line.startswith("["):
                continue
            try:
                idx = int(line[1 : line.index("]")])
            except (ValueError, KeyError):
                continue
            name = line.split("] ", 1)[1].split(" ::", 1)[0]
            cat, sub = (CATEGORY_OTHER, "")
            for key, path in rules.items():
                if key.lower() in name.lower():
                    cat, sub = path
                    break
            items.append({"idx": idx, "category": cat, "subcategory": sub})
        return _MockResponse(
            name="assign_categories", input_={"assignments": items}
        )

    return responder


def test_ai_suggest_builds_hierarchy(sample_file):
    rules = {
        "GitHub": ("Desenvolvimento", "Repositórios"),
        "Stack": ("Desenvolvimento", "Q&A"),
        "Curso": ("Aprendizado", "Cursos"),
        "Coursera": ("Aprendizado", "Cursos"),
        "YouTube": ("Entretenimento", ""),
    }
    with patch(
        "bookmarks_manager.ai_categorizer.get_client",
        return_value=_MockClient(_make_categorize_responder(rules)),
    ):
        suggestion = ai_suggest_reorganization(sample_file, _tax())

    assert suggestion.duplicates_removed >= 1
    # Aprendizado > Cursos deve ter ao menos 2 (Curso de Python + Coursera ML)
    assert len(suggestion.groups.get(("Aprendizado", "Cursos"), [])) >= 2
    # GitHub deduplicado → 1 item
    assert len(suggestion.groups.get(("Desenvolvimento", "Repositórios"), [])) == 1


def test_build_tree_from_suggestion_produces_two_levels(sample_file):
    rules = {
        "GitHub": ("Desenvolvimento", "Repositórios"),
        "Stack": ("Desenvolvimento", "Q&A"),
        "Curso": ("Aprendizado", "Cursos"),
        "Coursera": ("Aprendizado", "Cursos"),
        "YouTube": ("Entretenimento", ""),
    }
    with patch(
        "bookmarks_manager.ai_categorizer.get_client",
        return_value=_MockClient(_make_categorize_responder(rules)),
    ):
        suggestion = ai_suggest_reorganization(sample_file, _tax())
    new_file = build_tree_from_suggestion(suggestion, sample_file)

    bar = new_file.bookmark_bar
    folder_names = [f.name for f in bar.children]
    assert "Desenvolvimento" in folder_names
    assert "Aprendizado" in folder_names

    # Desenvolvimento deve ter subpastas (nível 2)
    dev = next(f for f in bar.children if f.name == "Desenvolvimento")
    sub_names = [c.name for c in dev.children]
    assert "Repositórios" in sub_names
    assert "Q&A" in sub_names

    # Entretenimento (sem subs) deve conter bookmarks direto
    entret = next((f for f in bar.children if f.name == "Entretenimento"), None)
    if entret is not None:
        for child in entret.children:
            assert child.type == "url"


def test_build_tree_other_at_end_when_present(sample_file):
    """Bookmarks que não casam vão pra Outros; pasta Outros aparece por último."""
    # Nenhuma regra → tudo cai em Outros
    with patch(
        "bookmarks_manager.ai_categorizer.get_client",
        return_value=_MockClient(_make_categorize_responder({})),
    ):
        suggestion = ai_suggest_reorganization(sample_file, _tax())
    new_file = build_tree_from_suggestion(suggestion, sample_file)

    bar = new_file.bookmark_bar
    assert any(f.name == CATEGORY_OTHER for f in bar.children)
    # Outros sempre por último
    assert bar.children[-1].name == CATEGORY_OTHER


# -- CLI --------------------------------------------------------------------


def test_cli_suggest_ai_requires_taxonomy_arg(sample_bookmarks_path, capsys):
    """--ai sem --taxonomy deve falhar com mensagem clara."""
    ret = main(["suggest", "--path", str(sample_bookmarks_path), "--ai"])
    assert ret == 1
    err = capsys.readouterr().err
    assert "taxonomy" in err.lower()


def test_cli_suggest_ai_with_taxonomy(sample_bookmarks_path, tmp_path: Path, capsys):
    tax_path = tmp_path / "tax.json"
    save_taxonomy(_tax(), tax_path)

    rules = {"GitHub": ("Desenvolvimento", "Repositórios")}
    with patch(
        "bookmarks_manager.ai_categorizer.get_client",
        return_value=_MockClient(_make_categorize_responder(rules)),
    ):
        ret = main(
            [
                "suggest",
                "--path",
                str(sample_bookmarks_path),
                "--ai",
                "--taxonomy",
                str(tax_path),
            ]
        )
    assert ret == 0
    out = capsys.readouterr().out
    assert "Sugestão de Reorganização (IA)" in out


def test_cli_reorganize_ai_writes_hierarchical_file(
    sample_bookmarks_path, tmp_path: Path
):
    tax_path = tmp_path / "tax.json"
    save_taxonomy(_tax(), tax_path)

    rules = {
        "GitHub": ("Desenvolvimento", "Repositórios"),
        "Stack": ("Desenvolvimento", "Q&A"),
        "Curso": ("Aprendizado", "Cursos"),
    }
    out_file = tmp_path / "Bookmarks"
    with patch(
        "bookmarks_manager.ai_categorizer.get_client",
        return_value=_MockClient(_make_categorize_responder(rules)),
    ):
        ret = main(
            [
                "reorganize",
                "--path",
                str(sample_bookmarks_path),
                "--ai",
                "--taxonomy",
                str(tax_path),
                "-o",
                str(out_file),
            ]
        )
    assert ret == 0
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "roots" in data

    # Recarregar e verificar profundidade ≥ 2
    reloaded = read_bookmarks(out_file)
    dev = next(
        (
            f
            for f in reloaded.bookmark_bar.children
            if hasattr(f, "name") and f.name == "Desenvolvimento"
        ),
        None,
    )
    assert dev is not None
    # Filhos de Desenvolvimento são pastas (subcategorias)
    assert all(getattr(c, "type", None) == "folder" for c in dev.children)


def test_cli_propose_tree(sample_bookmarks_path, tmp_path: Path, capsys):
    """propose-tree salva taxonomia chamando a IA mockada."""
    out_path = tmp_path / "tax.json"

    def responder(**kwargs):
        return _MockResponse(
            name="propose_taxonomy",
            input_={
                "categories": [
                    {
                        "name": "Tech",
                        "description": "Desenvolvimento",
                        "subcategories": [
                            {"name": "Código", "description": "Repos e Q&A"}
                        ],
                    },
                    {"name": "Outros", "description": "Resto", "subcategories": []},
                ]
            },
        )

    with patch(
        "bookmarks_manager.ai_taxonomy.get_client",
        return_value=_MockClient(responder),
    ):
        ret = main(
            [
                "propose-tree",
                "--path",
                str(sample_bookmarks_path),
                "-o",
                str(out_path),
            ]
        )
    assert ret == 0
    assert out_path.exists()
    data = json.loads(out_path.read_text(encoding="utf-8"))
    names = [c["name"] for c in data["categories"]]
    assert "Tech" in names
    assert "Outros" in names


def test_cli_propose_tree_refuses_existing_without_refresh(
    sample_bookmarks_path, tmp_path: Path, capsys
):
    out_path = tmp_path / "tax.json"
    out_path.write_text("{}", encoding="utf-8")
    ret = main(
        [
            "propose-tree",
            "--path",
            str(sample_bookmarks_path),
            "-o",
            str(out_path),
        ]
    )
    assert ret == 2
    err = capsys.readouterr().err
    assert "refresh" in err.lower()
