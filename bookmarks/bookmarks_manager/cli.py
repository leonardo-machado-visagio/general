"""Interface de linha de comando para o gerenciador de bookmarks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bookmarks_manager.analyzer import analyze
from bookmarks_manager.reader import default_chrome_path, read_bookmarks
from bookmarks_manager.reorganizer import (
    ai_suggest_reorganization,
    build_reorganized_tree,
    build_tree_from_suggestion,
    suggest_reorganization,
)
from bookmarks_manager.taxonomy import load_taxonomy, save_taxonomy


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Caminho do arquivo Bookmarks (padrão: auto-detectar)",
    )
    parser.add_argument(
        "--profile",
        default="Default",
        help="Perfil do Chrome (padrão: Default)",
    )


def cmd_path(args: argparse.Namespace) -> int:
    path = default_chrome_path(args.profile)
    print(path)
    print(f"Existe: {path.exists()}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    file = read_bookmarks(args.path, profile=args.profile)
    stats = analyze(file, top_n=args.top)
    print(stats.format_report())
    return 0


def cmd_propose_tree(args: argparse.Namespace) -> int:
    from bookmarks_manager.ai_taxonomy import propose_taxonomy

    out_path: Path = args.output
    if out_path.exists() and not args.refresh:
        print(
            f"Já existe taxonomia em {out_path}. Use --refresh para sobrescrever.",
            file=sys.stderr,
        )
        return 2

    file = read_bookmarks(args.path, profile=args.profile)
    bookmarks = list(file.iter_bookmarks())
    if not bookmarks:
        print("Nenhum bookmark encontrado.", file=sys.stderr)
        return 1

    print(f"Propondo taxonomia a partir de {len(bookmarks)} bookmarks...")
    taxonomy = propose_taxonomy(bookmarks, sample_size=args.sample_size)
    save_taxonomy(taxonomy, out_path)
    print(f"Taxonomia salva em: {out_path}")
    print()
    print(taxonomy.format_report())
    return 0


def cmd_suggest(args: argparse.Namespace) -> int:
    file = read_bookmarks(args.path, profile=args.profile)

    if args.ai:
        taxonomy = _load_or_fail(args.taxonomy)
        suggestion = ai_suggest_reorganization(
            file, taxonomy, remove_duplicates=not args.keep_duplicates
        )
    else:
        suggestion = suggest_reorganization(
            file, remove_duplicates=not args.keep_duplicates
        )

    if args.detailed:
        print(suggestion.format_detailed_report(limit_per_category=args.sample))
    else:
        print(suggestion.format_report())
    return 0


def cmd_reorganize(args: argparse.Namespace) -> int:
    file = read_bookmarks(args.path, profile=args.profile)

    out_path: Path = args.output
    if out_path.exists() and not args.force:
        print(
            f"Erro: {out_path} já existe. Use --force para sobrescrever.",
            file=sys.stderr,
        )
        return 2

    if args.ai:
        taxonomy = _load_or_fail(args.taxonomy)
        suggestion = ai_suggest_reorganization(
            file, taxonomy, remove_duplicates=not args.keep_duplicates
        )
        new_file = build_tree_from_suggestion(
            suggestion, file, target_root=args.target_root
        )
    else:
        new_file = build_reorganized_tree(
            file,
            remove_duplicates=not args.keep_duplicates,
            target_root=args.target_root,
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(new_file.to_chrome_dict(), fh, ensure_ascii=False, indent=3)

    print(f"Estrutura reorganizada salva em: {out_path}")
    print(
        "Importante: este arquivo NÃO substitui o arquivo do Chrome automaticamente. "
        "Para aplicá-lo: feche o Chrome, faça backup do arquivo Bookmarks atual, "
        "e copie o novo arquivo para o lugar do original."
    )
    return 0


def _load_or_fail(path: Path | None):
    if path is None:
        raise ValueError(
            "--ai requer --taxonomy <arquivo>. "
            "Rode `propose-tree -o taxonomy.json` antes."
        )
    return load_taxonomy(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bookmarks-manager",
        description="Lê e reorganiza bookmarks do Google Chrome.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_path = sub.add_parser("path", help="Mostra o caminho padrão do arquivo Bookmarks")
    p_path.add_argument(
        "--profile",
        default="Default",
        help="Perfil do Chrome (padrão: Default)",
    )
    p_path.set_defaults(func=cmd_path)

    p_analyze = sub.add_parser("analyze", help="Mostra estatísticas dos bookmarks")
    _add_common_args(p_analyze)
    p_analyze.add_argument(
        "--top",
        type=int,
        default=10,
        help="Quantos domínios listar no top (padrão: 10)",
    )
    p_analyze.set_defaults(func=cmd_analyze)

    p_propose = sub.add_parser(
        "propose-tree",
        help="Gera taxonomia (2 níveis) via IA a partir dos seus bookmarks",
    )
    _add_common_args(p_propose)
    p_propose.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Onde salvar o JSON da taxonomia",
    )
    p_propose.add_argument(
        "--sample-size",
        type=int,
        default=500,
        help="Tamanho máximo da amostra enviada à IA (padrão: 500)",
    )
    p_propose.add_argument(
        "--refresh",
        action="store_true",
        help="Sobrescrever taxonomia existente",
    )
    p_propose.set_defaults(func=cmd_propose_tree)

    p_suggest = sub.add_parser("suggest", help="Sugere reorganização por categorias")
    _add_common_args(p_suggest)
    p_suggest.add_argument(
        "--detailed",
        action="store_true",
        help="Mostra amostras de bookmarks em cada categoria",
    )
    p_suggest.add_argument(
        "--sample",
        type=int,
        default=5,
        help="Quantos itens mostrar por categoria em modo detalhado (padrão: 5)",
    )
    p_suggest.add_argument(
        "--keep-duplicates",
        action="store_true",
        help="Não remover URLs duplicadas",
    )
    p_suggest.add_argument(
        "--ai",
        action="store_true",
        help="Categorizar via IA usando a taxonomia indicada por --taxonomy",
    )
    p_suggest.add_argument(
        "--taxonomy",
        type=Path,
        default=None,
        help="Caminho do arquivo de taxonomia (obrigatório com --ai)",
    )
    p_suggest.set_defaults(func=cmd_suggest)

    p_reorg = sub.add_parser(
        "reorganize",
        help="Gera um novo arquivo Bookmarks reorganizado (não sobrescreve o original)",
    )
    _add_common_args(p_reorg)
    p_reorg.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Caminho de saída para o novo arquivo Bookmarks",
    )
    p_reorg.add_argument(
        "--target-root",
        choices=("bookmark_bar", "other", "synced"),
        default="bookmark_bar",
        help="Raiz onde colocar as pastas reorganizadas (padrão: bookmark_bar)",
    )
    p_reorg.add_argument(
        "--keep-duplicates",
        action="store_true",
        help="Não remover URLs duplicadas",
    )
    p_reorg.add_argument(
        "--force",
        action="store_true",
        help="Sobrescrever o arquivo de saída se já existir",
    )
    p_reorg.add_argument(
        "--ai",
        action="store_true",
        help="Categorizar via IA (árvore de 2 níveis) usando --taxonomy",
    )
    p_reorg.add_argument(
        "--taxonomy",
        type=Path,
        default=None,
        help="Caminho do arquivo de taxonomia (obrigatório com --ai)",
    )
    p_reorg.set_defaults(func=cmd_reorganize)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except FileNotFoundError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
