from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
class Base(DeclarativeBase): pass
class Conversation(Base):
    __tablename__="conversations"
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    title: Mapped[str]=mapped_column(String(200),default="New analysis")
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
class Message(Base):
    __tablename__="messages"
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    conversation_id: Mapped[str]=mapped_column(String(36),ForeignKey("conversations.id",ondelete="CASCADE"),index=True)
    role: Mapped[str]=mapped_column(String(20))
    content: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),nullable=False)
