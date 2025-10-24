"""
Real integration tests for LG-Urban that test actual code execution.
These tests require Docker and the sandbox image to be built.

Run with: conda run -n langgraph-py3.11 pytest tests/test_integration_real.py -v
"""
import pytest
import pytest_asyncio
import os
import asyncio
from pathlib import Path
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["LANGGRAPH_CHECKPOINT_DB_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "test-key")
os.environ["DEFAULT_MODEL"] = "gpt-4o"
os.environ["DEFAULT_TEMPERATURE"] = "0.7"
os.environ["CONTEXT_WINDOW"] = "30000"
os.environ["BLOBSTORE_DIR"] = "./test_blobstore"
os.environ["SANDBOX_IMAGE"] = "sandbox:latest"
os.environ["TMPFS_SIZE_MB"] = "100"
os.environ["SESSION_STORAGE"] = "TMPFS"
os.environ["DATASET_ACCESS"] = "NONE"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"
os.environ["ADDRESS_STRATEGY"] = "host"

from backend.db.models import Base, Thread
from backend.sandbox.session_manager import SessionManager, SessionStorage, DatasetAccess
from backend.artifacts.storage import ensure_blobstore, blob_path_for_sha


@pytest_asyncio.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_thread(db_session):
    """Create a test thread."""
    thread = Thread(user_id="test-user", title="Integration Test Thread")
    db_session.add(thread)
    await db_session.commit()
    await db_session.refresh(thread)
    return thread


@pytest.fixture
def session_manager():
    """Create a SessionManager for testing."""
    manager = SessionManager(
        image="sandbox:latest",
        session_storage=SessionStorage.TMPFS,
        dataset_access=DatasetAccess.NONE,
        tmpfs_size="100m",
        address_strategy="host"
    )
    yield manager
    # Cleanup: stop all sessions
    for session_key in list(manager.sessions.keys()):
        manager.stop(session_key)


class TestRealCodeExecution:
    """Test actual code execution in sandbox containers."""
    
    @pytest.mark.asyncio
    async def test_simple_print(self, session_manager, db_session, test_thread):
        """Test basic code execution with print statement."""
        session_key = session_manager.start("test-simple-print")
        
        try:
            result = await session_manager.exec(
                session_key=session_key,
                code='print("Hello from sandbox!")',
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-1"
            )
            
            assert result["ok"] is True
            assert "Hello from sandbox!" in result["stdout"]
            assert result["error"] == ""
        finally:
            session_manager.stop(session_key)
    
    @pytest.mark.asyncio
    async def test_variable_persistence(self, session_manager, db_session, test_thread):
        """Test that variables persist across executions in same session."""
        session_key = session_manager.start("test-persistence")
        
        try:
            # First execution - set variable
            result1 = await session_manager.exec(
                session_key=session_key,
                code="x = 42",
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-2a"
            )
            assert result1["ok"] is True
            
            # Second execution - use variable
            result2 = await session_manager.exec(
                session_key=session_key,
                code="print(f'x = {x}')",
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-2b"
            )
            assert result2["ok"] is True
            assert "x = 42" in result2["stdout"]
        finally:
            session_manager.stop(session_key)
    
    @pytest.mark.asyncio
    async def test_artifact_generation(self, session_manager, db_session, test_thread):
        """Test code execution that generates artifacts."""
        session_key = session_manager.start("test-artifacts")
        
        try:
            # Execute code that creates a file in /session/artifacts/
            code = """
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

x = np.linspace(0, 2*np.pi, 100)
y = np.sin(x)

plt.figure(figsize=(8, 6))
plt.plot(x, y)
plt.title('Sine Wave')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.grid(True)
plt.savefig('/session/artifacts/sine_plot.png')
plt.close()

print("Plot created successfully!")
"""
            
            result = await session_manager.exec(
                session_key=session_key,
                code=code,
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-3"
            )
            
            # Verify execution was successful
            assert result["ok"] is True
            assert "Plot created successfully!" in result["stdout"]
            
            # Verify artifact was created and ingested
            artifacts = result.get("artifacts", [])
            assert len(artifacts) > 0
            
            # Check artifact properties
            artifact = artifacts[0]
            assert artifact["name"] == "sine_plot.png"
            assert artifact["mime"] == "image/png"
            assert artifact["size"] > 0
            assert "url" in artifact
            
            # Verify artifact is in blobstore
            blobstore = await ensure_blobstore()
            blob_path = blob_path_for_sha(artifact["sha256"], blobstore)
            assert blob_path.exists()
            
        finally:
            session_manager.stop(session_key)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, session_manager, db_session, test_thread):
        """Test error handling for code that raises exceptions."""
        session_key = session_manager.start("test-errors")
        
        try:
            result = await session_manager.exec(
                session_key=session_key,
                code="raise ValueError('Test error')",
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-4"
            )
            
            # Should return error but not crash
            assert result["ok"] is False
            assert "ValueError" in result["error"] or "Test error" in result["error"]
        finally:
            session_manager.stop(session_key)
    
    @pytest.mark.asyncio
    async def test_numpy_pandas_available(self, session_manager, db_session, test_thread):
        """Test that common data science libraries are available."""
        session_key = session_manager.start("test-libraries")
        
        try:
            code = """
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Test numpy
arr = np.array([1, 2, 3, 4, 5])
print(f"numpy mean: {arr.mean()}")

# Test pandas
df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
print(f"pandas shape: {df.shape}")

print("All libraries available!")
"""
            
            result = await session_manager.exec(
                session_key=session_key,
                code=code,
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-5"
            )
            
            assert result["ok"] is True
            assert "numpy mean: 3.0" in result["stdout"]
            assert "pandas shape: (3, 2)" in result["stdout"]
            assert "All libraries available!" in result["stdout"]
        finally:
            session_manager.stop(session_key)
    
    @pytest.mark.asyncio
    async def test_multiple_artifacts(self, session_manager, db_session, test_thread):
        """Test creating multiple artifacts in one execution."""
        session_key = session_manager.start("test-multiple-artifacts")
        
        try:
            code = """
import os
os.makedirs('/session/artifacts', exist_ok=True)

# Create multiple files
with open('/session/artifacts/data1.txt', 'w') as f:
    f.write('First file content')

with open('/session/artifacts/data2.txt', 'w') as f:
    f.write('Second file content')

with open('/session/artifacts/data3.csv', 'w') as f:
    f.write('col1,col2\\n1,2\\n3,4')

print("Created 3 files")
"""
            
            result = await session_manager.exec(
                session_key=session_key,
                code=code,
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-6"
            )
            
            assert result["ok"] is True
            assert "Created 3 files" in result["stdout"]
            
            artifacts = result.get("artifacts", [])
            assert len(artifacts) == 3
            
            # Check artifact names
            artifact_names = {a["name"] for a in artifacts}
            assert "data1.txt" in artifact_names
            assert "data2.txt" in artifact_names
            assert "data3.csv" in artifact_names
        finally:
            session_manager.stop(session_key)


