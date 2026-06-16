import json
import uuid
from typing import Any

from agents.items import TResponseInputItem
from agents.memory.session import SessionABC
from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .models import MessageRecord, SessionRecord


def _item_to_dict(item: TResponseInputItem) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump()
    if hasattr(item, "__dict__"):
        return dict(item.__dict__)
    return {"content": str(item)}


class AgentSession(SessionABC):
    def __init__(
        self,
        *,
        session_id: str,
        request_id: str,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self.session_id = session_id
        self.request_id = request_id
        self._session_factory = session_factory

    async def get_items(self, limit: int | None = None) -> list[TResponseInputItem]:
        async with self._session_factory() as db_session:
            stmt = (
                select(MessageRecord.content)
                .where(MessageRecord.session_id == self.session_id)
                .order_by(MessageRecord.created_at.asc(), MessageRecord.id.asc())
            )
            if limit is not None:
                stmt = (
                    select(MessageRecord.content)
                    .where(MessageRecord.session_id == self.session_id)
                    .order_by(MessageRecord.created_at.desc(), MessageRecord.id.desc())
                    .limit(limit)
                )

            result = await db_session.execute(stmt)
            rows = [row[0] for row in result.all()]

            if limit is not None:
                rows.reverse()

        items: list[TResponseInputItem] = []
        for raw in rows:
            try:
                items.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
        return items

    async def add_items(self, items: list[TResponseInputItem]) -> None:
        if not items:
            return

        payload = []
        for item in items:
            item_dict = _item_to_dict(item)
            payload.append(
                {
                    "message_id": str(item_dict.get("id") or uuid.uuid4()),
                    "session_id": self.session_id,
                    "request_id": self.request_id,
                    "content": json.dumps(item_dict, separators=(",", ":")),
                    "role": item_dict.get("role"),
                    "status": item_dict.get("status"),
                }
            )

        async with self._session_factory() as db_session:
            async with db_session.begin():
                await db_session.execute(insert(MessageRecord), payload)
                await db_session.execute(
                    update(SessionRecord)
                    .where(SessionRecord.session_id == self.session_id)
                    .values(updated_at=func.now())
                )

    async def pop_item(self) -> TResponseInputItem | None:
        async with self._session_factory() as db_session:
            async with db_session.begin():
                stmt = (
                    select(MessageRecord.id, MessageRecord.content)
                    .where(MessageRecord.session_id == self.session_id)
                    .order_by(MessageRecord.created_at.desc(), MessageRecord.id.desc())
                    .limit(1)
                )
                result = await db_session.execute(stmt)
                row = result.first()
                if row is None:
                    return None

                message_id, content = row
                await db_session.execute(
                    delete(MessageRecord).where(MessageRecord.id == message_id)
                )

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None

    async def clear_session(self) -> None:
        async with self._session_factory() as db_session:
            async with db_session.begin():
                await db_session.execute(
                    delete(MessageRecord).where(MessageRecord.session_id == self.session_id)
                )
