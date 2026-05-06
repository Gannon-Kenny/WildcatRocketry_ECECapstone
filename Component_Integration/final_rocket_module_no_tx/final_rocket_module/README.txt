ECE 488 SENSOR DATA SYSTEM (NO TX)
README
Erik Kuhn

------------------------------------------------------------
1. PROJECT OVERVIEW
------------------------------------------------------------
This project is a multi-sensor telemetry system running on an ESP32-based platform.

It collects real-time data from multiple sensors and outputs structured telemetry through Serial communication. No wireless transmission is used.

------------------------------------------------------------
2. PURPOSE
------------------------------------------------------------
The purpose of this system is to:
- Collect environmental, motion, atmospheric, GPS, and soil data
- Convert raw sensor values into usable engineering units
- Monitor sensor health/status
- Output formatted telemetry for logging and analysis

------------------------------------------------------------
3. INPUT AND OUTPUT VARIABLES
------------------------------------------------------------

INPUTS (Sensors):
- MPU6050: acceleration (m/s²), gyro (rad/s)
- BMP390: pressure, temperature, altitude
- DHT11: temperature (°C), humidity (%)
- GPS module: latitude, longitude, altitude, satellites
- RS485 Soil sensor: soil moisture, soil temperature

OUTPUTS (Serial Monitor at 115200 baud):

SENSOR STATUS FLAGS:
- GPS_OK
- MPU_OK
- BMP_OK
- DHT_OK
- SOIL_OK

TELEMETRY DATA:
GPS:
- Latitude
- Longitude
- Altitude (ft)
- Satellite count

MPU6050 Data:
- Acceleration X, Y, Z
- Gyroscope X, Y, Z

BMP390 Data:
- Temperature (°F)
- Pressure (hPa)
- Altitude (ft)

DHT11 Data:
- Temperature (°F)
- Humidity (%)

Soil Data:
- Soil Moisture (%)
- Soil Temperature (°F)

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
5. LIBRARIES USED
------------------------------------------------------------
- Arduino.h
- Wire.h
- Adafruit_MPU6050
- Adafruit_Sensor
- Adafruit_BMP3XX
- DHT.h
- HT_TinyGPS++.h
- ModbusMaster.h

------------------------------------------------------------
6. SYSTEM OPERATION
------------------------------------------------------------
Loop process:
1. Read all sensors
2. Validate data
3. Convert units
4. Read GPS continuously
5. Query soil sensor after warm-up
6. Print telemetry to Serial
7. Wait 1 second
8. Repeat

------------------------------------------------------------
7. FUNCTIONS
------------------------------------------------------------

setup():
- Initializes Serial, I2C, UART, and all sensors
- Configures sensor ranges and filters
- Starts Modbus communication
- Records startup time

loop():
- Reads all sensors
- Processes and converts data
- Outputs formatted telemetry

preTransmission():
- Sets RS485 to transmit mode

postTransmission():
- Sets RS485 back to receive mode

------------------------------------------------------------
8. TIMING
------------------------------------------------------------
- Main loop delay: 1000 ms (1 Hz update rate)
- Soil sensor warm-up: 5000 ms after startup
- GPS runs continuously (non-blocking)

------------------------------------------------------------
9. DATA FORMAT
------------------------------------------------------------
Telemetry is printed in structured blocks for logging

------------------------------------------------------------
10. NOTES
------------------------------------------------------------
- No wireless transmission (This is for ground tests and demonstration only)
- All sensors run concurrently
- Units standardized:
  Temperature = °F
  Pressure = hPa
  Altitude = feet
- Designed for ground station logging and analysis
