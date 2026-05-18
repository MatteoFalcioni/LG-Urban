from __future__ import annotations

import os

# ---------- LLM Configuration ----------
# Default LLM configuration (can be overridden per-thread via configs table)
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-sonnet-4.6")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW", "200000"))  # Default 200k
