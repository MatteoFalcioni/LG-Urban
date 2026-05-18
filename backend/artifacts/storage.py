"""
Unified artifact storage using PostgreSQL metadata + S3 for blob data.

Architecture:
- PostgreSQL: Stores artifact metadata (id, sha256, filename, size, mime, thread_id relationships)
- S3: Stores actual file bytes under content-addressed keys (output/artifacts/..)
"""

from __future__ import annotations

import os
import uuid
from typing import Optional

import boto3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Artifact

# (Blobstore helpers removed in S3-only workflow)


# ---------- Database Operations ----------


async def find_artifact_by_sha(
    session: AsyncSession, sha256: str
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

    Note: File should already be in S3. This only creates the database metadata record.
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
    session: AsyncSession, artifact_id: uuid.UUID
) -> Optional[Artifact]:
    """Retrieve an artifact by its UUID."""
    stmt = select(Artifact).where(Artifact.id == artifact_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


# ---------------- S3 helpers (for presigned URLs and key resolution) ----------------


def s3_key_for_artifact(artifact: Artifact) -> str:
    """Get S3 key for an artifact. Falls back to content-addressed path under output/artifacts."""
    if (
        artifact.meta
        and isinstance(artifact.meta, dict)
        and artifact.meta.get("s3_key")
    ):
        return artifact.meta["s3_key"]
    # Default content-addressed layout
    return f"output/artifacts/{artifact.sha256[:2]}/{artifact.sha256[2:4]}/{artifact.sha256}"


def generate_presigned_url_from_s3_key(s3_key: str, expiry_seconds: int = 86400) -> str:
    """
    Generate a presigned S3 URL directly from an S3 key (driver dictionary).
    Used for streaming artifacts during SSE (when driver returns raw s3_key).
    """
    from botocore.client import Config

    bucket = os.getenv("S3_BUCKET", "lg-urban-prod")
    region = os.getenv("AWS_REGION", "eu-central-1")  # Default region

    # Configure boto3 to use Signature Version 4
    s3 = boto3.client("s3", region_name=region, config=Config(signature_version="s3v4"))

    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": s3_key},
        ExpiresIn=expiry_seconds,
    )


def generate_artifact_download_url(
    artifact: Artifact, expiry_seconds: int = 86400
) -> str:
    """
    Generate a presigned S3 URL for downloading the artifact from database record (accepts artifact object directly).
    Used when fetching historical artifacts from the database.
    """
    s3_key = s3_key_for_artifact(artifact)
    return generate_presigned_url_from_s3_key(s3_key, expiry_seconds)
