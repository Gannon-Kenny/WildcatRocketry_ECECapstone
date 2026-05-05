// ECE 487 Sensor Data TX – ALL SENSORS + GPS over LoRa (915 MHz)

#include <Arduino.h>
#include <Wire.h>

// ---- Sensors ----
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP3XX.h>
#include "DHT.h"

// ---- GPS ----
#include "HT_TinyGPS++.h"   // your existing GPS lib

// ---- LoRa (RadioLib) ----
#include <RadioLib.h>

// ----- Heltec Vext (Ve) control -----
#define VEXT_PIN 21   // ACTIVE LOW

// ----- I2C pin mapping -----
#define SDA_PIN 20
#define SCL_PIN 19

// ----- DHT11 Setup -----
#define DHTPIN 3
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ----- MPU6050 Setup -----
Adafruit_MPU6050 mpu;

// ----- BMP390 Setup -----
Adafruit_BMP3XX bmp;
#define SEALEVELPRESSURE_HPA (1013.25)

// ----- GPS Setup -----
TinyGPSPlus gps;
HardwareSerial GPSSerial(1);
#define GPS_RX_PIN 47
#define GPS_TX_PIN 48

// ----- LoRa SX1262 pins for Heltec WiFi LoRa 32 (V3) -----
SX1262 radio = new Module(8, 14, 12, 13); // NSS=8, DIO1=14, RST=12, BUSY=13

// LoRa settings (must match RX)
static const float LORA_FREQ_MHZ = 915.0;
static const float LORA_BW_KHZ   = 125.0;
static const uint8_t LORA_SF     = 7;
static const uint8_t LORA_CR     = 5;   // 5 => 4/5

void setup() {
  Serial.begin(115200);
  delay(500);

  // Enable external power rail (Vext/Ve)
  pinMode(VEXT_PIN, OUTPUT);
  digitalWrite(VEXT_PIN, LOW);  // LOW = ON
  delay(100);

  Serial.println("Starting ALL sensors + GPS + LoRa TX...");

  // I2C
  Wire.begin(SDA_PIN, SCL_PIN);

  // DHT11
  dht.begin();
  Serial.println("DHT11 initialized.");

  // MPU6050
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050!");
    while (1) delay(10);
  }
  Serial.println("MPU6050 Found!");
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  // BMP390
  if (!bmp.begin_I2C()) {
    Serial.println("Failed to find BMP390!");
    while (1) delay(10);
  }
  Serial.println("BMP390 Found!");
  bmp.setTemperatureOversampling(BMP3_OVERSAMPLING_8X);
  bmp.setPressureOversampling(BMP3_OVERSAMPLING_4X);
  bmp.setIIRFilterCoeff(BMP3_IIR_FILTER_COEFF_3);
  bmp.setOutputDataRate(BMP3_ODR_50_HZ);

  // GPS
  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);
  Serial.println("GPS initialized.");

  // LoRa init
  int state = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print("LoRa init failed, code=");
    Serial.println(state);
    while (true) delay(1000);
  }
  Serial.println("LoRa TX ready @ 915 MHz");

  Serial.println("All systems ready.\n");
}

void loop() {
  // ---------- Read MPU6050 ----------
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  // ---------- Read DHT11 ----------
  float h = dht.readHumidity();
  float t = dht.readTemperature();
  bool dht_ok = !(isnan(h) || isnan(t));

  // ---------- Read BMP390 ----------
  bool bmp_ok = bmp.performReading();
  float bmp_temp = bmp_ok ? bmp.temperature : NAN;
  float bmp_pres = bmp_ok ? (bmp.pressure / 100.0f) : NAN; // hPa
  float bmp_alt  = bmp_ok ? bmp.readAltitude(SEALEVELPRESSURE_HPA) : NAN;

  // ---------- Read GPS (non-blocking feed) ----------
  while (GPSSerial.available() > 0) {
    gps.encode(GPSSerial.read());
  }

  // Use latest-known values (may be invalid if no fix yet)
  bool gps_ok = gps.location.isValid();
  double lat = gps_ok ? gps.location.lat() : 0.0;
  double lon = gps_ok ? gps.location.lng() : 0.0;
  uint32_t sats = gps.satellites.isValid() ? gps.satellites.value() : 0;
  double gps_alt = gps.altitude.isValid() ? gps.altitude.meters() : 0.0;

  // ---------- Build payload ----------
  // Keep payload under ~200 bytes for reliability
  char payload[220];
  snprintf(payload, sizeof(payload),
           "AX=%.2f,AY=%.2f,AZ=%.2f,GX=%.2f,GY=%.2f,GZ=%.2f,MPUT=%.2f,"
           "DHOK=%d,DHT=%.2f,DHH=%.2f,"
           "BMPOK=%d,BMPT=%.2f,BMPP=%.2f,BMPA=%.2f,"
           "GPSOK=%d,LAT=%.6f,LON=%.6f,SAT=%lu,GPSA=%.1f",
           a.acceleration.x, a.acceleration.y, a.acceleration.z,
           g.gyro.x, g.gyro.y, g.gyro.z,
           temp.temperature,
           dht_ok ? 1 : 0, dht_ok ? t : -999.0f, dht_ok ? h : -999.0f,
           bmp_ok ? 1 : 0, bmp_ok ? bmp_temp : -999.0f, bmp_ok ? bmp_pres : -999.0f, bmp_ok ? bmp_alt : -999.0f,
           gps_ok ? 1 : 0, gps_ok ? lat : 0.0, gps_ok ? lon : 0.0,
           (unsigned long)sats, gps_ok ? gps_alt : 0.0);

  // Print locally
  Serial.println(payload);

  // ---------- Transmit over LoRa ----------
  int state = radio.transmit(payload);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.print("LoRa TX failed, code=");
    Serial.println(state);
  }

  delay(1000);
}
