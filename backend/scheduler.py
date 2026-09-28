from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from database import SessionLocal
from models import Reservation, ParkingSlot

def expire_reservations():
    db = SessionLocal()
    try:
        expired = db.query(Reservation).filter(
            Reservation.expires_at < datetime.now(),
            Reservation.status == "pending"
        ).all()
        for r in expired:
            r.status = "expired"
            slot = db.query(ParkingSlot).filter(ParkingSlot.id == r.slot_id).first()
            if slot:
                slot.is_reserved = False
        db.commit()
        if expired:
            print(f"Da het han {len(expired)} reservation(s)")
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(expire_reservations, 'interval', seconds=10) 
    scheduler.start()
    print("Scheduler da khoi dong")