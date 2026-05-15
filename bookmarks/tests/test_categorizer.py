"""Testes para o módulo categorizer."""

import pytest

from bookmarks_manager.categorizer import (
    CATEGORY_OTHER,
    available_categories,
    categorize_bookmarks,
    categorize_url,
)
from bookmarks_manager.reader import Bookmark


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/user/repo", "Desenvolvimento"),
        ("https://stackoverflow.com/q/123", "Desenvolvimento"),
        ("https://www.npmjs.com/package/react", "Desenvolvimento"),
        ("https://dev.to/article", "Desenvolvimento"),
        ("https://udemy.com/course/x", "Aprendizado"),
        ("https://coursera.org/learn/ml", "Aprendizado"),
        ("https://www.alura.com.br/curso", "Aprendizado"),
        ("https://chatgpt.com/c/abc", "IA e Pesquisa"),
        ("https://claude.ai/chats", "IA e Pesquisa"),
        ("https://huggingface.co/models", "IA e Pesquisa"),
        ("https://twitter.com/user", "Redes Sociais"),
        ("https://x.com/elon", "Redes Sociais"),
        ("https://www.linkedin.com/in/me", "Redes Sociais"),
        ("https://www.reddit.com/r/python", "Redes Sociais"),
        ("https://www.bbc.com/news", "Notícias"),
        ("https://g1.globo.com/economia", "Notícias"),
        ("https://news.ycombinator.com", "Notícias"),
        ("https://youtube.com/watch?v=x", "Entretenimento"),
        ("https://www.netflix.com/browse", "Entretenimento"),
        ("https://open.spotify.com/album/x", "Entretenimento"),
        ("https://www.amazon.com.br/dp/x", "Compras"),
        ("https://www.mercadolivre.com.br/p", "Compras"),
        ("https://mail.google.com/inbox", "Email e Comunicação"),
        ("https://app.slack.com", "Email e Comunicação"),
        ("https://discord.com/channels/x", "Email e Comunicação"),
        ("https://www.notion.so/page", "Trabalho e Produtividade"),
        ("https://figma.com/file/x", "Trabalho e Produtividade"),
        ("https://docs.google.com/document/x", "Documentos e Armazenamento"),
        ("https://www.dropbox.com/home", "Documentos e Armazenamento"),
        ("https://nubank.com.br/area-pj", "Finanças"),
        ("https://www.binance.com/trade", "Finanças"),
        ("https://www.booking.com/hotel", "Viagens"),
        ("https://www.airbnb.com.br/rooms", "Viagens"),
    ],
)
def test_categorize_known_domains(url, expected):
    assert categorize_url(url) == expected


def test_categorize_unknown_returns_other():
    assert categorize_url("https://random-blog-xyz.example") == CATEGORY_OTHER


def test_categorize_empty_url_returns_other():
    assert categorize_url("") == CATEGORY_OTHER


def test_categorize_subdomain_matches():
    assert categorize_url("https://gist.github.com/abc") == "Desenvolvimento"


def test_categorize_uses_keywords_in_name():
    assert categorize_url("https://example.com/", "Tutorial de Docker") == "Desenvolvimento"


def test_categorize_bookmarks_groups_correctly():
    bookmarks = [
        Bookmark(name="GitHub", url="https://github.com"),
        Bookmark(name="YouTube", url="https://youtube.com"),
        Bookmark(name="Random", url="https://random-xyz.example"),
    ]
    result = categorize_bookmarks(bookmarks)
    assert "Desenvolvimento" in result.categories
    assert "Entretenimento" in result.categories
    assert CATEGORY_OTHER in result.categories
    assert len(result.categories["Desenvolvimento"]) == 1
    assert len(result.categories[CATEGORY_OTHER]) == 1


def test_available_categories_returns_non_empty():
    cats = available_categories()
    assert len(cats) > 5
    assert CATEGORY_OTHER not in cats
