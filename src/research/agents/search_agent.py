from agents import Agent, WebSearchTool
from agents.model_settings import ModelSettings

from prompts.loader import RESEARCH_SEARCH_SYSTEM

search_agent = Agent(
    name="Search agent",
    instructions=RESEARCH_SEARCH_SYSTEM,
    tools=[WebSearchTool()],
    model_settings=ModelSettings(tool_choice="required"),
)
