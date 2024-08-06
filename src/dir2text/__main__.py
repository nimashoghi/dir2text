import argparse

from . import markdown, text
from ._util import create_common_parser


def main():
    parser = argparse.ArgumentParser(
        description="Convert project files to a structured string representation."
    )
    subparsers = parser.add_subparsers(dest="format", required=True)

    # Text subcommand
    parser_text = subparsers.add_parser(
        "text", parents=[create_common_parser()], help="Output in plain text format"
    )
    parser_text.set_defaults(func=text.main)

    # Markdown subcommand
    parser_md = subparsers.add_parser(
        "markdown", parents=[create_common_parser()], help="Output in Markdown format"
    )
    parser_md.set_defaults(func=markdown.main)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
