"""
Unit tests for artifact storage functionality.
Tests deduplication, file operations, and database operations.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.artifacts.storage import (
    ensure_blobstore,
    blob_path_for_sha,
    file_sha256,
    sniff_mime,
    get_artifact_blob_path,
    find_artifact_by_sha,
    create_artifact
)
from backend.artifacts.ingest import ingest_files
from backend.db.models import Artifact


class TestBlobstoreOperations:
    """Test blobstore directory and file operations."""
    
    @pytest.mark.asyncio
    async def test_ensure_blobstore_creation(self, temp_blobstore):
        """Test blobstore directory creation."""
        blob_dir = await ensure_blobstore(temp_blobstore)
        assert blob_dir.exists()
        assert blob_dir.is_dir()
    
    def test_blob_path_generation(self, temp_blobstore):
        """Test content-addressed path generation."""
        sha256 = "abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"
        expected_path = temp_blobstore / "ab" / "cd" / sha256
        actual_path = blob_path_for_sha(sha256, temp_blobstore)
        assert actual_path == expected_path
    
    def test_file_sha256_calculation(self, temp_blobstore):
        """Test SHA-256 calculation."""
        test_file = temp_blobstore / "test.txt"
        test_file.write_text("Hello, World!")
        
        sha256 = file_sha256(test_file)
        assert len(sha256) == 64
        assert sha256.isalnum()
    
    def test_mime_type_detection(self, temp_blobstore):
        """Test MIME type detection."""
        # Test PNG file
        png_file = temp_blobstore / "test.png"
        png_file.write_bytes(b"fake png data")
        assert sniff_mime(png_file) == "image/png"
        
        # Test unknown file
        unknown_file = temp_blobstore / "test.xyz"
        unknown_file.write_bytes(b"unknown data")
        assert sniff_mime(unknown_file) == "application/octet-stream"


class TestArtifactDeduplication:
    """Test artifact deduplication logic."""
    
    @pytest.mark.asyncio
    async def test_duplicate_artifact_deduplication(self, db_session, test_thread, temp_blobstore):
        """Test that identical files are deduplicated."""
        # Create test file
        test_file = temp_blobstore / "test.txt"
        test_file.write_text("Hello, World!")
        
        # Ingest first time
        artifacts1 = await ingest_files(
            session=db_session,
            thread_id=test_thread.id,
            new_host_files=[test_file],
            session_id="session1",
            run_id="run1",
            tool_call_id="call1"
        )
        
        # Ingest same file again
        artifacts2 = await ingest_files(
            session=db_session,
            thread_id=test_thread.id,
            new_host_files=[test_file],
            session_id="session2", 
            run_id="run2",
            tool_call_id="call2"
        )
        
        # Should be the same artifact (same SHA-256)
        assert len(artifacts1) == 1
        assert len(artifacts2) == 1
        assert artifacts1[0]["id"] == artifacts2[0]["id"]
        assert artifacts1[0]["sha256"] == artifacts2[0]["sha256"]
        
        # Verify only one blob file exists
        blob_path = blob_path_for_sha(artifacts1[0]["sha256"], temp_blobstore)
        assert blob_path.exists()
    
    @pytest.mark.asyncio
    async def test_different_files_different_artifacts(self, db_session, test_thread, temp_blobstore):
        """Test that different files create different artifacts."""
        # Create two different files
        file1 = temp_blobstore / "file1.txt"
        file1.write_text("Content 1")
        
        file2 = temp_blobstore / "file2.txt" 
        file2.write_text("Content 2")
        
        # Ingest both files
        artifacts1 = await ingest_files(
            session=db_session,
            thread_id=test_thread.id,
            new_host_files=[file1],
            session_id="session1",
            run_id="run1",
            tool_call_id="call1"
        )
        
        artifacts2 = await ingest_files(
            session=db_session,
            thread_id=test_thread.id,
            new_host_files=[file2],
            session_id="session2",
            run_id="run2", 
            tool_call_id="call2"
        )
        
        # Should be different artifacts
        assert len(artifacts1) == 1
        assert len(artifacts2) == 1
        assert artifacts1[0]["id"] != artifacts2[0]["id"]
        assert artifacts1[0]["sha256"] != artifacts2[0]["sha256"]


class TestArtifactQueries:
    """Test artifact query operations."""
    
    @pytest.mark.asyncio
    async def test_find_artifact_by_sha(self, db_session, test_thread, temp_blobstore):
        """Test finding artifacts by SHA-256."""
        # Create and ingest test file
        test_file = temp_blobstore / "test.txt"
        test_file.write_text("Hello, World!")
        
        artifacts = await ingest_files(
            session=db_session,
            thread_id=test_thread.id,
            new_host_files=[test_file],
            session_id="session1",
            run_id="run1",
            tool_call_id="call1"
        )
        
        assert len(artifacts) == 1
        artifact_sha = artifacts[0]["sha256"]
        
        # Find by SHA-256
        found_artifact = await find_artifact_by_sha(db_session, artifact_sha)
        assert found_artifact is not None
        assert found_artifact.id == artifacts[0]["id"]
        
        # Find non-existent SHA
        non_existent = await find_artifact_by_sha(db_session, "nonexistent" * 8)
        assert non_existent is None
