"""
Graph execution context management using contextvars.

This module provides a way to pass database sessions and thread IDs
through the async call stack without explicitly threading them through
every function parameter.
"""

from contextvars import ContextVar
from typing import Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

# Context variables for the current graph execution
_db_session: ContextVar[Optional[AsyncSession]] = ContextVar('db_session', default=None)
_thread_id: ContextVar[Optional[uuid.UUID]] = ContextVar('thread_id', default=None)


def set_db_session(session: AsyncSession) -> None:
    """Set the database session for the current execution context."""
    _db_session.set(session)


def get_db_session() -> Optional[AsyncSession]:
    """Get the database session from the current execution context."""
    return _db_session.get()


def set_thread_id(thread_id: uuid.UUID) -> None:
    """Set the thread ID for the current execution context."""
    _thread_id.set(thread_id)


def get_thread_id() -> Optional[uuid.UUID]:
    """Get the thread ID from the current execution context."""
    return _thread_id.get()

