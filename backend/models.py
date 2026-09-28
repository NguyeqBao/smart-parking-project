from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base

class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True, index=True)
    node_name = Column(String, unique=True)
    location_desc = Column(String)
    status = Column(String, default="offline")
    last_seen = Column(DateTime(timezone=True), onupdate=func.now())

class ParkingSlot(Base):
    __tablename__ = "parking_slots"
    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"))
    slot_code = Column(String, unique=True)
    is_occupied = Column(Boolean, default=False)
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    is_reserved = Column(Boolean, default=False)
    
class UsageHistory(Base):
    __tablename__ = "usage_history"
    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(Integer, ForeignKey("parking_slots.id"))
    event_type = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(Integer, ForeignKey("parking_slots.id"))
    user_name = Column(String)
    reserved_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    status = Column(String, default="pending")
