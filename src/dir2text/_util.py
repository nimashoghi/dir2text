from __future__ import annotations

import argparse
import fnmatch
import glob
import logging
import os
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import NamedTuple

import nbformat
import tiktoken
from gitignore_parser import parse_gitignore
from nbconvert import PythonExporter

log = logging.getLogger(__name__)
logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.INFO)


def resolve_paths(paths: str | list[str]) -> list[Path]:
    if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
        log.debug(f"Resolving paths: {paths}")

    if isinstance(paths, str):
        paths = [paths]

    resolved_paths = []
    for path_pattern in paths:
        # Handle glob patterns
        if any(char in path_pattern for char in "*?[]"):
            glob_paths = glob.glob(path_pattern)
            resolved_paths.extend(Path(p) for p in glob_paths)
        else:
            resolved_paths.append(Path(path_pattern))

    return resolved_paths


def create_common_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "paths",
        nargs="+",
        type=str,
        help="Files or directories to process. Supports glob patterns.",
    )
    parser.add_argument(
        "--extension", "-e", help="The file extension to search for (e.g., '.py')"
    )
    parser.add_argument(
        "--include",
        "-i",
        action="append",
        default=[],
        help="Patterns to include (can be used multiple times)",
    )
    parser.add_argument(
        "--exclude",
        "-x",
        action="append",
        default=[],
        help="Patterns to exclude (can be used multiple times)",
    )
    parser.add_argument(
        "--gitignore",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Respect .gitignore files",
    )
    parser.add_argument(
        "--dir2textignore",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Respect .dir2textignore files",
    )
    parser.add_argument(
        "--count-tokens",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Count and display the number of tokens in the output",
    )
    parser.add_argument(
        "--ipython",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Convert IPython notebooks to Python scripts (default: True)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--exclude-lock-files",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exclude lock files (e.g., Pipfile.lock, poetry.lock) from the output",
    )
    parser.add_argument(
        "--output-gitignore",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Output the contents of .gitignore files",
    )
    parser.add_argument(
        "--output-dir2textignore",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Output the contents of .dir2textignore files",
    )
    return parser


