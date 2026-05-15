"""Gerenciador de bookmarks do Google Chrome."""

from bookmarks_manager.analyzer import BookmarkStats, analyze
from bookmarks_manager.categorizer import categorize_url, categorize_bookmarks
from bookmarks_manager.reader import (
    Bookmark,
    BookmarkFile,
    Folder,
    default_chrome_path,
    read_bookmarks,
)
from bookmarks_manager.reorganizer import build_reorganized_tree, suggest_reorganization

__all__ = [
    "Bookmark",
    "BookmarkFile",
    "BookmarkStats",
    "Folder",
    "analyze",
    "build_reorganized_tree",
    "categorize_bookmarks",
    "categorize_url",
    "default_chrome_path",
    "read_bookmarks",
    "suggest_reorganization",
]
