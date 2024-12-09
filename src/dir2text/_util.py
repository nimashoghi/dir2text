from __future__ import annotations

import argparse
import fnmatch
import glob
import logging
import os
from collections.abc import Callable, Sequence
from pathlib import Path

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


def find_files_bfs(
    directory: Path,
    extension: str | None = None,
    include_patterns: Sequence[str] = [],
    exclude_patterns: Sequence[str] = [],
    respect_gitignore: bool = True,
    respect_dir2textignore: bool = True,
) -> list[Path]:
    matches: list[Path] = []
    gitignore_matchers: list[Callable[[str], bool]] = []
    dir2textignore_matchers: list[Callable[[str], bool]] = []

    # Collect all .gitignore files from the directory to the root
    if respect_gitignore:
        current_dir = directory
        while current_dir != current_dir.parent:  # Traverse up to the root
            gitignore_path = current_dir / ".gitignore"
            if gitignore_path.exists():
                gitignore_matchers.append(parse_gitignore(gitignore_path))
            current_dir = current_dir.parent

    # Collect all .dir2textignore files from the directory to the root
    if respect_dir2textignore:
        current_dir = directory
        while current_dir != current_dir.parent:  # Traverse up to the root
            dir2textignore_path = current_dir / ".dir2textignore"
            if dir2textignore_path.exists():
                dir2textignore_matchers.append(parse_gitignore(dir2textignore_path))
            current_dir = current_dir.parent

    for root, dirs, files in os.walk(directory):
        # Skip .git directories
        if ".git" in dirs:
            dirs.remove(".git")

        root_path = Path(root)

        for file in files:
            file_path = root_path / file
            relative_path = file_path.relative_to(directory)

            # Skip if matches any gitignore
            gitignore_matched = any(
                matcher(str(file_path)) for matcher in gitignore_matchers
            )
            log.debug(f"Checking {file_path} against gitignore: {gitignore_matched}")
            if gitignore_matched:
                continue

            # Skip if matches any dir2textignore
            # if any(matcher(str(file_path)) for matcher in dir2textignore_matchers):
            dir2textignore_matched = any(
                matcher(str(file_path)) for matcher in dir2textignore_matchers
            )
            log.debug(
                f"Checking {file_path} against dir2textignore: {dir2textignore_matched}"
            )
            if dir2textignore_matched:
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
