import random
import math

lines = []

lat = 40.7128
lon = -74.0060

alt = 0
velocity = 0

for t in range(1000):

    # BOOST (first ~80 steps)
    if t < 80:
        accel = 30 - (t * 0.2)
    # COAST
    elif t < 160:
        accel = -9.8
    # DESCENT (drag slows fall)
    else:
        accel = -9.8 + random.uniform(2,5)

    velocity += accel * 0.1
    alt += velocity * 0.1

    if alt < 0:
        alt = 0
        velocity = 0

    # GPS drift
    lat += random.uniform(0.00001, 0.00005)
    lon -= random.uniform(0.00001, 0.00005)

    # Atmospheric model
    temp = 15 - (0.0065 * alt) + random.uniform(-0.3,0.3)
    pressure = 101325 * (1 - 2.25577e-5 * alt) ** 5.25588
    humidity = 60 - (alt / 200) + random.uniform(-2,2)

    line = [
        1,1,1,1,
        random.randint(7,10),
        round(lat,6),
        round(lon,6),
        round(alt,2),
        round(random.uniform(-2,2),2),
        round(random.uniform(-2,2),2),
        round(accel,2),
        0,0,0,
        round(temp,2),
        round(pressure,2),
        round(alt,2),
        round(temp+0.1,2),
        round(humidity,2)
    ]

    lines.append(" ".join(map(str,line)))

with open("realistic_flight_data.txt","w") as f:
    for l in lines:
        f.write(l+"\n")

print("Generated 1000 lines of realistic flight data.")
