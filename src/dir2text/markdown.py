from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._util import (
    count_tokens,
    create_common_parser,
    find_files_bfs,
    read_file_content,
    resolve_paths,
)

EXTENSION_TO_LANGUAGE = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "html": "html",
    "css": "css",
    "md": "markdown",
    "json": "json",
    "yml": "yaml",
    "yaml": "yaml",
    "sh": "bash",
    "bat": "batch",
    "ps1": "powershell",
    "sql": "sql",
    "r": "r",
    "cpp": "cpp",
    "c": "c",
    "java": "java",
    "go": "go",
    "rb": "ruby",
    "php": "php",
    "swift": "swift",
    "kt": "kotlin",
    "rs": "rust",
    "scala": "scala",
    "m": "matlab",
    "tex": "latex",
}


def print_directory_tree_md(files: list[Path], base_dir: Path):
    def format_tree(path: Path, prefix: str = "") -> list[str]:
        result = []
        if path in files or any(f.is_relative_to(path) for f in files):
            result.append(f"{prefix}- `{path.name}{'/' if path.is_dir() else ''}`")
            if path.is_dir():
                children = sorted(path.iterdir(), key=lambda x: (x.is_dir(), x.name))
                for i, child in enumerate(children):
                    if child in files or any(f.is_relative_to(child) for f in files):
                        if i == len(children) - 1:
                            result.extend(format_tree(child, prefix + "  "))
                        else:
                            result.extend(format_tree(child, prefix + "  "))
        return result

    tree_lines = ["## Directory structure\n"]
    tree_lines.extend(format_tree(base_dir))
    return tree_lines


def create_parser() -> argparse.ArgumentParser:
    parser = create_common_parser()
    return parser


def main(args: argparse.Namespace | None = None):
    if args is None:
        args = create_parser().parse_args()

    resolved_paths = resolve_paths(args.paths)
    file_contents = ["# Project Structure and Contents\n"]
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
                args.gitignore,
                args.dir2textignore,
            )
            all_files.extend(matching_files)
            base_dir = path

        if len(resolved_paths) == 1:
            tree_lines = print_directory_tree_md(all_files, base_dir)
            tree_text = "\n".join(tree_lines)
            total_content += tree_text + "\n\n"
            print(tree_text)

    for file_path in sorted(all_files):
        relative_path = file_path.name if file_path.parent == Path(".") else file_path
        header = f"## {relative_path}\n"
        language = EXTENSION_TO_LANGUAGE.get(file_path.suffix.lstrip("."), "")
        content = read_file_content(file_path)

        file_section = f"{header}```{language}\n{content}\n```\n"
        total_content += file_section
        file_contents.append(file_section)
    print("\n".join(file_contents))

    if args.count_tokens:
        token_count = count_tokens(total_content)
        print(f"\nTotal tokens: {token_count}", file=sys.stderr)


if __name__ == "__main__":
    main()
