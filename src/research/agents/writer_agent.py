from agents import Agent
from pydantic import BaseModel

from prompts.loader import RESEARCH_WRITER_SYSTEM


class ReportData(BaseModel):
    short_summary: str
    """A short 2-3 sentence summary of the findings."""

    markdown_report: str
    """The final report"""

    follow_up_questions: list[str]
    """Suggested topics to research further"""


writer_agent = Agent(
    model="gpt-4.1-nano",
    name="Writer agent",
    instructions=RESEARCH_WRITER_SYSTEM,
    output_type=ReportData,
)
