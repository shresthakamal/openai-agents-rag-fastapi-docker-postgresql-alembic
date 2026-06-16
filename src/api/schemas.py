from typing import Any, Optional

from agents import TResponseInputItem
from pydantic import BaseModel


class AgentRequest(BaseModel):
    input: str | list[TResponseInputItem]
    context: Optional[dict[str, Any]] = None
    session_id: Optional[str] = None
