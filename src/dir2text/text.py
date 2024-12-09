from __future__ import annotations

import argparse
import fnmatch
import os
from collections.abc import Sequence
from pathlib import Path

from gitignore_parser import parse_gitignore

from ._util import count_tokens, create_common_parser, resolve_paths, convert_notebook_to_python


def read_file_content(file_path: Path, ipython: bool = True) -> str:
    """Read the content of a file.

    Args:
        file_path: Path to the file to read
        ipython: Whether to convert IPython notebooks to Python scripts

    Returns:
        The content of the file as a string
    """
    try:
        # Handle IPython notebooks
        if ipython and file_path.suffix == ".ipynb":
            return convert_notebook_to_python(file_path)

        # Handle regular files
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        return "[Binary file]"


def find_files_bfs(
    directory: Path,
    extension: str | None = None,
    include_patterns: Sequence[str] = [],
    exclude_patterns: Sequence[str] = [],
    respect_gitignore: bool = True,
    respect_dir2textignore: bool = True,
) -> list[Path]:
    matches = []
    gitignore_matcher = None
    dir2textignore_matcher = None

    # Check for .gitignore
    if respect_gitignore:
        gitignore_path = directory / ".gitignore"
        if gitignore_path.exists():
            gitignore_matcher = parse_gitignore(gitignore_path)

    # Check for .dir2textignore
    if respect_dir2textignore:
        dir2textignore_path = directory / ".dir2textignore"
        if dir2textignore_path.exists():
            dir2textignore_matcher = parse_gitignore(dir2textignore_path)

    for root, _, files in os.walk(directory):
        root_path = Path(root)

        for file in files:
            file_path = root_path / file
            relative_path = file_path.relative_to(directory)

            # Skip if matches gitignore
            if gitignore_matcher and gitignore_matcher(str(file_path)):
                continue

            # Skip if matches dir2textignore
            if dir2textignore_matcher and dir2textignore_matcher(str(file_path)):
                continue

            # Check extension
            if extension and not str(file_path).endswith(extension):
                continue

            # Check include patterns
            if include_patterns and not any(
                fnmatch.fnmatch(str(relative_path), pattern)
                for pattern in include_patterns
            ):
                continue

            # Check exclude patterns
            if any(
                fnmatch.fnmatch(str(relative_path), pattern)
                for pattern in exclude_patterns
            ):
                continue

            matches.append(file_path)

    return sorted(matches)


def print_directory_tree(files: Sequence[Path], base_dir: Path) -> list[str]:
    def format_tree(path: Path, prefix: str = "") -> list[str]:
        result = []
        if path in files or any(f.is_relative_to(path) for f in files):
            result.append(f"{prefix}{path.name}{'/' if path.is_dir() else ''}")
            if path.is_dir():
                children = sorted(path.iterdir(), key=lambda x: (x.is_dir(), x.name))
                for i, child in enumerate(children):
                    if child in files or any(f.is_relative_to(child) for f in files):
                        if i == len(children) - 1:
                            result.extend(format_tree(child, prefix + "    "))
                        else:
                            result.extend(format_tree(child, prefix + "│   "))
        return result

    tree_lines = ["Directory structure:", ""]
    tree_lines.extend(format_tree(base_dir))
    return tree_lines


def create_parser() -> argparse.ArgumentParser:
    parser = create_common_parser()
    return parser


def main(args: argparse.Namespace | None = None) -> None:
    if args is None:
        args = create_parser().parse_args()

    resolved_paths = resolve_paths(args.paths)
    file_contents = ["Project Structure and Contents", ""]
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
            tree_lines = print_directory_tree(all_files, base_dir)
            tree_text = "\n".join(tree_lines)
            total_content += tree_text + "\n\n"
            print(tree_text)
            print()

    for file_path in sorted(all_files):
        relative_path = file_path.name if file_path.parent == Path(".") else file_path
        header = f"=== {relative_path} ==="
        content = read_file_content(file_path, args.ipython)
        total_content += header + "\n" + content + "\n\n"
        file_contents.append(header)
        file_contents.append(content)
        file_contents.append("")

    if args.count_tokens:
        token_count = count_tokens(total_content)
        token_info = f"Total tokens: {token_count}\n"
        print(token_info)
    print("\n".join(file_contents))


if __name__ == "__main__":
    main()
