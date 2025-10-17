"""
Unit tests for database operations.
Tests cascade deletes, constraints, and data integrity.
"""
import pytest
from sqlalchemy.exc import IntegrityError

from backend.db.models import Thread, Message, Config, Artifact


class TestCascadeDeletes:
    """Test cascade delete behavior."""
    
    @pytest.mark.asyncio
    async def test_thread_deletion_cascades_to_messages(self, db_session):
        """Test that deleting a thread deletes its messages."""
        # Create thread
        thread = Thread(user_id="test-user", title="Test Thread")
        db_session.add(thread)
        await db_session.commit()
        await db_session.refresh(thread)
        
        # Create messages
        msg1 = Message(
            thread_id=thread.id,
            message_id="msg1",
            role="user",
            content={"text": "Hello"}
        )
        msg2 = Message(
            thread_id=thread.id,
            message_id="msg2", 
            role="assistant",
            content={"text": "Hi there"}
        )
        db_session.add_all([msg1, msg2])
        await db_session.commit()
        
        # Verify messages exist
        message_count = await db_session.execute(
            "SELECT COUNT(*) FROM messages WHERE thread_id = :thread_id",
            {"thread_id": thread.id}
        )
        assert message_count.scalar() == 2
        
        # Delete thread
        await db_session.delete(thread)
        await db_session.commit()
        
        # Verify messages are deleted
        message_count = await db_session.execute(
            "SELECT COUNT(*) FROM messages WHERE thread_id = :thread_id",
            {"thread_id": thread.id}
        )
        assert message_count.scalar() == 0
    
    @pytest.mark.asyncio
    async def test_thread_deletion_cascades_to_artifacts(self, db_session, temp_blobstore):
        """Test that deleting a thread deletes its artifacts."""
        from backend.artifacts.storage import ingest_artifact_file
        
        # Create thread
        thread = Thread(user_id="test-user", title="Test Thread")
        db_session.add(thread)
        await db_session.commit()
        await db_session.refresh(thread)
        
        # Create test file and ingest as artifact
        test_file = temp_blobstore / "test.txt"
        test_file.write_text("Hello, World!")
        
        artifact = await ingest_artifact_file(
            session=db_session,
            thread_id=thread.id,
            file_path=test_file,
            session_id="session1",
            run_id="run1",
            tool_call_id="call1"
        )
        
        # Verify artifact exists
        artifact_count = await db_session.execute(
            "SELECT COUNT(*) FROM artifacts WHERE thread_id = :thread_id",
            {"thread_id": thread.id}
        )
        assert artifact_count.scalar() == 1
        
        # Delete thread
        await db_session.delete(thread)
        await db_session.commit()
        
        # Verify artifact is deleted
        artifact_count = await db_session.execute(
            "SELECT COUNT(*) FROM artifacts WHERE thread_id = :thread_id",
            {"thread_id": thread.id}
        )
        assert artifact_count.scalar() == 0
        
        # Verify blob file still exists (not cleaned up by cascade)
        from backend.artifacts.storage import get_artifact_blob_path
        blob_path = get_artifact_blob_path(artifact, temp_blobstore)
        assert blob_path.exists()


class TestConstraints:
    """Test database constraints and validation."""
    
    @pytest.mark.asyncio
    async def test_unique_message_id_per_thread(self, db_session, test_thread):
        """Test that message_id must be unique within a thread."""
        # Create first message
        msg1 = Message(
            thread_id=test_thread.id,
            message_id="unique_id",
            role="user",
            content={"text": "First message"}
        )
        db_session.add(msg1)
        await db_session.commit()
        
        # Try to create second message with same ID
        msg2 = Message(
            thread_id=test_thread.id,
            message_id="unique_id",  # Same ID!
            role="assistant",
            content={"text": "Second message"}
        )
        db_session.add(msg2)
        
        # Should raise integrity error
        with pytest.raises(IntegrityError):
            await db_session.commit()
    
    @pytest.mark.asyncio
    async def test_sha256_uniqueness(self, db_session, test_thread, temp_blobstore):
        """Test that SHA-256 must be unique across all artifacts."""
        from backend.artifacts.storage import ingest_artifact_file
        
        # Create test file
        test_file = temp_blobstore / "test.txt"
        test_file.write_text("Hello, World!")
        
        # Ingest first time
        await ingest_artifact_file(
            session=db_session,
            thread_id=test_thread.id,
            file_path=test_file,
            session_id="session1",
            run_id="run1",
            tool_call_id="call1"
        )
        
        # Try to create artifact with same SHA-256 manually
        artifact2 = Artifact(
            thread_id=test_thread.id,
            sha256="same_sha256_hash",  # This should be unique
            filename="different.txt",
            mime="text/plain",
            size=100,
            session_id="session2",
            run_id="run2",
            tool_call_id="call2"
        )
        
        # First, create one with this SHA
        db_session.add(artifact2)
        await db_session.commit()
        
        # Now try to create another with same SHA
        artifact3 = Artifact(
            thread_id=test_thread.id,
            sha256="same_sha256_hash",  # Same SHA!
            filename="another.txt",
            mime="text/plain", 
            size=200,
            session_id="session3",
            run_id="run3",
            tool_call_id="call3"
        )
        db_session.add(artifact3)
        
        # Should raise integrity error
        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestDataIntegrity:
    """Test data integrity and relationships."""
    
    @pytest.mark.asyncio
    async def test_thread_config_relationship(self, db_session):
        """Test thread-config relationship."""
        # Create thread
        thread = Thread(user_id="test-user", title="Test Thread")
        db_session.add(thread)
        await db_session.commit()
        await db_session.refresh(thread)
        
        # Create config
        config = Config(
            thread_id=thread.id,
            model="gpt-4o",
            temperature=0.7,
            system_prompt="You are a helpful assistant"
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)
        
        # Verify relationship
        assert config.thread_id == thread.id
        assert config.thread == thread
        assert thread.config == config
    
    @pytest.mark.asyncio
    async def test_artifact_thread_relationship(self, db_session, test_thread, temp_blobstore):
        """Test artifact-thread relationship."""
        from backend.artifacts.storage import ingest_artifact_file
        
        # Create test file and ingest
        test_file = temp_blobstore / "test.txt"
        test_file.write_text("Hello, World!")
        
        artifact = await ingest_artifact_file(
            session=db_session,
            thread_id=test_thread.id,
            file_path=test_file,
            session_id="session1",
            run_id="run1",
            tool_call_id="call1"
        )
        
        # Verify relationship
        assert artifact.thread_id == test_thread.id
        assert artifact.thread == test_thread
        assert artifact in test_thread.artifacts
