// ECE 488 Sensor Data, No Tx
// Erik Kuhn

#include <Arduino.h>
#include <Wire.h>

// ---- Sensors Libraries ----
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BMP3XX.h>
#include "DHT.h"

// ---- GPS Library ----
#include "HT_TinyGPS++.h"

// ---- RS485 Soil Sensor (Modbus) ----
#include <ModbusMaster.h>

// ---------------- POWER ----------------
#define VEXT_PIN 21

// ---------------- I2C ----------------
#define SDA_PIN 20
#define SCL_PIN 19

// ---------------- DHT11 ----------------
#define DHTPIN 3
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

// ---------------- MPU6050 ----------------
Adafruit_MPU6050 mpu;

// ---------------- BMP390 ----------------
Adafruit_BMP3XX bmp;
#define SEALEVELPRESSURE_HPA 1013.25

// ---------------- GPS ----------------
TinyGPSPlus gps;
HardwareSerial GPSSerial(1);
#define GPS_RX_PIN 47
#define GPS_TX_PIN 48

// ---------------- SOIL (RS485) ----------------
#define RXD2 5
#define TXD2 6
#define MAX485_DE_RE 40

HardwareSerial RS485Serial(2);
ModbusMaster node;

// ---------------- TIMING ----------------
unsigned long startupTime;
const unsigned long sensorWarmup = 5000;

// ---------------- RS485 DIR CONTROL ----------------
// These functions control whether the RS485 chip is sending or receiving data.
// HIGH = transmit mode, LOW = receive mode.
void preTransmission() { digitalWrite(MAX485_DE_RE, HIGH); }
void postTransmission() { digitalWrite(MAX485_DE_RE, LOW); }

void setup() {

  Serial.begin(115200);   // Debug output to PC / ground station
  delay(500);

  // Enable external sensor power rail (if used in your system design)
  pinMode(VEXT_PIN, OUTPUT);
  digitalWrite(VEXT_PIN, LOW);

  // Start shared I2C bus for MPU + BMP sensors
  Wire.begin(SDA_PIN, SCL_PIN);

  // Initialize temperature + humidity sensor
  dht.begin();

  // ---------------- MPU6050 INIT ----------------
  // IMU provides acceleration + angular velocity (useful for flight dynamics)
  mpu.begin();

  // Configure measurement ranges to balance sensitivity vs noise
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);

  // Low-pass filter reduces vibration noise from rocket flight
  mpu.setFilterBandwidth(MPU6050_BAND_21_HZ);

  // ---------------- BMP390 INIT ----------------
  // Used for pressure + altitude estimation
  if (!bmp.begin_I2C()) {
    // If sensor fails, loop until it is found
    while (1) delay(10);
  }

  // Increase oversampling for more stable readings (slower but more accurate)
  bmp.setTemperatureOversampling(BMP3_OVERSAMPLING_8X);
  bmp.setPressureOversampling(BMP3_OVERSAMPLING_4X);

  // Smooths out noise in pressure readings
  bmp.setIIRFilterCoeff(BMP3_IIR_FILTER_COEFF_3);

  // Controls update rate of sensor internally
  bmp.setOutputDataRate(BMP3_ODR_50_HZ);

  // ---------------- GPS INIT ----------------
  // GPS provides position, altitude, and satellite lock info
  GPSSerial.begin(9600, SERIAL_8N1, GPS_RX_PIN, GPS_TX_PIN);

  // ---------------- RS485 SOIL SENSOR ----------------
  // Direction pin controls transmit/receive mode of RS485 driver
  pinMode(MAX485_DE_RE, OUTPUT);
  digitalWrite(MAX485_DE_RE, LOW); // default to receive mode

  RS485Serial.begin(4800, SERIAL_8N1, RXD2, TXD2);

  // Modbus device ID = 1 (soil sensor on RS485 network)
  node.begin(1, RS485Serial);

  // Attach direction control callbacks so library handles TX/RX switching
  node.preTransmission(preTransmission);
  node.postTransmission(postTransmission);

  // Record startup time for sensor warm-up delay
  startupTime = millis();
}

