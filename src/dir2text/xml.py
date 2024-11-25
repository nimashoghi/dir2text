from __future__ import annotations

import argparse
import html
from pathlib import Path

from ._util import create_common_parser, resolve_paths
from .text import find_files_bfs, read_file_content


def escape_xml_content(content: str) -> str:
    """Escape special characters for XML content."""
    return html.escape(content)


def print_directory_tree_xml(files: list[Path], base_dir: Path) -> list[str]:
    """Generate XML representation of the directory tree."""

    def format_tree(path: Path, indent: str = "") -> list[str]:
        result = []
        if path in files or any(f.is_relative_to(path) for f in files):
            if path.is_dir():
                result.append(f'{indent}<directory path="{path}">')
                children = sorted(path.iterdir(), key=lambda x: (x.is_dir(), x.name))
                for child in children:
                    if child in files or any(f.is_relative_to(child) for f in files):
                        result.extend(format_tree(child, indent + "  "))
                result.append(f"{indent}</directory>")
            else:
                result.append(f'{indent}<file path="{path}"/>')
        return result

    tree_lines = ["<structure>"]
    tree_lines.extend(format_tree(base_dir, "  "))
    tree_lines.append("</structure>")
    return tree_lines


def create_parser() -> argparse.ArgumentParser:
    parser = create_common_parser()
    parser.add_argument(
        "--encode-xml",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="HTML encode the XML content (default: False)",
    )
    return parser


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = create_parser().parse_args()

    resolved_paths = resolve_paths(args.paths)
    file_contents = ['<?xml version="1.0" encoding="UTF-8"?>', "<project>"]
    all_files = []

    for path in resolved_paths:
        if path.is_file():
            all_files.append(path)
            base_dir = path.parent
        else:
            matching_files = find_files_bfs(
                path,
                args.extension,
                args.include,
                args.exclude,
                args.gitignore,
                args.dir2textignore,
            )
            all_files.extend(matching_files)
            base_dir = path

        if len(resolved_paths) == 1:
            tree_lines = print_directory_tree_xml(all_files, base_dir)
            file_contents.extend(tree_lines)

    file_contents.append("<contents>")
    for file_path in sorted(all_files):
        relative_path = file_path.name if file_path.parent == Path(".") else file_path
        file_contents.append(f'  <document path="{relative_path}">')
        content = read_file_content(file_path)
        file_contents.append(f"    {escape_xml_content(content)}")
        file_contents.append("  </document>")

    file_contents.append("</contents>")
    file_contents.append("</project>")
    print("\n".join(file_contents))


if __name__ == "__main__":
    main()