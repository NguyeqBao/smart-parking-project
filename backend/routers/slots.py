from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import ParkingSlot
from schemas import SlotResponse
from typing import List

router = APIRouter(prefix="/api", tags=["slots"])

@router.get("/slots", response_model=List[SlotResponse])
def get_all_slots(db: Session = Depends(get_db)):
    return db.query(ParkingSlot).all()
