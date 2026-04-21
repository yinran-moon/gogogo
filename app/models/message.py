from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Literal
from app.core.database import Base


class MessageORM(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    msg_type = Column(String, default="text")
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, server_default=func.now())


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str = ""
    msg_type: str = Field(default="text", description="text/card/timeline/map")
    metadata: dict = Field(default_factory=dict)
