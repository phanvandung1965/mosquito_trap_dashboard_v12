import csv
import json
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
areas_file = BASE / "sample_data_areas.csv"
traps_file = BASE / "sample_data_traps.csv"
obs_file = BASE / "sample_data_observation.csv"
alerts_file = BASE / "alerts_snapshot.json"
forecast_file = BASE / "forecast_snapshot.json"
out_file = BASE / "dashboard_v4.html"

areas = []
with areas_file.open() as f:
    for r in csv.DictReader(f):
        areas.append(r)

traps = []
with traps_file.open() as f:
    for r in csv.DictReader(f):
        traps.append(r)

obs = []
with obs_file.open() as f:
    for r in csv.DictReader(f):
        r["mosquito_count"] = int(r["mosquito_count"])
        obs.append(r)

alerts = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "alert_count": 0, "alerts": []}
if alerts_file.exists():
    alerts = json.loads(alerts_file.read_text())

forecast = {"generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "method": "none", "history": [], "forecast": []}
if forecast_file.exists():
    forecast = json.loads(forecast_file.read_text())

payload = {
    "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "areas": areas,
    "traps": traps,
    "observations": obs,
    "alerts": alerts,
    "forecast": forecast,
}

html = f"""<!doctype html>
<html lang='vi'>
<head>
  <meta charset='utf-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1' />
  <title>Mosquito Dashboard V4</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 14px; background:#f4f7fb; color:#0f172a; }}
    .top {{ display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px; flex-wrap:wrap; }}
    .filters {{ display:grid; grid-template-columns: repeat(4, minmax(130px, 1fr)); gap:8px; margin-bottom:12px; }}
    .card-grid {{ display:grid; grid-template-columns: repeat(7, 1fr); gap:10px; margin-bottom:14px; }}
    .card,.panel {{ background:#fff; border-radius:12px; padding:12px; box-shadow:0 1px 6px rgba(0,0,0,.08); }}
    .k {{ font-size:12px; color:#64748b; }}
    .v {{ font-size:22px; font-weight:700; margin-top:4px; }}
    .layout {{ display:grid; grid-template-columns: 1.25fr 1fr; gap:12px; }}
    #trendSvg,#geoSvg,#forecastSvg {{ width:100%; height:250px; border:1px solid #e2e8f0; border-radius:8px; background:#fff; }}
    .heatmap {{ display:grid; grid-template-columns: repeat(3, 1fr); gap:8px; }}
    .heatbox {{ border-radius:10px; padding:10px; font-weight:600; min-height:72px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
    th, td {{ text-align:left; padding:8px; border-bottom:1px solid #eef2f7; font-size:13px; }}
    th {{ background:#f8fafc; }}

    @media (max-width: 1100px) {{
      .card-grid {{ grid-template-columns: repeat(3, 1fr); }}
      .layout {{ grid-template-columns: 1fr; }}
      .heatmap {{ grid-template-columns: repeat(2,1fr); }}
    }}
    @media (max-width: 680px) {{
      body {{ margin: 8px; }}
      .filters {{ grid-template-columns: 1fr 1fr; }}
      .card-grid {{ grid-template-columns: 1fr 1fr; }}
      .v {{ font-size:18px; }}
      #trendSvg,#geoSvg,#forecastSvg {{ height:210px; }}
      .heatmap {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class='top'>
    <h2>Dashboard bẫy muỗi V4 (Auto + Forecast + Mobile)</h2>
    <div>Cập nhật: <b>{payload['generated_at']}</b></div>
  </div>

  <div class='filters'>
    <select id='areaFilter'><option value='ALL'>Tất cả khu vực</option></select>
    <select id='statusFilter'>
      <option value='ALL'>Tất cả trạng thái bẫy</option>
      <option value='active'>active</option><option value='offline'>offline</option><option value='maintenance'>maintenance</option>
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
    <div class='card'><div class='k'>Alert Count</div><div class='v' id='kAlerts'>0</div></div>
  </div>

  <div class='layout'>
    <div>
      <div class='panel'><h3>Xu hướng thực tế</h3><svg id='trendSvg' viewBox='0 0 800 250'></svg></div>
      <div class='panel'><h3>Bản đồ marker theo tọa độ</h3><svg id='geoSvg' viewBox='0 0 800 250'></svg></div>
      <div class='panel'><h3>Dự báo 3 bước tiếp theo ({payload['forecast'].get('method','n/a')})</h3><svg id='forecastSvg' viewBox='0 0 800 250'></svg></div>
    </div>
    <div>
      <div class='panel'><h3>Heatmap khu vực</h3><div id='heatmap' class='heatmap'></div></div>
      <div class='panel'>
        <h3>Cảnh báo vận hành</h3>
        <table><thead><tr><th>Type</th><th>Severity</th><th>Trap</th><th>Area</th><th>Nội dung</th></tr></thead><tbody id='alertTable'></tbody></table>
      </div>
      <div class='panel'>
        <h3>Bảng Forecast</h3>
        <table><thead><tr><th>Thời điểm</th><th>Số muỗi dự báo</th></tr></thead><tbody id='forecastTable'></tbody></table>
      </div>
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
for (const a of DATA.areas) {{ const op=document.createElement('option'); op.value=a.area_id; op.textContent=`${{a.area_id}} - ${{a.area_name}}`; areaFilter.appendChild(op); }}

const sortedTimes = [...new Set(DATA.observations.map(o=>o.observed_at))].sort();
const fmtInput=(s)=>s.replace(' ','T').slice(0,16);
if (sortedTimes.length) {{ fromDate.value=fmtInput(sortedTimes[0]); toDate.value=fmtInput(sortedTimes[sortedTimes.length-1]); }}

const inRange=(ts)=>{{
  const t=new Date(ts.replace(' ','T')).getTime();
  const f=fromDate.value?new Date(fromDate.value).getTime():-Infinity;
  const to=toDate.value?new Date(toDate.value).getTime():Infinity;
  return t>=f && t<=to;
}}
const heatColor=(v,m)=>{{ if(!m)return '#e2e8f0'; const r=v/m; return `rgb(255,${{Math.round(240-r*120)}},${{Math.round(240-r*180)}})`; }}

function drawLine(svgId, series, color='#2563eb') {{
  const svg=document.getElementById(svgId); const W=800,H=250,p=22;
  const vals=series.map(s=>s.y); const max=Math.max(1,...vals);
  let points='';
  series.forEach((s,i)=>{{ const x=p+(series.length===1?0:i*(W-2*p)/(series.length-1)); const y=H-p-(s.y/max)*(H-2*p); points+=`${{x}},${{y}} `; }});
  svg.innerHTML=`<line x1='${{p}}' y1='${{H-p}}' x2='${{W-p}}' y2='${{H-p}}' stroke='#cbd5e1'/><line x1='${{p}}' y1='${{p}}' x2='${{p}}' y2='${{H-p}}' stroke='#cbd5e1'/><polyline points='${{points}}' fill='none' stroke='${{color}}' stroke-width='3'/>`;
}}

function drawGeo(filteredAreas, areaCount) {{
  const svg=document.getElementById('geoSvg'); const W=800,H=250,p=20;
  if(!filteredAreas.length) {{ svg.innerHTML=''; return; }}
  const lats=filteredAreas.map(a=>parseFloat(a.latitude)), lons=filteredAreas.map(a=>parseFloat(a.longitude));
  const minLat=Math.min(...lats), maxLat=Math.max(...lats), minLon=Math.min(...lons), maxLon=Math.max(...lons);
  const maxCount=Math.max(1,...Object.values(areaCount));
  let body=`<rect x='0' y='0' width='${{W}}' height='${{H}}' fill='#f8fafc'/>`;
  for(const a of filteredAreas) {{
    const lat=parseFloat(a.latitude), lon=parseFloat(a.longitude);
    const x=p+((lon-minLon)/Math.max(0.0001,(maxLon-minLon)))*(W-2*p);
    const y=H-p-((lat-minLat)/Math.max(0.0001,(maxLat-minLat)))*(H-2*p);
    const c=areaCount[a.area_id]||0, r=6+(c/maxCount)*12;
    body += `<circle cx='${{x}}' cy='${{y}}' r='${{r}}' fill='rgba(239,68,68,.55)' stroke='#b91c1c'/>`;
    body += `<text x='${{x+10}}' y='${{y-8}}' font-size='11'>${{a.area_id}} (${{c}})</text>`;
  }}
  svg.innerHTML=body;
}}

function render() {{
  const af=areaFilter.value, sf=statusFilter.value;
  const fTraps=DATA.traps.filter(t=>(af==='ALL'||t.area_id===af)&&(sf==='ALL'||t.status===sf));
  const trapIds=new Set(fTraps.map(t=>t.trap_id));
  const fObs=DATA.observations.filter(o=>trapIds.has(o.trap_id)&&inRange(o.observed_at));

  const active=fTraps.filter(t=>t.status==='active').length;
  const offline=fTraps.filter(t=>t.status==='offline').length;
  const maint=fTraps.filter(t=>t.status==='maintenance').length;
  const totalMosq=fObs.reduce((s,o)=>s+o.mosquito_count,0);
  const avg=active?(totalMosq/active).toFixed(2):0;

  document.getElementById('kTotalTraps').textContent=fTraps.length;
  document.getElementById('kActive').textContent=active;
  document.getElementById('kOffline').textContent=offline;
  document.getElementById('kMaint').textContent=maint;
  document.getElementById('kMosq').textContent=totalMosq;
  document.getElementById('kAvg').textContent=avg;

  const byTime={};
  for(const o of fObs) byTime[o.observed_at]=(byTime[o.observed_at]||0)+o.mosquito_count;
  const tSeries=Object.keys(byTime).sort().map(t=>({x:t,y:byTime[t]}));
  drawLine('trendSvg', tSeries, '#2563eb');

  const areaCount={};
  for(const o of fObs) {{ const a=trapMap[o.trap_id]?.area_id; if(!a) continue; areaCount[a]=(areaCount[a]||0)+o.mosquito_count; }}
  const maxArea=Math.max(0,...Object.values(areaCount));
  const fAreas=DATA.areas.filter(a=>af==='ALL'||a.area_id===af);
  document.getElementById('heatmap').innerHTML=fAreas.map(a=>{{ const c=areaCount[a.area_id]||0; return `<div class='heatbox' style='background:${{heatColor(c,maxArea)}}'>${{a.area_id}}<br/>${{a.area_name}}<br/>${{c}} muỗi</div>`; }}).join('');
  drawGeo(fAreas, areaCount);

  const alerts=(DATA.alerts.alerts||[]).filter(a=>af==='ALL'||a.area_id===af);
  document.getElementById('kAlerts').textContent=alerts.length;
  document.getElementById('alertTable').innerHTML=alerts.map(a=>`<tr><td>${{a.alert_type}}</td><td>${{a.severity}}</td><td>${{a.trap_id||''}}</td><td>${{a.area_id||''}}</td><td>${{a.message}}</td></tr>`).join('');

  const fSeries=(DATA.forecast.forecast||[]).map(x=>({x:x.time,y:x.count}));
  drawLine('forecastSvg', fSeries, '#9333ea');
  document.getElementById('forecastTable').innerHTML=(DATA.forecast.forecast||[]).map(x=>`<tr><td>${{x.time}}</td><td>${{x.count}}</td></tr>`).join('');
}}

[areaFilter,statusFilter,fromDate,toDate].forEach(el=>el.addEventListener('change',render));
render();
</script>
</body>
</html>
"""

out_file.write_text(html)
print(f"Wrote {out_file}")
