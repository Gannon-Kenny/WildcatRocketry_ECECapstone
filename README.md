# WildcatRocketry_ECECapstone

## Component Integration
Please see individual README files within their respective folder.

## LoRa Communication
This section overviews the readme for the final transmitter and reciever code. This readme is specifically for the Transmitter and Reciever code with BER (the final iteration of our work). The other codes in file are test codes in which we do not provide a readme file as the final code is built on top of these. The Lora code w/ BER is final product and what is described.

### Transmitter 

Erik Kuhn and Justin Osmond

============================================================================================
1. PROJECT OVERVIEW

This project is a multi-sensor telemetry system running on an ESP32-based platform.

It collects real-time data from multiple sensors and transmits the data wirelessly using LoRa (915 MHz).

============================================================================================
2. PURPOSE

The system is designed to:
- Collect environmental, motion, atmospheric, GPS, and soil data
- Standardize sensor outputs into engineering units
- Monitor sensor health/status
- Package all data into a structured RF telemetry packet
- Transmit data using LoRa for long-range communication
- Include a BER field for link quality testing

============================================================================================
3. INPUT AND OUTPUT VARIABLES

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

============================================================================================
4. HARDWARE CONNECTIONS


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

============================================================================================
5. COMMUNICATION SYSTEM (LoRa)


RADIO MODULE:
- SX1262 LoRa transceiver
- Frequency: 915 MHz (ISM band)

LoRa CONFIGURATION:
- Bandwidth: 125 kHz
- Spreading Factor: 7
- Coding Rate: 4/5
- Output Power: 17 dBm

============================================================================================
6. PACKET STRUCTURE


Each transmitted LoRa packet contains:

[SEQ (2 bytes)] + [PAYLOAD] + [BER FIELD]

------------------------------------------------------------
A) SEQUENCE NUMBER

- 16-bit counter (increments every transmission)
- Used for packet tracking and loss detection

------------------------------------------------------------
B) PAYLOAD FORMAT (ASCII STRING)


Formatted as:

GPSOK MPUOK BMPOK DHTOK SOILOK
SAT LAT LON GPS_ALT
AX AY AZ
GX GY GZ
BMP_TEMP BMP_PRESS BMP_ALT
DHT_TEMP DHT_HUM
SOIL_TEMP SOIL_MOISTURE

C) BER FIELD
- 64-byte pseudo-random data block
- Generated using XORSHIFT PRNG
- Used to estimate Bit Error Rate (BER)
- Helps evaluate RF link quality

============================================================================================
7. LIBRARIES USED
- Arduino.h
- Wire.h
- Adafruit_MPU6050
- Adafruit_Sensor
- Adafruit_BMP3XX
- DHT.h
- HT_TinyGPS++.h
- ModbusMaster.h
- RadioLib.h

============================================================================================
8. SYSTEM OPERATION

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

============================================================================================
9. FUNCTIONS

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

============================================================================================
10. TIMING
- Main loop delay: 1000 ms (1 Hz update rate)
- Soil sensor warm-up: 5000 ms
- GPS runs continuously (non-blocking)
- LoRa transmit: synchronous per loop cycle

============================================================================================
11. DATA FORMAT
Telemetry is printed in structured blocks for logging
View Payload section above

============================================================================================
12. NOTES
- Designed for long-range telemetry applications
- Includes built-in link quality testing (BER field)
- Sequence numbering allows packet loss detection
- All sensors run concurrently
- Units standardized:
  Temperature = °F
  Pressure = hPa
  Altitude = feet
- System optimized for real-time flight or field deployment

### Receiver
This section overviews the LoRa receiver code:

It receives telemetry packets from the transmitter, extracts sensor data, and evaluates link performance using Bit Error Rate (BER) and packet tracking.

============================================================================================
2. PURPOSE

The system is designed to:

Receive LoRa telemetry data
Extract and display sensor payload information
Measure Bit Error Rate (BER) for link quality analysis
Track packet sequence numbers and detect packet loss
Monitor signal quality using RSSI and SNR

============================================================================================
3. INPUT AND OUTPUT VARIABLES
INPUTS:
LoRa RF packets from transmitter
OUTPUTS:

SENSOR DATA (from payload):

Parsed ASCII telemetry string (all transmitted sensor values)

COMMUNICATION DATA:

Sequence number (SEQ)
Bit errors per packet
Total bits received
Cumulative BER
Packet count (received)
Packet loss (missed packets)
RSSI (dBm)
SNR (dB)

