import os
import re
import sys
from pathlib import Path

here = Path(__file__).resolve()
repo_root = here.parents[3]

# Ensure imports like `backend.*` work regardless of where pytest is launched from
sys.path.insert(0, str(repo_root))

# Ensure CWD is repo root so relative paths in app.py (e.g. backend/modal_runtime/driver.py) resolve
try:
    os.chdir(repo_root)
except Exception:
    pass


def clean_output(raw_text: str) -> str:
    """
    Strip ANSI escape codes and normalize line endings.

    Use this in CI/CD tests to handle output differences between
    local terminals (with TTY) and GitHub Actions runners (no TTY).

    ANSI codes appear as raw \\x1b[...] sequences in non-TTY environments,
    which can break string assertions.
    """
    if not raw_text:
        return ""
    # Strip ANSI escape sequences (colors, cursor movements, etc.)
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    text = ansi_escape.sub("", raw_text)
    # Normalize line endings (Windows/Mac -> Unix)
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()
