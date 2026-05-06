// ECE 488 Sensor Data TX – ALL SENSORS + GPS + BER + STATUS + SOIL over LoRa (915 MHz)
// Erik Kuhn and Justin Osmond

#include <Arduino.h>
#include <Wire.h>

// ---- Sensors ----
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP3XX.h>
#include "DHT.h"

// ---- GPS ----
#include "HT_TinyGPS++.h"

// ---- LoRa ----
#include <RadioLib.h>

// ---- RS485 Soil ----
#include <ModbusMaster.h>

// ----- Power -----
#define VEXT_PIN 21   // ACTIVE LOW

// ----- I2C -----
#define SDA_PIN 20
#define SCL_PIN 19

// ----- DHT11 -----
#define DHTPIN 3
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ----- MPU6050 -----
Adafruit_MPU6050 mpu;

// ----- BMP390 -----
Adafruit_BMP3XX bmp;
#define SEALEVELPRESSURE_HPA (1013.25)

// ----- GPS -----
TinyGPSPlus gps;
HardwareSerial GPSSerial(1);
#define GPS_RX_PIN 47
#define GPS_TX_PIN 48

// ----- RS485 Soil -----
#define RXD2 5
#define TXD2 6
#define MAX485_DE_RE 40

HardwareSerial RS485Serial(2);
ModbusMaster node;

// ----- LoRa -----
SX1262 radio = new Module(8, 14, 12, 13);

static const float   LORA_FREQ_MHZ = 915.0;
static const float   LORA_BW_KHZ   = 125.0;
static const uint8_t LORA_SF       = 9;
static const uint8_t LORA_CR       = 5;

// ----- BER SETTINGS -----
static const size_t BER_BYTES = 64;
static uint16_t seq = 0;

// ----- STATUS FLAGS -----
int MPUOK = 0;

// ----- SOIL TIMING -----
unsigned long startupTime;
const unsigned long sensorWarmup = 5000;

// ----- BER PRNG -----
static uint32_t xorshift32(uint32_t &x) {
  x ^= x << 13;
  x ^= x >> 17;
  x ^= x << 5;
  return x;
}

static void genBerField(uint16_t seqNum, uint8_t *out, size_t n) {
  uint32_t s = 0xC0FFEE00u ^ (uint32_t)seqNum;
  for (size_t i = 0; i < n; i++) {
    out[i] = (uint8_t)(xorshift32(s) & 0xFF);
  }
}

// ----- RS485 Direction -----
void preTransmission() { digitalWrite(MAX485_DE_RE, HIGH); }
void postTransmission() { digitalWrite(MAX485_DE_RE, LOW); }

void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(VEXT_PIN, OUTPUT);
  digitalWrite(VEXT_PIN, LOW);
  delay(100);

  Wire.begin(SDA_PIN, SCL_PIN);

  dht.begin();

  // MPU
  if (mpu.begin()) MPUOK = 1;
  else MPUOK = 0;

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  // BMP
  if (!bmp.begin_I2C()) {
    while (1) delay(10);
  }

  bmp.setTemperatureOversampling(BMP3_OVERSAMPLING_8X);
  bmp.setPressureOversampling(BMP3_OVERSAMPLING_4X);
  bmp.setIIRFilterCoeff(BMP3_IIR_FILTER_COEFF_3);
  bmp.setOutputDataRate(BMP3_ODR_50_HZ);

  // GPS
  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

  // RS485 Soil
  pinMode(MAX485_DE_RE, OUTPUT);
  digitalWrite(MAX485_DE_RE, LOW);
  RS485Serial.begin(4800, SERIAL_8N1, RXD2, TXD2);

  node.begin(1, RS485Serial);
  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);

  startupTime = millis();

  // LoRa
  int state = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR);
  if (state != RADIOLIB_ERR_NONE) {
    while (true) delay(1000);
  }

  radio.setOutputPower(17);
}

