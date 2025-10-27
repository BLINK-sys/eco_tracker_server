// Альтернативный метод с использованием встроенных HTTP функций TinyGSM
// Если первый способ не работает, попробуйте этот

void setup() {
  // ... предыдущий код инициализации остается тот же ...
  
  // 🔗 Правильная инициализация HTTP клиента для A7670
  modem.sendAT("+SHCONF=\"URL\",\"" + String(SERVER_URL) + "\"");
  modem.waitResponse();
  
  modem.sendAT("+SHCONF=\"BODYLEN\",1024");
  modem.waitResponse();
  
  modem.sendAT("+SHCONF=\"HEADERLEN\",350");
  modem.waitResponse();

  // 🔁 Основной цикл
  while (true) {
    for (int i = 0; i < SEND_COUNT; i++) {
      SerialMon.println();
      SerialMon.printf("📤 Отправка #%d...\n", i + 1);

      String json = buildJson(FILL_LEVELS[i][0], FILL_LEVELS[i][1]);
      SerialMon.println("📄 JSON: " + json);

      // ❗ Метод 1: Установка заголовков через SHPARA
      modem.sendAT("+SHREQ=\"" + String(SERVER_URL) + "\",1,\"application/json\"," + String(json.length()));
      if (modem.waitResponse(10000L) == 1) {
        // Отправляем данные
        modem.sendAT(json);
        if (modem.waitResponse(10000L) == 1) {
          SerialMon.println("✅ Data sent successfully!");
          
          // Читаем ответ
          modem.sendAT("+SHREAD=0,1000");
          String response = "";
          if (modem.waitResponse(10000L, response) == 1) {
            SerialMon.println("📥 Response: " + response);
          }
        }
      }

      delay(SEND_INTERVAL);
    }
  }
}

// ===== МЕТОД 2: Если A7670 поддерживает AT+HTTPPARA =====
void alternativeMethod() {
  // Инициализация HTTP
  modem.sendAT("+HTTPINIT");
  modem.waitResponse();
  
  // Установка параметров
  modem.sendAT("+HTTPPARA=\"CID\",1");
  modem.waitResponse();
  
  modem.sendAT("+HTTPPARA=\"URL\",\"" + String(SERVER_URL) + "\"");
  modem.waitResponse();
  
  modem.sendAT("+HTTPPARA=\"CONTENT\",\"application/json\"");
  modem.waitResponse();
  
  String json = buildJson(85, 45);
  
  // Установка данных
  modem.sendAT("+HTTPDATA=" + String(json.length()) + ",10000");
  modem.waitResponse(1000, "DOWNLOAD");
  
  modem.sendAT(json);
  modem.waitResponse();
  
  // Выполнение POST
  modem.sendAT("+HTTPACTION=1");
  modem.waitResponse(30000);
  
  // Чтение ответа
  modem.sendAT("+HTTPREAD");
  modem.waitResponse();
  
  // Завершение
  modem.sendAT("+HTTPTERM");
  modem.waitResponse();
}
