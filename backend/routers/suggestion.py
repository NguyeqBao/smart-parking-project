from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import ParkingSlot
from typing import Optional

router = APIRouter(prefix="/api", tags=["suggestion"])

ZONE_PRIORITY = {"A": 1, "B": 2, "C": 3}

def calculate_score(slot: ParkingSlot) -> float:
    zone = slot.slot_code[0] if slot.slot_code else "Z"
    zone_score = ZONE_PRIORITY.get(zone, 99) * 10

    try:
        position_score = int(slot.slot_code[1:]) 
    except ValueError:
        position_score = 99 
        
    return zone_score + position_score


@router.get("/suggest")
def suggest_parking_slot(db: Session = Depends(get_db)):
    available_slots = db.query(ParkingSlot).filter(
        ParkingSlot.is_occupied == False,
        ParkingSlot.is_reserved == False
    ).all()

    if not available_slots:
        return {"message": "Khong con cho trong", "suggested_slot": None, "all_ranked": []}

    ranked_slots = sorted(available_slots, key=calculate_score)

    return {
        "suggested_slot": ranked_slots[0].slot_code,
        "all_ranked": [
            {"slot_code": s.slot_code, "score": calculate_score(s)}
            for s in ranked_slots
        ]
    }