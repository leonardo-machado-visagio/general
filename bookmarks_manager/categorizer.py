"""Categorização heurística de URLs em grupos temáticos.

A categorização é baseada em:
1. Correspondência de domínio (mais confiável)
2. Palavras-chave no nome do bookmark ou path da URL (fallback)

Cada categoria possui um nome em português e uma lista de padrões.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from bookmarks_manager.reader import Bookmark


CATEGORY_OTHER = "Outros"


@dataclass(frozen=True)
class CategoryRule:
    name: str
    domains: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


_RULES: tuple[CategoryRule, ...] = (
    CategoryRule(
        name="Desenvolvimento",
        domains=(
            "github.com",
            "gitlab.com",
            "bitbucket.org",
            "stackoverflow.com",
            "stackexchange.com",
            "npmjs.com",
            "pypi.org",
            "rubygems.org",
            "crates.io",
            "packagist.org",
            "docker.com",
            "hub.docker.com",
            "kubernetes.io",
            "dev.to",
            "hashnode.com",
            "codepen.io",
            "jsfiddle.net",
            "replit.com",
            "codesandbox.io",
            "go.dev",
            "rust-lang.org",
            "python.org",
            "nodejs.org",
            "mozilla.org",
            "mdn.io",
            "developer.mozilla.org",
            "regex101.com",
        ),
        keywords=("docs", "documentation", "api", "sdk", "github", "tutorial"),
    ),
    CategoryRule(
        name="Aprendizado",
        domains=(
            "udemy.com",
            "coursera.org",
            "edx.org",
            "khanacademy.org",
            "codecademy.com",
            "freecodecamp.org",
            "pluralsight.com",
            "leetcode.com",
            "hackerrank.com",
            "exercism.io",
            "scrimba.com",
            "alura.com.br",
            "rocketseat.com.br",
            "domestika.org",
            "skillshare.com",
        ),
        keywords=("curso", "course", "tutorial", "aprenda", "learn"),
    ),
    CategoryRule(
        name="IA e Pesquisa",
        domains=(
            "chatgpt.com",
            "chat.openai.com",
            "openai.com",
            "claude.ai",
            "anthropic.com",
            "gemini.google.com",
            "bard.google.com",
            "perplexity.ai",
            "huggingface.co",
            "kaggle.com",
            "arxiv.org",
            "papers.with.code",
            "paperswithcode.com",
            "scholar.google.com",
        ),
        keywords=("llm", "gpt", "ml", "ai-research"),
    ),
    CategoryRule(
        name="Redes Sociais",
        domains=(
            "facebook.com",
            "twitter.com",
            "x.com",
            "instagram.com",
            "linkedin.com",
            "reddit.com",
            "tiktok.com",
            "snapchat.com",
            "threads.net",
            "bsky.app",
            "mastodon.social",
            "pinterest.com",
            "tumblr.com",
        ),
    ),
    CategoryRule(
        name="Notícias",
        domains=(
            "bbc.com",
            "bbc.co.uk",
            "cnn.com",
            "nytimes.com",
            "theguardian.com",
            "reuters.com",
            "bloomberg.com",
            "wsj.com",
            "ft.com",
            "economist.com",
            "globo.com",
            "g1.globo.com",
            "folha.uol.com.br",
            "uol.com.br",
            "estadao.com.br",
            "valor.globo.com",
            "exame.com",
            "hackernews.com",
            "news.ycombinator.com",
        ),
        keywords=("noticia", "noticias", "news"),
    ),
    CategoryRule(
        name="Entretenimento",
        domains=(
            "youtube.com",
            "youtu.be",
            "netflix.com",
            "hulu.com",
            "disneyplus.com",
            "primevideo.com",
            "hbomax.com",
            "max.com",
            "twitch.tv",
            "spotify.com",
            "soundcloud.com",
            "vimeo.com",
            "deezer.com",
            "apple.com/music",
            "tidal.com",
            "imdb.com",
            "letterboxd.com",
        ),
    ),
    CategoryRule(
        name="Compras",
        domains=(
            "amazon.com",
            "amazon.com.br",
            "mercadolivre.com.br",
            "mercadolivre.com",
            "ebay.com",
            "aliexpress.com",
            "magazineluiza.com.br",
            "americanas.com.br",
            "shopee.com.br",
            "shopify.com",
            "etsy.com",
            "shein.com",
        ),
    ),
    CategoryRule(
        name="Email e Comunicação",
        domains=(
            "gmail.com",
            "mail.google.com",
            "outlook.com",
            "outlook.live.com",
            "office.com",
            "slack.com",
            "discord.com",
            "teams.microsoft.com",
            "whatsapp.com",
            "web.whatsapp.com",
            "telegram.org",
            "web.telegram.org",
            "zoom.us",
            "meet.google.com",
            "signal.org",
        ),
    ),
    CategoryRule(
        name="Trabalho e Produtividade",
        domains=(
            "notion.so",
            "trello.com",
            "asana.com",
            "monday.com",
            "clickup.com",
            "linear.app",
            "jira.com",
            "atlassian.net",
            "atlassian.com",
            "figma.com",
            "miro.com",
            "lucidchart.com",
            "airtable.com",
            "basecamp.com",
            "todoist.com",
            "evernote.com",
        ),
    ),
    CategoryRule(
        name="Documentos e Armazenamento",
        domains=(
            "docs.google.com",
            "drive.google.com",
            "sheets.google.com",
            "slides.google.com",
            "dropbox.com",
            "onedrive.live.com",
            "box.com",
            "icloud.com",
            "mega.nz",
        ),
    ),
    CategoryRule(
        name="Finanças",
        domains=(
            "nubank.com.br",
            "itau.com.br",
            "bancodobrasil.com.br",
            "bradesco.com.br",
            "santander.com.br",
            "binance.com",
            "coinbase.com",
            "stripe.com",
            "paypal.com",
            "wise.com",
            "investing.com",
            "tradingview.com",
            "yahoo.com/finance",
            "b3.com.br",
        ),
        keywords=("banco", "bank", "invest"),
    ),
    CategoryRule(
        name="Viagens",
        domains=(
            "booking.com",
            "airbnb.com",
            "airbnb.com.br",
            "expedia.com",
            "kayak.com",
            "decolar.com",
            "latam.com",
            "gol.com.br",
            "azul.com.br",
            "tripadvisor.com",
            "skyscanner.com",
            "maps.google.com",
            "google.com/maps",
        ),
        keywords=("travel", "viagem", "voos"),
    ),
)


@dataclass
class CategorizedBookmark:
    bookmark: Bookmark
    category: str


@dataclass
class CategorizationResult:
    categories: dict[str, list[Bookmark]] = field(default_factory=dict)

    def add(self, category: str, bookmark: Bookmark) -> None:
        self.categories.setdefault(category, []).append(bookmark)

    def summary(self) -> list[tuple[str, int]]:
        return sorted(
            ((cat, len(bms)) for cat, bms in self.categories.items()),
            key=lambda x: (-x[1], x[0]),
        )


def _normalize_host(host: str) -> str:
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_matches(host: str, pattern: str) -> bool:
    """Verifica se ``host`` é igual ou subdomínio de ``pattern``.

    Suporta padrões com path (ex: ``yahoo.com/finance``).
    """
    pattern = pattern.lower()
    if "/" in pattern:
        # Apenas comparação de host; o path é tratado separadamente.
        pattern = pattern.split("/", 1)[0]
    if host == pattern:
        return True
    return host.endswith("." + pattern)


def categorize_url(url: str, name: str = "") -> str:
    """Retorna o nome da categoria mais provável para uma URL.

    Retorna ``CATEGORY_OTHER`` se nenhuma categoria casar.
    """
    if not url:
        return CATEGORY_OTHER

    try:
        parsed = urlparse(url)
    except ValueError:
        return CATEGORY_OTHER

    host = _normalize_host(parsed.hostname or "")
    path = (parsed.path or "").lower()
    text = f"{name} {path}".lower()

    if not host:
        return CATEGORY_OTHER

    for rule in _RULES:
        for domain in rule.domains:
            if "/" in domain:
                base, _, sub_path = domain.partition("/")
                if _host_matches(host, base) and sub_path in path:
                    return rule.name
            elif _host_matches(host, domain):
                return rule.name

    for rule in _RULES:
        for keyword in rule.keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", text):
                return rule.name

    return CATEGORY_OTHER


def categorize_bookmarks(bookmarks: list[Bookmark]) -> CategorizationResult:
    """Aplica ``categorize_url`` em uma lista de bookmarks."""
    result = CategorizationResult()
    for bm in bookmarks:
        category = categorize_url(bm.url, bm.name)
        result.add(category, bm)
    return result


def available_categories() -> list[str]:
    """Lista todas as categorias disponíveis (sem ``Outros``)."""
    return [rule.name for rule in _RULES]
