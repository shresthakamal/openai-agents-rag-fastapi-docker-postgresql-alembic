"""Prompt loader for Akin Chat agents.

Loads prompt templates from .md files under src/prompts/.
"""

from config import settings


def _load(name: str) -> str:
    path = settings.prompts_dir / name
    if not path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {path}. " "Add it under src/prompts/ or fix the filename."
        )
    return path.read_text(encoding="utf-8").strip()


ASSISTANT_SYSTEM = _load("assistant_system.md")
CHAT_SYSTEM = _load("chat_system.md")
RESEARCH_PLANNER_SYSTEM = _load("research_planner_system.md")
RESEARCH_SEARCH_SYSTEM = _load("research_search_system.md")
RESEARCH_WRITER_SYSTEM = _load("research_writer_system.md")
