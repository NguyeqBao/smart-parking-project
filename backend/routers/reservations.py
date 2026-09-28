from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import get_db
from models import ParkingSlot, Reservation
from schemas import ReservationCreate, ReservationResponse
from typing import List

router = APIRouter(prefix="/api", tags=["reservations"])

RESERVATION_TIMEOUT_MINUTES = 1

@router.post("/reservation", response_model=ReservationResponse)
def create_reservation(data: ReservationCreate, db: Session = Depends(get_db)):
    slot = db.query(ParkingSlot).filter(ParkingSlot.id == data.slot_id).first()

    if not slot:
        raise HTTPException(status_code=404, detail="Slot not found")

    if slot.is_occupied:
        raise HTTPException(status_code=400, detail="Slot is currently occupied")

    db.query(Reservation).filter(
        Reservation.slot_id == data.slot_id,
        Reservation.status == "pending"
    ).update({"status": "cancelled"})

    reservation = Reservation(
        slot_id=data.slot_id,
        user_name=data.user_name,
        reserved_at=datetime.now(),
        expires_at=datetime.now() + timedelta(minutes=RESERVATION_TIMEOUT_MINUTES),
        status="pending"
    )

    slot.is_reserved = True

    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation

@router.get("/reservations", response_model=List[ReservationResponse])
def get_all_reservations(db: Session = Depends(get_db)):
    return db.query(Reservation).all()

@router.delete("/reservation/{reservation_id}")
def cancel_reservation(reservation_id: int, db: Session = Depends(get_db)):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
        
    reservation.status = "cancelled"
    
    slot = db.query(ParkingSlot).filter(ParkingSlot.id == reservation.slot_id).first()
    if slot:
        slot.is_reserved = False

    db.commit()
    return {"message": "Reservation cancelled"}