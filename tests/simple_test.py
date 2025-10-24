"""
Simple test to validate the core LG-Urban functionality.
This is a minimal test suite that focuses on the most important features.
"""
import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Set test environment variables before importing backend modules
import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["LANGGRAPH_CHECKPOINT_DB_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["DEFAULT_MODEL"] = "gpt-4o"
os.environ["DEFAULT_TEMPERATURE"] = "0.7"
os.environ["CONTEXT_WINDOW"] = "30000"
os.environ["BLOBSTORE_DIR"] = "./test_blobstore"
os.environ["SANDBOX_IMAGE"] = "sandbox:latest"
os.environ["TMPFS_SIZE_MB"] = "100"
os.environ["SESSION_STORAGE"] = "TMPFS"
os.environ["DATASET_ACCESS"] = "NONE"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

from backend.artifacts.storage import (
    ensure_blobstore,
    blob_path_for_sha,
    file_sha256,
    sniff_mime
)


class TestBasicFunctionality:
    """Test basic functionality without complex fixtures."""
    
    def test_blob_path_generation(self):
        """Test content-addressed path generation."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            sha256 = "abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"
            expected_path = temp_dir / "ab" / "cd" / sha256
            actual_path = blob_path_for_sha(sha256, temp_dir)
            assert actual_path == expected_path
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    def test_file_sha256_calculation(self):
        """Test SHA-256 calculation."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            test_file = temp_dir / "test.txt"
            test_file.write_text("Hello, World!")
            
            sha256 = file_sha256(test_file)
            assert len(sha256) == 64
            assert sha256.isalnum()
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    def test_mime_type_detection(self):
        """Test MIME type detection."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Test PNG file
            png_file = temp_dir / "test.png"
            png_file.write_bytes(b"fake png data")
            assert sniff_mime(png_file) == "image/png"
            
            # Test unknown file (expect application/octet-stream)
            unknown_file = temp_dir / "test.xyz"
            unknown_file.write_bytes(b"unknown data")
            # Note: .xyz files might be detected as chemical/x-xyz, so we'll be flexible
            mime_type = sniff_mime(unknown_file)
            assert mime_type in ["application/octet-stream", "chemical/x-xyz"]
        finally:
            import shutil
            shutil.rmtree(temp_dir)
    
    @pytest.mark.asyncio
    async def test_blobstore_creation(self):
        """Test blobstore directory creation."""
        temp_dir = Path(tempfile.mkdtemp())
        try:
            blob_dir = await ensure_blobstore(temp_dir)
            assert blob_dir.exists()
            assert blob_dir.is_dir()
        finally:
            import shutil
            shutil.rmtree(temp_dir)


class TestDatabaseModels:
    """Test database model imports and basic functionality."""
    
    def test_import_models(self):
        """Test that we can import database models."""
        from backend.db.models import Thread, Message, Config, Artifact
        assert Thread is not None
        assert Message is not None
        assert Config is not None
        assert Artifact is not None
    
    def test_model_creation(self):
        """Test creating model instances."""
        from backend.db.models import Thread, Message, Config, Artifact
        import uuid
        
        # Test Thread creation
        thread = Thread(user_id="test-user", title="Test Thread")
        assert thread.user_id == "test-user"
        assert thread.title == "Test Thread"
        
        # Test Message creation
        message = Message(
            thread_id=uuid.uuid4(),
            message_id="test-msg",
            role="user",
            content={"text": "Hello"}
        )
        assert message.message_id == "test-msg"
        assert message.role == "user"
        assert message.content == {"text": "Hello"}


class TestAPIEndpoints:
    """Test API endpoint imports and basic functionality."""
    
    def test_import_main_app(self):
        """Test that we can import the main FastAPI app."""
        from backend.main import app
        assert app is not None
    
    def test_health_endpoint_exists(self):
        """Test that health endpoint is defined."""
        from backend.main import app
        
        # Check if health endpoint exists (it's /healthz)
        routes = [route.path for route in app.routes]
        assert "/healthz" in routes


class TestSandboxIntegration:
    """Test sandbox-related functionality."""
    
    def test_import_session_manager(self):
        """Test that we can import SessionManager."""
        from backend.sandbox.session_manager import SessionManager
        assert SessionManager is not None
    
    def test_session_manager_creation(self):
        """Test creating SessionManager instance."""
        from backend.sandbox.session_manager import SessionManager, SessionStorage, DatasetAccess
        
        # This should not raise an exception
        manager = SessionManager(
            image="sandbox:latest",
            session_storage=SessionStorage.TMPFS,
            dataset_access=DatasetAccess.NONE,
            tmpfs_size="100m",
            address_strategy="host"
        )
        assert manager is not None


class TestToolIntegration:
    """Test tool integration functionality."""
    
    def test_import_opendata_tools(self):
        """Test that we can import OpenData API tools."""
        from backend.graph.api_tools import list_catalog_tool, preview_dataset_tool
        assert list_catalog_tool is not None
        assert preview_dataset_tool is not None


class TestArtifactSystem:
    """Test artifact system functionality."""
    
    def test_import_artifact_modules(self):
        """Test that we can import artifact modules."""
        from backend.artifacts.storage import ensure_blobstore, blob_path_for_sha
        from backend.artifacts.ingest import ingest_files
        from backend.artifacts.api import router as artifacts_router
        
        assert ensure_blobstore is not None
        assert blob_path_for_sha is not None
        assert ingest_files is not None
        assert artifacts_router is not None
    
    def test_artifact_ingest_signature(self):
        """Test that ingest_files has the expected signature."""
        from backend.artifacts.ingest import ingest_files
        import inspect
        
        sig = inspect.signature(ingest_files)
        params = list(sig.parameters.keys())
        
        # Should have these key parameters
        assert "session" in params
        assert "thread_id" in params
        assert "new_host_files" in params
        assert "session_id" in params


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])
