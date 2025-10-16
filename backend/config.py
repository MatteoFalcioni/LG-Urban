from __future__ import annotations

import os
from pathlib import Path


# ---------- LLM Configuration ----------
# Default LLM configuration (can be overridden per-thread via configs table)
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "gpt-4o")
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW", "30000"))  # Default 30k


# ---------- Sandbox Configuration ----------
# Docker sandbox image (build with Dockerfile.sandbox)
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "sandbox:latest")

# Session storage mode: TMPFS (RAM-backed, ephemeral) or BIND (disk-backed, persistent)
SESSION_STORAGE = os.getenv("SESSION_STORAGE", "TMPFS")

# TMPFS size limit in MB (only used when SESSION_STORAGE=TMPFS)
TMPFS_SIZE_MB = int(os.getenv("TMPFS_SIZE_MB", "1024"))

# Dataset access mode: NONE, LOCAL_RO, API, HYBRID
DATASET_ACCESS = os.getenv("DATASET_ACCESS", "NONE")

# Hybrid mode local datasets path (mounted as /heavy_data in sandbox)
HYBRID_LOCAL_PATH = os.getenv("HYBRID_LOCAL_PATH", None)
if HYBRID_LOCAL_PATH:
    HYBRID_LOCAL_PATH = Path(HYBRID_LOCAL_PATH)

# Session directory (for BIND mode and logs)
SESSIONS_ROOT = Path(os.getenv("SESSIONS_ROOT", "./sessions"))

# Blobstore directory (for artifact storage)
BLOBSTORE_DIR = Path(os.getenv("BLOBSTORE_DIR", "./blobstore"))

# Network configuration for sandbox containers
SANDBOX_NETWORK = os.getenv("SANDBOX_NETWORK", "langgraph-network")

# Maximum artifact size in MB
MAX_ARTIFACT_SIZE_MB = int(os.getenv("MAX_ARTIFACT_SIZE_MB", "50"))

# Artifact token configuration
ARTIFACTS_SECRET = os.getenv("ARTIFACTS_SECRET", "default-secret-change-in-production")
ARTIFACTS_TOKEN_TTL_SECONDS = int(os.getenv("ARTIFACTS_TOKEN_TTL_SECONDS", "86400"))  # 24 hours default 

