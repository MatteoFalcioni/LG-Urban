from __future__ import annotations

"""
SQLAlchemy 2.0 models for the dual-store design.

Ownership boundaries:
- Postgres is the source of truth for transcripts, configs, artifacts, metadata.
- LangGraph checkpointer stores ephemeral state (summaries, control flow) only.

Key choices:
- UUID primary keys for all entities to support offline client generation.
- messages.message_key is a client-supplied idempotency key to deduplicate retries.
- JSONB for flexible content, tool inputs/outputs, and metadata.
- Composite indexes optimized for timeline queries per thread.
"""

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    text,
    Index,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Multi-tenant scoping; all queries must filter by user_id
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # Arbitrary thread-level metadata (e.g., tags, UI state)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()"), server_onupdate=text("NOW()")
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    messages: Mapped[list[Message]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", passive_deletes=True
    )
    config: Mapped[Optional[Config]] = relationship(
        back_populates="thread", uselist=False, cascade="all, delete-orphan", passive_deletes=True
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="thread", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("ix_threads_user_updated", "user_id", "updated_at"),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Client-supplied idempotency key (e.g., a UUID the client generates per send)
    message_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    # role determines rendering and lineage; store finalized assistant content only (no partial tokens)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # user | assistant | system | tool
    # content supports text or structured message blocks
    content: Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tool_input: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    tool_output: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    # message-level metadata (e.g., tokens, costs, trace ids)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Relationships
    thread: Mapped[Thread] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_messages_thread_created", "thread_id", "created_at"),
    )


class Config(Base):
    __tablename__ = "configs"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), primary_key=True
    )
    # Common generation settings per thread; nullable to allow defaults at runtime
    model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    temperature: Mapped[Optional[float]] = mapped_column(nullable=True)
    system_prompt: Mapped[Optional[str]] = mapped_column(nullable=True)
    context_window: Mapped[Optional[int]] = mapped_column(nullable=True)  # Max tokens for context (e.g., 128000 for gpt-4o)
    settings: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Relationships
    thread: Mapped[Thread] = relationship(back_populates="config")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("threads.id", ondelete="CASCADE"), 
        nullable=False, index=True
    )
    
    # Deduplication via SHA-256 fingerprint
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    
    # File metadata
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    mime: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(nullable=False)
    
    # Session/run tracking for sandbox artifacts
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    run_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    
    # Arbitrary metadata (e.g., original container path, etc.)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("NOW()")
    )

    # Relationships
    thread: Mapped[Thread] = relationship(back_populates="artifacts")
    
    __table_args__ = (
        Index("ix_artifacts_thread_created", "thread_id", "created_at"),
        Index("ix_artifacts_sha256", "sha256"),
    )


