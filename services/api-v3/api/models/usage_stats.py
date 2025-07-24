from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, func


class UsageStats(BaseModel):
    id: int
    user_id: int
    action: str
    timestamp: datetime
