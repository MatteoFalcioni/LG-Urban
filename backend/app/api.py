from __future__ import annotations

from typing import Optional, Any
from datetime import datetime, timezone
from uuid import UUID

import logging
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_session
from backend.db.models import Thread, Message, Config


# API router for thread- and message-related endpoints, mounted under /api
router = APIRouter()


# Request schema for creating a new thread
class ThreadCreate(BaseModel):
    # Caller-provided user id. In production, this would come from auth.
    user_id: str
    # Optional title; can be auto-titled later from first assistant reply.
    title: str = "New chat"


# Response schema returned for thread resources
class ThreadOut(BaseModel):
    id: UUID
    user_id: str
    title: Optional[str]
    archived_at: Optional[datetime] = None

    class Config:
        # Allow constructing from ORM models
        from_attributes = True


def to_jsonable(value: Any) -> Any:
    """
    Best-effort conversion of arbitrary objects (LangChain/LangGraph types, Pydantic models, etc.)
    into JSON-serializable primitives for DB storage and SSE.
    """
    try:
        json.dumps(value)
        return value
    except Exception:
        pass

    # Pydantic v2
    try:
        if hasattr(value, "model_dump"):
            return value.model_dump()
    except Exception:
        pass

    # Pydantic v1 / dataclass-like
    try:
        if hasattr(value, "dict"):
            return value.dict()
    except Exception:
        pass

    # LangChain message chunks often have .content
    try:
        if hasattr(value, "content"):
            return getattr(value, "content")
    except Exception:
        pass

    # Bytes → utf-8 string
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="ignore")

    # Fallback string representation
    try:
        return str(value)
    except Exception:
        return None


@router.post("/threads", response_model=ThreadOut)
async def create_thread(payload: ThreadCreate, session: AsyncSession = Depends(get_session)) -> ThreadOut:
    """
    Create a new thread row for the given user.
    Returns the created thread in a stable response shape for the frontend.
    """
    thread = Thread(user_id=payload.user_id, title=payload.title)
    session.add(thread)
    await session.commit()
    # Refresh to ensure we return DB-generated values (e.g., UUID)
    await session.refresh(thread)
    return ThreadOut.model_validate(thread)


