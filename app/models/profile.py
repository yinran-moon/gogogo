from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from app.core.database import Base


class ProfileORM(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True)
    session_id = Column(String, index=True, nullable=False)
    travel_style = Column(String, default="")
    budget_level = Column(String, default="")
    companions = Column(String, default="")
    physical_level = Column(String, default="")
    interests = Column(JSON, default=list)
    constraints = Column(JSON, default=dict)
    travel_dates = Column(JSON, default=dict)
    destination_pref = Column(JSON, default=dict)
    raw_summary = Column(String, default="")
    is_complete = Column(String, default="false")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class TravelerProfile(BaseModel):
    travel_style: str = Field(default="", description="慢旅行/打卡型/探险型/文艺型")
    budget_level: str = Field(default="", description="穷游/舒适/轻奢/不设限")
    companions: str = Field(default="", description="独行/情侣/亲子/朋友团")
    physical_level: str = Field(default="", description="轻松为主/适度运动/户外硬核")
    interests: list[str] = Field(default_factory=list, description="兴趣标签")
    constraints: dict = Field(default_factory=dict, description="特殊约束")
    travel_dates: dict = Field(default_factory=dict, description="出行日期")
    destination_pref: dict = Field(default_factory=dict, description="目的地偏好")
    is_complete: bool = Field(default=False, description="画像是否采集完成")