class TestSessionManagement:
    """Test session lifecycle management."""
    
    def test_session_start_stop(self, session_manager):
        """Test starting and stopping sessions."""
        session_key = session_manager.start("test-lifecycle")
        
        # Verify session exists
        assert session_key in session_manager.sessions
        
        # Stop session
        session_manager.stop(session_key)
        
        # Verify session is removed
        assert session_key not in session_manager.sessions
    
    def test_session_reuse(self, session_manager):
        """Test that starting same session returns same key."""
        session_key1 = session_manager.start("test-reuse")
        session_key2 = session_manager.start("test-reuse")
        
        assert session_key1 == session_key2
        assert session_key1 in session_manager.sessions
        
        session_manager.stop(session_key1)
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, session_manager, db_session, test_thread):
        """Test running multiple sessions concurrently."""
        session_key1 = session_manager.start("test-concurrent-1")
        session_key2 = session_manager.start("test-concurrent-2")
        
        try:
            # Execute in both sessions
            result1 = await session_manager.exec(
                session_key=session_key1,
                code="x = 'session1'",
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-7a"
            )
            
            result2 = await session_manager.exec(
                session_key=session_key2,
                code="x = 'session2'",
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-7b"
            )
            
            assert result1["ok"] is True
            assert result2["ok"] is True
            
            # Verify variables are isolated
            result1_check = await session_manager.exec(
                session_key=session_key1,
                code="print(x)",
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-7c"
            )
            
            result2_check = await session_manager.exec(
                session_key=session_key2,
                code="print(x)",
                timeout=30,
                db_session=db_session,
                thread_id=test_thread.id,
                tool_call_id="test-call-7d"
            )
            
            assert "session1" in result1_check["stdout"]
            assert "session2" in result2_check["stdout"]
        finally:
            session_manager.stop(session_key1)
            session_manager.stop(session_key2)


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v", "-s"])