void loop() {

  // ---------- MPU ----------
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  MPUOK = (!isnan(a.acceleration.x) && !isnan(g.gyro.x)) ? 1 : 0;

  // ---------- DHT ----------
  float dhtC = dht.readTemperature();
  float dhtH = dht.readHumidity();
  bool DHTOK = !(isnan(dhtC) || isnan(dhtH));
  float DHTT = DHTOK ? (dhtC * 9.0 / 5.0 + 32.0) : 0.0;

  // ---------- BMP ----------
  bool BMPOK = bmp.performReading();
  float bmpC = BMPOK ? bmp.temperature : 0.0;
  float BMPT = BMPOK ? (bmpC * 9.0 / 5.0 + 32.0) : 0.0;
  float BMPP = BMPOK ? (bmp.pressure / 100.0f) : 0.0;
  float BMPA = BMPOK ? (bmp.readAltitude(SEALEVELPRESSURE_HPA) * 3.28084) : 0.0;

  // ---------- GPS ----------
  while (GPSSerial.available()) gps.encode(GPSSerial.read());

  bool GPSOK = gps.location.isValid();
  double LAT = GPSOK ? gps.location.lat() : 0.0;
  double LON = GPSOK ? gps.location.lng() : 0.0;
  uint32_t SAT = gps.satellites.isValid() ? gps.satellites.value() : 0;
  double GPSA = gps.altitude.isValid() ? (gps.altitude.meters() * 3.28084) : 0.0;

  // ---------- SOIL ----------
  int SOILOK = 0;
  float soilMoisture = 0.0;
  float soilTempF = 0.0;

  if ((millis() - startupTime) >= sensorWarmup) {
    uint8_t result = node.readHoldingRegisters(0x0000, 2);

    if (result == node.ku8MBSuccess) {
      SOILOK = 1;

      uint16_t rawMoisture = node.getResponseBuffer(0);
      uint16_t rawTemp = node.getResponseBuffer(1);

      soilMoisture = rawMoisture / 10.0;
      float tempC = rawTemp / 10.0;
      soilTempF = (tempC * 9.0 / 5.0) + 32.0;
    }
  }

  // ---------- PAYLOAD ----------
  char payload[260];

  int payloadLen = snprintf(payload, sizeof(payload),
    "%d %d %d %d %d "
    "%lu %.6f %.6f %.1f "
    "%.2f %.2f %.2f "
    "%.2f %.2f %.2f "
    "%.2f %.2f %.2f "
    "%.2f %.2f "
    "%.2f %.2f",
    GPSOK ? 1 : 0,
    MPUOK,
    BMPOK ? 1 : 0,
    DHTOK ? 1 : 0,
    SOILOK,   // <-- NEW STATUS

    (unsigned long)SAT,
    LAT, LON, GPSA,

    a.acceleration.x, a.acceleration.y, a.acceleration.z,
    g.gyro.x, g.gyro.y, g.gyro.z,

    BMPT, BMPP, BMPA,
    DHTT,
    DHTOK ? dhtH : 0.0,

    soilTempF,        // <-- NEW DATA
    soilMoisture      // <-- NEW DATA
  );

  if (payloadLen < 0) payloadLen = 0;

  // ---------- PACKET ----------
  const size_t packetMax = 2 + sizeof(payload) + BER_BYTES;
  static uint8_t packet[packetMax];

  packet[0] = (uint8_t)(seq & 0xFF);
  packet[1] = (uint8_t)((seq >> 8) & 0xFF);

  memcpy(&packet[2], payload, payloadLen);

  genBerField(seq, &packet[2 + payloadLen], BER_BYTES);

  size_t packetLen = 2 + payloadLen + BER_BYTES;

  // ---------- DEBUG ----------
  Serial.print("SEQ=");
  Serial.print(seq);
  Serial.print(" | TX bytes=");
  Serial.print(packetLen);
  Serial.print(" | ");
  Serial.println(payload);

  // ---------- TX ----------
  int state = radio.transmit(packet, packetLen);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print("LoRa TX failed, code=");
    Serial.println(state);
  }

  seq++;
  delay(1000);
}