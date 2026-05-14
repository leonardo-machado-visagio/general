"""Permite executar via ``python -m bookmarks_manager``."""

import sys

from bookmarks_manager.cli import main

if __name__ == "__main__":
    sys.exit(main())
