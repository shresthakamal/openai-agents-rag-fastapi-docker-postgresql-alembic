from api.routers.agent_router import create_agent_router
from chat.main import chat_agent
from db import get_agent_session, get_agent_session_info, get_session_by_id

router = create_agent_router(
    agent=chat_agent,
    prefix="/chat",
    agent_name=chat_agent.name,
    agent_session_dep=get_agent_session,
    session_by_id_dep=get_session_by_id,
    session_info_provider=get_agent_session_info,
)
