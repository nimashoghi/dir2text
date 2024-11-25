from __future__ import annotations

import argparse

from . import markdown, text, xml


def main():
    parser = argparse.ArgumentParser(
        description="Convert project files to a structured string representation."
    )
    subparsers = parser.add_subparsers(dest="format", required=True)

    # Text subcommand
    parser_text = subparsers.add_parser(
        "text", parents=[text.create_parser()], help="Output in plain text format"
    )
    parser_text.set_defaults(func=text.main)

    # Markdown subcommand
    parser_md = subparsers.add_parser(
        "markdown", parents=[markdown.create_parser()], help="Output in Markdown format"
    )
    parser_md.set_defaults(func=markdown.main)

    # XML subcommand
    parser_xml = subparsers.add_parser(
        "xml", parents=[xml.create_parser()], help="Output in XML format"
    )
    parser_xml.set_defaults(func=xml.main)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