@router.get("/threads", response_model=list[ThreadOut])
async def list_threads(
    user_id: str = Query(..., description="Scope threads by user"),
    limit: int = Query(20, ge=1, le=100),
    include_archived: bool = Query(False, description="Include archived threads"),
    session: AsyncSession = Depends(get_session),
) -> list[ThreadOut]:
    """
    List recent threads for a user, ordered by last update.
    Limit is capped to avoid excessive payloads.
    """
    conditions = [Thread.user_id == user_id]
    if not include_archived:
        conditions.append(Thread.archived_at.is_(None))
    
    stmt = (
        select(Thread)
        .where(*conditions)
        .order_by(Thread.updated_at.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    rows = res.scalars().all()
    return [ThreadOut.model_validate(r) for r in rows]


@router.get("/threads/{thread_id}", response_model=ThreadOut)
async def get_thread(
    thread_id: str,
    session: AsyncSession = Depends(get_session),
) -> ThreadOut:
    """
    Get thread metadata by ID.
    """
    t = await session.get(Thread, thread_id)
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadOut.model_validate(t)


@router.post("/threads/{thread_id}/archive", response_model=ThreadOut)
async def archive_thread(
    thread_id: str,
    session: AsyncSession = Depends(get_session),
) -> ThreadOut:
    """
    Soft-delete (archive) a thread. Archived threads are hidden from list by default.
    """
    t = await session.get(Thread, thread_id)
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    if t.archived_at is None:
        t.archived_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(t)
    return ThreadOut.model_validate(t)


@router.post("/threads/{thread_id}/unarchive", response_model=ThreadOut)
async def unarchive_thread(
    thread_id: str,
    session: AsyncSession = Depends(get_session),
) -> ThreadOut:
    """
    Un-archive a thread, making it visible in the default list again.
    """
    t = await session.get(Thread, thread_id)
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    if t.archived_at is not None:
        t.archived_at = None
        await session.commit()
        await session.refresh(t)
    return ThreadOut.model_validate(t)


@router.delete("/threads/{thread_id}", status_code=204, response_class=Response)
async def delete_thread(
    thread_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Hard-delete a thread and all related rows (messages, configs, artifacts) via cascades.
    Best-effort: acquire per-thread lock to avoid concurrent runs.
    """
    from backend.main import get_thread_lock

    lock = get_thread_lock(str(thread_id))
    async with lock:
        t = await session.get(Thread, thread_id)
        if not t:
            # Idempotent: deleting a non-existent thread returns 204
            return Response(status_code=204)

        await session.delete(t)
        await session.commit()

        # Best-effort: we could also remove LangGraph checkpoints here if API allows.
        # Skipped to keep implementation simple.

    return Response(status_code=204)


class ThreadTitleUpdate(BaseModel):
    title: str


@router.patch("/threads/{thread_id}/title", response_model=ThreadOut)
async def update_thread_title(
    thread_id: str,
    payload: ThreadTitleUpdate,
    session: AsyncSession = Depends(get_session),
) -> ThreadOut:
    """
    Update thread title manually.
    """
    t = await session.get(Thread, thread_id)
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    t.title = payload.title
    await session.commit()
    await session.refresh(t)
    return ThreadOut.model_validate(t)

@router.post("/threads/{thread_id}/title/auto", response_model=ThreadOut)
async def llm_update_thread_title(
    thread_id: str,
    session: AsyncSession = Depends(get_session),
) -> ThreadOut:
    """
    Auto-generate thread title using LLM based on conversation so far.
    """
    t = await session.get(Thread, thread_id)
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Fetch recent messages (max last 6 for context)
    stmt = (
        select(Message)
        .where(Message.thread_id == t.id)
        .order_by(Message.created_at.asc())
        .limit(6)
    )
    res = await session.execute(stmt)
    messages = res.scalars().all()
    
    # Build thread text from messages
    thread_text = "\n".join([
        f"{m.role}: {m.content.get('text', str(m.content)) if m.content else ''}"
        for m in messages
    ])
    
    if not thread_text.strip():
        raise HTTPException(status_code=400, detail="No messages to generate title from")

    # Generate title with LLM
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Return a concise, engaging title. No quotes, <= 8 words."),
        ("user", "Text:\n{body}\n\nTitle:")
    ])
    chain = prompt | llm | StrOutputParser()

    t.title = chain.invoke({"body": thread_text})
    await session.commit()
    await session.refresh(t)
    return ThreadOut.model_validate(t)


# Config schemas
class ConfigOut(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None
    context_window: Optional[int] = None
    settings: Optional[dict] = None

    class Config:
        from_attributes = True


class ConfigUpdate(BaseModel):
    model: Optional[str] = None
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None
    context_window: Optional[int] = None
    settings: Optional[dict] = None


@router.get("/config/defaults", response_model=ConfigOut)
async def get_default_config() -> ConfigOut:
    """
    Get default config from environment variables (no thread required).
    """
    from backend.config import DEFAULT_MODEL, DEFAULT_TEMPERATURE, CONTEXT_WINDOW
    
    return ConfigOut(
        model=DEFAULT_MODEL,
        temperature=DEFAULT_TEMPERATURE,
        context_window=CONTEXT_WINDOW,
        settings=None
    )


@router.get("/threads/{thread_id}/config", response_model=ConfigOut)
async def get_thread_config(
    thread_id: str,
    session: AsyncSession = Depends(get_session),
) -> ConfigOut:
    """
    Get thread-specific config (model, temperature, system_prompt).
    Returns defaults if no config exists.
    """
    from backend.config import DEFAULT_MODEL, DEFAULT_TEMPERATURE
    
    cfg = await session.get(Config, thread_id)
    if not cfg:
        # Return env-based defaults
        from backend.config import CONTEXT_WINDOW
        return ConfigOut(
            model=DEFAULT_MODEL,
            temperature=DEFAULT_TEMPERATURE,
            context_window=CONTEXT_WINDOW,
            settings=None
        )
    return ConfigOut.model_validate(cfg)


@router.post("/threads/{thread_id}/config", response_model=ConfigOut)
async def update_thread_config(
    thread_id: str,
    payload: ConfigUpdate,
    session: AsyncSession = Depends(get_session),
) -> ConfigOut:
    """
    Update thread config (upsert). Frontend can set model, temperature, system_prompt per thread.
    """
    t = await session.get(Thread, thread_id)
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    cfg = await session.get(Config, thread_id)
    if not cfg:
        cfg = Config(thread_id=t.id)
        session.add(cfg)
    
    # Update fields if provided
    if payload.model is not None:
        cfg.model = payload.model
    if payload.temperature is not None:
        cfg.temperature = payload.temperature
    if payload.system_prompt is not None:
        cfg.system_prompt = payload.system_prompt
    if payload.context_window is not None:
        cfg.context_window = payload.context_window
    if payload.settings is not None:
        cfg.settings = payload.settings
    
    await session.commit()
    await session.refresh(cfg)
    return ConfigOut.model_validate(cfg)


# Response schema for messages
class ArtifactOut(BaseModel):
    id: UUID
    name: str
    mime: str
    size: int
    url: str
    
    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: UUID
    thread_id: UUID
    role: str
    content: Optional[dict] = None
    tool_name: Optional[str] = None
    tool_input: Optional[dict] = None
    tool_output: Optional[dict] = None
    artifacts: list[ArtifactOut] = []

    class Config:
        from_attributes = True


@router.get("/threads/{thread_id}/messages", response_model=list[MessageOut])
async def list_messages(
    thread_id: str,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[MessageOut]:
    """
    List recent messages for a thread (reverse chronological by created_at).
    Only finalized messages are stored and returned (no partial tokens).
    Includes artifacts associated with each message via tool_call_id.
    """
    from backend.db.models import Artifact
    from backend.artifacts.tokens import create_download_url
    
    stmt = (
        select(Message)
        .where(Message.thread_id == thread_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(stmt)
    messages = res.scalars().all()
    
    # Build message outputs with artifacts
    message_outputs = []
    for msg in messages:
        msg_dict = {
            "id": msg.id,
            "thread_id": msg.thread_id,
            "role": msg.role,
            "content": msg.content,
            "tool_name": msg.tool_name,
            "tool_input": msg.tool_input,
            "tool_output": msg.tool_output,
            "artifacts": [],
        }
        
        # For assistant messages, look for artifacts from recent tool calls
        if msg.role == "assistant":
            # Look backwards through messages to find the most recent tool message with artifacts
            # We need to check all messages in this thread, not just the current batch
            all_messages_stmt = (
                select(Message)
                .where(Message.thread_id == thread_id)
                .where(Message.created_at <= msg.created_at)
                .where(Message.role == "tool")
                .order_by(Message.created_at.desc())
            )
            all_messages_res = await session.execute(all_messages_stmt)
            recent_tool_messages = all_messages_res.scalars().all()
            
            # Find the most recent tool message with artifacts
            for tool_msg in recent_tool_messages:
                # Extract tool_call_id from tool_input (where it's actually stored)
                tool_call_id = None
                if isinstance(tool_msg.tool_input, dict):
                    tool_call_id = tool_msg.tool_input.get("tool_call_id")
                
                # Fallback: check tool_output
                if not tool_call_id and isinstance(tool_msg.tool_output, dict):
                    tool_call_id = tool_msg.tool_output.get("tool_call_id")
                
                # Also check meta field
                if not tool_call_id and tool_msg.meta:
                    tool_call_id = tool_msg.meta.get("tool_call_id")
                
                if tool_call_id:
                    # Query artifacts for this tool call
                    artifact_stmt = select(Artifact).where(Artifact.tool_call_id == tool_call_id)
                    artifact_res = await session.execute(artifact_stmt)
                    artifacts = artifact_res.scalars().all()
                    
                    if artifacts:  # Only process if we found artifacts
                        # Build artifact outputs with download URLs
                        for artifact in artifacts:
                            try:
                                url = create_download_url(str(artifact.id))
                                msg_dict["artifacts"].append({
                                    "id": artifact.id,
                                    "name": artifact.filename,
                                    "mime": artifact.mime,
                                    "size": artifact.size,
                                    "url": url,
                                })
                            except Exception as e:
                                print(f"Warning: Could not create URL for artifact {artifact.id}: {e}")
                        break  # Found artifacts, stop looking
        
        message_outputs.append(MessageOut.model_validate(msg_dict))
    
    return message_outputs



class PostMessageIn(BaseModel):
    # Client idempotency key (required)
    message_id: str
    # Message body (text or structured blocks); keep minimal for stub
    content: dict
    # Role must be 'user' for this stub
    role: str = "user"


@router.post("/threads/{thread_id}/messages")
async def post_message_stream(
    request: Request,
    thread_id: str,
    payload: PostMessageIn,
    session: AsyncSession = Depends(get_session),
):
    """
    Accept user message, run LangGraph agent, stream tokens via SSE,
    and persist finalized assistant message at end.
    Enforces idempotency via unique message_id and per-thread locking.
    """
    if payload.role != "user":
        raise HTTPException(status_code=400, detail="Only user role allowed")

    # Ensure thread exists
    t = await session.get(Thread, thread_id)
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    # Read thread config (model, temperature, system_prompt, context_window)
    cfg = await session.get(Config, thread_id)

    # Insert user message; unique constraint on message_id enforces idempotency
    msg = Message(
        thread_id=t.id,
        message_id=payload.message_id,
        role="user",
        content=payload.content,
    )
    session.add(msg)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Duplicate message_id")

    # Stream LangGraph agent response via SSE
    async def event_stream():
        from backend.main import get_thread_lock
        from backend.graph.graph import make_graph
        from backend.main import _checkpointer_cm
        from backend.db.session import ASYNC_SESSION_MAKER
        from backend.graph.context import set_db_session, set_thread_id
        import uuid as uuid_module
        
        if not _checkpointer_cm:
            yield f"data: {json.dumps({'error': 'Checkpointer not initialized'})}\n\n"
            return
        
        # Create graph with thread-specific config
        graph = make_graph(
            model_name=cfg.model if cfg else None,
            temperature=cfg.temperature if cfg else None,
            system_prompt=cfg.system_prompt if cfg else None,
            context_window=cfg.context_window if cfg else None,  # Use thread config or env default
            checkpointer=_checkpointer_cm[0],  # Reuse global checkpointer
        )

        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        assistant_content = None
        tool_calls = []  # Track tool calls for persistence

        # Get context usage from graph state BEFORE streaming
        try:
            from backend.config import CONTEXT_WINDOW as DEFAULT_CONTEXT_WINDOW
            state_snapshot = await graph.aget_state(config)
            token_count = state_snapshot.values.get("token_count", 0) if state_snapshot.values else 0
            # Use thread config context_window or env default
            max_tokens = cfg.context_window if cfg and cfg.context_window else DEFAULT_CONTEXT_WINDOW
            # Emit context update for frontend circle
            yield f"data: {json.dumps({'type': 'context_update', 'tokens_used': token_count, 'max_tokens': max_tokens})}\n\n"
        except Exception as e:
            logging.warning(f"Failed to get state for context update: {e}")
        
        try:
            lock = get_thread_lock(str(thread_id))
            async with lock:
                # Set context variables for tools to access database session and thread_id
                set_db_session(session)
                set_thread_id(uuid_module.UUID(str(thread_id)))
                
                # Extract text from content dict; LangChain messages expect string content
                user_text = payload.content.get("text", str(payload.content))
                state = {"messages": [{"role": "user", "content": user_text}]}
                config = {"configurable": {"thread_id": str(thread_id)}}
                
                # Stream events from LangGraph
                # We follow docs here: https://python.langchain.com/api_reference/core/language_models/langchain_core.language_models.chat_models.BaseChatModel.html?_gl=1*15ktatf*_gcl_au*MTc4MTgwMzA1Ny4xNzU4ODA2Mjcy*_ga*MTUzOTQwNjk3NS4xNzUwODY1MDM0*_ga_47WX3HKKY2*czE3NTk4MjY0Mzkkbzk5JGcxJHQxNzU5ODI2NTg0JGoxMyRsMCRoMA..#langchain_core.language_models.chat_models.BaseChatModel.astream_events
                async for event in graph.astream_events(state, config, version="v2"):
                    event_type = event.get("event")
                    event_name = event.get("name", "")
                    event_meta = event.get("metadata", {})
                    node = event_meta.get("langgraph_node")
                    checkpoint_ns = event_meta.get("langgraph_checkpoint_ns", "")
                    
                    # Stream token chunks from the LLM (but not from summarizer or its sub-calls)
                    if event_type == "on_chat_model_stream":
                        # Skip if we're inside summarization context (agent called by summarizer)
                        if checkpoint_ns.startswith("summarize_conversation:"):
                            continue
                        
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            yield f"data: {json.dumps({'type': 'token', 'content': chunk.content})}\n\n"
                    
                    # Detect summarization start
                    elif event_type == "on_chat_model_start" and checkpoint_ns.startswith("summarize_conversation:"):
                        yield f"data: {json.dumps({'type': 'summarizing', 'status': 'start'})}\n\n"
                    
                    # Detect summarization end
                    elif event_type == "on_chat_model_end" and checkpoint_ns.startswith("summarize_conversation:"):
                        yield f"data: {json.dumps({'type': 'summarizing', 'status': 'done'})}\n\n"
                        # Emit context reset immediately after summarization (token_count is now 0)
                        from backend.config import CONTEXT_WINDOW as DEFAULT_CONTEXT_WINDOW
                        max_tokens = cfg.context_window if cfg and cfg.context_window else DEFAULT_CONTEXT_WINDOW
                        yield f"data: {json.dumps({'type': 'context_update', 'tokens_used': 0, 'max_tokens': max_tokens})}\n\n"
                
                    # Stream tool execution start
                    elif event_type == "on_tool_start":
                        tool_input = event.get("data", {}).get("input")
                        yield f"data: {json.dumps({'type': 'tool_start', 'name': event_name, 'input': tool_input})}\n\n"
                        
                    # Stream tool execution end and capture for persistence
                    elif event_type == "on_tool_end":   
                        raw_input = event.get("data", {}).get("input")
                        raw_output = event.get("data", {}).get("output")
                        
                        # Extract artifacts and content from Command -> ToolMessage if present
                        artifacts = None
                        tool_content = None
                        
                        # Case 1: Output is a Command object (from code_sandbox tool)
                        if hasattr(raw_output, "update") and isinstance(raw_output.update, dict):
                            messages = raw_output.update.get("messages", [])
                            if messages and len(messages) > 0:
                                tool_msg = messages[0]
                                # Extract artifacts
                                if hasattr(tool_msg, "artifact") and tool_msg.artifact:
                                    artifacts = tool_msg.artifact
                                # Extract content for database persistence
                                if hasattr(tool_msg, "content"):
                                    tool_content = tool_msg.content
                        # Case 2: Output is a ToolMessage directly
                        elif hasattr(raw_output, "artifact"):
                            artifacts = raw_output.artifact
                            if hasattr(raw_output, "content"):
                                tool_content = raw_output.content
                        
                        # For database: store the tool content as dict (not the whole Command object)
                        if tool_content:
                            # If content is a string, wrap it in a dict
                            tool_output_for_db = {"content": tool_content} if isinstance(tool_content, str) else to_jsonable(tool_content)
                        else:
                            # Fallback to jsonable representation
                            tool_output_for_db = to_jsonable(raw_output)
                        
                        # Extract tool_call_id from raw_output (Command object)
                        tool_call_id = None
                        if hasattr(raw_output, "update") and isinstance(raw_output.update, dict):
                            messages = raw_output.update.get("messages", [])
                            if messages and len(messages) > 0:
                                tool_msg = messages[0]
                                if hasattr(tool_msg, "tool_call_id"):
                                    tool_call_id = tool_msg.tool_call_id
                        
                        tool_calls.append({
                            "name": event_name,
                            "input": to_jsonable(raw_input),
                            "output": tool_output_for_db,
                            "tool_call_id": tool_call_id,
                        })
                        
                        # Include artifacts in SSE event for frontend
                        event_data = {
                            'type': 'tool_end',
                            'name': event_name,
                            'output': tool_output_for_db
                        }
                        if artifacts:
                            event_data['artifacts'] = artifacts
                        
                        yield f"data: {json.dumps(event_data)}\n\n"
                    
                    # Capture final assistant message (but not from summarizer or its sub-calls)
                    elif event_type == "on_chat_model_end":
                        # Skip if inside summarization context
                        if checkpoint_ns.startswith("summarize_conversation:"):
                            continue
                        
                        output = event.get("data", {}).get("output")
                        if output and hasattr(output, "content"):
                            assistant_content = output.content
                
                # Persist using a short-lived session to avoid holding an open connection during SSE
                a_msg_id = None
                async with ASYNC_SESSION_MAKER() as write_sess:
                    # Tool messages first
                    for idx, tool_call in enumerate(tool_calls):
                        # Extract tool_call_id if available
                        tool_call_id = tool_call.get("id") or tool_call.get("tool_call_id")
                        
                        tool_msg = Message(
                            thread_id=t.id,
                            message_id=f"tool:{payload.message_id}:{idx}",
                            role="tool",
                            tool_name=tool_call["name"],
                            tool_input=tool_call.get("input"),
                            tool_output=tool_call.get("output"),
                            content=None,
                            meta={"tool_call_id": tool_call_id} if tool_call_id else None,
                        )
                        write_sess.add(tool_msg)

                    # Assistant message
                    if assistant_content:
                        a_msg = Message(
                            thread_id=t.id,
                            message_id=f"assistant:{payload.message_id}",
                            role="assistant",
                            content={"text": assistant_content} if isinstance(assistant_content, str) else assistant_content,
                        )
                        write_sess.add(a_msg)
                        await write_sess.commit()
                        a_msg_id = str(a_msg.id)
                    elif tool_calls:
                        await write_sess.commit()

                # Auto-title in a separate short-lived session (best-effort)
                if a_msg_id:
                    try:
                        from langchain_openai import ChatOpenAI
                        from langchain_core.prompts import ChatPromptTemplate
                        from langchain_core.output_parsers import StrOutputParser
                        async with ASYNC_SESSION_MAKER() as title_sess:
                            thread_check = await title_sess.get(Thread, t.id)
                            if thread_check and thread_check.title == "New chat":
                                stmt = (
                                    select(Message)
                                    .where(Message.thread_id == thread_check.id)
                                    .order_by(Message.created_at.asc())
                                    .limit(4)
                                )
                                res = await title_sess.execute(stmt)
                                messages = res.scalars().all()
                                thread_text = "\n".join([
                                    f"{m.role}: {m.content.get('text', str(m.content)) if m.content else ''}"
                                    for m in messages
                                ])
                                llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
                                prompt = ChatPromptTemplate.from_messages([
                                    ("system", "Return a concise, engaging title. No quotes, <= 8 words."),
                                    ("user", "Text:\n{body}\n\nTitle:")
                                ])
                                chain = prompt | llm | StrOutputParser()
                                new_title = chain.invoke({"body": thread_text})
                                thread_check.title = new_title
                                await title_sess.commit()
                                # Notify frontend of title update
                                yield f"data: {json.dumps({'type': 'title_updated', 'title': new_title})}\n\n"
                    except Exception as e:
                        logging.warning(f"Auto-title failed: {e}")

                yield f"data: {json.dumps({'type': 'done', 'message_id': a_msg_id})}\n\n"
                    
        except Exception as e:
            logging.exception(
                "agent_stream_failed",
                extra={
                    "request_id": request_id,
                    "thread_id": str(thread_id),
                    "message_id": payload.message_id,
                },
            )
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


