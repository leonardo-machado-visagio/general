"""Estrutura de dados da taxonomia (2 níveis) + I/O JSON.

Uma ``Taxonomy`` é uma lista de ``Category`` (nível 1), cada uma contendo
uma lista de ``Subcategory`` (nível 2). Categorias podem ter zero
subcategorias — nesse caso a categoria atua como folha.

A categoria especial ``Outros`` é sempre garantida no carregamento e
recebe bookmarks que a IA não conseguiu encaixar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

CATEGORY_OTHER = "Outros"
SUBCATEGORY_GENERAL = "Geral"
TAXONOMY_SCHEMA_VERSION = 1


@dataclass
class Subcategory:
    name: str
    description: str = ""


@dataclass
class Category:
    name: str
    description: str = ""
    subcategories: list[Subcategory] = field(default_factory=list)

    def subcategory_names(self) -> list[str]:
        return [s.name for s in self.subcategories]


@dataclass
class Taxonomy:
    categories: list[Category] = field(default_factory=list)
    version: int = TAXONOMY_SCHEMA_VERSION
    generated_at: str = ""
    model: str = ""
    n_bookmarks_sampled: int = 0

    def category_names(self) -> list[str]:
        return [c.name for c in self.categories]

    def find_category(self, name: str) -> Category | None:
        norm = name.strip().lower()
        for cat in self.categories:
            if cat.name.strip().lower() == norm:
                return cat
        return None

    def has_path(self, category: str, subcategory: str | None) -> bool:
        cat = self.find_category(category)
        if cat is None:
            return False
        if not subcategory:
            return not cat.subcategories
        norm = subcategory.strip().lower()
        return any(s.name.strip().lower() == norm for s in cat.subcategories)

    def ensure_other(self) -> None:
        """Garante que existe uma categoria 'Outros' como destino de fallback."""
        if self.find_category(CATEGORY_OTHER) is None:
            self.categories.append(
                Category(
                    name=CATEGORY_OTHER,
                    description="Bookmarks que não se encaixam nas demais categorias.",
                    subcategories=[],
                )
            )

    def flatten_paths(self) -> list[str]:
        """Lista todos os paths 'Categoria > Subcategoria' (ou só 'Categoria')."""
        out: list[str] = []
        for cat in self.categories:
            if cat.subcategories:
                for sub in cat.subcategories:
                    out.append(f"{cat.name} > {sub.name}")
            else:
                out.append(cat.name)
        return out

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "model": self.model,
            "n_bookmarks_sampled": self.n_bookmarks_sampled,
            "categories": [
                {
                    "name": c.name,
                    "description": c.description,
                    "subcategories": [
                        {"name": s.name, "description": s.description}
                        for s in c.subcategories
                    ],
                }
                for c in self.categories
            ],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Taxonomy":
        cats: list[Category] = []
        for raw in data.get("categories", []):
            subs = [
                Subcategory(name=s.get("name", ""), description=s.get("description", ""))
                for s in raw.get("subcategories", [])
                if s.get("name")
            ]
            if raw.get("name"):
                cats.append(
                    Category(
                        name=raw["name"],
                        description=raw.get("description", ""),
                        subcategories=subs,
                    )
                )
        tax = cls(
            categories=cats,
            version=int(data.get("version", TAXONOMY_SCHEMA_VERSION)),
            generated_at=data.get("generated_at", ""),
            model=data.get("model", ""),
            n_bookmarks_sampled=int(data.get("n_bookmarks_sampled", 0)),
        )
        tax.ensure_other()
        return tax

    def format_report(self) -> str:
        lines = ["=== Taxonomia ==="]
        if self.model:
            lines.append(f"Gerada por: {self.model}")
        if self.generated_at:
            lines.append(f"Em: {self.generated_at}")
        if self.n_bookmarks_sampled:
            lines.append(f"Amostra: {self.n_bookmarks_sampled} bookmarks")
        lines.append("")
        for cat in self.categories:
            lines.append(f"[{cat.name}]")
            if cat.description:
                lines.append(f"  {cat.description}")
            for sub in cat.subcategories:
                lines.append(f"    - {sub.name}")
                if sub.description:
                    lines.append(f"        {sub.description}")
            lines.append("")
        return "\n".join(lines).rstrip()


def save_taxonomy(tax: Taxonomy, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as fh:
        json.dump(tax.to_dict(), fh, ensure_ascii=False, indent=2)


def load_taxonomy(path: str | Path) -> Taxonomy:
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"Taxonomia não encontrada em: {target}")
    with target.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return Taxonomy.from_dict(data)
