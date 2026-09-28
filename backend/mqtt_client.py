import paho.mqtt.client as mqtt
import json
import os
from datetime import datetime
from database import SessionLocal
from models import ParkingSlot, UsageHistory, Node


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Da ket noi toi MQTT broker")
        client.subscribe("parking/+/+/status")
        client.subscribe("parking/+/+/lwt")
        client.subscribe("parking/+/+/entry")
        client.subscribe("parking/+/+/command")
        print("Da subscribe: parking/+/+/status, parking/+/+/lwt, parking/+/+/entry")
    else:
        print(f"Ket noi MQTT that bai, ma loi: {rc}")


SLOT_TO_NODE = {
    "A1": "ESP32-A",
    "A2": "ESP32-A",
    "A3": "ESP32-B",
    "A4": "ESP32-B",
}


def get_or_create_slot(db, slot_code: str) -> ParkingSlot:
    slot = db.query(ParkingSlot).filter(ParkingSlot.slot_code == slot_code).first()
    if slot:
        return slot

    node_name = SLOT_TO_NODE.get(slot_code)
    node = None
    if node_name:
        node = db.query(Node).filter(Node.node_name == node_name).first()
        if not node:
            node = Node(node_name=node_name, status="online")
            db.add(node)
            db.flush()

    slot = ParkingSlot(
        node_id=node.id if node else None,
        slot_code=slot_code,
        is_occupied=False
    )
    db.add(slot)
    db.flush()
    print(f"Tu dong tao moi slot '{slot_code}' (chua tung co trong database)")
    return slot


def handle_status_message(slot_code: str, payload: dict):
    db = SessionLocal()
    try:
        slot = get_or_create_slot(db, slot_code)

        occupied = payload.get("occupied")
        if occupied is None:
            print(f"Canh bao: payload thieu truong 'occupied' cho slot {slot_code}")
            db.rollback()
            return

        slot.is_occupied = occupied
        slot.last_updated = datetime.now()
        if occupied:
            slot.is_reserved = False
            from models import Reservation
            db.query(Reservation).filter(
                Reservation.slot_id == slot.id,
                Reservation.status == "pending"
            ).update({"status": "completed"})
        else:
            slot.is_reserved = False

        db.add(UsageHistory(
            slot_id=slot.id,
            event_type="occupied" if occupied else "vacated"
        ))

        db.commit()
        print(f"Cap nhat slot {slot_code}: occupied={occupied}")

    except Exception as e:
        print(f"Loi khi xu ly status message cho slot {slot_code}: {e}")
        db.rollback()
    finally:
        db.close()


def handle_lwt_message(node_id: str, payload: dict):
    db = SessionLocal()
    try:
        node = db.query(Node).filter(Node.node_name == node_id).first()

        status = payload.get("status")
        if status not in ("online", "offline"):
            print(f"Canh bao: gia tri status khong hop le tu node {node_id}: {payload}")
            return

        if not node:
            node = Node(node_name=node_id, status=status)
            db.add(node)
            print(f"Tao moi node {node_id} voi trang thai {status}")
        else:
            node.status = status
            print(f"Cap nhat node {node_id}: status={status}")

        node.last_seen = datetime.now()
        db.commit()

    except Exception as e:
        print(f"Loi khi xu ly LWT message cho node {node_id}: {e}")
        db.rollback()
    finally:
        db.close()


def handle_gate_entry_message(gate_id: str, payload: dict):
    event = payload.get("event")
    timestamp = payload.get("timestamp")
    print(f"Ghi nhan su kien tai cong {gate_id}: {event} luc {timestamp}")

def handle_command_message(slot_code: str, payload: dict):
    db = SessionLocal()
    try:
        slot = get_or_create_slot(db, slot_code)
        action = payload.get("action")

        if action == "RESERVE":
            slot.is_reserved = True
            print(f"[MQTT] Slot {slot_code} da duoc DAT CHO (is_reserved = True)")
        elif action == "CANCEL_RESERVE":
            slot.is_reserved = False
            print(f"[MQTT] Slot {slot_code} da HUY DAT CHO (is_reserved = False)")

        db.commit()
    except Exception as e:
        print(f"Loi khi xu ly command cho slot {slot_code}: {e}")
        db.rollback()
    finally:
        db.close()
def on_message(client, userdata, msg):
    try:
        topic_parts = msg.topic.split("/")
        if len(topic_parts) != 4:
            print(f"Canh bao: topic khong dung dinh dang: {msg.topic}")
            return

        _, lot_id, identifier, event_type = topic_parts
        payload = json.loads(msg.payload.decode())

        if event_type == "status":
            handle_status_message(identifier, payload)
        elif event_type == "lwt":
            handle_lwt_message(identifier, payload)
        elif event_type == "entry":
            handle_gate_entry_message(identifier, payload)
        elif event_type == "command": 
            handle_command_message(identifier, payload)
        else:
            print(f"Canh bao: khong nhan dien duoc loai event: {event_type}")

    except json.JSONDecodeError:
        print(f"Loi: payload khong phai JSON hop le tu topic {msg.topic}")
    except Exception as e:
        print(f"Loi khong xac dinh khi xu ly message: {e}")


def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Mat ket noi MQTT ngoai y muon, dang thu ket noi lai...")


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect


def start_mqtt():
    broker = os.getenv("MQTT_BROKER_URL")
    port = int(os.getenv("MQTT_PORT", 1883))

    mqtt_user = os.getenv("MQTT_USER")
    mqtt_pass = os.getenv("MQTT_PASSWORD")
    if mqtt_user and mqtt_pass:
        client.username_pw_set(mqtt_user, mqtt_pass)

    if port == 8883:
        client.tls_set()

    client.connect(broker, port, keepalive=60)
    client.loop_start()
    print(f"MQTT client da khoi dong, ket noi toi {broker}:{port}")
    
    def handle_status_message(slot_code: str, payload: dict):
        db = SessionLocal()
        try:
            slot = get_or_create_slot(db, slot_code)

            occupied = payload.get("occupied")
            if occupied is None:
                print(f"Canh bao: payload thieu truong 'occupied' cho slot {slot_code}")
                db.rollback()
                return

            slot.is_occupied = occupied
            slot.last_updated = datetime.now()

            if occupied:
                slot.is_reserved = False
                from models import Reservation
                db.query(Reservation).filter(
                    Reservation.slot_id == slot.id,
                    Reservation.status == "pending"
                ).update({"status": "completed"})
            # -----------------------------------------

            db.add(UsageHistory(
                slot_id=slot.id,
                event_type="occupied" if occupied else "vacated"
            ))

            db.commit()
            print(f"Cap nhat slot {slot_code}: occupied={occupied}")

        except Exception as e:
            print(f"Loi khi xu ly status message cho slot {slot_code}: {e}")
            db.rollback()
        finally:
            db.close()