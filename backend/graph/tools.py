from tavily import TavilyClient
import os
from langchain_core.tools import tool

from backend.sandbox.session_manager import SessionManager
from backend.tool_factory.make_tools import make_code_sandbox_tool
from backend.config import (
    SANDBOX_IMAGE,
    SESSION_STORAGE,
    DATASET_ACCESS,
    TMPFS_SIZE_MB,
    SANDBOX_NETWORK,
    HYBRID_LOCAL_PATH,
)


# ---------- Internet Search Tool ----------

@tool
def internet_search(query):
    """Search the internet for information"""
    tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    return tavily_client.search(query)


# ---------- Code Sandbox Tool ----------

# Global session manager instance (initialized once)
_session_manager = None


def get_session_manager() -> SessionManager:
    """
    Get or create the global SessionManager instance.
    
    The session manager is initialized once and reused for all code executions.
    Sessions are identified by thread_id to maintain isolation between conversations.
    """
    global _session_manager
    if _session_manager is None:
        # Convert MB to string format (e.g., "1024" -> "1g")
        tmpfs_mb = TMPFS_SIZE_MB
        tmpfs_size = f"{tmpfs_mb}m" if tmpfs_mb < 1024 else f"{tmpfs_mb // 1024}g"
        
        _session_manager = SessionManager(
            image=SANDBOX_IMAGE,
            session_storage=SESSION_STORAGE,
            dataset_access=DATASET_ACCESS,
            tmpfs_size=tmpfs_size,
            compose_network=SANDBOX_NETWORK,
            hybrid_local_path=HYBRID_LOCAL_PATH,  # Required for HYBRID mode
        )
    return _session_manager


def make_code_sandbox(session_key_fn=None):
    """
    Create a code sandbox tool with the global session manager.
    
    Args:
        session_key_fn: Optional function that returns the session key (thread_id).
                       If None, retrieves thread_id from context.
    
    Returns:
        LangChain tool for code execution
    """
    if session_key_fn is None:
        # Default: get thread_id from context (set by API layer)
        def _get_session_key():
            from backend.graph.context import get_thread_id
            tid = get_thread_id()
            return str(tid) if tid else "default"
        
        session_key_fn = _get_session_key
    
    return make_code_sandbox_tool(
        session_manager=get_session_manager(),
        session_key_fn=session_key_fn,
        name="code_sandbox",
        description=(
            "Execute Python code in a sandboxed Docker environment. "
            "The environment persists across calls within the same conversation. "
            "Use this to run calculations, data analysis, create visualizations, etc. "
            "Files created in /session/artifacts/ will be available for download. "
            "Always use print() to show results to the user."
        ),
    )

# ---------- Dataset Tools ----------
# Note: Dataset tools (select_dataset, export_datasets, list_datasets) are available
# in make_tools.py but require dataset management infrastructure to be set up.
# They can be added when needed by importing from tool_factory.make_tools.