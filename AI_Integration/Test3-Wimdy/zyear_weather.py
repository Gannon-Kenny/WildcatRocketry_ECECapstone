import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, accuracy_score, brier_score_loss
from sklearn.inspection import permutation_importance
from sklearn.calibration import calibration_curve
import matplotlib.pyplot as plt
import seaborn as sns
import threading
import numpy as np

class_map = {
   0: "Fair          : ",
   1: "Fog           : ",
   2: "Partly Cloudy : ",
   3: "Mostly Cloudy : ",
   4: "Cloudy        : ",
   5: "Light Rain    : ",
   6: "Rain          : ",
   7: "Heavy Rain    : ",
   8: "Light Snow    : ",
   9: "Heavy Snow    : "
}

historic_file = "year_historic_weather_data.txt"
df_full = pd.read_csv(historic_file, sep=" ", header=None,
   names=["Month","Day","Year","Hour","Temp","Humidity","Pressure","Wind","Condition"])

df_full["Condition"] = df_full["Condition"].fillna(10).astype(int)
df_full = df_full.sort_values(by=["Year","Month","Day","Hour"]).reset_index(drop=True)

df_full["Temp_Lag1"] = df_full["Temp"].shift(1)
df_full["Humidity_Lag1"] = df_full["Humidity"].shift(1)
df_full["Pressure_Lag1"] = df_full["Pressure"].shift(1)
df_full["Wind_Lag1"] = df_full["Wind"].shift(1)
df_full["Temp_Roll3"] = df_full["Temp"].rolling(3).mean()
df_full["Humidity_Roll3"] = df_full["Humidity"].rolling(3).mean()
df_full["Pressure_Roll3"] = df_full["Pressure"].rolling(3).mean()
df_full["Wind_Roll3"] = df_full["Wind"].rolling(3).mean()
df_full = df_full.dropna().reset_index(drop=True)

feature_cols_wind = ["Month","Day","Hour","Temp","Humidity","Pressure","Wind",
   "Temp_Lag1","Humidity_Lag1","Pressure_Lag1","Wind_Lag1",
   "Temp_Roll3","Humidity_Roll3","Pressure_Roll3","Wind_Roll3"]

feature_cols_nowind = ["Month","Day","Hour","Temp","Humidity","Pressure",
   "Temp_Lag1","Humidity_Lag1","Pressure_Lag1",
   "Temp_Roll3","Humidity_Roll3","Pressure_Roll3"]

X_wind = df_full[feature_cols_wind]
X_nowind = df_full[feature_cols_nowind]
y = df_full["Condition"].astype(int)

X_train_w, X_test_w, y_train_w, y_test_w = train_test_split(X_wind, y, test_size=0.2, random_state=42)
X_train_nw, X_test_nw, y_train_nw, y_test_nw = train_test_split(X_nowind, y, test_size=0.2, random_state=42)

rf_wind = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42)
rf_nowind = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42)

rf_wind.fit(X_train_w, y_train_w)
rf_nowind.fit(X_train_nw, y_train_nw)

def print_weather_probabilities(probs, classes):
   for cls, p in zip(classes, probs):
      if cls == 10:
         continue
      label = class_map.get(cls, f"Class {cls} : ")
      print(f"{label}{p*100:5.1f}%")

realtime_file = "rocket_weather_data.txt"
with open(realtime_file, "r") as f:
   last_line = f.readlines()[-1]

row_values = list(map(float, last_line.strip().split()))
latest_data = pd.DataFrame([row_values[:8]],
   columns=["Month","Day","Year","Hour","Temp","Humidity","Pressure","Wind"])

latest_data["Temp_Lag1"] = latest_data["Temp"]
latest_data["Humidity_Lag1"] = latest_data["Humidity"]
latest_data["Pressure_Lag1"] = latest_data["Pressure"]
latest_data["Wind_Lag1"] = latest_data["Wind"]
latest_data["Temp_Roll3"] = latest_data["Temp"]
latest_data["Humidity_Roll3"] = latest_data["Humidity"]
latest_data["Pressure_Roll3"] = latest_data["Pressure"]
latest_data["Wind_Roll3"] = latest_data["Wind"]

X_current_w = latest_data[feature_cols_wind]
X_current_nw = latest_data[feature_cols_nowind]

probs_wind = None
probs_nowind = None

def run_wind():
   global probs_wind
   probs_wind = rf_wind.predict_proba(X_current_w)[0]

def run_nowind():
   global probs_nowind
   probs_nowind = rf_nowind.predict_proba(X_current_nw)[0]

