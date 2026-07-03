import re
from pathlib import Path

# --------------------------------------------------------------------------- #
# Sandbox root
# --------------------------------------------------------------------------- #
SANDBOX_ROOT = (Path(__file__).parent.parent / "sandbox").resolve()

# --------------------------------------------------------------------------- #
# Safety limits
# --------------------------------------------------------------------------- #
# Maximum file size the agent will read or write, in bytes.
MAX_FILE_SIZE = 1024 * 1024  # 1 MB

# --------------------------------------------------------------------------- #
# Forbidden path patterns (defense in depth).
# Each pattern is matched against the normalized path string after ~/$VAR
# expansion. They block traversal attempts and sensitive system paths.
# --------------------------------------------------------------------------- #
FORBIDDEN_PATTERNS = [
    re.compile(r"\.\./"),           # parent-directory traversal fragment
    re.compile(r"/\.\./"),          # absolute traversal fragment
    re.compile(r"^\.\.$"),          # literal ".." as the whole path
    re.compile(r"^/etc(?:/|$)"),    # /etc and anything under it
    re.compile(r"^/usr(?:/|$)"),   # /usr
    re.compile(r"^/bin(?:/|$)"),   # /bin
    re.compile(r"^/sbin(?:/|$)"),  # /sbin
    re.compile(r"^/var(?:/|$)"),   # /var
    re.compile(r"^/opt(?:/|$)"),   # /opt
    re.compile(r"^/root(?:/|$)"),  # /root
    re.compile(r"\.ssh(?:/|$)"),   # .ssh anywhere
    re.compile(r"\.bashrc(?:/|$)?"), # .bashrc
    re.compile(r"\.env(?:/|$)?"),  # .env files
]