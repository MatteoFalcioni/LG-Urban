"""
Integration tests for sandbox code execution.
Tests session persistence, artifact creation, and tool integration.
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.sandbox.session_manager import SessionManager, SessionStorage, DatasetAccess
from backend.artifacts.ingest import ingest_files


class TestSandboxExecution:
    """Test sandbox code execution functionality."""
    
    @pytest.fixture
    def session_manager(self):
        """Create a test session manager."""
        return SessionManager(
            image="sandbox:latest",
            session_storage=SessionStorage.TMPFS,
            dataset_access=DatasetAccess.NONE,
            tmpfs_size="100m",
            address_strategy="host"
        )
    
    @pytest.mark.asyncio
    async def test_simple_code_execution(self, session_manager, db_session, test_thread):
        """Test basic code execution."""
        # Start session
        session_key = session_manager.start("test-session")
        
        # Execute simple code
        result = await session_manager.exec(
            session_key=session_key,
            code="print('Hello, World!')",
            timeout=30,
            db_session=db_session,
            thread_id=test_thread.id,
            tool_call_id="test-call"
        )
        
        # Verify execution
        assert result["ok"] is True
        assert "Hello, World!" in result["stdout"]
        assert result["error"] == ""
    
    @pytest.mark.asyncio
    async def test_variable_persistence(self, session_manager, db_session, test_thread):
        """Test that variables persist between executions."""
        session_key = session_manager.start("test-session")
        
        # First execution - set variable
        result1 = await session_manager.exec(
            session_key=session_key,
            code="x = 42\nprint(f'x = {x}')",
            timeout=30,
            db_session=db_session,
            thread_id=test_thread.id,
            tool_call_id="call1"
        )
        
        assert result1["ok"] is True
        assert "x = 42" in result1["stdout"]
        
        # Second execution - use variable
        result2 = await session_manager.exec(
            session_key=session_key,
            code="print(f'x is still {x}')",
            timeout=30,
            db_session=db_session,
            thread_id=test_thread.id,
            tool_call_id="call2"
        )
        
        assert result2["ok"] is True
        assert "x is still 42" in result2["stdout"]
    
    @pytest.mark.asyncio
    async def test_artifact_creation(self, session_manager, db_session, test_thread, temp_blobstore):
        """Test artifact creation and ingestion."""
        session_key = session_manager.start("test-session")
        
        # Create artifact directory
        container = session_manager.container_for(session_key)
        container.exec_run(["mkdir", "-p", "/session/artifacts"], user="root")
        container.exec_run(["chmod", "777", "/session/artifacts"], user="root")
        
        # Execute code that creates a file
        result = await session_manager.exec(
            session_key=session_key,
            code="""
import os
os.makedirs('/session/artifacts', exist_ok=True)
with open('/session/artifacts/test.txt', 'w') as f:
    f.write('Hello from sandbox!')
print('File created')
""",
            timeout=30,
            db_session=db_session,
            thread_id=test_thread.id,
            tool_call_id="test-call"
        )
        
        # Verify execution
        assert result["ok"] is True
        assert "File created" in result["stdout"]
        
        # Check if artifacts were ingested
        artifacts = result.get("artifacts", [])
        assert len(artifacts) == 1
        assert artifacts[0]["name"] == "test.txt"
        assert artifacts[0]["mime"] == "text/plain"
    
    @pytest.mark.asyncio
    async def test_error_handling(self, session_manager, db_session, test_thread):
        """Test error handling in code execution."""
        session_key = session_manager.start("test-session")
        
        # Execute code with error
        result = await session_manager.exec(
            session_key=session_key,
            code="print(undefined_variable)",
            timeout=30,
            db_session=db_session,
            thread_id=test_thread.id,
            tool_call_id="test-call"
        )
        
        # Verify error handling
        assert result["ok"] is False
        assert "NameError" in result["error"] or "undefined_variable" in result["error"]
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, session_manager, db_session, test_thread):
        """Test timeout handling."""
        session_key = session_manager.start("test-session")
        
        # Execute code that sleeps longer than timeout
        result = await session_manager.exec(
            session_key=session_key,
            code="import time; time.sleep(10)",
            timeout=2,  # 2 second timeout
            db_session=db_session,
            thread_id=test_thread.id,
            tool_call_id="test-call"
        )
        
        # Should timeout
        assert result["ok"] is False
        assert "timeout" in result["error"].lower() or "timed out" in result["error"].lower()


class TestSessionManagement:
    """Test session management functionality."""
    
    @pytest.mark.asyncio
    async def test_session_reuse(self):
        """Test that sessions can be reused."""
        session_manager = SessionManager(
            image="sandbox:latest",
            session_storage=SessionStorage.TMPFS,
            dataset_access=DatasetAccess.NONE,
            tmpfs_size="100m",
            address_strategy="host"
        )
        
        # Start session
        session_key = session_manager.start("reuse-test")
        
        # Verify session exists
        assert session_key in session_manager.sessions
        
        # Start same session again (should reuse)
        same_key = session_manager.start("reuse-test")
        assert same_key == session_key
        
        # Cleanup
        session_manager.stop(session_key)
    
    @pytest.mark.asyncio
    async def test_session_cleanup(self):
        """Test session cleanup."""
        session_manager = SessionManager(
            image="sandbox:latest",
            session_storage=SessionStorage.TMPFS,
            dataset_access=DatasetAccess.NONE,
            tmpfs_size="100m",
            address_strategy="host"
        )
        
        # Start session
        session_key = session_manager.start("cleanup-test")
        
        # Stop session
        session_manager.stop(session_key)
        
        # Verify session is removed
        assert session_key not in session_manager.sessions
