"""
Unified artifact storage using PostgreSQL metadata + filesystem blobstore.
Replaces SQLite-based storage from LangGraph-Sandbox.

Architecture:
- PostgreSQL: Stores artifact metadata (id, sha256, filename, size, mime, thread_id relationships)
- Filesystem Blobstore: Stores actual file bytes in content-addressed storage (blobstore/<2-char>/<2-char>/<sha256>)
- Deduplication: SHA-256 fingerprinting ensures identical files are stored once

Environment variables:
- BLOBSTORE_DIR: path to blob folder (default: ./blobstore)
- MAX_ARTIFACT_SIZE_MB: per-file size cap (default: 50 MB)
"""

from __future__ import annotations
import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.models import Artifact


# ---------- Configuration ----------

def get_blobstore_dir() -> Path:
    """Get blobstore directory from environment or use default."""
    return Path(os.getenv("BLOBSTORE_DIR", "./blobstore"))


def get_max_artifact_size() -> int:
    """Get max artifact size in bytes (default 50 MB)."""
    mb = int(os.getenv("MAX_ARTIFACT_SIZE_MB", "50"))
    return mb * 1024 * 1024


# ---------- Blobstore Path Management ----------

async def ensure_blobstore(base_dir: Optional[Path] = None) -> Path:
    """Create blobstore directory if it doesn't exist."""
    if base_dir is None:
        base_dir = get_blobstore_dir()
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def blob_path_for_sha(sha256: str, blob_dir: Optional[Path] = None) -> Path:
    """
    Generate content-addressed path for a SHA-256 hash.
    
    Example: blobstore/ab/cd/abcdef123456...
    
    This sharding (2-char prefixes) prevents filesystem slowdown 
    when many files are stored in a single directory.
    """
    if blob_dir is None:
        blob_dir = get_blobstore_dir()
    return blob_dir / sha256[:2] / sha256[2:4] / sha256


def get_artifact_blob_path(artifact: Artifact, blob_dir: Optional[Path] = None) -> Path:
    """Get the filesystem path for an artifact's blob data."""
    return blob_path_for_sha(artifact.sha256, blob_dir)


# ---------- File Hashing & Metadata ----------

def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute SHA-256 fingerprint of a file.
    
    Uses chunked reading to handle large files efficiently.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def sniff_mime(path: Path) -> str:
    """Guess MIME type from filename extension."""
    mt, _ = mimetypes.guess_type(path.name)
    return mt or "application/octet-stream"


# ---------- Blob Storage Operations ----------

def copy_to_blobstore(
    src_file: Path,
    sha256: str,
    blob_dir: Optional[Path] = None,
    chunk_size: int = 1024 * 1024
) -> Path:
    """
    Copy a file into the content-addressed blobstore.
    
    Returns the destination path. If blob already exists, skips copy.
    """
    if blob_dir is None:
        blob_dir = get_blobstore_dir()
    
    dst_path = blob_path_for_sha(sha256, blob_dir)
    
    # Create parent directories
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Skip if already exists (deduplication!)
    if dst_path.exists():
        return dst_path
    
    # Copy file in chunks
    with src_file.open("rb") as fsrc, dst_path.open("wb") as fdst:
        for chunk in iter(lambda: fsrc.read(chunk_size), b""):
            fdst.write(chunk)
    
    return dst_path


def safe_delete_file(path: Path) -> None:
    """Delete a file, ignoring errors (e.g., for cleanup)."""
    try:
        path.unlink(missing_ok=True)
    except Exception:
        # Don't crash on cleanup failures
        pass


# ---------- Database Operations ----------

async def find_artifact_by_sha(
    session: AsyncSession,
    sha256: str
) -> Optional[Artifact]:
    """
    Look up an existing artifact by SHA-256 hash.
    
    Used for deduplication - if we already have this file, return its metadata.
    """
    stmt = select(Artifact).where(Artifact.sha256 == sha256)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_artifact(
    session: AsyncSession,
    thread_id: uuid.UUID,
    sha256: str,
    filename: str,
    mime: str,
    size: int,
    session_id: Optional[str] = None,
    run_id: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    meta: Optional[dict] = None,
) -> Artifact:
    """
    Create a new artifact record in PostgreSQL.
    
    Note: This does NOT copy the file to blobstore - use copy_to_blobstore() separately.
    """
    artifact = Artifact(
        id=uuid.uuid4(),
        thread_id=thread_id,
        sha256=sha256,
        filename=filename,
        mime=mime,
        size=size,
        session_id=session_id,
        run_id=run_id,
        tool_call_id=tool_call_id,
        meta=meta,
    )
    session.add(artifact)
    await session.flush()  # Get the ID without committing transaction
    return artifact


async def get_artifact_by_id(
    session: AsyncSession,
    artifact_id: uuid.UUID
) -> Optional[Artifact]:
    """Retrieve an artifact by its UUID."""
    stmt = select(Artifact).where(Artifact.id == artifact_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()

