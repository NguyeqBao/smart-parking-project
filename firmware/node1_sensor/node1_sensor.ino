#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <time.h>
#include "config.h"

const int NUM_SLOTS = 2;
const char *SLOT_CODES[NUM_SLOTS] = {"A1", "A2"};
const int SENSOR_PINS[NUM_SLOTS] = {14, 27};
const char *NODE_ID = "ESP32-A";

const int ENTRANCE_PIN = 15;
const char *GATE_ID = "gate1";

LiquidCrystal_I2C lcd(0x27, 16, 2);

int currentStatus[NUM_SLOTS];
int stableCount[NUM_SLOTS];
const int REQUIRED_COUNT = 5;

int entranceStatus = HIGH;
int entranceStableCount = 0;

bool lcdBusy = false;
unsigned long lcdBusyUntil = 0;
unsigned long lastClockUpdate = 0;
String lastDisplayedTime = "";

char statusTopics[NUM_SLOTS][64];
char nodeLwtTopic[64];
char gateEntryTopic[64];

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

String getDisplayTime()
{
    time_t now = time(nullptr);
    struct tm timeinfo;
    localtime_r(&now, &timeinfo);
    char buf[20];
    strftime(buf, sizeof(buf), "%H:%M:%S %d/%m", &timeinfo);
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

bool readEntranceDebounced()
{
    int reading = digitalRead(ENTRANCE_PIN);

    if (!isValidReading(reading))
    {
        return false;
    }

    if (reading != entranceStatus)
    {
        entranceStableCount++;
        if (entranceStableCount >= REQUIRED_COUNT)
        {
            entranceStatus = reading;
            entranceStableCount = 0;
            return true;
        }
    }
    else
    {
        entranceStableCount = 0;
    }
    return false;
}

void showLcdMessage(String line1, String line2)
{
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print(line1);
    lcd.setCursor(0, 1);
    lcd.print(line2);
}

void updateClockDisplay()
{
    if (lcdBusy)
    {
        if (millis() < lcdBusyUntil)
        {
            return;
        }
        lcdBusy = false;
        lastDisplayedTime = "";
    }

    if (millis() - lastClockUpdate < 1000)
    {
        return;
    }
    lastClockUpdate = millis();

    String currentTime = getDisplayTime();
    if (currentTime != lastDisplayedTime)
    {
        lastDisplayedTime = currentTime;
        lcd.setCursor(0, 0);
        lcd.print("San sang       ");
        lcd.setCursor(0, 1);
        lcd.print(currentTime);
        lcd.print("   ");
    }
}

void showTemporaryMessage(String line1, String line2, unsigned long durationMs)
{
    showLcdMessage(line1, line2);
    lcdBusy = true;
    lcdBusyUntil = millis() + durationMs;
}

void fetchAndShowSuggestion()
{
    if (WiFi.status() != WL_CONNECTED)
    {
        showTemporaryMessage("Loi WiFi", "Khong the goi y", 5000);
        return;
    }

    HTTPClient http;
    String url = String(BACKEND_URL) + "/api/suggest";
    http.begin(url);
    int httpCode = http.GET();

    if (httpCode == 200)
    {
        String payload = http.getString();

        StaticJsonDocument<512> doc;
        DeserializationError error = deserializeJson(doc, payload);

        if (!error)
        {
            const char *suggested = doc["suggested_slot"];
            if (suggested)
            {
                showTemporaryMessage("Cho trong:", String(suggested), 5000);
                Serial.print("Goi y cho: ");
                Serial.println(suggested);
            }
            else
            {
                showTemporaryMessage("Bai xe da", "het cho!", 5000);
                Serial.println("Khong con cho trong");
            }
        }
        else
        {
            showTemporaryMessage("Loi du lieu", "tu server", 5000);
            Serial.println("Loi parse JSON tu suggestion API");
        }
    }
    else
    {
        showTemporaryMessage("Khong ket noi", "duoc server", 5000);
        Serial.print("HTTP GET that bai, ma loi: ");
        Serial.println(httpCode);
    }

    http.end();
}

void publishGateEntry()
{
    StaticJsonDocument<128> doc;
    doc["event"] = "car_entered";
    doc["timestamp"] = getIsoTimestamp();

    char buffer[128];
    serializeJson(doc, buffer);

    client.publish(gateEntryTopic, buffer);
    Serial.print("Xe vao cong -> ");
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
    snprintf(gateEntryTopic, sizeof(gateEntryTopic), "parking/%s/%s/entry", LOT_ID, GATE_ID);

    pinMode(ENTRANCE_PIN, INPUT);

    Wire.begin();
    lcd.init();
    lcd.backlight();
    showLcdMessage("Khoi dong...", "");

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

    if (readEntranceDebounced() && entranceStatus == LOW)
    {
        publishGateEntry();
        fetchAndShowSuggestion();
    }

    updateClockDisplay();

    delay(50);
}
