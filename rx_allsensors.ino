// ECE 487 Sensor Data RX – receive LoRa payload (915 MHz) and print

#include <Arduino.h>
#include <RadioLib.h>

// Heltec WiFi LoRa 32 (V3) SX1262 pins:
SX1262 radio = new Module(8, 14, 12, 13); // NSS=8, DIO1=14, RST=12, BUSY=13

static const float LORA_FREQ_MHZ = 915.0;
static const float LORA_BW_KHZ   = 125.0;
static const uint8_t LORA_SF     = 7;
static const uint8_t LORA_CR     = 5;   // 4/5

volatile bool gotPacket = false;
void setFlag() { gotPacket = true; }

void setup() {
  Serial.begin(115200);
  delay(500);

  int state = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print("LoRa init failed, code=");
    Serial.println(state);
    while (true) delay(1000);
  }

  radio.setDio1Action(setFlag);

  state = radio.startReceive();
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print("startReceive failed, code=");
    Serial.println(state);
  }

  Serial.println("LoRa RX listening @ 915 MHz");
}

void loop() {
  if (!gotPacket) return;
  gotPacket = false;

  String msg;
  int state = radio.readData(msg);

  if (state == RADIOLIB_ERR_NONE) {
    Serial.println("----- RX PACKET -----");
    Serial.println(msg);

    Serial.print("RSSI: ");
    Serial.print(radio.getRSSI());
    Serial.print(" dBm | SNR: ");
    Serial.print(radio.getSNR());
    Serial.println(" dB");
    Serial.println("---------------------");
  } else {
    Serial.print("readData failed, code=");
    Serial.println(state);
  }

  radio.startReceive(); // keep listening
}