============================================================================================
4. HARDWARE CONNECTIONS
RADIO MODULE (SX1262):
Signal	GPIO
NSS	8
DIO1	14
NRST	12
BUSY	13

============================================================================================
5. COMMUNICATION SYSTEM (LoRa)

RADIO MODULE:

SX1262 LoRa transceiver
Frequency: 915 MHz 
LoRa CONFIGURATION:

Bandwidth: 125 kHz
Spreading Factor: 9
Coding Rate: 4/5
- Matching transmitter settings

============================================================================================
6. PACKET STRUCTURE

Each received LoRa packet contains:

[SEQ (2 bytes)] + [PAYLOAD] + [BER FIELD]
A) SEQUENCE NUMBER
16-bit counter
Used for packet tracking and loss detection
B) PAYLOAD FORMAT (ASCII STRING)
Variable-length sensor data string
Extracted and printed directly to Serial
C) BER FIELD
64-byte pseudo-random data block
Generated using XORSHIFT PRNG on transmitter
Re-generated on receiver for comparison
Used to compute Bit Error Rate

============================================================================================
7. LIBRARIES USED
Arduino.h
RadioLib.h

============================================================================================
8. SYSTEM OPERATION

Loop process:

Wait for LoRa packet interrupt
Read received packet data
Extract sequence number
Detect missed packets using sequence tracking
Separate payload and BER field
Re-generate expected BER data using PRNG
Compare received vs expected bits
Compute bit errors and update totals
Calculate cumulative BER
Print sensor data and link data
Restart receiver mode

============================================================================================
9. FUNCTIONS

setup():

Initializes Serial communication
Initializes LoRa radio
Sets frequency, bandwidth, SF, and coding rate
Attaches interrupt for packet reception
Starts receive mode

loop():

Handles incoming packets
Performs BER and packet loss calculations
Outputs telemetry and diagnostics

============================================================================================
11. DATA FORMAT

Serial Output Example:

SF: 9  
Bit Errors: X / 512  
Packets RX: N | Missed: M  
Cumulative BER: 0.0000000000  
RSSI: -XX dBm  SNR: X.X dB  

============================================================================================
12. NOTES
Designed to pair with LoRa TX system
BER field must match transmitter PRNG exactly
BER improves in accuracy over time (more packets) because its cumulative


## AI Implementation

### Purpose & Files
The purpose of this section of files is for the ground station's weather prediction algorithm, and trajectory & GUI.
Inside this section you'll find tests from early on in the process for different tests that were carried out to resolve the best data set to use in the final product for the most accurate results.
In addtion there is:
1) dummy_data.py - a file which creates realistic simulated flight, weather and trajectory data
2) dummy_flight_data.txt - an outdated output of [1], primarily used as a secondary testing case for the GUI, to see how it reacts with much more varying data.
3) flight_log.txt - a log which is created to store the time and date, in addition to all other data recieved from the rocket for future use and testing.
4) historic_weather_data.txt - the output of scraper.py, this file is data which has been scraped from the Weather Underground site. Currently this is data for the past 7 years, from March to May in the Utica area.
5) realistic_flight_data - the new output of [1].
6) rocket_weather_data.txt - data directly recieved from the rocket - this is also used in single test cases (where the rocket is not in motion, and you are testing only the AI, not the GUI).
7) scraper.py - Running this file scrapes data from a specified website [currently Weather Underground] using it's API key, and parses the data into a more reasonable & readable state.
8) weather.py - Runs the GUI and weather prediction algorithms. Uses data from the rocket, in real time.
9) weather_file.py - Runs the GUI and weather prediction algorithms. Uses data from a file.

In addition to these files, when run you will recieve four additonal files:
1) feature_importance.png - A graph which shows how important each aspect input into the algorithm had on it's output.
2) weather_prediction.png - A pie chart which shows the make up of the weather predictions probabilities.
3) reliability.png - Shows the overall reliability of the system - currently should show ~75%.
4) confusion_matrix.png - A confusion Matrix, showing the commonly mistaken weather of the given set.

### Use
The optimal use of these files are within VS Code, as it is the simplest to run, and easiest to get started with.
Should you be using a VM or Linux based system (especially for testing):
- This code was created on python3.12, meaning that should you run into problems, please attempt to revert your python environment first.
- When running a python script, use "python3.12 [file.py]"

#### Required Downloads
This system uses a number of imports which need to be installed prior to use, it is recommended to set up an environment first.
- pandas
- numpy
- threads
- tkinter
- matplotlib
- seaborn
- sklearn
