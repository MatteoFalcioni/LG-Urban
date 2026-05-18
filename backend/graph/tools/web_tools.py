import os

from langchain_core.tools import tool
from tavily import TavilyClient

# ---------- Internet Search Tool ----------


@tool
def internet_search(query):
    """Search the internet for information. Be as secific as you can in your query."""
    tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    return tavily_client.search(query)