t1 = threading.Thread(target=run_wind)
t2 = threading.Thread(target=run_nowind)
t1.start(); t2.start()
t1.join(); t2.join()

print("Prediction WITH wind:")
print_weather_probabilities(probs_wind, rf_wind.classes_)
print("\nPrediction WITHOUT wind:")
print_weather_probabilities(probs_nowind, rf_nowind.classes_)

labels = [class_map.get(cls, f"Class {cls} : ").strip(" :") for cls in rf_wind.classes_ if cls != 10]
values_w = [p for cls,p in zip(rf_wind.classes_, probs_wind) if cls != 10]
values_nw = [p for cls,p in zip(rf_nowind.classes_, probs_nowind) if cls != 10]

plt.figure(figsize=(8,8))
plt.pie(values_w, labels=labels, autopct="%1.1f%%", startangle=140)
plt.title("Predicted Weather Probabilities (With Wind)")
plt.savefig("weather_prediction_with_wind.png", bbox_inches="tight")
plt.clf()

plt.figure(figsize=(8,8))
plt.pie(values_nw, labels=labels, autopct="%1.1f%%", startangle=140)
plt.title("Predicted Weather Probabilities (No Wind)")
plt.savefig("weather_prediction_without_wind.png", bbox_inches="tight")
plt.clf()

diff = np.array(values_w) - np.array(values_nw)
plt.figure(figsize=(10,6))
plt.bar(labels, diff)
plt.axhline(0)
plt.ylabel("Probability Difference")
plt.title("Wind vs No-Wind Prediction Difference")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("weather_prediction_difference.png")
plt.clf()

imp_w = rf_wind.feature_importances_
order_w = np.argsort(imp_w)
plt.figure(figsize=(10,6))
plt.barh(range(len(order_w)), imp_w[order_w])
plt.yticks(range(len(order_w)), np.array(feature_cols_wind)[order_w])
plt.title("Feature Importance (With Wind)")
plt.tight_layout()
plt.savefig("feature_importance_with_wind.png")
plt.clf()

imp_nw = rf_nowind.feature_importances_
order_nw = np.argsort(imp_nw)
plt.figure(figsize=(10,6))
plt.barh(range(len(order_nw)), imp_nw[order_nw])
plt.yticks(range(len(order_nw)), np.array(feature_cols_nowind)[order_nw])
plt.title("Feature Importance (No Wind)")
plt.tight_layout()
plt.savefig("feature_importance_without_wind.png")
plt.clf()

result_perm_w = permutation_importance(rf_wind, X_test_w, y_test_w, n_repeats=10, random_state=42, n_jobs=-1)
importances_perm_w = result_perm_w.importances_mean
order_perm_w = np.argsort(importances_perm_w)
plt.figure(figsize=(10,6))
plt.barh(range(len(order_perm_w)), importances_perm_w[order_perm_w])
plt.yticks(range(len(order_perm_w)), np.array(feature_cols_wind)[order_perm_w])
plt.title("Permutation Feature Importance (With Wind)")
plt.tight_layout()
plt.savefig("perm_importance_with_wind.png")
plt.clf()

result_perm_nw = permutation_importance(rf_nowind, X_test_nw, y_test_nw, n_repeats=10, random_state=42, n_jobs=-1)
importances_perm_nw = result_perm_nw.importances_mean
order_perm_nw = np.argsort(importances_perm_nw)
plt.figure(figsize=(10,6))
plt.barh(range(len(order_perm_nw)), importances_perm_nw[order_perm_nw])
plt.yticks(range(len(order_perm_nw)), np.array(feature_cols_nowind)[order_perm_nw])
plt.title("Permutation Feature Importance (No Wind)")
plt.tight_layout()
plt.savefig("perm_importance_without_wind.png")
plt.clf()

def evaluate_model(model, X_test, y_test, name):
   preds = model.predict(X_test)
   pure_acc = (preds == y_test).mean()
   group_map = {0:0,1:1,2:1,3:1,4:1,5:2,6:2,7:2,8:3,9:3}
   grouped_preds = [group_map.get(p,p) for p in preds]
   grouped_true = [group_map.get(t,t) for t in y_test]
   varied_acc = (np.array(grouped_preds) == np.array(grouped_true)).mean()
   print(f"\n{name}\nPure Accuracy   : {pure_acc*100:5.2f}%\nVaried Accuracy : {varied_acc*100:5.2f}%")

evaluate_model(rf_wind, X_test_w, y_test_w, "Model WITH Wind")
evaluate_model(rf_nowind, X_test_nw, y_test_nw, "Model WITHOUT Wind")

