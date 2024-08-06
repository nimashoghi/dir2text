import argparse
from pathlib import Path

from ._util import create_common_parser
from .text import find_files_bfs, read_file_content

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


def main(args: argparse.Namespace | None = None):
    if args is None:
        args = create_common_parser().parse_args()

    matching_files = find_files_bfs(
        args.directory,
        args.extension,
        args.include,
        args.exclude,
        args.gitignore,
    )

    tree_lines = print_directory_tree_md(matching_files, args.directory)
    file_contents = ["# Project Structure and Contents\n"]

    for file_path in matching_files:
        relative_path = file_path.relative_to(args.directory)
        file_contents.append(f"## {relative_path}\n")

        language = EXTENSION_TO_LANGUAGE.get(file_path.suffix, "")
        file_contents.append(f"```{language}")
        file_contents.append(read_file_content(file_path))
        file_contents.append("```\n")

    # Print in reverse order
    print("\n".join(tree_lines))
    print("\n".join(file_contents))


if __name__ == "__main__":
    main()