void loop() {

  // ======================================================
  // ---------------- MPU6050 READ ------------------------
  // ======================================================
  sensors_event_t a, g, temp;

  // Reads acceleration (m/s^2), gyro (rad/s), and internal temp
  mpu.getEvent(&a, &g, &temp);

  // Basic validity check to ensure sensor is responding
  bool MPU_OK = (!isnan(a.acceleration.x) && !isnan(g.gyro.x));

  // ======================================================
  // ---------------- DHT11 READ --------------------------
  // ======================================================
  float dhtC = dht.readTemperature(); // Celsius
  float dhtH = dht.readHumidity();    // Relative humidity %

  // If either value fails, sensor is considered invalid
  bool DHT_OK = !(isnan(dhtC) || isnan(dhtH));

  // Convert temperature to Fahrenheit
  float DHT_T = DHT_OK ? (dhtC * 9.0 / 5.0 + 32.0) : 0;

  // ======================================================
  // ---------------- BMP390 READ -------------------------
  // ======================================================
  bool BMP_OK = bmp.performReading(); // triggers new sensor read

  // Convert values to flight-friendly units
  float BMP_T = BMP_OK ? (bmp.temperature * 9.0 / 5.0 + 32.0) : 0;
  float BMP_P = BMP_OK ? (bmp.pressure / 100.0f) : 0; // Pa → hPa

  // Altitude derived from pressure using sea level reference
  float BMP_ALT = BMP_OK ? (bmp.readAltitude(SEALEVELPRESSURE_HPA) * 3.28084) : 0;

  // ======================================================
  // ---------------- GPS READ ----------------------------
  // ======================================================
  // Continuously feed incoming GPS serial data into parser
  while (GPSSerial.available())
    gps.encode(GPSSerial.read());

  // Check if GPS has a valid fix
  bool GPS_OK = gps.location.isValid();

  // Extract position data (or zero if invalid)
  double LAT = GPS_OK ? gps.location.lat() : 0;
  double LON = GPS_OK ? gps.location.lng() : 0;

  // Satellite count helps determine fix quality
  uint32_t SAT = gps.satellites.isValid() ? gps.satellites.value() : 0;

  // Convert altitude from meters to feet
  double ALT_ft = gps.altitude.isValid() ? gps.altitude.meters() * 3.28084 : 0;

  // ======================================================
  // ---------------- SOIL SENSOR READ --------------------
  // ======================================================
  int SOIL_OK = 0;
  float SOIL_T = 0;
  float SOIL_M = 0;

  // Prevent reading before sensor has stabilized after power-up
  if (millis() - startupTime > sensorWarmup) {

    // Request 2 registers: moisture + temperature
    uint8_t result = node.readHoldingRegisters(0x0000, 2);

    if (result == node.ku8MBSuccess) {
      SOIL_OK = 1;

      // Extract raw register values
      uint16_t moisture = node.getResponseBuffer(0);
      uint16_t temp = node.getResponseBuffer(1);

      // Convert raw values into usable units
      SOIL_M = moisture / 10.0; // scaled %
      SOIL_T = (temp / 10.0) * 9.0 / 5.0 + 32.0; // °F
    }
  }

  // ======================================================
  // ---------------- SERIAL OUTPUT -----------------------
  // ======================================================
  // Everything below is formatted telemetry for ground station logging

  Serial.println("------------------ DATA ------------------");

  // Sensor health flags (1 = working, 0 = failed)
  Serial.print("GPS Status  : "); Serial.println(GPS_OK);
  Serial.print("MPU Status  : "); Serial.println(MPU_OK);
  Serial.print("BMP Status  : "); Serial.println(BMP_OK);
  Serial.print("DHT Status  : "); Serial.println(DHT_OK);
  Serial.print("SOIL Status : "); Serial.println(SOIL_OK);

  // GPS telemetry
  Serial.print("# Satellites  : "); Serial.println(SAT);
  Serial.print("Latitude      : "); Serial.println(LAT, 6);
  Serial.print("Longitude     : "); Serial.println(LON, 6);
  Serial.print("Altitude (ft) : "); Serial.println(ALT_ft);

  // IMU motion data (used for flight dynamics / stability)
  Serial.print("Acceleration X  : "); Serial.println(a.acceleration.x);
  Serial.print("Acceleration Y  : "); Serial.println(a.acceleration.y);
  Serial.print("Acceleration Z  : "); Serial.println(a.acceleration.z);

  Serial.print("Gyroscope X     : "); Serial.println(g.gyro.x);
  Serial.print("Gyroscope Y     : "); Serial.println(g.gyro.y);
  Serial.print("Gyroscope Z     : "); Serial.println(g.gyro.z);

  // Atmospheric conditions from BMP sensor
  Serial.print("BMP Temperature    : "); Serial.println(BMP_T);
  Serial.print("BMP Pressure (hPa) : "); Serial.println(BMP_P);
  Serial.print("BMP Altitude (ft)  : "); Serial.println(BMP_ALT);

  // Environmental humidity + temperature
  Serial.print("DHT Temperature    : "); Serial.println(DHT_T);
  Serial.print("DHT Humidity       : "); Serial.println(DHT_OK ? dhtH : 0);

  // Soil conditions (useful for payload analysis)
  Serial.print("Soil Temperature   : "); Serial.println(SOIL_T);
  Serial.print("Soil Moisture      : "); Serial.println(SOIL_M);

  Serial.println("------------------------------------------\n");

  // 1-second telemetry update rate
  delay(1000);
}