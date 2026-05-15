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
from bookmarks_manager.reorganizer import (
    ai_suggest_reorganization,
    build_reorganized_tree,
    build_reorganized_tree_from_assignments,
    build_tree_from_suggestion,
    suggest_reorganization,
)
from bookmarks_manager.taxonomy import (
    Category,
    Subcategory,
    Taxonomy,
    load_taxonomy,
    save_taxonomy,
)

__all__ = [
    "Bookmark",
    "BookmarkFile",
    "BookmarkStats",
    "Category",
    "Folder",
    "Subcategory",
    "Taxonomy",
    "ai_suggest_reorganization",
    "analyze",
    "build_reorganized_tree",
    "build_reorganized_tree_from_assignments",
    "build_tree_from_suggestion",
    "categorize_bookmarks",
    "categorize_url",
    "default_chrome_path",
    "load_taxonomy",
    "read_bookmarks",
    "save_taxonomy",
    "suggest_reorganization",
]
