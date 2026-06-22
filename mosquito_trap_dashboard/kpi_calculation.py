import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
traps_file = BASE / "sample_data_traps.csv"
obs_file = BASE / "sample_data_observation.csv"
out_file = BASE / "kpi_snapshot.json"

traps = []
with traps_file.open() as f:
    reader = csv.DictReader(f)
    for r in reader:
        r["battery_level"] = int(r["battery_level"])
        traps.append(r)

obs = []
with obs_file.open() as f:
    reader = csv.DictReader(f)
    for r in reader:
        r["mosquito_count"] = int(r["mosquito_count"])
        obs.append(r)

status_counter = Counter(t["status"] for t in traps)
trap_area = {t["trap_id"]: t["area_id"] for t in traps}

count_by_area = defaultdict(int)
for r in obs:
    area = trap_area.get(r["trap_id"])
    if area:
        count_by_area[area] += r["mosquito_count"]

total_traps = len(traps)
active_traps = status_counter.get("active", 0)
offline_traps = status_counter.get("offline", 0)
maintenance_traps = status_counter.get("maintenance", 0)
total_mosquito = sum(r["mosquito_count"] for r in obs)
avg_per_active = round(total_mosquito / active_traps, 2) if active_traps else 0

payload = {
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "kpis": {
        "total_traps": total_traps,
        "active_traps": active_traps,
        "offline_traps": offline_traps,
        "maintenance_traps": maintenance_traps,
        "total_mosquito_count": total_mosquito,
        "avg_mosquito_per_active_trap": avg_per_active,
    },
    "top_areas": sorted(
        [{"area_id": k, "mosquito_count": v} for k, v in count_by_area.items()],
        key=lambda x: x["mosquito_count"],
        reverse=True,
    ),
}

out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
print(f"Wrote {out_file}")
