import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
kpi_file = BASE / "kpi_snapshot.json"
out_file = BASE / "dashboard_mvp.html"

if not kpi_file.exists():
    raise SystemExit("kpi_snapshot.json not found. Run kpi_calculation.py first.")

data = json.loads(kpi_file.read_text())
k = data["kpis"]
areas = data.get("top_areas", [])

rows = "".join(
    f"<tr><td>{i+1}</td><td>{a['area_id']}</td><td>{a['mosquito_count']}</td></tr>"
    for i, a in enumerate(areas)
)

html = f"""<!doctype html>
<html lang='vi'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>Mosquito Trap Dashboard MVP</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 20px; background: #f7f9fc; }}
    .header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; }}
    .grid {{ display:grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
    .card {{ background:#fff; border-radius:12px; padding:14px; box-shadow: 0 1px 6px rgba(0,0,0,.08); }}
    .k {{ font-size:12px; color:#64748b; }}
    .v {{ font-size:28px; font-weight:700; margin-top:4px; }}
    table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:12px; overflow:hidden; }}
    th, td {{ border-bottom:1px solid #eef2f7; padding:10px; text-align:left; }}
    th {{ background:#f1f5f9; }}
  </style>
</head>
<body>
  <div class='header'>
    <h2>Dashboard theo dõi bẫy muỗi (MVP)</h2>
    <div>Cập nhật: {data['generated_at']}</div>
  </div>

  <div class='grid'>
    <div class='card'><div class='k'>Total Traps</div><div class='v'>{k['total_traps']}</div></div>
    <div class='card'><div class='k'>Active Traps</div><div class='v'>{k['active_traps']}</div></div>
    <div class='card'><div class='k'>Offline Traps</div><div class='v'>{k['offline_traps']}</div></div>
    <div class='card'><div class='k'>Maintenance Traps</div><div class='v'>{k['maintenance_traps']}</div></div>
    <div class='card'><div class='k'>Total Mosquito Count</div><div class='v'>{k['total_mosquito_count']}</div></div>
    <div class='card'><div class='k'>Avg Mosquito / Active Trap</div><div class='v'>{k['avg_mosquito_per_active_trap']}</div></div>
  </div>

  <h3 style='margin-top:24px;'>Top khu vực theo mật độ muỗi</h3>
  <table>
    <thead><tr><th>#</th><th>Khu vực</th><th>Số muỗi</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""

out_file.write_text(html)
print(f"Wrote {out_file}")
