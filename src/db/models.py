from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SessionRecord(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    requests: Mapped[list["RequestRecord"]] = relationship(back_populates="session")
    messages: Mapped[list["MessageRecord"]] = relationship(back_populates="session")
    usages: Mapped[list["UsageRecord"]] = relationship(back_populates="session")


class RequestRecord(Base):
    __tablename__ = "requests"

    request_id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["SessionRecord"] = relationship(back_populates="requests")
    messages: Mapped[list["MessageRecord"]] = relationship(back_populates="request")
    usages: Mapped[list["UsageRecord"]] = relationship(back_populates="request")


class MessageRecord(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    request_id: Mapped[str] = mapped_column(
        ForeignKey("requests.request_id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["SessionRecord"] = relationship(back_populates="messages")
    request: Mapped["RequestRecord"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_messages_session_created", "session_id", "created_at"),
        Index("idx_messages_request_id", "request_id"),
    )


class UsageRecord(Base):
    __tablename__ = "usages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(
        ForeignKey("requests.request_id", ondelete="CASCADE"),
        nullable=False,
    )
    response_id: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.session_id", ondelete="CASCADE"),
        nullable=False,
    )
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    session: Mapped["SessionRecord"] = relationship(back_populates="usages")
    request: Mapped["RequestRecord"] = relationship(back_populates="usages")

    __table_args__ = (
        Index("idx_usages_session_created", "session_id", "created_at"),
        Index("idx_usages_request_id", "request_id"),
    )
