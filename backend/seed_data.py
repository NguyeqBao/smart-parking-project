from database import SessionLocal
from models import Node, ParkingSlot

db = SessionLocal()

node = Node(node_name="ESP32-A", location_desc="Khu A", status="online")
db.add(node)
db.commit()
db.refresh(node)

slot1 = ParkingSlot(node_id=node.id, slot_code="A1", is_occupied=False)
slot2 = ParkingSlot(node_id=node.id, slot_code="A2", is_occupied=True)
db.add(slot1)
db.add(slot2)
db.commit()

print("Da them du lieu mau!")
db.close()