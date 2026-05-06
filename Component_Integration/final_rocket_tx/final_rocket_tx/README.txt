ECE 488 SENSOR DATA SYSTEM (LoRa TX VERSION)
README
Erik Kuhn and Justin Osmond

------------------------------------------------------------
1. PROJECT OVERVIEW
------------------------------------------------------------
This project is a multi-sensor telemetry system running on an ESP32-based platform.

It collects real-time data from multiple sensors and transmits the data wirelessly using LoRa (915 MHz).

------------------------------------------------------------
2. PURPOSE
------------------------------------------------------------
The system is designed to:
- Collect environmental, motion, atmospheric, GPS, and soil data
- Standardize sensor outputs into engineering units
- Monitor sensor health/status
- Package all data into a structured RF telemetry packet
- Transmit data using LoRa for long-range communication
- Include a BER field for link quality testing

------------------------------------------------------------
3. INPUT AND OUTPUT VARIABLES
------------------------------------------------------------

INPUTS (Sensors):
- MPU6050: acceleration (m/s²), gyro (rad/s)
- BMP390: temperature, pressure, altitude
- DHT11: temperature (°C), humidity (%)
- GPS module: latitude, longitude, altitude, satellites
- RS485 Soil sensor: soil moisture, soil temperature

OUTPUTS:

SENSOR STATUS FLAGS:
- GPSOK
- MPUOK
- BMPOK
- DHTOK
- SOILOK

TELEMETRY DATA:
GPS:
- Latitude
- Longitude
- Altitude (feet)
- Satellite count

MPU6050 Data:
- Acceleration X, Y, Z
- Gyroscope X, Y, Z

BMP390:
- Temperature (°F)
- Pressure (hPa)
- Altitude (feet)

DHT11:
- Temperature (°F)
- Humidity (%)

SOIL SENSOR:
- Soil Temperature (°F)
- Soil Moisture (%)

COMMUNICATION DATA:
- Sequence number (SEQ)
- BER test field (randomized byte block)

------------------------------------------------------------
4. HARDWARE CONNECTIONS
------------------------------------------------------------

I2C BUS:
- SDA: GPIO 20
- SCL: GPIO 19
Used by MPU6050 and BMP390

UART DEVICES:

GPS:
- RX: GPIO 47
- TX: GPIO 48
- Baud: 9600

RS485 Soil Sensor:
- RX: GPIO 5
- TX: GPIO 6
- Baud: 4800

RS485 CONTROL:
- MAX485_DE_RE (GPIO 40)
  HIGH = transmit mode
  LOW = receive mode

------------------------------------------------------------
5. COMMUNICATION SYSTEM (LoRa)
------------------------------------------------------------

RADIO MODULE:
- SX1262 LoRa transceiver
- Frequency: 915 MHz (ISM band)

LoRa CONFIGURATION:
- Bandwidth: 125 kHz
- Spreading Factor: 7
- Coding Rate: 4/5
- Output Power: 17 dBm

------------------------------------------------------------
6. PACKET STRUCTURE
------------------------------------------------------------

Each transmitted LoRa packet contains:

[SEQ (2 bytes)] + [PAYLOAD] + [BER FIELD]

------------------------------------------------------------
A) SEQUENCE NUMBER
------------------------------------------------------------
- 16-bit counter (increments every transmission)
- Used for packet tracking and loss detection

------------------------------------------------------------
B) PAYLOAD FORMAT (ASCII STRING)
------------------------------------------------------------

Formatted as:

GPSOK MPUOK BMPOK DHTOK SOILOK
SAT LAT LON GPS_ALT
AX AY AZ
GX GY GZ
BMP_TEMP BMP_PRESS BMP_ALT
DHT_TEMP DHT_HUM
SOIL_TEMP SOIL_MOISTURE

------------------------------------------------------------
C) BER FIELD
------------------------------------------------------------
- 64-byte pseudo-random data block
- Generated using XORSHIFT PRNG
- Used to estimate Bit Error Rate (BER)
- Helps evaluate RF link quality

------------------------------------------------------------
7. LIBRARIES USED
------------------------------------------------------------
- Arduino.h
- Wire.h
- Adafruit_MPU6050
- Adafruit_Sensor
- Adafruit_BMP3XX
- DHT.h
- HT_TinyGPS++.h
- ModbusMaster.h
- RadioLib.h

------------------------------------------------------------
8. SYSTEM OPERATION
------------------------------------------------------------

Loop process:
1. Read all sensors
2. Validate sensor data
3. Convert raw values to engineering units
4. Read GPS continuously
5. Query soil sensor after warm-up
6. Format telemetry payload
7. Attach sequence number
8. Append BER test field
9. Transmit via LoRa
10. Print debug info to Serial
11. Increment sequence number
12. Wait 1 second

------------------------------------------------------------
9. FUNCTIONS
------------------------------------------------------------

setup():
- Initializes Serial, I2C, UART, sensors
- Configures MPU6050 and BMP390
- Starts GPS and RS485 communication
- Initializes LoRa radio
- Sets transmission parameters

loop():
- Collects all sensor data
- Builds telemetry payload
- Constructs RF packet
- Transmits via LoRa
- Logs debug output

preTransmission():
- Enables RS485 transmit mode

postTransmission():
- Enables RS485 receive mode

genBerField():
- Generates pseudo-random BER test bytes

xorshift32():
- PRNG used for BER generation

------------------------------------------------------------
10. TIMING
------------------------------------------------------------
- Main loop delay: 1000 ms (1 Hz update rate)
- Soil sensor warm-up: 5000 ms
- GPS runs continuously (non-blocking)
- LoRa transmit: synchronous per loop cycle

------------------------------------------------------------
11. DATA FORMAT
------------------------------------------------------------
Telemetry is printed in structured blocks for logging
View Payload section above

------------------------------------------------------------
12. NOTES
------------------------------------------------------------
- Designed for long-range telemetry applications
- Includes built-in link quality testing (BER field)
- Sequence numbering allows packet loss detection
- All sensors run concurrently
- Units standardized:
  Temperature = °F
  Pressure = hPa
  Altitude = feet
- System optimized for real-time flight or field deployment