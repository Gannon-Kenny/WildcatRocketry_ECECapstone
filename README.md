# WildcatRocketry_ECECapstone

## Component Integration
Please see individual README files within their respective folder.

## LoRa Communication
This section overviews the readme for the final reciever code product. The transmitter code is covered in the Component integration section as it deals more with the processing of the sensors (see there for more). This readme is specifically for the Reciever code with BER (the final iteration of our work). The other codes in file are test codes in which we do not provide a readme file as the final code is built on top of these. The Lora code w/ BER is final product and what is described.
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
