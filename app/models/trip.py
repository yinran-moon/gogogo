from sqlalchemy import Column, String, JSON, DateTime, Integer
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from app.core.database import Base


class TripORM(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True)
    session_id = Column(String, index=True, nullable=False)
    destination = Column(String, default="")
    days = Column(Integer, default=1)
    itinerary = Column(JSON, default=list)
    total_budget = Column(String, default="")
    status = Column(String, default="draft")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class DayPlan(BaseModel):
    day: int
    date: str = ""
    activities: list[dict] = Field(default_factory=list)
    meals: list[dict] = Field(default_factory=list)
    transport: list[dict] = Field(default_factory=list)
    estimated_cost: float = 0
    notes: str = ""


class TripPlan(BaseModel):
    destination: str = ""
    days: int = 1
    daily_plans: list[DayPlan] = Field(default_factory=list)
    total_budget: float = 0
    tips: list[str] = Field(default_factory=list)
