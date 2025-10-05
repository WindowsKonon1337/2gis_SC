/*
  ESP32 RSSI Only Collector
  - Собирает ТОЛЬКО значения RSSI
*/

#include <Arduino.h>
#include "esp_wifi.h"
#include "WiFi.h"

// ---------------- CONFIG ----------------
#define CHANNELS_COUNT 3
const uint8_t channels[CHANNELS_COUNT] = {1, 6, 11};
#define CHANNEL_DWELL_MS 400
#define MIN_RSSI -100
// ----------------------------------------

// Глобальные переменные
uint32_t lastChannelSwitch = 0;
uint8_t currentChannelIndex = 0;

// ---------------- ISR ----------------
void IRAM_ATTR wifi_sniffer_cb(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;

  wifi_promiscuous_pkt_t *ppkt = (wifi_promiscuous_pkt_t *)buf;
  
  // Только Probe Request пакеты
  if (ppkt->payload[0] != 0x40) return;
  
  int8_t rssi = ppkt->rx_ctrl.rssi;
  
  // Фильтр по минимальному RSSI
  if (rssi < MIN_RSSI) return;

  // Отправка времени и RSSI в Serial
  Serial.print(millis());
  Serial.print(",");
  Serial.println(rssi);
}

// ---------------- Настройка сниффера ----------------
bool startSniffer() {
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  delay(250);
  
  wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
  cfg.nvs_enable = 0;
  
  esp_err_t err = esp_wifi_init(&cfg);
  if (err != ESP_OK) return false;
  
  err = esp_wifi_set_storage(WIFI_STORAGE_RAM);
  err |= esp_wifi_set_mode(WIFI_MODE_STA);
  err |= esp_wifi_start();
  
  if (err != ESP_OK) return false;
  
  wifi_promiscuous_filter_t filt = {.filter_mask = WIFI_PROMIS_FILTER_MASK_MGMT};
  esp_wifi_set_promiscuous_filter(&filt);
  esp_wifi_set_promiscuous_rx_cb(&wifi_sniffer_cb);
  esp_wifi_set_promiscuous(true);
  
  return true;
}

// ---------------- Setup ----------------
void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("RSSI_COLLECTOR_START");
  Serial.println("Format: timestamp,rssi");
  
  if (!startSniffer()) {
    Serial.println("ERROR: Init failed");
    while(1) delay(1000);
  }

  lastChannelSwitch = millis();
}

// ---------------- Main Loop ----------------
void loop() {
  uint32_t now = millis();

  // Переключение каналов
  if (now - lastChannelSwitch >= CHANNEL_DWELL_MS) {
    currentChannelIndex = (currentChannelIndex + 1) % CHANNELS_COUNT;
    esp_wifi_set_channel(channels[currentChannelIndex], WIFI_SECOND_CHAN_NONE);
    lastChannelSwitch = now;
  }

  delay(10);
}