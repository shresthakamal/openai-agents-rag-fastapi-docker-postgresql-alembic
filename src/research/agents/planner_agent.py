from agents import Agent
from pydantic import BaseModel

from prompts.loader import RESEARCH_PLANNER_SYSTEM


class WebSearchItem(BaseModel):
    reason: str
    "Your reasoning for why this search is important to the query."

    query: str
    "The search term to use for the web search."


class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem]
    """A list of web searches to perform to best answer the query."""


planner_agent = Agent(
    model="gpt-4.1-nano",
    name="Planner Agent",
    instructions=RESEARCH_PLANNER_SYSTEM,
    output_type=WebSearchPlan,
)
