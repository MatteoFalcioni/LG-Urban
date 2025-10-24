"""
Pytest configuration and shared fixtures for LG-Urban tests.
"""
import asyncio
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import AsyncClient

# Set test environment variables before importing backend modules
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

from backend.db.models import Base, Thread, Message, Config, Artifact
from backend.db.session import get_database_url
from backend.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Create a temporary test database."""
    # Use in-memory SQLite for fast tests
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    yield async_session
    
    # Cleanup
    await engine.dispose()


@pytest.fixture
async def db_session(test_db):
    """Get a database session for testing."""
    async with test_db() as session:
        yield session


@pytest.fixture
async def test_thread(db_session):
    """Create a test thread."""
    thread = Thread(user_id="test-user", title="Test Thread")
    db_session.add(thread)
    await db_session.commit()
    await db_session.refresh(thread)
    return thread


@pytest.fixture
def test_client():
    """Create a test HTTP client."""
    return AsyncClient(app=app, base_url="http://test")


@pytest.fixture
def temp_blobstore():
    """Create a temporary blobstore directory."""
    temp_dir = tempfile.mkdtemp(prefix="test_blobstore_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_artifact_data():
    """Sample artifact data for testing."""
    return {
        "filename": "test_plot.png",
        "mime": "image/png", 
        "size": 12345,
        "sha256": "abcd1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab",
        "session_id": "test-session",
        "run_id": "test-run",
        "tool_call_id": "test-tool-call"
    }
