from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

from tqdm import tqdm

from ._util import (
    count_tokens,
    create_common_parser,
    find_files_bfs,
    main_init,
    read_file_content,
    resolve_paths,
)


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

    main_init(args)

    resolved_paths = resolve_paths(args.paths)
    file_contents = ['<?xml version="1.0" encoding="UTF-8"?>', "<project>"]
    all_files = []
    total_content = ""

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
                args.exclude_lock_files,
                args.gitignore,
                args.dir2textignore,
                args.output_gitignore,
                args.output_dir2textignore,
            )
            all_files.extend(matching_files)
            base_dir = path

        if len(resolved_paths) == 1:
            tree_lines = print_directory_tree_xml(all_files, base_dir)
            tree_text = "\n".join(tree_lines)
            total_content += tree_text + "\n"
            file_contents.extend(tree_lines)

    file_contents.append("<contents>")
    for file_path in (
        pbar := tqdm(sorted(all_files), desc="Processing files", unit="file")
    ):
        pbar.set_postfix_str(file_path.name)
        relative_path = file_path.name if file_path.parent == Path(".") else file_path
        content = read_file_content(file_path)
        if args.encode_xml:
            content = escape_xml_content(content)
        doc_section = (
            f'  <document path="{relative_path}">\n    {content}\n  </document>'
        )
        total_content += doc_section + "\n"
        file_contents.append(doc_section)

    file_contents.append("</contents>")
    file_contents.append("</project>")
    print("\n".join(file_contents))

    if args.count_tokens:
        token_count = count_tokens(total_content)
        print(f"\nTotal tokens: {token_count}", file=sys.stderr)


if __name__ == "__main__":
    main()
