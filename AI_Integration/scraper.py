import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time

API_URL = "https://api.weather.com/v1/location/KRME:9:US/observations/historical.json"
API_KEY = "e1f10a1e78da46f5b10a1e78da96f525"
HEADERS = {
   "User-Agent": "Mozilla/5.0"
}

def map_condition(text):
   if not text:
      return 10
   text = text.lower()
   if "fair" in text:
      return 0
   elif "fog" in text:
      return 1
   elif "partly" in text:
      return 2
   elif "mostly" in text:
      return 3
   elif text == "cloudy":
      return 4
   elif "light rain" in text:
      return 5
   elif "heavy rain" in text:
      return 7
   elif "rain" in text:
      return 6
   elif "light snow" in text:
      return 8
   elif "heavy snow" in text:
      return 9
   else:
      return 10

def round_hour(dt):
   if dt.minute >= 30:
      dt = dt + timedelta(hours=1)
   return dt.replace(minute=0, second=0, microsecond=0)

def fetch_day(date_obj):
   params = {
      "apiKey": API_KEY,
      "units": "e",
      "startDate": date_obj.strftime("%Y%m%d")
   }
   try:
      r = requests.get(API_URL, params=params, headers=HEADERS)
      r.raise_for_status()
      return r.json()
   except requests.RequestException as e:
      print(f"Error fetching {date_obj.strftime('%Y-%m-%d')}: {e}")
      return {}

def process_observations(data, date_obj):
   lines = []
   observations = data.get("observations", [])

   if not observations:
      dt = date_obj.replace(hour=12)
      mm = dt.strftime("%m")
      dd = dt.strftime("%d")
      yyyy = dt.strftime("%Y")
      tt = f"{dt.hour:02d}"

      temp = 0
      humidity = 0
      pressure = 0.00
      wind = 0
      condition = 10

      line = f"{mm} {dd} {yyyy} {tt} {temp} {humidity} {pressure:.2f} {wind} {condition}"
      lines.append(line)
      return lines

   for obs in observations:
      from datetime import datetime, timedelta
      from zoneinfo import ZoneInfo

      utc_dt = datetime.fromtimestamp(obs.get("valid_time_gmt", date_obj.timestamp()), tz=ZoneInfo("UTC"))
      dt = utc_dt.astimezone(ZoneInfo("America/New_York"))

      if dt.minute >= 30:
         dt = dt + timedelta(hours=1)
      dt = dt.replace(minute=0, second=0, microsecond=0)

      if dt.hour < 7 or dt.hour > 21:
         continue

      mm = dt.strftime("%m")
      dd = dt.strftime("%d")
      yyyy = dt.strftime("%Y")
      tt = f"{dt.hour:02d}"

      temp = obs.get("temp") if obs.get("temp") is not None else 0
      humidity = obs.get("rh") if obs.get("rh") is not None else 0
      pressure = obs.get("pressure") if obs.get("pressure") is not None else 0.00
      wind = obs.get("wspd") if obs.get("wspd") is not None else 0
      condition = map_condition(obs.get("wx_phrase"))

      line = f"{mm} {dd} {yyyy} {tt} {temp} {humidity} {pressure:.2f} {wind} {condition}"
      lines.append(line)

   return lines

def main():
   today = datetime.today()
   start_year = today.year - 7

   with open("historic_weather_data.txt", "a") as f:
      for year in range(start_year, today.year):
         for month in [3, 4, 5]:
            start_date = datetime(year, month, 1)

            while start_date.month == month:
               print(f"Fetching {start_date.strftime('%Y-%m-%d')}")

               data = fetch_day(start_date)
               lines = process_observations(data, start_date)

               if lines:
                  for line in lines:
                     f.write(line + "\n")
                  print(f"Sample: {lines[0]}")
               else:
                  print("No data returned for this day.")

               start_date += timedelta(days=1)
               time.sleep(0.5)

   print("Done.")

if __name__ == "__main__":
   main()
