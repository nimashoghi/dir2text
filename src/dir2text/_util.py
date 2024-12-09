from __future__ import annotations

import argparse
import glob
from pathlib import Path
import nbformat
from nbconvert import PythonExporter
import tiktoken


def resolve_paths(paths: str | list[str]) -> list[Path]:
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
    return parser


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
