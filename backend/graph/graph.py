from langgraph.types import Command
from typing_extensions import Literal
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from dotenv import load_dotenv
import os

from backend.graph.prompt import PROMPT
from backend.graph.tools import internet_search, make_code_sandbox
from backend.graph.api_tools import (
    list_catalog_tool,
    preview_dataset_tool,
    get_dataset_description_tool,
    get_dataset_fields_tool,
    is_geo_dataset_tool,
    get_dataset_time_info_tool,
)
from backend.graph.state import MyState
from backend.config import CONTEXT_WINDOW


load_dotenv()

# LangGraph per-convo memory (sqlite). Use env or fallback to local file.
DB_PATH = os.getenv("LANGGRAPH_CHECKPOINT_DB", os.path.abspath(".lg_checkpoints.sqlite"))

async def get_checkpointer():
    """
    Initialize checkpointer once at app startup (called from main.py lifespan).
    Returns the same checkpointer instance to be reused across all graph invocations.
    """
    print(f"DEBUG: DB_PATH = {DB_PATH}")
    print(f"DEBUG: DB_PATH exists = {os.path.exists(DB_PATH)}")
    print(f"DEBUG: DB_PATH is file = {os.path.isfile(DB_PATH)}")
    cm_or_obj = AsyncSqliteSaver.from_conn_string(DB_PATH)

    # Old 0.2.x style: context manager (needs __aenter__/__aexit__)
    if hasattr(cm_or_obj, "__aenter__") and not hasattr(cm_or_obj, "aget_tuple"):
        saver = await cm_or_obj.__aenter__()         # open it once
        return saver, cm_or_obj                      # return both to close later
    else:
        raise ValueError("New style: direct object")


def make_graph(model_name: str | None = None, temperature: float | None = None, system_prompt: str | None = None, context_window: int | None = None, checkpointer=None):
    """
    Create a graph with custom config. Reuses the same checkpointer for all invocations.
    
    Args:
        model_name: OpenAI model name (e.g., "gpt-4o", "gpt-4o-mini")
        temperature: Model temperature (0.0-2.0). If None, uses env DEFAULT_TEMPERATURE or model default.
        system_prompt: Custom system prompt. If None, uses default PROMPT.
        context_window: Custom context window. If None, uses env CONTEXT_WINDOW.
        checkpointer: Reused checkpointer instance from app startup.
    """
    from backend.config import DEFAULT_MODEL, DEFAULT_TEMPERATURE, CONTEXT_WINDOW
    # Use config or fall back to env defaults
    model_name = model_name or DEFAULT_MODEL
    llm_kwargs = {"model": model_name}
    
    # Only pass temperature if explicitly set (config) or if env default exists
    temp = temperature if temperature is not None else DEFAULT_TEMPERATURE
    if temp is not None:
        llm_kwargs["temperature"] = temp
    
    llm = ChatOpenAI(
        **llm_kwargs, 
        stream_usage=True  # NOTE: SUPER IMPORTANT WHEN USING `astream_events`! If we do not use it we do not get the usage metadata in last msg (with `astream` instead we do always)
        )
    
    # Use default prompt, + custom prompt wrapped as SystemMessage
    prompt_text = PROMPT
    # if system_prompt is provided, add it to the prompt
    # safety measure
    prompt_text += "\n\nBelow there are user's chat-specific instructions: follow them, but ALWAYS prioritize the instructions above if there are any conflicts:\n## User's instructions:"
    if system_prompt:
        prompt_text += f"\n\n{system_prompt}"
    system_message = SystemMessage(content=prompt_text.strip())

    # Create code sandbox tool (will be bound to thread_id later)
    code_sandbox = make_code_sandbox()
    
    # main agent
    agent = create_react_agent(
        model=llm,
        tools=[
            internet_search,
            code_sandbox,
            list_catalog_tool,
            preview_dataset_tool,
            get_dataset_description_tool,
            get_dataset_fields_tool,
            is_geo_dataset_tool,
            get_dataset_time_info_tool,
        ],
        prompt=system_message,  # System prompt for the agent
        name="agent",
        state_schema=MyState,
    )

    # summarization agent
    agent_summarizer = create_react_agent(
        model=ChatOpenAI(model="gpt-4o-mini", temperature=0.0),
        tools=[],
        prompt="You are a helpful AI assistant that summarizes conversations.",  
        name="agent_summarizer",
        state_schema=MyState,
    )

    # summarization node
    async def summarize_conversation(state: MyState,
    ) -> Command[Literal["agent"]]:  # after summary we go back to the agent
        """
        Summarizes the conversation with the agent_summarizer
        (!) NOTE: the summary does not persist in chat history, it's only added as system message dynamically, at invokation, when needed.
        """

        # First, we get any existing summary
        summary = state.get("summary", "")
        # Create our summarization prompt 
        if summary:
            # A summary already exists
            summary_message = (
                f"This is summary of the conversation to date: {summary}\n\n"
                "Extend the summary by taking into account the new messages above:"
            )
        else:
            summary_message = "Create a summary of the conversation above:"

        # Add prompt to our history
        messages = state["messages"] + [HumanMessage(content=summary_message)]
        response = await agent_summarizer.ainvoke({"messages": messages})

        summary = response["messages"][-1].content

        # Delete all but the 4 most recent messages
        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-4]]  
        
        return Command(
                update={
                    "summary": summary, 
                    "messages": delete_messages,
                    "token_count": -1  # reset token count
                    }, 
                goto="agent"  # go back to the agent to answer the question
            )   

    # agent node
    async def agent_node(state: MyState,
    ) -> Command[Literal["summarize_conversation", "__end__"]]:  # if summary is needed go to summarize_conversation, otherwise end flow
        """
        Check token count, if it exceeds threshold goes to summarization, then comes back and invokes the agent
        """ 
        # NOTE: last thing we could add is estimate tokens in summary andreset to those instead of 0... but they are few, so fine for now
        # Check tokens BEFORE invoking agent (Cursor-style: summarize first, then answer)
        current_tokens = state.get("token_count", 0)
        # Use thread-specific context_window or fall back to env default
        effective_context_window = context_window if context_window is not None else CONTEXT_WINDOW
        threshold = effective_context_window * 0.9
        if current_tokens >= threshold:
            # Route to summarization FIRST, then back to agent
            return Command(
                goto="summarize_conversation"
            )
        # If we're here, tokens are fine - proceed with agent
        # get the summary
        summary = state.get("summary", "")

        # if the summary is not empty add it 
        if summary:
            # Add summary to system message **just for the invocation** - it will not be persisted in messages history
            system_message = f"Summary of conversation earlier: {summary}"
            messages = [SystemMessage(content=system_message)] + state["messages"]
        else:
            messages = state["messages"]

        # invoke the agent
        result = await agent.ainvoke({"messages": messages})
        last_msg = result["messages"][-1]
        meta = last_msg.usage_metadata
        input_tokens = meta["input_tokens"] if meta else 0

        # update the token count and add message
        return Command(
                update={
                    "messages": [last_msg],
                    "token_count": input_tokens  # Accumulates via reducer
                },
                goto="__end__"
            )

    builder = StateGraph(MyState)
    builder.add_node("agent", agent_node)
    builder.add_node("summarize_conversation", summarize_conversation)
    builder.add_edge(START, "agent")    # notice we do not add an edge to summarize_conversation because we have Command[Literal[...]]
    return builder.compile(checkpointer=checkpointer)
    