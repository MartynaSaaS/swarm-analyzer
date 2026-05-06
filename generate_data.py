import pandas as pd
import random
from datetime import datetime, timedelta

random.seed(42)

directions = ["North", "Northwest", "West", "Northeast", "East"]
targets = ["Power station", "Bridge", "Fuel depot", "Railway hub", "Military base"]

attacks = []
base_date = datetime(2024, 1, 1)

for i in range(200):
    direction = random.choices(directions, weights=[10, 40, 15, 25, 10])[0]
    if direction == "Northwest":
        target = random.choices(targets, weights=[50, 10, 20, 15, 5])[0]
    elif direction == "Northeast":
        target = random.choices(targets, weights=[10, 15, 10, 50, 15])[0]
    else:
        target = random.choices(targets, weights=[20, 20, 20, 20, 20])[0]
    attacks.append({
        "date": base_date + timedelta(days=random.randint(0, 365)),
        "direction": direction,
        "target": target,
        "drone_count": random.randint(3, 42),
        "hour": random.randint(0, 23)
    })

df = pd.DataFrame(attacks)
df = df.sort_values("date").reset_index(drop=True)
df.to_csv("attacks.csv", index=False)
print(f"Generated {len(df)} attack records")
print(df.head())
