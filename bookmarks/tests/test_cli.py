"""Testes para a CLI."""

import json
from pathlib import Path

import pytest

from bookmarks_manager.cli import main


def test_cli_path_command(capsys):
    ret = main(["path"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Bookmarks" in out
    assert "Existe:" in out


def test_cli_analyze(sample_bookmarks_path, capsys):
    ret = main(["analyze", "--path", str(sample_bookmarks_path)])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Total de bookmarks" in out


def test_cli_suggest(sample_bookmarks_path, capsys):
    ret = main(["suggest", "--path", str(sample_bookmarks_path)])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Sugestão de Reorganização" in out


def test_cli_suggest_detailed(sample_bookmarks_path, capsys):
    ret = main(["suggest", "--path", str(sample_bookmarks_path), "--detailed"])
    assert ret == 0
    out = capsys.readouterr().out
    assert "Amostras por Categoria" in out


def test_cli_reorganize_writes_output(sample_bookmarks_path, tmp_path: Path, capsys):
    out_file = tmp_path / "Bookmarks"
    ret = main(
        [
            "reorganize",
            "--path",
            str(sample_bookmarks_path),
            "-o",
            str(out_file),
        ]
    )
    assert ret == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "roots" in data
    assert data["version"] == 1


def test_cli_reorganize_refuses_existing_without_force(
    sample_bookmarks_path, tmp_path: Path, capsys
):
    out_file = tmp_path / "Bookmarks"
    out_file.write_text("existing")
    ret = main(
        [
            "reorganize",
            "--path",
            str(sample_bookmarks_path),
            "-o",
            str(out_file),
        ]
    )
    assert ret == 2


def test_cli_reorganize_with_force_overwrites(
    sample_bookmarks_path, tmp_path: Path, capsys
):
    out_file = tmp_path / "Bookmarks"
    out_file.write_text("existing")
    ret = main(
        [
            "reorganize",
            "--path",
            str(sample_bookmarks_path),
            "-o",
            str(out_file),
            "--force",
        ]
    )
    assert ret == 0
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "roots" in data


def test_cli_missing_file_returns_error(tmp_path: Path, capsys):
    ret = main(["analyze", "--path", str(tmp_path / "missing.json")])
    assert ret == 1
    err = capsys.readouterr().err
    assert "Erro" in err
