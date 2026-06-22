import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
traps_file = BASE / "sample_data_traps.csv"
obs_file = BASE / "sample_data_observation.csv"
out_file = BASE / "alerts_snapshot.json"

traps = []
with traps_file.open() as f:
    for r in csv.DictReader(f):
        traps.append(r)

obs = []
with obs_file.open() as f:
    for r in csv.DictReader(f):
        r["mosquito_count"] = int(r["mosquito_count"])
        obs.append(r)

alerts = []

# Rule 1: offline trap => critical alert
for t in traps:
    if t["status"] == "offline":
        alerts.append({
            "alert_type": "offline",
            "severity": "critical",
            "trap_id": t["trap_id"],
            "area_id": t["area_id"],
            "message": f"Trap {t['trap_code']} đang offline",
        })

# Rule 2: spike (latest value > 1.5 * average)
by_trap = defaultdict(list)
for o in obs:
    by_trap[o["trap_id"]].append(o)

for trap_id, rows in by_trap.items():
    rows.sort(key=lambda x: x["observed_at"])
    vals = [r["mosquito_count"] for r in rows]
    if len(vals) < 2:
        continue
    latest = vals[-1]
    avg = sum(vals[:-1]) / max(1, len(vals)-1)
    if latest > 1.5 * avg:
        area_id = next((t["area_id"] for t in traps if t["trap_id"] == trap_id), None)
        alerts.append({
            "alert_type": "spike",
            "severity": "high",
            "trap_id": trap_id,
            "area_id": area_id,
            "message": f"Spike muỗi tại trap {trap_id}: latest={latest}, baseline={round(avg,2)}",
        })

payload = {
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "alert_count": len(alerts),
    "alerts": alerts,
}

out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
print(f"Wrote {out_file}")
