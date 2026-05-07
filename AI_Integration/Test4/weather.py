import pandas as pd
import numpy as np
import threading
import time
import tkinter as tk
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mticker
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, accuracy_score
import sys

shutdown = False

scraped_data = {
    "statuses":[0,0,0,0],
    "satelite":0,
    "latilong":[0.0,0.0],
    "alt":0.0,
    "acc":[0.0,0.0,0.0],
    "gps":[0.0,0.0,0.0],
    "temp1":0.0,
    "pressure":0.0,
    "altFalse":0.0,
    "temp2":0.0,
    "humidity":0.0
}

flight_started = False
ml_done = False
ml_result = None

remap = {0:0,1:0,2:1,3:1,4:1,5:2,6:2,7:2,8:3,9:3,10:4}

class_map = {
    0:"Fair",
    1:"Cloudy",
    2:"Rain",
    3:"Snow",
    4:"Unspecified"
}

df = pd.read_csv(
    "historic_weather_data.txt",
    sep=" ",
    header=None,
    names=["Month","Day","Year","Hour","Temp","Humidity","Pressure","Wind","Condition"]
)

df["Condition"] = df["Condition"].fillna(10).astype(int).map(remap)

for c in ["Temp","Humidity","Pressure","Wind"]:
    df[f"{c}_Lag1"] = df[c].shift(1)
    df[f"{c}_Roll3"] = df[c].rolling(3).mean()

df = df.dropna()

FEATURES = [
    "Month","Day","Hour","Temp","Humidity","Pressure","Wind",
    "Temp_Lag1","Humidity_Lag1","Pressure_Lag1","Wind_Lag1",
    "Temp_Roll3","Humidity_Roll3","Pressure_Roll3","Wind_Roll3"
]

X_train, X_test, y_train, y_test = train_test_split(
    df[FEATURES],
    df["Condition"],
    test_size=0.2,
    random_state=42,
    stratify=df["Condition"]
)

model = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42)
model.fit(X_train, y_train)

def build_row():
    now = time.localtime()

    base = {
        "Month": now.tm_mon,
        "Day": now.tm_mday,
        "Hour": now.tm_hour,
        "Temp": scraped_data["temp1"],
        "Humidity": scraped_data["humidity"],
        "Pressure": scraped_data["pressure"] * 0.02953,
        "Wind": 0.0
    }

    row = pd.DataFrame([base])

    for f in FEATURES:
        if f not in row.columns:
            row[f] = 0.0

    return row[FEATURES]

def run_ml_once(reason):
    global ml_done, ml_result

    if ml_done:
        return
    ml_done = True

    X = build_row()

    probs = model.predict_proba(X)[0]
    ml_result = [(class_map[c], float(p)) for c,p in zip(model.classes_, probs)]

    labels = [class_map[c] for c in model.classes_]

    plt.figure()
    plt.pie(probs, labels=labels, autopct="%1.1f%%")
    plt.title("Weather Prediction")
    plt.savefig("ml_pie.png")
    plt.close()

    plt.figure()
    plt.bar(labels, probs)
    plt.title("Weather Probabilities")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig("ml_bar.png")
    plt.close()

    # FEATURE IMPORTANCE
    imp = model.feature_importances_
    order = np.argsort(imp)

    plt.figure(figsize=(8,5))
    plt.barh(np.array(FEATURES)[order], imp[order])
    plt.title("Feature Importance")
    plt.tight_layout()
    plt.savefig("ml_feature_importance.png")
    plt.close()

    preds_full = model.predict(X_test)
    cm = confusion_matrix(y_test, preds_full)

    plt.figure(figsize=(6,5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=labels,
                yticklabels=labels)
    plt.title("Confusion Matrix")
    plt.tight_layout()
    plt.savefig("ml_confusion.png")
    plt.close()

    acc = accuracy_score(y_test, preds_full)

    plt.figure()
    plt.bar(["Accuracy"], [acc])
    plt.ylim(0,1)
    plt.title("Model Accuracy")
    plt.savefig("ml_accuracy.png")
    plt.close()

def file_loop(filename="dummy_flight_data.txt", delay=0.05):
    global flight_started

    with open(filename, "r") as f:
        for line in f:

            if shutdown:
                break

            vals = line.strip().split()
            if len(vals) != 19:
                continue

            scraped_data["statuses"] = list(map(int, vals[0:4]))
            scraped_data["satelite"] = int(vals[4])
            scraped_data["latilong"] = [float(vals[5]), float(vals[6])]
            scraped_data["alt"] = float(vals[7])
            scraped_data["acc"] = list(map(float, vals[8:11]))
            scraped_data["gps"] = list(map(float, vals[11:14]))
            scraped_data["temp1"] = float(vals[14])
            scraped_data["pressure"] = float(vals[15])
            scraped_data["altFalse"] = float(vals[16])
            scraped_data["temp2"] = float(vals[17])
            scraped_data["humidity"] = float(vals[18])

            flight_started = True
            time.sleep(delay)

    run_ml_once("file_complete")

threading.Thread(target=file_loop, daemon=True).start()

class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Rocket Telemetry")

        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.fig, self.ax = plt.subplots(3,1,figsize=(7,9), gridspec_kw={'hspace':0.9})

        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        self.canvas = FigureCanvasTkAgg(self.fig, self.root)
        self.canvas.get_tk_widget().pack()

        self.label = tk.Label(self.root, text="")
        self.label.pack()

        self.lat=[]
        self.lon=[]
        self.alt=[]

        self.sc = None
        self.cbar = None

        self.setup_axes()

    def setup_axes(self):

        formatter = mticker.ScalarFormatter(useOffset=False)
        formatter.set_scientific(False)

        for a in self.ax:
            a.xaxis.set_major_formatter(formatter)
            a.yaxis.set_major_formatter(formatter)

        self.ax[0].set_title("Latitude vs Altitude")
        self.ax[1].set_title("Longitude vs Altitude")
        self.ax[2].set_title("GPS Location (Altitude Colored)")

        for a in self.ax:
            a.grid(True)

    def close(self):
        global shutdown
        shutdown = True
        self.root.destroy()
        sys.exit(0)

    def update(self):
        if shutdown:
            return

        if flight_started:

            lat, lon = scraped_data["latilong"]

            self.lat.append(lat)
            self.lon.append(lon)
            self.alt.append(scraped_data["alt"])

            self.ax[0].plot(self.lat, self.alt)
            self.ax[1].plot(self.lon, self.alt)

            if len(self.lat) > 1:
                self.ax[2].plot(self.lat, self.lon, color="purple")

                self.sc = self.ax[2].scatter(
                    self.lat,
                    self.lon,
                    c=self.alt,
                    cmap="plasma",
                    s=10
                )

                if self.cbar is None:
                    self.cbar = self.fig.colorbar(self.sc, ax=self.ax[2])

            self.canvas.draw()

        if ml_result:
            self.label.config(
                text="\n".join([f"{k}: {v*100:.1f}%" for k,v in ml_result])
            )

        self.root.after(150, self.update)

    def run(self):
        self.update()
        self.root.mainloop()

GUI().run()