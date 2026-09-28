#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include "config.h"

const int NUM_SLOTS = 2;
const char *SLOT_CODES[NUM_SLOTS] = {"A3", "A4"};
const int SENSOR_PINS[NUM_SLOTS] = {14, 27};
const char *NODE_ID = "ESP32-B";

int currentStatus[NUM_SLOTS];
int stableCount[NUM_SLOTS];
const int REQUIRED_COUNT = 5;

char statusTopics[NUM_SLOTS][64];
char nodeLwtTopic[64];

WiFiClientSecure espClient;
PubSubClient client(espClient);

const char *NTP_SERVER = "pool.ntp.org";
const long GMT_OFFSET_SEC = 7 * 3600;
const int DAYLIGHT_OFFSET_SEC = 0;

void setup_wifi()
{
    delay(10);
    Serial.println();
    Serial.print("Connecting to WiFi: ");
    Serial.println(WIFI_SSID);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print("-");
    }
    Serial.println("\nWiFi connected successfully!");
}

void setup_time()
{
    configTime(GMT_OFFSET_SEC, DAYLIGHT_OFFSET_SEC, NTP_SERVER);
    Serial.print("Syncing time");
    time_t now = time(nullptr);
    while (now < 100000)
    {
        delay(500);
        Serial.print(".");
        now = time(nullptr);
    }
    Serial.println("\nTime synced!");
}

String getIsoTimestamp()
{
    time_t now = time(nullptr);
    struct tm timeinfo;
    gmtime_r(&now, &timeinfo);
    char buf[30];
    strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
    return String(buf);
}

void reconnect()
{
    while (!client.connected())
    {
        Serial.print("Attempting MQTT connection...");
        String clientId = String(NODE_ID) + "-" + String(random(0, 1000));

        const char *willPayload = "{\"status\":\"offline\"}";

        if (client.connect(clientId.c_str(), MQTT_USER, MQTT_PASS,
                           nodeLwtTopic, 1, true, willPayload))
        {
            Serial.println(" Connected to MQTT!");
            client.publish(nodeLwtTopic, "{\"status\":\"online\"}", true);
        }
        else
        {
            Serial.print(" Failed, rc=");
            Serial.print(client.state());
            Serial.println(" Trying again in 5 seconds");
            delay(5000);
        }
    }
}

bool isValidReading(int reading)
{
    return (reading == HIGH || reading == LOW);
}

bool readSensorDebounced(int index)
{
    int reading = digitalRead(SENSOR_PINS[index]);

    if (!isValidReading(reading))
    {
        return false;
    }

    if (reading != currentStatus[index])
    {
        stableCount[index]++;
        if (stableCount[index] >= REQUIRED_COUNT)
        {
            currentStatus[index] = reading;
            stableCount[index] = 0;
            return true;
        }
    }
    else
    {
        stableCount[index] = 0;
    }
    return false;
}

void publishSlotStatus(int index)
{
    bool occupied = (currentStatus[index] == LOW);

    StaticJsonDocument<160> doc;
    doc["occupied"] = occupied;
    doc["timestamp"] = getIsoTimestamp();

    char buffer[160];
    serializeJson(doc, buffer);

    client.publish(statusTopics[index], buffer, true);

    Serial.print(SLOT_CODES[index]);
    Serial.print(occupied ? " Car detected -> " : " Spot available -> ");
    Serial.println(buffer);
}

void setup()
{
    Serial.begin(115200);

    for (int i = 0; i < NUM_SLOTS; i++)
    {
        pinMode(SENSOR_PINS[i], INPUT);
        currentStatus[i] = HIGH;
        stableCount[i] = 0;
        snprintf(statusTopics[i], sizeof(statusTopics[i]),
                 "parking/%s/%s/status", LOT_ID, SLOT_CODES[i]);
    }
    snprintf(nodeLwtTopic, sizeof(nodeLwtTopic), "parking/%s/%s/lwt", LOT_ID, NODE_ID);

    setup_wifi();
    setup_time();

    espClient.setInsecure();
    client.setServer(MQTT_SERVER, MQTT_PORT);
}

void loop()
{
    if (WiFi.status() != WL_CONNECTED)
    {
        Serial.println("WiFi mat ket noi, dang thu lai...");
        setup_wifi();
    }

    if (!client.connected())
    {
        reconnect();
    }
    client.loop();

    for (int i = 0; i < NUM_SLOTS; i++)
    {
        if (readSensorDebounced(i))
        {
            publishSlotStatus(i);
        }
    }

    delay(50);
}
