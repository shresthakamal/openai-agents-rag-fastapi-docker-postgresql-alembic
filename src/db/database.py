import uuid
from typing import Annotated, Any, ClassVar

from fastapi import Depends
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from api.schemas import AgentRequest
from config import settings
from utils.logging import get_logger

from .agent_session import AgentSession
from .models import MessageRecord, RequestRecord, SessionRecord, UsageRecord

logger = get_logger(__name__)


class Database:
    _instance: ClassVar["Database | None"] = None

    def __new__(cls) -> "Database":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._engine = None
            instance._session_factory: async_sessionmaker[AsyncSession] | None = None
            cls._instance = instance
        return cls._instance

    @property
    def engine(self) -> AsyncEngine:
        if self._engine is None:
            raise RuntimeError(
                "Database engine is not initialized. Call init_db() during app startup."
            )
        return self._engine

    def build_database_url(self, *, hide_password: bool = False) -> str:
        return settings.build_database_url(hide_password=hide_password)

    async def init(self) -> None:
        if self._engine is not None:
            return

        self._engine = create_async_engine(self.build_database_url())
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

        logger.info("[agents_db] [init] : Database engine initialized")

    async def close(self) -> None:
        if self._engine is None:
            return

        await self._engine.dispose()
        self._engine = None
        self._session_factory = None
        logger.info("[agents_db] [close] : Database closed")

    async def ensure_session(self, session_id: str) -> None:
        assert self._session_factory is not None

        async with self._session_factory() as db_session:
            async with db_session.begin():
                existing = await db_session.execute(
                    select(SessionRecord.session_id).where(SessionRecord.session_id == session_id)
                )
                if existing.scalar_one_or_none() is None:
                    await db_session.execute(insert(SessionRecord).values(session_id=session_id))

    async def create_request(self, session_id: str, request_id: str) -> None:
        assert self._session_factory is not None

        async with self._session_factory() as db_session:
            async with db_session.begin():
                await db_session.execute(
                    insert(RequestRecord).values(
                        request_id=request_id,
                        session_id=session_id,
                    )
                )

    def create_agent_session(self, session_id: str, request_id: str) -> AgentSession:
        assert self._session_factory is not None

        return AgentSession(
            session_id=session_id,
            request_id=request_id,
            session_factory=self._session_factory,
        )

    async def record_usage(
        self,
        *,
        request_id: str,
        response_id: str,
        session_id: str,
        usage: dict[str, Any],
    ) -> None:
        if not usage or self._session_factory is None:
            return

        async with self._session_factory() as db_session:
            async with db_session.begin():
                await db_session.execute(
                    insert(UsageRecord).values(
                        request_id=request_id,
                        response_id=response_id,
                        session_id=session_id,
                        input_tokens=usage.get("input_tokens", 0),
                        output_tokens=usage.get("output_tokens", 0),
                        total_tokens=usage.get("total_tokens", 0),
                    )
                )

        logger.info(
            f"[agents_db] [record_usage] : session={session_id} request={request_id} "
            f"response={response_id} tokens={usage.get('total_tokens', 0)}"
        )

    async def get_session_usage(self, session_id: str) -> dict[str, int]:
        if self._session_factory is None:
            return {
                "run_count": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            }

        async with self._session_factory() as db_session:
            result = await db_session.execute(
                select(
                    func.count(UsageRecord.id),
                    func.coalesce(func.sum(UsageRecord.input_tokens), 0),
                    func.coalesce(func.sum(UsageRecord.output_tokens), 0),
                    func.coalesce(func.sum(UsageRecord.total_tokens), 0),
                ).where(UsageRecord.session_id == session_id)
            )
            run_count, input_tokens, output_tokens, total_tokens = result.one()

        return {
            "run_count": int(run_count),
            "input_tokens": int(input_tokens),
            "output_tokens": int(output_tokens),
            "total_tokens": int(total_tokens),
        }

    async def get_session_messages(
        self, session_id: str, limit: int | None = None
    ) -> list[dict[str, Any]]:
        if self._session_factory is None:
            return []

        async with self._session_factory() as db_session:
            stmt = (
                select(
                    MessageRecord.message_id,
                    MessageRecord.session_id,
                    MessageRecord.request_id,
                    MessageRecord.content,
                    MessageRecord.role,
                    MessageRecord.status,
                    MessageRecord.created_at,
                )
                .where(MessageRecord.session_id == session_id)
                .order_by(MessageRecord.created_at.asc(), MessageRecord.id.asc())
            )
            if limit is not None:
                stmt = (
                    select(
                        MessageRecord.message_id,
                        MessageRecord.session_id,
                        MessageRecord.request_id,
                        MessageRecord.content,
                        MessageRecord.role,
                        MessageRecord.status,
                        MessageRecord.created_at,
                    )
                    .where(MessageRecord.session_id == session_id)
                    .order_by(MessageRecord.created_at.desc(), MessageRecord.id.desc())
                    .limit(limit)
                )

            result = await db_session.execute(stmt)
            rows = result.all()

        if limit is not None:
            rows = list(reversed(rows))

        return [
            {
                "message_id": message_id,
                "session_id": row_session_id,
                "request_id": request_id,
                "content": content,
                "role": role,
                "status": status,
                "created_at": created_at.isoformat(),
            }
            for message_id, row_session_id, request_id, content, role, status, created_at in rows
        ]

    def session_info(self) -> dict[str, object]:
        return {
            "backend": "postgresql",
            "database_url": self.build_database_url(hide_password=True),
            "postgres_host": settings.postgres_host,
            "postgres_port": settings.postgres_port,
            "postgres_db": settings.postgres_db,
            "auto_create_session_id": True,
            "auto_create_request_id": True,
            "usage_tracking": True,
            "tables": ["sessions", "requests", "messages", "usages"],
        }


agents_db = Database()


async def init_db() -> None:
    await agents_db.init()


async def close_db() -> None:
    await agents_db.close()


async def get_agent_session(request: AgentRequest) -> AgentSession:
    session_id = request.session_id or str(uuid.uuid4())
    request_id = str(uuid.uuid4())

    await agents_db.ensure_session(session_id)
    await agents_db.create_request(session_id, request_id)

    logger.info(f"[agents_db] [get_agent_session] : session={session_id} request={request_id}")

    return agents_db.create_agent_session(session_id, request_id)


async def get_session_by_id(session_id: str) -> AgentSession:
    request_id = str(uuid.uuid4())
    await agents_db.ensure_session(session_id)
    await agents_db.create_request(session_id, request_id)
    return agents_db.create_agent_session(session_id, request_id)


AgentSessionDep = Annotated[AgentSession, Depends(get_agent_session)]
SessionByIdDep = Annotated[AgentSession, Depends(get_session_by_id)]


def get_agent_session_info() -> dict[str, object]:
    return agents_db.session_info()
