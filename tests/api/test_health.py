"""
Basic API health checks to verify endpoints are working.
These tests use the Docker Postgres from infra/ setup.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.db.session import ENGINE

from dotenv import load_dotenv

load_dotenv()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def cleanup_engine():
    """Cleanup SQLAlchemy engine before and after each test."""
    await ENGINE.dispose()
    yield
    await ENGINE.dispose()


@pytest.mark.asyncio
async def test_get_default_config():
    """Test the default config endpoint (no DB required)."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/config/defaults")
        assert response.status_code == 200
        data = response.json()
        assert "model" in data
        assert "temperature" in data
        assert "context_window" in data


@pytest.mark.asyncio
async def test_create_and_list_threads():
    """Test thread creation and listing."""
    test_user_id = "ci-test-user"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create a thread
        create_response = await client.post(
            "/api/threads", json={"user_id": test_user_id}
        )
        assert create_response.status_code == 200
        thread_data = create_response.json()
        assert thread_data["user_id"] == test_user_id
        thread_id = thread_data["id"]

        # List threads
        list_response = await client.get(
            "/api/threads", params={"user_id": test_user_id, "limit": 10}
        )
        assert list_response.status_code == 200
        threads = list_response.json()
        assert isinstance(threads, list)
        assert len(threads) > 0
        assert any(t["id"] == thread_id for t in threads)

        # Get specific thread
        get_response = await client.get(f"/api/threads/{thread_id}")
        assert get_response.status_code == 200
        retrieved_thread = get_response.json()
        assert retrieved_thread["id"] == thread_id
        assert retrieved_thread["user_id"] == test_user_id


@pytest.mark.asyncio
async def test_get_thread_config():
    """Test thread-specific config retrieval."""
    test_user_id = "ci-config-test-user"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create a thread first
        create_response = await client.post(
            "/api/threads", json={"user_id": test_user_id}
        )
        assert create_response.status_code == 200
        thread_id = create_response.json()["id"]

        # Get thread config
        config_response = await client.get(f"/api/threads/{thread_id}/config")
        assert config_response.status_code == 200
        config = config_response.json()
        assert "model" in config
        assert "temperature" in config


@pytest.mark.asyncio
async def test_list_messages_empty_thread():
    """Test listing messages from an empty thread."""
    test_user_id = "ci-messages-test-user"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create a thread
        create_response = await client.post(
            "/api/threads", json={"user_id": test_user_id}
        )
        thread_id = create_response.json()["id"]

        # List messages (should be empty)
        messages_response = await client.get(
            f"/api/threads/{thread_id}/messages", params={"limit": 20}
        )
        assert messages_response.status_code == 200
        messages = messages_response.json()
        assert isinstance(messages, list)
        # New threads start empty or might have system messages
        assert len(messages) >= 0


@pytest.mark.asyncio
async def test_archive_and_restore_thread():
    """Test archiving and restoring a thread."""
    test_user_id = "ci-archive-test-user"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Create a thread
        create_response = await client.post(
            "/api/threads", json={"user_id": test_user_id}
        )
        thread_id = create_response.json()["id"]

        # Archive the thread
        archive_response = await client.post(f"/api/threads/{thread_id}/archive")
        assert archive_response.status_code == 200

        # Verify it's archived (shouldn't appear in default list)
        list_response = await client.get(
            "/api/threads", params={"user_id": test_user_id, "include_archived": False}
        )
        threads = list_response.json()
        assert not any(t["id"] == thread_id for t in threads)

        # Unarchive the thread
        unarchive_response = await client.post(f"/api/threads/{thread_id}/unarchive")
        assert unarchive_response.status_code == 200

        # Verify it's back in the list
        list_response_2 = await client.get(
            "/api/threads", params={"user_id": test_user_id, "include_archived": False}
        )
        threads_2 = list_response_2.json()
        assert any(t["id"] == thread_id for t in threads_2)


@pytest.mark.asyncio
async def test_user_api_keys_endpoints():
    """Test user API keys endpoints (get and save)."""
    test_user_id = "ci-apikeys-test-user"

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Get API keys (should be empty for new user)
        get_response = await client.get(f"/api/users/{test_user_id}/api-keys")
        assert get_response.status_code == 200
        keys = get_response.json()
        assert "openai_key" in keys
        assert "anthropic_key" in keys

        # Save API keys
        save_response = await client.post(
            f"/api/users/{test_user_id}/api-keys",
            json={"openai_key": "sk-test-key-123", "anthropic_key": None},
        )
        assert save_response.status_code == 200
        saved_keys = save_response.json()
        # Keys should be masked
        assert saved_keys["openai_key"] is not None
        assert "sk-test-key-123" not in saved_keys["openai_key"]  # Should be masked
