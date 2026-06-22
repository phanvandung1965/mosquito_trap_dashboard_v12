import csv
import json
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
OUT = BASE / "star_schema_output"
OUT.mkdir(exist_ok=True)

areas_file = BASE / "sample_data_areas.csv"
traps_file = BASE / "sample_data_traps.csv"
obs_file = BASE / "sample_data_observation.csv"
alerts_file = BASE / "alerts_snapshot.json"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(s.replace(" ", "T"))


def date_key(dt):
    return int(dt.strftime("%Y%m%d"))


areas = read_csv(areas_file)
traps = read_csv(traps_file)
obs = read_csv(obs_file)
alerts = []
if alerts_file.exists():
    payload = json.loads(alerts_file.read_text(encoding="utf-8"))
    alerts = payload.get("alerts", [])

# ----- Dimensions -----
area_key_map = {}
dim_area = []
for i, a in enumerate(areas, 1):
    area_key_map[a["area_id"]] = i
    dim_area.append({
        "AreaKey": i,
        "area_id": a.get("area_id", ""),
        "area_name": a.get("area_name", ""),
        "district": a.get("district", ""),
        "ward": a.get("ward", ""),
        "latitude": a.get("latitude", ""),
        "longitude": a.get("longitude", ""),
        "risk_level": a.get("risk_level", ""),
    })

trap_key_map = {}
dim_trap = []
for i, t in enumerate(traps, 1):
    trap_key_map[t["trap_id"]] = i
    dim_trap.append({
        "TrapKey": i,
        "trap_id": t.get("trap_id", ""),
        "trap_code": t.get("trap_code", ""),
        "AreaKey": area_key_map.get(t.get("area_id", ""), ""),
        "install_date": t.get("install_date", ""),
        "trap_type": t.get("trap_type", ""),
        "current_status": t.get("status", ""),
        "last_maintenance_at": t.get("last_maintenance_at", ""),
        "battery_level": t.get("battery_level", ""),
    })

status_values = sorted({t.get("status", "unknown") for t in traps})
status_key_map = {s: i + 1 for i, s in enumerate(status_values)}
dim_status = [{"StatusKey": k, "status_name": s} for s, k in status_key_map.items()]

# Date dimension from all dates found in observations + traps + alerts
date_set = set()
for o in obs:
    dt = parse_dt(o.get("observed_at", ""))
    if dt:
        date_set.add(dt.date())
for t in traps:
    for col in ("install_date", "last_maintenance_at"):
        dt = parse_dt(t.get(col, "")) if t.get(col) else None
        if dt:
            date_set.add(dt.date())
for a in alerts:
    at = a.get("alert_time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dt = parse_dt(at)
    if dt:
        date_set.add(dt.date())

sorted_dates = sorted(date_set)
dim_date = []
for d in sorted_dates:
    dt = datetime(d.year, d.month, d.day)
    dim_date.append({
        "DateKey": int(dt.strftime("%Y%m%d")),
        "Date": dt.strftime("%Y-%m-%d"),
        "Year": dt.year,
        "Quarter": f"Q{((dt.month - 1)//3) + 1}",
        "Month": dt.month,
        "MonthName": dt.strftime("%b"),
        "WeekOfYear": int(dt.strftime("%W")),
        "Day": dt.day,
        "DayOfWeek": dt.strftime("%A"),
    })

# ----- Facts -----
fact_observation = []
for idx, o in enumerate(obs, 1):
    dt = parse_dt(o.get("observed_at", ""))
    trap_id = o.get("trap_id", "")
    trap_key = trap_key_map.get(trap_id, "")
    area_key = ""
    if trap_key:
        tr = next((x for x in dim_trap if x["TrapKey"] == trap_key), None)
        area_key = tr["AreaKey"] if tr else ""
    fact_observation.append({
        "ObservationKey": idx,
        "DateKey": date_key(dt) if dt else "",
        "AreaKey": area_key,
        "TrapKey": trap_key,
        "observed_at": o.get("observed_at", ""),
        "mosquito_count": int(o.get("mosquito_count", 0) or 0),
        "species": o.get("species", ""),
        "temperature_c": o.get("temperature_c", ""),
        "humidity_pct": o.get("humidity_pct", ""),
        "rainfall_mm": o.get("rainfall_mm", ""),
    })

fact_trap_health = []
for idx, t in enumerate(traps, 1):
    check_time = t.get("last_maintenance_at", "") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dt = parse_dt(check_time)
    fact_trap_health.append({
        "HealthKey": idx,
        "DateKey": date_key(dt) if dt else "",
        "AreaKey": area_key_map.get(t.get("area_id", ""), ""),
        "TrapKey": trap_key_map.get(t.get("trap_id", ""), ""),
        "StatusKey": status_key_map.get(t.get("status", ""), ""),
        "check_time": check_time,
        "battery_level": t.get("battery_level", ""),
        "signal_strength": "", 
        "error_code": "" 
    })

fact_alert = []
now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
for idx, a in enumerate(alerts, 1):
    alert_time = a.get("alert_time", now_str)
    dt = parse_dt(alert_time)
    area_id = a.get("area_id", "")
    trap_id = a.get("trap_id", "")
    fact_alert.append({
        "AlertKey": idx,
        "DateKey": date_key(dt) if dt else "",
        "AreaKey": area_key_map.get(area_id, ""),
        "TrapKey": trap_key_map.get(trap_id, ""),
        "alert_time": alert_time,
        "alert_type": a.get("alert_type", ""),
        "severity": a.get("severity", ""),
        "resolved": "false",
        "resolved_at": "",
        "message": a.get("message", ""),
    })


def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

write_csv(OUT / "dim_date.csv", dim_date)
write_csv(OUT / "dim_area.csv", dim_area)
write_csv(OUT / "dim_trap.csv", dim_trap)
write_csv(OUT / "dim_status.csv", dim_status)
write_csv(OUT / "fact_observation.csv", fact_observation)
write_csv(OUT / "fact_trap_health.csv", fact_trap_health)
write_csv(OUT / "fact_alert.csv", fact_alert)

summary = {
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "output_dir": str(OUT),
    "counts": {
        "dim_date": len(dim_date),
        "dim_area": len(dim_area),
        "dim_trap": len(dim_trap),
        "dim_status": len(dim_status),
        "fact_observation": len(fact_observation),
        "fact_trap_health": len(fact_trap_health),
        "fact_alert": len(fact_alert),
    }
}
(OUT / "etl_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))
