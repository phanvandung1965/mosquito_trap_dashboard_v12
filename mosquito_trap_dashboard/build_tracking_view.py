import csv
from pathlib import Path

BASE = Path(__file__).resolve().parent
areas_file = BASE / "sample_data_areas.csv"
traps_file = BASE / "sample_data_traps.csv"
obs_file = BASE / "sample_data_observation.csv"
out_file = BASE / "tracking_view.csv"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

areas = read_csv(areas_file)
traps = read_csv(traps_file)
obs = read_csv(obs_file)

area_name_by_id = {a["area_id"]: a.get("area_name", a["area_id"]) for a in areas}
trap_by_id = {t["trap_id"]: t for t in traps}

rows = []
for o in obs:
    trap = trap_by_id.get(o.get("trap_id", ""), {})
    area_id = trap.get("area_id", "")
    rows.append({
        "date": o.get("observed_at", ""),
        "area": area_name_by_id.get(area_id, area_id),
        "trap": trap.get("trap_code", o.get("trap_id", "")),
        "mosquito_name": o.get("species", "unknown"),
        "number_of_mosquitoes": int(o.get("mosquito_count", 0) or 0),
    })

with out_file.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["date", "area", "trap", "mosquito_name", "number_of_mosquitoes"])
    w.writeheader()
    w.writerows(rows)

print(f"Wrote {out_file} ({len(rows)} rows)")
