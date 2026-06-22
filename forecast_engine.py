import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
obs_file = BASE / "sample_data_observation.csv"
out_file = BASE / "forecast_snapshot.json"

obs = []
with obs_file.open() as f:
    for r in csv.DictReader(f):
        r["mosquito_count"] = int(r["mosquito_count"])
        obs.append(r)

# Aggregate by timestamp
by_time = {}
for r in obs:
    ts = r["observed_at"]
    by_time[ts] = by_time.get(ts, 0) + r["mosquito_count"]

times = sorted(by_time.keys())
series = [{"time": t, "count": by_time[t]} for t in times]

# Simple forecast: linear trend on last 2 points, fallback flat
forecast = []
if len(times) >= 2:
    t1 = datetime.fromisoformat(times[-2].replace(" ", "T"))
    t2 = datetime.fromisoformat(times[-1].replace(" ", "T"))
    v1 = by_time[times[-2]]
    v2 = by_time[times[-1]]
    step = t2 - t1 if t2 > t1 else timedelta(hours=6)
    slope = v2 - v1
    base_t = t2
    base_v = v2
    for i in range(1, 4):
        nt = base_t + step * i
        nv = max(0, round(base_v + slope * i))
        forecast.append({"time": nt.strftime("%Y-%m-%d %H:%M:%S"), "count": nv})
elif len(times) == 1:
    t = datetime.fromisoformat(times[0].replace(" ", "T"))
    v = by_time[times[0]]
    for i in range(1, 4):
        nt = t + timedelta(hours=6 * i)
        forecast.append({"time": nt.strftime("%Y-%m-%d %H:%M:%S"), "count": v})

payload = {
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "method": "linear_last_2_points",
    "history": series,
    "forecast": forecast,
}

out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
print(f"Wrote {out_file}")
