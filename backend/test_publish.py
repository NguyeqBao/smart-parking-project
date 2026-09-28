import os
import ssl
import time
import threading

import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

connected = threading.Event()


def on_connect(client, userdata, flags, rc):
    print(f"MQTT publisher connect rc={rc}")
    if rc == 0:
        connected.set()


broker = os.getenv("MQTT_BROKER_URL")
port = int(os.getenv("MQTT_PORT", "8883"))
username = os.getenv("MQTT_USER")
password = os.getenv("MQTT_PASSWORD")

client = mqtt.Client()
client.username_pw_set(username, password)
client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
client.on_connect = on_connect

print(f"Broker: {broker}:{port}")
print("Dang ket noi MQTT...")

client.connect(broker, port, 60)
client.loop_start()

if not connected.wait(timeout=10):
    print("LOI: Khong ket noi duoc MQTT")
    client.loop_stop()
    raise SystemExit(1)

topic = "parking/lot1/A1/status"
payload = '{"occupied":true}'

info = client.publish(topic, payload, qos=1)
info.wait_for_publish()

print(f"Da gui: {topic} -> {payload}")

time.sleep(2)
client.loop_stop()
client.disconnect()