from langchain.agents import AgentState
from typing import Annotated

# we add reducers not mainly for conurrency of update, but more to define rules for updates
# we want string updates for summary (if a summary exists, we want to extend it) so no reducers needed
# but we want to count tokens AND reset to 0 after each summary update

def update_token_count(token_count: int | None = None, token_used: int | None = None) -> int:
    """
    Updates the token count
    """
    # init safeguards
    if token_count is None:
        token_count = 0
    if token_used is None:
        token_used = 0
        
    # a value of -1 means reset to 0
    if token_used == -1:
        return 0
    else:
        return token_count + token_used


class MyState(AgentState):
    summary : str   # No reducer - just replace
    token_count : Annotated[int, update_token_count]