def plot_confusion(model, X_test, y_test, title, filename):
   preds = model.predict(X_test)
   cm = confusion_matrix(y_test, preds)
   labels_cm = [class_map.get(i,str(i)).strip(" :") for i in sorted(set(y_test))]
   plt.figure(figsize=(10,8))
   sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels_cm, yticklabels=labels_cm)
   plt.xlabel("Predicted"); plt.ylabel("Actual"); plt.title(title)
   plt.tight_layout(); plt.savefig(filename); plt.clf()

plot_confusion(rf_wind, X_test_w, y_test_w, "Confusion Matrix (With Wind)", "confusion_with_wind.png")
plot_confusion(rf_nowind, X_test_nw, y_test_nw, "Confusion Matrix (No Wind)", "confusion_without_wind.png")

def heidke_skill_score(y_true, y_pred):
   acc = accuracy_score(y_true, y_pred)
   counts = np.bincount(y_true)
   baseline = counts.max()/counts.sum()
   return (acc - baseline)/(1 - baseline)

def evaluate_skill(model, X_test, y_test, name):
   preds = model.predict(X_test)
   acc = accuracy_score(y_test, preds)
   hss = heidke_skill_score(y_test, preds)
   print(f"\n{name}\nAccuracy : {acc*100:5.2f}%\nHeidke Skill Score : {hss:5.3f}")
   return acc, hss

acc_w, hss_w = evaluate_skill(rf_wind, X_test_w, y_test_w, "Model WITH Wind")
acc_nw, hss_nw = evaluate_skill(rf_nowind, X_test_nw, y_test_nw, "Model WITHOUT Wind")

labels_skill = ["With Wind","Without Wind"]
scores_skill = [hss_w, hss_nw]
plt.figure(figsize=(6,5))
plt.bar(labels_skill, scores_skill)
plt.ylabel("Heidke Skill Score"); plt.title("Forecast Skill Comparison")
plt.axhline(0); plt.tight_layout(); plt.savefig("skill_score_comparison.png"); plt.clf()

def reliability_plot(model, X_test, y_test, title, filename):
   probs = model.predict_proba(X_test)
   rain_classes = [5,6,7]
   rain_probs = [sum(row[i] for i,cls in enumerate(model.classes_) if cls in rain_classes) for row in probs]
   rain_truth = [1 if y in rain_classes else 0 for y in y_test]
   prob_true, prob_pred = calibration_curve(rain_truth, rain_probs, n_bins=10)
   plt.figure(figsize=(6,6))
   plt.plot(prob_pred, prob_true, marker="o", label="Model")
   plt.plot([0,1],[0,1], linestyle="--", label="Perfect Calibration")
   plt.xlabel("Predicted Rain Probability"); plt.ylabel("Observed Rain Frequency")
   plt.title(title); plt.legend(); plt.tight_layout()
   plt.savefig(filename); plt.clf()

reliability_plot(rf_wind, X_test_w, y_test_w, "Reliability Diagram (With Wind)", "reliability_with_wind.png")
reliability_plot(rf_nowind, X_test_nw, y_test_nw, "Reliability Diagram (No Wind)", "reliability_without_wind.png")

def brier_rain_score(model, X_test, y_test, name):
   probs = model.predict_proba(X_test)
   rain_classes = [5,6,7]
   rain_probs = [sum(row[i] for i,cls in enumerate(model.classes_) if cls in rain_classes) for row in probs]
   rain_truth = [1 if y in rain_classes else 0 for y in y_test]
   score = brier_score_loss(rain_truth, rain_probs)
   baseline = np.mean(rain_truth)
   baseline_probs = [baseline]*len(rain_truth)
   baseline_score = brier_score_loss(rain_truth, baseline_probs)
   skill = 1 - (score / baseline_score)
   print(f"\n{name}\nBrier Score        : {score:.4f}\nBaseline Brier     : {baseline_score:.4f}\nBrier Skill Score  : {skill:.4f}")
   return score, skill

brier_w, skill_w = brier_rain_score(rf_wind, X_test_w, y_test_w, "Wind Model")
brier_nw, skill_nw = brier_rain_score(rf_nowind, X_test_nw, y_test_nw, "No-Wind Model")

labels_brier = ["Wind","No Wind"]
scores_brier = [skill_w, skill_nw]
plt.figure(figsize=(6,5))
plt.bar(labels_brier, scores_brier)
plt.ylabel("Brier Skill Score"); plt.title("Rain Forecast Skill")
plt.axhline(0); plt.tight_layout(); plt.savefig("brier_skill_comparison.png"); plt.clf()