def main_init(args: argparse.Namespace) -> None:
    """Initialize logging based on verbose flag"""
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        log.debug("Debug logging enabled")
    else:
        logging.getLogger().setLevel(logging.INFO)


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """
    Count the number of tokens in a text using tiktoken.

    Args:
        text: The text to count tokens for
        model: The model to use for counting tokens (default: gpt-4)

    Returns:
        The number of tokens in the text
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to cl100k_base if model-specific encoding is not found
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))


def convert_notebook_to_python(file_path: Path) -> str:
    """Convert an IPython notebook to Python script.

    Args:
        file_path: Path to the notebook file

    Returns:
        The notebook contents converted to a Python script as a string
    """
    try:
        with open(file_path) as f:
            nb = nbformat.read(f, as_version=4)
        exporter = PythonExporter()
        python_code, _ = exporter.from_notebook_node(nb)
        return python_code
    except Exception as e:
        return f"[Error converting notebook: {str(e)}]"


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


class IgnoreMatchers(NamedTuple):
    gitignore: list[Callable[[str], bool]]
    dir2textignore: list[Callable[[str], bool]]


def get_ignore_matchers(directory: Path) -> IgnoreMatchers:
    """Get ignore matchers for a specific directory."""
    gitignore_matchers: list[Callable[[str], bool]] = []
    dir2textignore_matchers: list[Callable[[str], bool]] = []

    # Check for .gitignore in current directory
    gitignore_path = directory / ".gitignore"
    if gitignore_path.exists():
        log.debug(f"Using .gitignore file: {gitignore_path}")
        gitignore_matchers.append(parse_gitignore(gitignore_path))

    # Check for .dir2textignore in current directory
    dir2textignore_path = directory / ".dir2textignore"
    if dir2textignore_path.exists():
        log.debug(f"Using .dir2textignore file: {dir2textignore_path}")
        dir2textignore_matchers.append(parse_gitignore(dir2textignore_path))

    return IgnoreMatchers(gitignore_matchers, dir2textignore_matchers)


def find_files_bfs(
    directory: Path,
    extension: str | None = None,
    include_patterns: Sequence[str] = [],
    exclude_patterns: Sequence[str] = [],
    exclude_lock_files: bool = True,
    respect_gitignore: bool = True,
    respect_dir2textignore: bool = True,
) -> list[Path]:
    """
    Find files using breadth-first search while respecting nested ignore files.

    Args:
        directory: Root directory to start search from
        extension: Optional file extension filter
        include_patterns: Patterns to explicitly include
        exclude_patterns: Patterns to explicitly exclude
        exclude_lock_files: Whether to exclude lock files
        respect_gitignore: Whether to respect .gitignore files
        respect_dir2textignore: Whether to respect .dir2textignore files

    Returns:
        List of matching file paths
    """
    matches: list[Path] = []
    directory = Path(directory).resolve().absolute()

    # Get ignore matchers that apply to the entire tree (from root down to start directory)
    root_matchers = IgnoreMatchers([], [])
    if respect_gitignore or respect_dir2textignore:
        current_dir = directory
        while current_dir != current_dir.parent:
            ignore_matchers = get_ignore_matchers(current_dir)
            if respect_gitignore:
                root_matchers.gitignore.extend(ignore_matchers.gitignore)
            if respect_dir2textignore:
                root_matchers.dir2textignore.extend(ignore_matchers.dir2textignore)
            current_dir = current_dir.parent

    # Use a queue for BFS traversal
    # Each entry is (directory_path, accumulated_ignore_matchers)
    queue = [(directory, root_matchers)]

    while queue:
        current_dir, current_matchers = queue.pop(0)

        try:
            # Get additional ignore matchers for current directory
            dir_matchers = get_ignore_matchers(current_dir)
            combined_matchers = IgnoreMatchers(
                current_matchers.gitignore
                + (dir_matchers.gitignore if respect_gitignore else []),
                current_matchers.dir2textignore
                + (dir_matchers.dir2textignore if respect_dir2textignore else []),
            )

            for entry in os.scandir(current_dir):
                entry_path = Path(entry.path)
                relative_path = entry_path.relative_to(directory)

                if entry.is_dir():
                    if entry.name == ".git":
                        continue

                    # Check if directory should be ignored
                    if (
                        respect_gitignore
                        and any(
                            matcher(str(entry_path))
                            for matcher in combined_matchers.gitignore
                        )
                    ) or (
                        respect_dir2textignore
                        and any(
                            matcher(str(entry_path))
                            for matcher in combined_matchers.dir2textignore
                        )
                    ):
                        log.debug(f"Skipping ignored directory: {entry_path}")
                        continue

                    queue.append((entry_path, combined_matchers))

                else:  # Regular file
                    # Skip lock files if requested
                    if exclude_lock_files and entry.name.endswith(".lock"):
                        continue

                    # Check extension filter
                    if extension and not entry.name.endswith(extension):
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

                    # Check ignore matchers
                    if (
                        respect_gitignore
                        and any(
                            matcher(str(entry_path))
                            for matcher in combined_matchers.gitignore
                        )
                    ) or (
                        respect_dir2textignore
                        and any(
                            matcher(str(entry_path))
                            for matcher in combined_matchers.dir2textignore
                        )
                    ):
                        log.debug(f"Skipping ignored file: {entry_path}")
                        continue

                    matches.append(entry_path)

        except PermissionError:
            log.warning(f"Permission denied accessing {current_dir}")
            continue

    matches = [m.relative_to(directory) for m in sorted(matches)]
    log.debug(f"Found {len(matches)} matching files: {matches}")
    return matches
