# backend/artifacts/ingest.py
"""
Ingest new artifact files from a session's staging folder (/session/artifacts inside the container).

Host-side: we receive HOST paths of new files, move their bytes into a content-addressed blobstore,
insert metadata in PostgreSQL, delete the originals from the session folder, and return descriptors.

Steps:
- We compute a SHA-256 fingerprint of each file (its "digital fingerprint").
- We save the file once under blobstore/<2-char>/<2-char>/<sha256>.
- We record a row in 'artifacts' (PostgreSQL) with deduplication via SHA-256.
- We remove the original file from the session folder.
- We return a small "descriptor" for each artifact (id, name, mime, size, sha, created_at).

Env knobs (optional):
- BLOBSTORE_DIR: blob folder (default: ./blobstore)
- MAX_ARTIFACT_SIZE_MB: per-file size cap (default: 50 MB)
"""

from __future__ import annotations
import uuid
from pathlib import Path
from typing import Iterable, List, Dict, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from .storage import (
    file_sha256,
    sniff_mime,
    copy_to_blobstore,
    safe_delete_file,
    find_artifact_by_sha,
    create_artifact,
    get_max_artifact_size,
)
from .tokens import create_download_url


# ---------- small helpers ----------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------- core ingest ----------

async def ingest_files(
    session: AsyncSession,
    thread_id: uuid.UUID,
    new_host_files: Iterable[Path],
    *,
    session_id: str,
    run_id: Optional[str] = None,
    tool_call_id: Optional[str] = None,
) -> List[Dict]:
    """
    Ingest files from sandbox session into artifact storage.
    
    Args:
      session: SQLAlchemy async session for database operations
      thread_id: UUID of the chat thread (for artifact ownership)
      new_host_files: list of new files detected under the session's staging folder (HOST paths)
      session_id: sandbox session identifier
      run_id: LangGraph run identifier
      tool_call_id: tool invocation identifier

    Returns:
      List of artifact descriptors:
      {
        "id": str (UUID),
        "name": str,
        "mime": str,
        "size": int,
        "sha256": str,
        "created_at": str (ISO datetime),
        "url": str (optional, if token generation succeeds)
      }
    """
    descriptors: List[Dict] = []
    max_bytes = get_max_artifact_size()

    # Normalize to Path
    new_paths = [Path(p) for p in new_host_files if p and Path(p).is_file()]

    for src in new_paths:
        size = src.stat().st_size
        
        # Check size limit
        if size > max_bytes:
            # Skip too-big files gracefully
            descriptors.append({
                "id": None,
                "name": src.name,
                "mime": sniff_mime(src),
                "size": size,
                "sha256": None,
                "created_at": _now_iso(),
                "error": f"File too large (> {max_bytes} bytes)."
            })
            continue

        # Compute fingerprint and metadata
        sha = file_sha256(src)
        mime = sniff_mime(src)
        created_at = _now_iso()

        # Upsert: check if we already have this file (deduplication)
        artifact = await _upsert_artifact(
            session=session,
            thread_id=thread_id,
            sha256=sha,
            size=size,
            mime=mime,
            filename=src.name,
            session_id=session_id,
            run_id=run_id,
            tool_call_id=tool_call_id,
            src_file=src,
        )

        # Build descriptor
        desc = {
            "id": str(artifact.id),
            "name": artifact.filename,
            "mime": artifact.mime,
            "size": artifact.size,
            "sha256": artifact.sha256,
            "created_at": artifact.created_at.isoformat(),
        }
        
        # Optional URL injection (if env is configured)
        try:
            desc["url"] = create_download_url(str(artifact.id))
        except Exception:
            # No PUBLIC_BASE_URL or SECRET set; descriptor remains without url
            pass

        # Remove the original from the session folder (keep containers lean)
        safe_delete_file(src)

        descriptors.append(desc)

    # Commit all artifacts in one transaction
    await session.commit()
    
    return descriptors


async def _upsert_artifact(
    session: AsyncSession,
    thread_id: uuid.UUID,
    sha256: str,
    size: int,
    mime: str,
    filename: str,
    session_id: str,
    run_id: Optional[str],
    tool_call_id: Optional[str],
    src_file: Path,
) -> "Artifact":
    """
    Upsert artifact with deduplication.
    
    If sha256 already exists for this thread, we could either:
    1. Return the existing artifact (full deduplication)
    2. Create a new artifact record pointing to same blob (track multiple uploads)
    
    For now: Create a new artifact record even if blob exists (allows tracking 
    multiple references to the same file in different contexts).
    """
    from backend.db.models import Artifact
    
    # Copy file to blobstore (idempotent - skips if exists)
    copy_to_blobstore(src_file, sha256)
    
    # Always create a new artifact record (allows multiple references)
    # In the future, you could add logic here to reuse existing artifacts
    artifact = await create_artifact(
        session=session,
        thread_id=thread_id,
        sha256=sha256,
        filename=filename,
        mime=mime,
        size=size,
        session_id=session_id,
        run_id=run_id,
        tool_call_id=tool_call_id,
    )
    
    return artifact
