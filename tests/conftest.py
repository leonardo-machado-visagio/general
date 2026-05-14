"""Configuração compartilhada e fixtures para testes."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_bookmarks.json"


@pytest.fixture
def sample_bookmarks_path() -> Path:
    return FIXTURE_PATH


@pytest.fixture
def sample_file(sample_bookmarks_path):
    from bookmarks_manager.reader import read_bookmarks

    return read_bookmarks(sample_bookmarks_path)
