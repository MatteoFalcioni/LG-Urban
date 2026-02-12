# backend/modal_runtime/functions.py
"""
DEPRECATED: This module contains Modal functions that are no longer used in production.

## Why These Functions Are Deprecated

These functions (`list_loaded_datasets`, `write_dataset_bytes`, `export_dataset`) were originally
designed to interact with Modal volumes from outside the sandbox. However, they suffer from a
critical issue: **Modal volume sync delays**.

### The Problem

When a file is written to a Modal volume by one function (e.g., `write_dataset_bytes.remote()`),
it takes time for that file to sync and become visible to other functions or the running sandbox.
This causes:
- Flaky behavior: files sometimes appear, sometimes don't
- Race conditions: second file writes may not be visible
- Unreliable tests and production failures

### The Solution

We now use `executor.execute()` to run Python code directly inside the sandbox. This approach:
- Eliminates volume sync issues (files are written and read in the same container)
- Provides immediate file availability
- Is more reliable and consistent

### Migration

All tools in `backend/graph/tools/sandbox_tools.py` now use `executor.execute()` instead:
- `load_dataset_tool`: writes datasets directly in sandbox using `executor.execute()`
- `list_loaded_datasets_tool`: lists datasets directly from sandbox using `executor.execute()`
- `export_dataset_tool`: already used `executor.execute()` (was the pattern to follow)

### Legacy Support

These functions are kept for:
- Backward compatibility (if any external code still uses them)
- Reference/documentation purposes
- Potential future use cases where volume sync is acceptable

They should NOT be used in new code. Use `executor.execute()` instead.
"""

import hashlib
import mimetypes
from pathlib import Path
import os
from typing import List, Dict, Any

import modal

# Import the Modal app from app.py
# note: since we import like this, we need to deploy with: modal deploy -m backend.modal_runtime.functions
from .app import app, image
from .session import volume_name

WORKSPACE_VOLUME = modal.Volume.from_name(volume_name(), create_if_missing=True)


def _walk_files(base: Path, exts: set) -> List[Path]:
    files = []
    if base.exists():
        for p in base.rglob("*"):
            if p.is_file() and (not exts or p.suffix.lower() in exts):
                files.append(p)
    return files


def _session_base(session_id: str) -> Path:
    """Resolve per-session base dir; session_id must be provided by caller."""
    return Path("/workspace") / "sessions" / session_id


# --------------------- (!) DEPRECATED (!) ---------------------
# This function is deprecated. Use executor.execute() in sandbox_tools.py instead.
# See module docstring for full explanation.
@app.function(
    image=image,
    volumes={"/workspace": WORKSPACE_VOLUME},
    timeout=60,
)
def list_loaded_datasets(
    session_id: str, subdir: str = "datasets"
) -> List[Dict[str, Any]]:
    """
    List datasets in the workspace. Return structured metadata.

    DEPRECATED: Use executor.execute() to list datasets directly in the sandbox instead.
    This function suffers from Modal volume sync delays.
    """
    base = _session_base(session_id) / subdir

    exts = {".csv", ".parquet", ".xlsx", ".xls"}
    out: List[Dict[str, Any]] = []
    for p in _walk_files(base, exts):
        stat = p.stat()
        rel = str(p.relative_to(base))
        out.append(
            {
                "path": rel,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 3),
                "mtime": stat.st_mtime,
                "mime": mimetypes.guess_type(p.name)[0] or "application/octet-stream",
            }
        )
    return out


# --------------------- (!) DEPRECATED (!) ---------------------
# This function is deprecated. Use executor.execute() in sandbox_tools.py instead.
# See module docstring for full explanation.
# Accept dataset bytes from backend and persist into the sandbox, returning summary
@app.function(
    image=image,
    volumes={"/workspace": WORKSPACE_VOLUME},
    timeout=180,
)
def write_dataset_bytes(
    dataset_id: str,
    data_b64: str,
    session_id: str,
    ext: str = "parquet",
    subdir: str = "datasets",
) -> Dict[str, Any]:
    """
    Write dataset bytes to the workspace volume.

    DEPRECATED: Use executor.execute() to write datasets directly in the sandbox instead.
    This function suffers from Modal volume sync delays, causing files to not be immediately
    visible to the running sandbox.
    """
    import base64

    data = base64.b64decode(data_b64)
    base_dir = _session_base(session_id)
    datasets_dir = base_dir / subdir
    datasets_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{dataset_id}.{ext.lstrip('.')}"
    path = datasets_dir / filename
    path.write_bytes(data)

    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    size = path.stat().st_size

    summary: Dict[str, Any] = {
        "dataset_id": dataset_id,
        "path": str(path),
        "rel_path": str(path.relative_to(base_dir)),
        "mime": mime,
        "size_bytes": size,
        "size_mb": round(size / (1024 * 1024), 3),
        "ext": ext.lower(),
    }

    return summary


# --------------------- (!) DEPRECATED (!) ---------------------
# This function is deprecated. Use executor.execute() in sandbox_tools.py instead.
# See module docstring for full explanation.
@app.function(
    image=image,
    volumes={"/workspace": WORKSPACE_VOLUME},
    timeout=180,
    secrets=[modal.Secret.from_name("aws-credentials-IAM")],  # store AWS creds in Modal
)
def export_dataset(dataset_path: str, bucket: str, session_id: str) -> Dict[str, Any]:
    """
    Upload a file from the Modal workspace to S3 and return metadata.

    DEPRECATED: Use executor.execute() to export datasets directly from the sandbox instead.
    This function is useless when exporting from a running sandbox because Modal volumes
    do not sync to outside functions unless we terminate the sandbox (which defeats the purpose).
    The export_dataset_tool already uses executor.execute() and works correctly.
    """
    import boto3
    import time

    base = _session_base(session_id)
    full = base / dataset_path

    # Retry logic to handle volume sync delays
    # Files created in sandbox take time to sync to volume before being visible to other functions
    max_retries = 20  # up to ~10s to allow Volume sync
    for attempt in range(max_retries):
        if full.exists():
            break
        if attempt < max_retries - 1:
            time.sleep(0.5)
    else:
        return {
            "error": f"File not found after {max_retries * 0.5}s (volume sync timeout): {dataset_path}"
        }

    try:
        data = full.read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        mime = mimetypes.guess_type(full.name)[0] or "application/octet-stream"
        size = len(data)

        # Datasets exported under a separate prefix
        s3_key = f"output/datasets/{sha256[:2]}/{sha256[2:4]}/{sha256}"

        from botocore.client import Config

        region = os.getenv("AWS_REGION", "eu-central-1")
        s3_client = boto3.client(
            "s3", region_name=region, config=Config(signature_version="s3v4")
        )
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=data,
            ContentType=mime,
        )

        return {
            "name": full.name,
            "path": str(full),
            "sha256": sha256,
            "mime": mime,
            "size": size,
            "s3_key": s3_key,
            "s3_url": f"s3://{bucket}/{s3_key}",
        }
    except Exception as e:
        return {"error": f"S3 upload failed: {e}"}
