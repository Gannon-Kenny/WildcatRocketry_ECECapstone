#include <Arduino.h>
#include <RadioLib.h>

SX1262 radio = new Module(8, 14, 12, 13);

static const float   LORA_FREQ_MHZ = 915.0;
static const float   LORA_BW_KHZ   = 125.0;
static const uint8_t LORA_SF       = 9;
static const uint8_t LORA_CR       = 5;

static const size_t BER_BYTES = 64;
static const size_t MAX_PACKET = 256;

volatile bool gotPacket = false;
void setFlag() { gotPacket = true; }

//// SAME PRNG AS TX ////
static uint32_t xorshift32(uint32_t &x) {
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  return x;
}

static void genExpected(uint16_t seq, uint8_t *out, size_t n) {
  uint32_t s = 0xC0FFEE00u ^ (uint32_t)seq;
  for (size_t i = 0; i < n; i++) {
    out[i] = (uint8_t)(xorshift32(s) & 0xFF);
  }
}

static uint32_t countBitErrors(const uint8_t *a, const uint8_t *b, size_t n) {
  uint32_t errors = 0;
  for (size_t i = 0; i < n; i++) {
    uint8_t diff = a[i] ^ b[i];
    diff = diff - ((diff >> 1) & 0x55);
    diff = (diff & 0x33) + ((diff >> 2) & 0x33);
    errors += ((diff + (diff >> 4)) & 0x0F);
  }
  return errors;
}

// Stats
uint32_t totalBits = 0;
uint32_t totalBitErrors = 0;
uint32_t packetsRx = 0;
uint32_t packetsMissed = 0;
int32_t lastSeq = -1;

void setup() {
  Serial.begin(115200);
  delay(500);

  int state = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.println("LoRa init failed");
    while (true);
  }

  radio.setDio1Action(setFlag);
  radio.startReceive();

  Serial.println("RX READY (Sensor + BER mode)");
}

void loop() {
  if (!gotPacket) return;
  gotPacket = false;

  uint8_t rx[MAX_PACKET];
  int len = radio.getPacketLength();

  int state = radio.readData(rx, len);
  if (state != RADIOLIB_ERR_NONE) {
    radio.startReceive();
    return;
  }

  packetsRx++;

  // ----- Extract sequence -----
  uint16_t seq = rx[0] | (rx[1] << 8);

  // ----- Packet loss estimation -----
  if (lastSeq >= 0 && seq > lastSeq + 1)
    packetsMissed += seq - (lastSeq + 1);
  lastSeq = seq;

  // ----- Split payload and BER field -----
  int payloadLen = len - 2 - BER_BYTES;
  if (payloadLen < 0) payloadLen = 0;

  char sensorPayload[220];
  memcpy(sensorPayload, &rx[2], payloadLen);
  sensorPayload[payloadLen] = '\0';

  uint8_t *rxBer = &rx[2 + payloadLen];

  // ----- Generate expected BER bytes -----
  uint8_t expected[BER_BYTES];
  genExpected(seq, expected, BER_BYTES);

  uint32_t bitErr = countBitErrors(rxBer, expected, BER_BYTES);
  uint32_t bitsThis = BER_BYTES * 8;

  totalBitErrors += bitErr;
  totalBits += bitsThis;

  double BER = (double)totalBitErrors / totalBits;

  // ----- PRINT EVERYTHING -----
  //Serial.println("\n===== RX PACKET =====");

  //Serial.print("SEQ: "); Serial.println(seq);
  //Serial.print("Sensor Data: ");
  Serial.println(sensorPayload);

  Serial.print("SF: ");
  Serial.println(LORA_SF);

  Serial.print("Bit Errors: ");
  Serial.print(bitErr);
  Serial.print(" / ");
  Serial.println(bitsThis);

  Serial.print("Packets RX: ");
  Serial.print(packetsRx);
  Serial.print(" | Missed: ");
  Serial.println(packetsMissed);

  Serial.print("Cumulative BER: ");
  Serial.println(BER, 10);

  Serial.print("RSSI: ");
  Serial.print(radio.getRSSI());
  Serial.print(" dBm  SNR: ");
  Serial.print(radio.getSNR());
  Serial.println(" dB");

  Serial.println("=====================");

  radio.startReceive();
}