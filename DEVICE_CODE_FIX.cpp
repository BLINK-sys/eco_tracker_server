#define TINY_GSM_MODEM_A7670
#define TINY_GSM_RX_BUFFER 1024

#include <TinyGsmClient.h>
#include "config.h"

#define SerialMon Serial
#define SerialAT  Serial1

// 🧩 Пины для LilyGO T-Call A7670 V1.0
#define MODEM_RX_PIN 25
#define MODEM_TX_PIN 26
#define BOARD_PWRKEY_PIN 4
#define MODEM_RESET_PIN 27
#define MODEM_RESET_LEVEL LOW

TinyGsm modem(SerialAT);

// 🧠 Генерация JSON
String buildJson(int fill1, int fill2) {
  String json = "{";
  json += "\"location_id\":\"" + String(LOCATION_ID) + "\",";
  json += "\"containers\":[";
  json += "{\"container_id\":\"" + String(CONTAINER_1_ID) + "\",\"fill_level\":" + String(fill1) + "},";
  json += "{\"container_id\":\"" + String(CONTAINER_2_ID) + "\",\"fill_level\":" + String(fill2) + "}";
  json += "],";
  json += "\"timestamp\":\"2025-10-27T12:00:00Z\"";
  json += "}";
  return json;
}

// 🔧 Функция для HTTP POST запроса с правильными заголовками
bool sendHttpPost(String jsonData) {
  TinyGsmClient client(modem);
  
  if (!client.connect("eco-tracker-server.onrender.com", 443)) {
    SerialMon.println("❌ Connection failed!");
    return false;
  }
  
  // Формируем HTTP POST запрос вручную
  String postRequest = "POST /api/sensors/location-update HTTP/1.1\r\n";
  postRequest += "Host: eco-tracker-server.onrender.com\r\n";
  postRequest += "Content-Type: application/json\r\n";  // ❗ Важно!
  postRequest += "Content-Length: " + String(jsonData.length()) + "\r\n";
  postRequest += "User-Agent: EcoTracker-Device/1.0\r\n";
  postRequest += "Accept: application/json\r\n";
  postRequest += "Connection: close\r\n";
  postRequest += "\r\n";
  postRequest += jsonData;
  
  SerialMon.println("📤 Sending request:");
  SerialMon.println(postRequest);
  
  client.print(postRequest);
  
  // Читаем ответ
  unsigned long timeout = millis();
  String response = "";
  
  while (client.connected() && millis() - timeout < 10000) {
    if (client.available()) {
      String line = client.readStringUntil('\n');
      response += line + "\n";
      if (line == "\r") {
        break; // Конец заголовков
      }
    }
  }
  
  // Читаем тело ответа
  while (client.available()) {
    response += client.readString();
  }
  
  SerialMon.println("📥 Response:");
  SerialMon.println(response);
  
  client.stop();
  
  // Проверяем статус код
  return response.indexOf("200 OK") > 0;
}

void setup() {
  SerialMon.begin(115200);
  delay(2000);
  SerialMon.println("🚀 EcoTracker POST Test via TinyGSM (A7670E) - Fixed Version");

  SerialAT.begin(115200, SERIAL_8N1, MODEM_RX_PIN, MODEM_TX_PIN);
  delay(300);

  // ⚡ Подаём питание на модем
  pinMode(BOARD_PWRKEY_PIN, OUTPUT);
  digitalWrite(BOARD_PWRKEY_PIN, LOW);
  delay(100);
  digitalWrite(BOARD_PWRKEY_PIN, HIGH);
  delay(100);
  digitalWrite(BOARD_PWRKEY_PIN, LOW);
  delay(5000);

  SerialMon.print("🔍 Checking modem...");
  while (!modem.testAT(1000)) SerialMon.print(".");
  SerialMon.println("✅ Ready!");

  // 💳 Проверка SIM
  while (modem.getSimStatus() != SIM_READY) {
    SerialMon.println("💳 Waiting for SIM...");
    delay(1000);
  }

  // 📶 Подключение к сети
  modem.gprsConnect(APN, APN_USER, APN_PASS);
  if (!modem.isGprsConnected()) {
    SerialMon.println("❌ Network failed!");
    return;
  }
  SerialMon.println("📶 Network connected!");
  SerialMon.print("🌍 IP Address: ");
  SerialMon.println(modem.getLocalIP());

  // 🔁 Бесконечный цикл отправки данных
  while (true) {
    for (int i = 0; i < SEND_COUNT; i++) {
      SerialMon.println();
      SerialMon.printf("📤 Отправка #%d...\n", i + 1);

      String json = buildJson(FILL_LEVELS[i][0], FILL_LEVELS[i][1]);
      SerialMon.println("📄 JSON: " + json);

      bool success = sendHttpPost(json);
      
      if (success) {
        SerialMon.println("✅ POST success!");
      } else {
        SerialMon.println("⚠️ POST failed!");
      }

      SerialMon.print("⏳ Ждём ");
      SerialMon.print(SEND_INTERVAL / 1000);
      SerialMon.println(" секунд...\n");
      delay(SEND_INTERVAL);
    }
  }

  // 📴 На случай выхода из цикла
  modem.gprsDisconnect();
  SerialMon.println("🔚 Завершено.");
}

void loop() {}
