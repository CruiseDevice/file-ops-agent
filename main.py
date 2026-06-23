import argparse
import re
import sys

from src.config import SANDBOX_ROOT
from src.tools import editor, file_read, file_write, resolve_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Sandbox file tools")
    sub = parser.add_subparsers(dest="command", required=True)

    # read
    p_read = sub.add_parser("read", help="Read a sandbox file")
    p_read.add_argument("path")
    p_read.add_argument("--offset", type=int, default=1)
    p_read.add_argument("--limit", type=int, default=0)
    p_read.add_argument("--search", default="")

    # write
    p_write = sub.add_parser("write", help="Write to a sandbox file")
    p_write.add_argument("path")
    p_write.add_argument("--content", required=True)
    p_write.add_argument("--mode", choices=["overwrite", "append"], default="overwrite")

    # edit
    p_edit = sub.add_parser("edit", help="Edit a sandbox file")
    p_edit.add_argument("path")
    p_edit.add_argument("edit_command", choices=["str_replace", "insert_at_line"])
    p_edit.add_argument("--old-str", default="")
    p_edit.add_argument("--new-str", required=True)
    p_edit.add_argument("--line", type=int, default=0)

    args = parser.parse_args(argv)

    if args.command == "read":
        result = file_read(args.path, args.offset, args.limit, args.search)

    elif args.command == "write":
        result = file_write(args.path, args.content, args.mode)

    elif args.command == "edit":
        result = editor(
            args.path,
            args.edit_command,
            args.old_str,
            args.new_str,
            args.line,
        )

    print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
