import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
areas_file = BASE / "sample_data_areas.csv"
traps_file = BASE / "sample_data_traps.csv"
obs_file = BASE / "sample_data_observation.csv"
out_file = BASE / "dashboard_v2.html"

areas = []
with areas_file.open() as f:
    for r in csv.DictReader(f):
        areas.append(r)

traps = []
with traps_file.open() as f:
    for r in csv.DictReader(f):
        r["battery_level"] = int(r["battery_level"])
        traps.append(r)

obs = []
with obs_file.open() as f:
    for r in csv.DictReader(f):
        r["mosquito_count"] = int(r["mosquito_count"])
        obs.append(r)

payload = {
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "areas": areas,
    "traps": traps,
    "observations": obs,
}

html = f"""<!doctype html>
<html lang='vi'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>Mosquito Dashboard V2</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 16px; background:#f4f7fb; color:#0f172a; }}
    .top {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; }}
    .filters {{ display:grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap:8px; margin-bottom:12px; }}
    .card-grid {{ display:grid; grid-template-columns: repeat(6, 1fr); gap:10px; margin-bottom:14px; }}
    .card {{ background:#fff; border-radius:12px; padding:12px; box-shadow:0 1px 6px rgba(0,0,0,.08); }}
    .k {{ font-size:12px; color:#64748b; }}
    .v {{ font-size:24px; font-weight:700; margin-top:4px; }}
    .layout {{ display:grid; grid-template-columns: 1.2fr 1fr; gap:12px; }}
    .panel {{ background:#fff; border-radius:12px; padding:12px; box-shadow:0 1px 6px rgba(0,0,0,.08); }}
    #trendSvg {{ width:100%; height:280px; border:1px solid #e2e8f0; border-radius:8px; background:#fff; }}
    .heatmap {{ display:grid; grid-template-columns: repeat(3, 1fr); gap:8px; }}
    .heatbox {{ border-radius:10px; padding:10px; color:#111827; font-weight:600; min-height:72px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
    th, td {{ text-align:left; padding:8px; border-bottom:1px solid #eef2f7; font-size:13px; }}
    th {{ background:#f8fafc; }}
  </style>
</head>
<body>
  <div class='top'>
    <h2>Dashboard bẫy muỗi V2 (Interactive)</h2>
    <div>Cập nhật: <b>{payload['generated_at']}</b></div>
  </div>

  <div class='filters'>
    <select id='areaFilter'><option value='ALL'>Tất cả khu vực</option></select>
    <select id='statusFilter'>
      <option value='ALL'>Tất cả trạng thái bẫy</option>
      <option value='active'>active</option>
      <option value='offline'>offline</option>
      <option value='maintenance'>maintenance</option>
    </select>
    <input id='fromDate' type='datetime-local' />
    <input id='toDate' type='datetime-local' />
  </div>

  <div class='card-grid'>
    <div class='card'><div class='k'>Total Traps</div><div class='v' id='kTotalTraps'>0</div></div>
    <div class='card'><div class='k'>Active</div><div class='v' id='kActive'>0</div></div>
    <div class='card'><div class='k'>Offline</div><div class='v' id='kOffline'>0</div></div>
    <div class='card'><div class='k'>Maintenance</div><div class='v' id='kMaint'>0</div></div>
    <div class='card'><div class='k'>Total Mosquito</div><div class='v' id='kMosq'>0</div></div>
    <div class='card'><div class='k'>Avg/Active Trap</div><div class='v' id='kAvg'>0</div></div>
  </div>

  <div class='layout'>
    <div class='panel'>
      <h3>Xu hướng theo thời gian</h3>
      <svg id='trendSvg' viewBox='0 0 800 280'></svg>
      <table>
        <thead><tr><th>Thời điểm</th><th>Tổng muỗi</th></tr></thead>
        <tbody id='trendTable'></tbody>
      </table>
    </div>
    <div class='panel'>
      <h3>Heatmap theo khu vực</h3>
      <div id='heatmap' class='heatmap'></div>
      <h3 style='margin-top:14px;'>Top khu vực</h3>
      <table>
        <thead><tr><th>#</th><th>Khu vực</th><th>Số muỗi</th></tr></thead>
        <tbody id='topAreaTable'></tbody>
      </table>
    </div>
  </div>

<script>
const DATA = {json.dumps(payload, ensure_ascii=False)};

const areaFilter = document.getElementById('areaFilter');
const statusFilter = document.getElementById('statusFilter');
const fromDate = document.getElementById('fromDate');
const toDate = document.getElementById('toDate');

const areaMap = Object.fromEntries(DATA.areas.map(a => [a.area_id, a]));
const trapMap = Object.fromEntries(DATA.traps.map(t => [t.trap_id, t]));

for (const a of DATA.areas) {{
  const op = document.createElement('option');
  op.value = a.area_id; op.textContent = `${{a.area_id}} - ${{a.area_name}}`;
  areaFilter.appendChild(op);
}}

const fmtInput = (s) => s.replace(' ', 'T').slice(0,16);
const sortedTimes = [...new Set(DATA.observations.map(o => o.observed_at))].sort();
if (sortedTimes.length) {{
  fromDate.value = fmtInput(sortedTimes[0]);
  toDate.value = fmtInput(sortedTimes[sortedTimes.length-1]);
}}

function inRange(ts) {{
  const t = new Date(ts.replace(' ','T')).getTime();
  const from = fromDate.value ? new Date(fromDate.value).getTime() : -Infinity;
  const to = toDate.value ? new Date(toDate.value).getTime() : Infinity;
  return t >= from && t <= to;
}}

function heatColor(value, max) {{
  if (!max) return '#e2e8f0';
  const ratio = value / max;
  const r = Math.round(255);
  const g = Math.round(240 - ratio*120);
  const b = Math.round(240 - ratio*180);
  return `rgb(${{r}},${{g}},${{b}})`;
}}

function render() {{
  const af = areaFilter.value;
  const sf = statusFilter.value;

  const filteredTraps = DATA.traps.filter(t => (af==='ALL' || t.area_id===af) && (sf==='ALL' || t.status===sf));
  const trapIds = new Set(filteredTraps.map(t => t.trap_id));
  const filteredObs = DATA.observations.filter(o => trapIds.has(o.trap_id) && inRange(o.observed_at));

  const active = filteredTraps.filter(t=>t.status==='active').length;
  const offline = filteredTraps.filter(t=>t.status==='offline').length;
  const maint = filteredTraps.filter(t=>t.status==='maintenance').length;
  const totalMosq = filteredObs.reduce((s,o)=>s+o.mosquito_count,0);
  const avg = active ? (totalMosq/active).toFixed(2) : 0;

  document.getElementById('kTotalTraps').textContent = filteredTraps.length;
  document.getElementById('kActive').textContent = active;
  document.getElementById('kOffline').textContent = offline;
  document.getElementById('kMaint').textContent = maint;
  document.getElementById('kMosq').textContent = totalMosq;
  document.getElementById('kAvg').textContent = avg;

  const byTime = {{}};
  for (const o of filteredObs) byTime[o.observed_at] = (byTime[o.observed_at] || 0) + o.mosquito_count;
  const times = Object.keys(byTime).sort();

  const tbody = document.getElementById('trendTable');
  tbody.innerHTML = times.map(t => `<tr><td>${{t}}</td><td>${{byTime[t]}}</td></tr>`).join('');

  const svg = document.getElementById('trendSvg');
  const W=800,H=280,p=28;
  const vals = times.map(t=>byTime[t]);
  const max = Math.max(1, ...vals);
  let points = '';
  times.forEach((t,i)=>{{
    const x = p + (times.length===1 ? 0 : i*(W-2*p)/(times.length-1));
    const y = H-p - (byTime[t]/max)*(H-2*p);
    points += `${{x}},${{y}} `;
  }});
  svg.innerHTML = `
    <line x1='${{p}}' y1='${{H-p}}' x2='${{W-p}}' y2='${{H-p}}' stroke='#cbd5e1'/>
    <line x1='${{p}}' y1='${{p}}' x2='${{p}}' y2='${{H-p}}' stroke='#cbd5e1'/>
    <polyline points='${{points}}' fill='none' stroke='#2563eb' stroke-width='3'/>
  `;

  const areaCount = {{}};
  for (const o of filteredObs) {{
    const area = trapMap[o.trap_id]?.area_id;
    if (!area) continue;
    areaCount[area] = (areaCount[area] || 0) + o.mosquito_count;
  }}
  const maxArea = Math.max(0, ...Object.values(areaCount));
  const heat = document.getElementById('heatmap');
  heat.innerHTML = DATA.areas
    .filter(a => af==='ALL' || a.area_id===af)
    .map(a => {{
      const c = areaCount[a.area_id] || 0;
      return `<div class='heatbox' style='background:${{heatColor(c,maxArea)}}'>${{a.area_id}}<br/>${{a.area_name}}<br/>${{c}} muỗi</div>`;
    }}).join('');

  const top = Object.entries(areaCount).sort((a,b)=>b[1]-a[1]);
  document.getElementById('topAreaTable').innerHTML = top.map((x,i)=>
    `<tr><td>${{i+1}}</td><td>${{x[0]}} - ${{areaMap[x[0]]?.area_name || ''}}</td><td>${{x[1]}}</td></tr>`
  ).join('');
}}

[areaFilter, statusFilter, fromDate, toDate].forEach(el => el.addEventListener('change', render));
render();
</script>
</body>
</html>
"""

out_file.write_text(html)
print(f"Wrote {out_file}")
