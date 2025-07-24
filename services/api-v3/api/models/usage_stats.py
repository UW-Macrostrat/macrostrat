from sqlalchemy import Column, Integer, String, DateTime, func
from pydantic import BaseModel

class UsageStats(BaseModel):
    id: int
    user_id: int
    action: str
    timestamp: datetime
