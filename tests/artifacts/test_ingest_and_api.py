"""
Integration tests: real RDS (Postgres) + S3 presign redirect via backend API.

Requirements:
- DATABASE_URL pointing to localhost (tunnel will auto-start if needed!)
- S3_BUCKET, AWS_REGION and AWS credentials set in env

SSH Tunnel:
The conftest.py automatically starts the SSH tunnel to RDS if:
1. DATABASE_URL uses localhost
2. Port 5432 is not already open

This means you can just run:
    export DATABASE_URL='postgresql+asyncpg://postgres:PASSWORD@localhost:5432/lgurban'
    pytest new_tests/artifacts/

The tunnel will start automatically and stay running for subsequent test runs!
"""

import os
import uuid
import hashlib
import pytest
import pytest_asyncio
import boto3
from botocore.client import Config
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.db.session import ASYNC_SESSION_MAKER, ENGINE
from backend.db.models import Thread
from backend.artifacts.ingest import ingest_artifact_metadata


@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_engine():
    """Cleanup SQLAlchemy engine before and after each test to avoid event loop issues."""
    # Dispose any existing connections before test
    await ENGINE.dispose()
    yield
    # Dispose connections after test
    await ENGINE.dispose()


def _have_real_rds_and_s3() -> bool:
    if (
        os.getenv("DATABASE_URL")
        and os.getenv("S3_BUCKET")
        and os.getenv("AWS_ACCESS_KEY_ID")
        and os.getenv("AWS_SECRET_ACCESS_KEY")
    ):
        print("RDS/S3 env configured")
        print("=" * 100)
        print(os.getenv(f"Database URL: {os.getenv('DATABASE_URL')}"))
        print(os.getenv(f"S3 Bucket: {os.getenv('S3_BUCKET')}"))
        print(os.getenv(f"AWS Access Key ID: {os.getenv('AWS_ACCESS_KEY_ID')}"))
        print(os.getenv(f"AWS Secret Access Key: {os.getenv('AWS_SECRET_ACCESS_KEY')}"))
        print("=" * 100)
        return True
    return False


@pytest.mark.asyncio
@pytest.mark.skipif(not _have_real_rds_and_s3(), reason="RDS/S3 env not configured")
async def test_ingest_artifact_and_head_metadata():
    async with ASYNC_SESSION_MAKER() as session:
        # Create a thread first (required for foreign key)
        thread_id = uuid.uuid4()
        thread = Thread(id=thread_id, user_id="test-user")
        session.add(thread)
        await session.commit()

        # Build a fake sha + content-addressed S3 key
        sha256 = ("cafebabe" * 8)[:64]
        s3_key = f"output/artifacts/{sha256[:2]}/{sha256[2:4]}/{sha256}"

        desc = await ingest_artifact_metadata(
            session=session,
            thread_id=thread_id,
            s3_key=s3_key,
            sha256=sha256,
            filename="it_plot.png",
            mime="image/png",
            size=1234,
            session_id="it-session",
            tool_call_id="it-tool",
        )
        art_id = desc["id"]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get(f"/api/artifacts/{art_id}/head")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == art_id
        assert data["sha256"] == sha256
        assert data["filename"] == "it_plot.png"
        assert data["mime"] == "image/png"
        assert data["size"] == 1234


@pytest.mark.asyncio
@pytest.mark.skipif(not _have_real_rds_and_s3(), reason="RDS/S3 env not configured")
async def test_download_redirects_to_s3_presigned_url():
    """Test that download endpoint generates a redirect with a presigned URL."""
    async with ASYNC_SESSION_MAKER() as session:
        # Create a thread first (required for foreign key)
        thread_id = uuid.uuid4()
        thread = Thread(id=thread_id, user_id="test-user")
        session.add(thread)
        await session.commit()

        sha256 = ("deadbeef" * 8)[:64]
        s3_key = f"output/artifacts/{sha256[:2]}/{sha256[2:4]}/{sha256}"

        desc = await ingest_artifact_metadata(
            session=session,
            thread_id=thread_id,
            s3_key=s3_key,
            sha256=sha256,
            filename="asset.html",
            mime="text/html",
            size=999,
            session_id="it-session",
            tool_call_id=None,
        )
        art_id = desc["id"]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        r = await client.get(f"/api/artifacts/{art_id}", follow_redirects=False)
        assert r.status_code in (302, 307)
        loc = r.headers.get("location") or r.headers.get("Location")
        assert loc and loc.startswith("https://")
        # Optional check: ensure bucket name appears
        bucket = os.getenv("S3_BUCKET", "")
        if bucket:
            assert bucket in loc


@pytest.mark.asyncio
@pytest.mark.skipif(not _have_real_rds_and_s3(), reason="RDS/S3 env not configured")
async def test_end_to_end_upload_and_download_from_s3():
    """
    End-to-end test: Upload a real file to S3, create artifact metadata,
    then download it via the API to verify presigned URL actually works.

    This test catches AWS signature version issues that the redirect-only test misses.
    """
    # Create test content
    test_content = b"Test artifact content for signature verification"
    sha256 = hashlib.sha256(test_content).hexdigest()
    s3_key = f"output/artifacts/{sha256[:2]}/{sha256[2:4]}/{sha256}"

    # Upload to S3 with proper signature version
    bucket = os.getenv("S3_BUCKET")
    region = os.getenv("AWS_REGION", "eu-central-1")
    s3_client = boto3.client(
        "s3", region_name=region, config=Config(signature_version="s3v4")
    )

    s3_client.put_object(
        Bucket=bucket, Key=s3_key, Body=test_content, ContentType="text/plain"
    )

    try:
        # Create artifact metadata in database
        async with ASYNC_SESSION_MAKER() as session:
            thread_id = uuid.uuid4()
            thread = Thread(id=thread_id, user_id="test-user")
            session.add(thread)
            await session.commit()

            desc = await ingest_artifact_metadata(
                session=session,
                thread_id=thread_id,
                s3_key=s3_key,
                sha256=sha256,
                filename="test_file.txt",
                mime="text/plain",
                size=len(test_content),
                session_id="e2e-test-session",
                tool_call_id="e2e-test-tool",
            )
            art_id = desc["id"]

        # Download via API (follow redirects to actually fetch from S3)
        async with AsyncClient(
            app=app, base_url="http://test", follow_redirects=True
        ) as client:
            r = await client.get(f"/api/artifacts/{art_id}")
            assert r.status_code == 200, f"Download failed with status {r.status_code}"
            assert (
                r.content == test_content
            ), "Downloaded content doesn't match uploaded content"

        print(
            f"✅ Successfully uploaded and downloaded artifact with SHA256: {sha256[:16]}..."
        )

    finally:
        # Cleanup: delete test object from S3
        try:
            s3_client.delete_object(Bucket=bucket, Key=s3_key)
        except Exception as e:
            print(f"Warning: Failed to cleanup S3 object: {e}")
