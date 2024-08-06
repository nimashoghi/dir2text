import argparse
import fnmatch
from collections import defaultdict, deque
from collections.abc import Callable
from pathlib import Path

from gitignore_parser import parse_gitignore

from ._util import create_common_parser


def print_directory_tree(files: list[Path], base_dir: Path):
    def nested_defaultdict():
        return defaultdict(nested_defaultdict)

    def add_to_tree(tree, parts):
        for part in parts:
            tree = tree[part]
        return tree

    def format_tree(tree, prefix=""):
        result = []
        entries = sorted(
            tree.items(), key=lambda x: (not isinstance(x[1], defaultdict), x[0])
        )
        for i, (name, subtree) in enumerate(entries):
            is_last = i == len(entries) - 1
            result.append(f"{prefix}{'└── ' if is_last else '├── '}{name}")
            if isinstance(subtree, defaultdict):
                extension = "    " if is_last else "│   "
                result.extend(format_tree(subtree, prefix + extension))
        return result

    file_tree = nested_defaultdict()
    for file in files:
        relative = file.relative_to(base_dir)
        add_to_tree(file_tree, relative.parts)

    tree_lines = ["Directory structure:", base_dir.name]
    tree_lines.extend(format_tree(file_tree))
    return tree_lines


def find_parent_gitignores(directory: Path) -> list[Path]:
    gitignores = []
    current = Path(directory).absolute()
    while current != current.parent:
        gitignore = current / ".gitignore"
        if gitignore.is_file():
            gitignores.append(gitignore)
        current = current.parent
    return list(reversed(gitignores))  # Reverse to respect override order


def should_ignore(path: str, gitignore_matchers: list[Callable[..., bool]]) -> bool:
    # Ignore some common files
    if path in (
        ".gitignore",
        ".git",
        ".hg",
        ".svn",
        ".DS_Store",
        "package-lock.json",
        "yarn.lock",
        "poetry.lock",
        "Pipfile.lock",
        "pixi.lock",
    ):
        return True

    return any(matcher(path) for matcher in gitignore_matchers)


def find_files_bfs(
    directory: Path,
    extension: str | None,
    include_patterns: list[str],
    exclude_patterns: list[str],
    respect_gitignore: bool,
) -> list[Path]:
    result = []
    queue = deque([(directory, [])])

    if respect_gitignore:
        parent_gitignores = find_parent_gitignores(directory)
        parent_matchers = [
            parse_gitignore(gitignore) for gitignore in parent_gitignores
        ]
    else:
        parent_matchers = []

    while queue:
        current_dir, current_matchers = queue.popleft()

        # Skip the .git directory
        if current_dir.name == ".git":
            continue

        # Check for a .gitignore in the current directory
        if respect_gitignore:
            current_gitignore = current_dir / ".gitignore"
            if current_gitignore.is_file():
                current_matchers = (
                    parent_matchers
                    + current_matchers
                    + [parse_gitignore(current_gitignore)]
                )
            else:
                current_matchers = parent_matchers + current_matchers

        for item in current_dir.iterdir():
            # Check if the item should be ignored based on accumulated gitignore rules
            if respect_gitignore and should_ignore(str(item), current_matchers):
                continue

            if item.is_file():
                if extension and item.suffix != extension:
                    continue

                # Check include patterns
                if include_patterns and not any(
                    fnmatch.fnmatch(item.name, pattern) for pattern in include_patterns
                ):
                    continue

                # Check exclude patterns
                if any(
                    fnmatch.fnmatch(item.name, pattern) for pattern in exclude_patterns
                ):
                    continue

                result.append(item)
            elif item.is_dir():
                queue.append((item, current_matchers))

    return sorted(result)


def read_file_content(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


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

    tree_lines = print_directory_tree(matching_files, args.directory)
    file_contents = []

    for file_path in matching_files:
        relative_path = file_path.relative_to(args.directory)
        file_contents.append(f"# BEGIN {relative_path}")
        file_contents.append(read_file_content(file_path))
        file_contents.append(f"# END {relative_path}\n")

    print("\n".join(tree_lines))
    print("\n".join(file_contents))


if __name__ == "__main__":
    main()
