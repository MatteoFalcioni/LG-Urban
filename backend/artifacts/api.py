# backend/artifacts/api.py
from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.session import get_session

from .storage import get_artifact_by_id, get_artifact_blob_path
from .tokens import verify_token

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}")
async def download_artifact(
    artifact_id: str,
    token: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Download an artifact by ID.
    
    Requires a valid token for authentication.
    Streams the file from the content-addressed blobstore.
    """
    # 1) Verify token (artifact_id must match)
    try:
        data = verify_token(token)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    if data["artifact_id"] != artifact_id:
        raise HTTPException(status_code=403, detail="Token does not match artifact")

    # 2) Look up artifact in PostgreSQL
    try:
        artifact_uuid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact ID format")
    
    artifact = await get_artifact_by_id(session, artifact_uuid)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # 3) Resolve blob on disk
    blob_path = get_artifact_blob_path(artifact)
    if not blob_path.exists():
        raise HTTPException(status_code=410, detail="Blob missing (pruned?)")

    # 4) Stream it
    # For HTML and images, display inline. For other files, download.
    inline_mimes = ["text/html", "image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/svg+xml"]
    
    response = FileResponse(
        path=str(blob_path),
        media_type=artifact.mime or "application/octet-stream",
    )
    
    # Set Content-Disposition header
    if artifact.mime in inline_mimes:
        response.headers["Content-Disposition"] = "inline"
    else:
        response.headers["Content-Disposition"] = f'attachment; filename="{artifact.filename or artifact_id}"'
    
    return response


@router.get("/{artifact_id}/head")
async def head_artifact(
    artifact_id: str,
    token: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Get artifact metadata without downloading the file.
    
    Requires a valid token for authentication.
    Returns artifact metadata (size, mime type, SHA-256, etc.)
    """
    # 1) Verify token (artifact_id must match)
    try:
        data = verify_token(token)
    except RuntimeError as e:
        raise HTTPException(status_code=401, detail=str(e))
    if data["artifact_id"] != artifact_id:
        raise HTTPException(status_code=403, detail="Token does not match artifact")

    # 2) Look up artifact in PostgreSQL
    try:
        artifact_uuid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact ID format")
    
    artifact = await get_artifact_by_id(session, artifact_uuid)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # 3) Return metadata
    return JSONResponse({
        "id": str(artifact.id),
        "sha256": artifact.sha256,
        "mime": artifact.mime,
        "filename": artifact.filename,
        "size": artifact.size,
        "created_at": artifact.created_at.isoformat(),
        "thread_id": str(artifact.thread_id),
        "session_id": artifact.session_id,
        "run_id": artifact.run_id,
        "tool_call_id": artifact.tool_call_id,
    })
