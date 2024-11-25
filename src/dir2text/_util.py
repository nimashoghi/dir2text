from __future__ import annotations

import argparse
import glob
from pathlib import Path


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
    return parser
