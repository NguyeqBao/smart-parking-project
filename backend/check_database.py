from database import SessionLocal
from models import ParkingSlot

db = SessionLocal()

try:
    slots = db.query(ParkingSlot).all()

    print(f"So luong slot: {len(slots)}")

    for slot in slots:
        print(slot.__dict__)

except Exception as error:
    print("Loi ket noi database:")
    print(error)

finally:
    db.close()