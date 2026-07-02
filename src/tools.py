import os
import re
from pathlib import Path

from src.config import SANDBOX_ROOT


def resolve_path(path: str) -> Path:
    """
    Resolve `path` to a real absolute path inside ./sandbox.
    Raises ValueError if the resolved path escapes the sandbox.
    """
    if not path or not path.strip():
        raise ValueError("Path cannot be empty")

    # Expand ~ and environment variables (e.g. $HOME) before resolving.
    expanded = os.path.expanduser(os.path.expandvars(path))
    p = Path(expanded)

    # Absolute paths are only allowed if they already live under the sandbox.
    if p.is_absolute():
        resolved = p.resolve()
    else:
        resolved = (SANDBOX_ROOT / path).resolve()

    # relative_to() succeeds only when `resolved` is inside SANDBOX_ROOT.
    try:
        resolved.relative_to(SANDBOX_ROOT)
    except ValueError as exc:
        raise ValueError(
            f"Path {path!r} resolves outside the sandbox ({SANDBOX_ROOT})"
        ) from exc

    return resolved


# --------------------------------------------------------------------------- #
# File read
# --------------------------------------------------------------------------- #
def file_read(path: str, offset: int = 1, limit: int = 0, search: str = "") -> str:
    """
    Read from `path` inside the sandbox.
    - offset: 1-indexed starting line.
    - limit: 0 means full file; otherwise return that many lines.
    - search: if non-empty, return only lines matching this regex.

    Order of operations: the file is first sliced by offset/limit, then
    search filters only the selected range. The search regex is not applied
    to the whole file.
    """
    try:
        target = resolve_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if not target.exists():
        return f"Error: file not found: {path}"
    if not target.is_file():
        return f"Error: not a file: {path}"

    text = target.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    # Normalize pagination parameters
    offset = max(1, offset)
    start = offset - 1
    if start >= len(lines):
        return f"Error: offset {offset} is beyond file length ({len(lines)} lines)"
    end = len(lines) if limit <= 0 else start + limit

    # Slice first, then filter by regex
    selected = lines[start:end]

    if search:
        try:
            pattern = re.compile(search)
        except re.error as exc:
            return f"Error: invalid regex {search!r}: {exc}"
        selected = [line for line in selected if pattern.search(line)]

    return "\n".join(selected)


# --------------------------------------------------------------------------- #
# File write
# --------------------------------------------------------------------------- #
def file_write(path: str, content: str, mode: str = "overwrite") -> str:
    """
    Write `content` to `path` inside the sandbox.
    - mode: "overwrite" or "append".
    - Creates parent directories if needed.
    """
    try:
        target = resolve_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if target.exists() and target.is_dir():
        return f"Error: {path} is a directory"

    if mode not in ("overwrite", "append"):
        return f"Error: invalid mode {mode!r}; use 'overwrite' or 'append'"

    # Ensure parent directories exist inside the sandbox.
    target.parent.mkdir(parents=True, exist_ok=True)

    # When appending, guarantee a newline boundary if the file exists and lacks one.
    if mode == "append" and target.exists() and target.stat().st_size > 0:
        with open(target, "rb") as f:
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                content = "\n" + content

    file_mode = "a" if mode == "append" else "w"
    with open(target, file_mode, encoding="utf-8") as f:
        f.write(content)

    return f"Successfully {'appended to' if mode == 'append' else 'wrote'} {target}"


# --------------------------------------------------------------------------- #
# Editor
# --------------------------------------------------------------------------- #
def editor(
    path: str,
    command: str,
    old_str: str = "",
    new_str: str = "",
    line: int = 0,
) -> str:
    """
    Edit a file inside the sandbox.
    - command: "str_replace" or "insert_at_line".
    - str_replace: replace first occurrence of old_str with new_str.
    - insert_at_line: insert new_str after the given 1-indexed line.
      If line > file length, append to end.
    """
    try:
        target = resolve_path(path)
    except ValueError as exc:
        return f"Error: {exc}"

    if not target.exists():
        return f"Error: file not found: {path}"
    if not target.is_file():
        return f"Error: not a file: {path}"

    text = target.read_text(encoding="utf-8", errors="replace")

    if command == "str_replace":
        if not old_str:
            return "Error: old_str cannot be empty for str_replace"
        if old_str not in text:
            return f"Error: old_str not found in {path}"

        # First occurrence only
        new_text = text.replace(old_str, new_str, 1)
        target.write_text(new_text, encoding="utf-8")
        return f"Successfully replaced text in {target}"

    elif command == "insert_at_line":
        lines = text.splitlines()
        trailing_newline = text.endswith("\n")

        if line <= 0 or line >= len(lines):
            lines.append(new_str)
        else:
            lines.insert(line, new_str)

        new_text = "\n".join(lines)
        if trailing_newline:
            new_text += "\n"

        target.write_text(new_text, encoding="utf-8")
        if line <= 0:
            return f"Successfully inserted text at the end of {target}"
        return f"Successfully inserted text into {target} after line {line}"

    else:
        return f"Error: unknown editor command {command!r}"

