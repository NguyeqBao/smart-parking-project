from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SlotBase(BaseModel):
    slot_code: str
    is_occupied: bool

class SlotResponse(SlotBase):
    id: int
    node_id: int
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True

class NodeResponse(BaseModel):
    id: int
    node_name: str
    location_desc: Optional[str] = None
    status: str
    last_seen: Optional[datetime] = None

    class Config:
        from_attributes = True

class ReservationCreate(BaseModel):
    slot_id: int
    user_name: str

class ReservationResponse(BaseModel):
    id: int
    slot_id: int
    user_name: str
    reserved_at: datetime
    expires_at: datetime
    status: str

    class Config:
        from_attributes = True
