import pandas as pd
import numpy as np
import threading
import time
import math
import serial
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# =========================
# USER-SET WIND VALUE
# =========================
WIND_MANUAL = 0.0  # <-- CHANGE THIS BEFORE FLIGHT IF NEEDED

# =========================
# GLOBAL DATA STORE
# =========================
scraped_data = {
   "statuses": [0,0,0,0],
   "satelite": 0,
   "latilong": [0.0,0.0],
   "alt": 0.0,
   "acc": [0.0,0.0,0.0],
   "gps": [0.0,0.0,0.0],
   "temp1": 0.0,
   "pressure": 0.0,
   "altFalse": 0.0,
   "temp2": 0.0,
   "humidity": 0.0
}

# =========================
# WEATHER REMAP (11 → 5)
# =========================
remap = {
   0:0, 1:0,
   2:1, 3:1, 4:1,
   5:2, 6:2, 7:2,
   8:3, 9:3,
   10:4
}

class_map = {
   0:"Fair",
   1:"Cloudy",
   2:"Rain",
   3:"Snow",
   4:"Unspecified"
}

# =========================
# LOAD + TRAIN MODEL
# =========================
df = pd.read_csv("historic_weather_data.txt", sep=" ", header=None,
   names=["Month","Day","Year","Hour","Temp","Humidity","Pressure","Wind","Condition"])

df["Condition"] = df["Condition"].fillna(10).astype(int)
df["Condition"] = df["Condition"].map(remap)

df = df.sort_values(by=["Year","Month","Day","Hour"]).reset_index(drop=True)

for col in ["Temp","Humidity","Pressure","Wind"]:
   df[f"{col}_Lag1"] = df[col].shift(1)
   df[f"{col}_Roll3"] = df[col].rolling(3).mean()

df = df.dropna().reset_index(drop=True)

features = ["Month","Day","Hour","Temp","Humidity","Pressure","Wind",
            "Temp_Lag1","Humidity_Lag1","Pressure_Lag1","Wind_Lag1",
            "Temp_Roll3","Humidity_Roll3","Pressure_Roll3","Wind_Roll3"]

X = df[features]
y = df["Condition"]

X_train, X_test, y_train, y_test = train_test_split(X,y,test_size=0.2)

model = RandomForestClassifier(n_estimators=200, max_depth=12)
model.fit(X_train, y_train)

# =========================
# BUILD REALTIME ROW
# =========================
def build_row():
   now = time.localtime()

   row = {
      "Month": now.tm_mon,
      "Day": now.tm_mday,
      "Hour": now.tm_hour,

      "Temp": scraped_data["temp1"],  # <-- temp1 USED HERE (switch to temp2 if needed)
      "Humidity": scraped_data["humidity"],
      "Pressure": scraped_data["pressure"] * .02953,
      "Wind": WIND_MANUAL
   }

   df_row = pd.DataFrame([row])

   for col in ["Temp","Humidity","Pressure","Wind"]:
      df_row[f"{col}_Lag1"] = df_row[col]
      df_row[f"{col}_Roll3"] = df_row[col]

   return df_row[features]

# =========================
# APOGEE DETECTION
# =========================
alt_buffer = []
apogee_triggered = False

def check_apogee():
   global apogee_triggered

   alt = scraped_data["alt"]
   alt_buffer.append(alt)

   if len(alt_buffer) > 10:
      alt_buffer.pop(0)

   if alt < 4000 or len(alt_buffer) < 4:
      return

   if alt_buffer[-1] < alt_buffer[-2] < alt_buffer[-3] < alt_buffer[-4]:
      if not apogee_triggered:
         apogee_triggered = True
         print("\n🚀 APOGEE DETECTED\n")
         run_ml()

# =========================
# MACHINE LEARNING
# =========================
def run_ml():
   X_live = build_row()
   probs = model.predict_proba(X_live)[0]

   print("Weather Prediction at Apogee:")
   for cls,p in zip(model.classes_, probs):
      print(f"{class_map[cls]:12}: {p*100:5.1f}%")

# =========================
# SERIAL + LOGGING
# =========================
def file_loop(filename="dummy_flight_data.txt", delay=0.1):
   global scraped_data

   try:
      with open(filename, "r") as f:
         for line in f:
            line = line.strip()
            if not line:
               continue

            values = line.split()
            if len(values) != 19:
               continue

            try:
               scraped_data["statuses"] = [int(values[0]), int(values[1]), int(values[2]), int(values[3])]
               scraped_data["satelite"] = int(values[4])
               scraped_data["latilong"] = [float(values[5]), float(values[6])]
               scraped_data["alt"] = float(values[7])
               scraped_data["acc"] = [float(values[8]), float(values[9]), float(values[10])]
               scraped_data["gps"] = [float(values[11]), float(values[12]), float(values[13])]
               scraped_data["temp1"] = float(values[14])  # <-- temp1 USED HERE
               scraped_data["pressure"] = float(values[15])
               scraped_data["altFalse"] = float(values[16])
               scraped_data["temp2"] = float(values[17])
               scraped_data["humidity"] = float(values[18])
            except:
               continue

            # Logging (same as flight)
            with open("flight_log.txt", "a") as log:
               log.write(f"{time.time()} | {line}\n")

            check_apogee()

            time.sleep(delay)  # simulate real-time feed

   except Exception as e:
      print("File Read Error:", e)

# =========================
# GUI
# =========================
class GUI:
   def __init__(self):
      self.root = tk.Tk()
      self.root.title("Rocket Telemetry")

      self.fig, self.ax = plt.subplots(3,1,figsize=(6,8))
      self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
      self.canvas.get_tk_widget().pack()

      self.lat = []
      self.lon = []
      self.alt = []
      self.started = False

   def update(self):
      lat,lon = scraped_data["latilong"]
      alt = scraped_data["alt"]

      if not self.started:
         if alt > 50:
            self.started = True
         else:
            self.root.after(500, self.update)
            return

      self.lat.append(lat)
      self.lon.append(lon)
      self.alt.append(alt)

      self.ax[0].cla()
      self.ax[1].cla()
      self.ax[2].cla()

      self.ax[0].plot(self.lat,self.alt)
      self.ax[0].set_title("Latitude vs Altitude")

      self.ax[1].plot(self.lon,self.alt)
      self.ax[1].set_title("Longitude vs Altitude")

      self.ax[2].plot(self.lat,self.lon)
      self.ax[2].set_title("Trajectory")

      self.canvas.draw()
      self.root.after(500, self.update)

   def run(self):
      self.update()
      self.root.mainloop()

# =========================
# START SYSTEM
# =========================
threading.Thread(target=file_loop, daemon=True).start()

gui = GUI()
gui.run()
