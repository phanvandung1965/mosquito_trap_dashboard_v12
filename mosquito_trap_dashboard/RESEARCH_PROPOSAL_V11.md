# 🦟 RESEARCH PROPOSAL — Mosquito Trap Dashboard V11+

**Tác giả:** AI Research Agent  
**Ngày:** 2026-04-03  
**Dựa trên phân tích thực tế:** Database SQLite, api_server_v9.py, dashboard_v10.html, star schema, và toàn bộ source code hiện có.

---

## Mục lục

1. [Tổng quan hiện trạng V10](#1-tổng-quan-hiện-trạng-v10)
2. [Phân tích chi tiết dữ liệu](#2-phân-tích-chi-tiết-dữ-liệu)
3. [Đề xuất báo cáo mới cho V11](#3-đề-xuất-báo-cáo-mới-cho-v11)
4. [Đề xuất tối ưu tốc độ bổ sung](#4-đề-xuất-tối-ưu-tốc-độ-bổ-sung)
5. [Kiến trúc backend V11 đề xuất](#5-kiến-trúc-backend-v11-đề-xuất)
6. [Kiến trúc frontend V11 đề xuất](#6-kiến-trúc-frontend-v11-đề-xuất)
7. [Lộ trình triển khai](#7-lộ-trình-triển-khai)
8. [Phụ lục — SQL Queries mẫu](#8-phụ-lục--sql-queries-mẫu)

---

## 1. Tổng quan hiện trạng V10

### 1.1. Cấu trúc project

```
mosquito_trap_dashboard/
├── data/mosquito_trap_dashboard.db   # SQLite (10,340 rows raw_data + star schema)
├── api_server.py                      # Basic backend (port 8788, chỉ /api/data)
├── api_server_v9.py                   # Advanced backend (gzip cache, port 7807, /api/data + /api/summary)
├── dashboard_v10.html                 # Frontend (vẫn reference CDN ngoài, chưa dùng static/)
├── static/                            # Đã download: chart.js, leaflet.js, markercluster, date-fns adapter
├── etl_to_star_schema.py             # ETL pipeline CSV → star schema
├── alert_engine.py                    # Rule-based alerts (offline + spike)
├── forecast_engine.py                 # Simple linear forecast (2-point)
└── ... (các file doc, snapshot, backup)
```

### 1.2. Vấn đề tồn đọng từ V10

| # | Vấn đề | Chi tiết |
|---|--------|----------|
| 1 | **dashboard_v10.html vẫn dùng CDN ngoài** | `<script src="https://cdn.jsdelivr.net/...">` thay vì `static/chart.js`. File `download_assets.py` đã tải file về `static/` nhưng HTML chưa được cập nhật reference. |
| 2 | **api_server_v9.py serve dashboard_v9.01.html** | Route `/` trả file `dashboard_v9.01.html`, không phải v10. |
| 3 | **Star schema data rất ít** | dim_date: 10 rows, dim_area: 3 rows (VN), dim_trap: 4 rows, fact_observation: 6 rows — trong khi raw_data: 10,340 rows (Australia). Hai nguồn dữ liệu **không đồng bộ**. |
| 4 | **Không có indexes trên raw_data** | Mặc dù RELEASE_v10.md nói đã thêm indexes, thực tế kiểm tra `sqlite_master` cho thấy **không có index nào**. |
| 5 | **Dashboard v10 gọi API endpoints chưa tồn tại** | HTML gọi `/api/table`, `/api/kpi`, `/api/chart/bar`, `/api/chart/line`, `/api/map`, `/api/filters/areas`, `/api/filters/traps` — nhưng cả `api_server.py` và `api_server_v9.py` đều **không implement** các endpoint này. |
| 6 | **Forecast & Alert chỉ dùng sample CSV** | `alert_engine.py` và `forecast_engine.py` đọc từ `sample_data_*.csv` (3-6 records), không dùng `raw_data` (10,340 records). |

### 1.3. Những gì V10 đã làm tốt

- ✅ Thiết kế frontend responsive, card KPI, chart, map, pagination
- ✅ Tải asset CDN về `static/` (script sẵn sàng)
- ✅ Star schema design hoàn chỉnh (model tốt, chỉ thiếu ETL raw_data → star schema)
- ✅ Gzip cache trong api_server_v9.py
- ✅ Document đầy đủ (DATA_MODEL, ETL_MAPPING, REQUIREMENTS, ROADMAP)

---

## 2. Phân tích chi tiết dữ liệu

### 2.1. raw_data — Dữ liệu chính (10,340 rows)

| Thuộc tính | Giá trị |
|------------|---------|
| **Phạm vi thời gian** | 2024-11-19 → 2026-03-19 (16 tháng) |
| **Số loài (detected_name)** | **39 loài** (Culex quinquefasciatus dẫn đầu: 2,404) |
| **Số AI models** | 8 (whole23: 3,723; whole22-41: 2,773; ...) |
| **Confidence range** | 0.0 → 1.0, trung bình **0.8433** |
| **Bang/State** | 4 (WA: 9,472; NSW: 554; QLD: 166; VIC: 148) |
| **Thành phố** | ~30+ (Piara Waters: 2,235; Bassendean: 1,322; Harrisdale: 1,242) |
| **Site codes** | ~40+ (5,079 records không có sitecode) |
| **GPS coverage** | **92%** (9,515/10,340 có lat/lon) |
| **Weather data** | Có (temperature, humidity, wind, visibility — dạng text string) |

### 2.2. Phân bổ theo thời gian

```
2024-11:    38  ▏
2024-12:   517  ████
2025-01: 1,623  ████████████
2025-02:   924  ███████
2025-03:   204  ██
2025-04:   116  █
2025-05:   301  ██
2025-07:   275  ██
2025-08:   420  ███
2025-09: 1,431  ███████████
2025-10: 1,430  ███████████
2025-11: 1,396  ██████████
2025-12:   564  ████
2026-01:   541  ████
2026-02:   335  ███
2026-03:   225  ██
```

**Nhận xét:** Có pattern **mùa vụ rõ ràng** — peak vào mùa hè Australia (tháng 9-11 và 1) và giảm mùa đông (3-5). Tháng 6 không có data (gap).

### 2.3. Top 10 loài phổ biến nhất

| # | Loài | Số lượng | % |
|---|------|----------|---|
| 1 | *Culex quinquefasciatus* | 2,404 | 23.3% |
| 2 | *Culex annulirostris* | 2,293 | 22.2% |
| 3 | *Aedes vigilax* | 1,310 | 12.7% |
| 4 | *Anopheles annulipes* | 843 | 8.2% |
| 5 | *Aedes notoscriptus* | 778 | 7.5% |
| 6 | *Aedes camptorhynchus* | 729 | 7.1% |
| 7 | *Culex australicus* | 410 | 4.0% |
| 8 | *Aedes alboannulatus* | 355 | 3.4% |
| 9 | Other | 243 | 2.4% |
| 10 | *Culex globocoxitus* | 153 | 1.5% |

### 2.4. Weather data (cần parse)

Weather hiện lưu dạng text:
```
Temperature: 20.05°C, Description: broken clouds, Humidity: 60%, Wind Speed: 7.72 m/s, Visibility: 10.0 km
```

**Cần parse** để trích xuất: `temperature_c`, `humidity_pct`, `wind_speed_ms`, `weather_desc`, `visibility_km`.

---

## 3. Đề xuất báo cáo mới cho V11

### 📊 Report 1: Species Distribution Analysis (Phân bổ loài muỗi)

**Mục tiêu:** Hiểu cấu trúc quần thể muỗi theo không gian và thời gian.

**Các component:**

| Component | Mô tả | API Endpoint |
|-----------|--------|-------------|
| **Donut Chart — Species Breakdown** | Top 10 loài + "Others" gộp lại. Click vào segment để drill-down. | `GET /api/v11/species/breakdown?area=&date_from=&date_to=` |
| **Stacked Bar — Species by Area** | Mỗi bar là 1 city/area, stacked theo loài. So sánh cấu trúc quần thể. | `GET /api/v11/species/by-area?top_n=10` |
| **Species Diversity Index** | Shannon-Wiener diversity index (H') per area. Chỉ số càng cao = hệ sinh thái muỗi càng đa dạng. | `GET /api/v11/species/diversity` |
| **Genus-level Aggregation** | Group theo genus (Aedes, Culex, Anopheles, etc.) cho overview cao hơn. | `GET /api/v11/species/genus` |
| **Species Heatmap Matrix** | Hàng = species, cột = month. Cell color = intensity. | `GET /api/v11/species/matrix?group_by=month` |

**Giá trị nghiệp vụ:**
- *Anopheles annulipes* (843 records) là vector sốt rét — cần giám sát đặc biệt.
- *Aedes aegypti* (41 records) là vector Dengue/Zika — dù ít nhưng quan trọng.
- Phân bổ loài theo khu vực giúp target biện pháp kiểm soát phù hợp.

---

### 📈 Report 2: Temporal Trends (Xu hướng theo thời gian)

**Mục tiêu:** Phát hiện pattern mùa vụ, xu hướng dài hạn, và anomaly.

**Các component:**

| Component | Mô tả | API Endpoint |
|-----------|--------|-------------|
| **Multi-line Chart — Monthly Trend** | Tổng records/tháng với **moving average 3 tháng**. Overlay nhiều năm. | `GET /api/v11/trends/monthly?years=2024,2025,2026` |
| **Weekly Heatmap Calendar** | Kiểu GitHub contribution graph — mỗi ô = 1 ngày, color = số lượng. | `GET /api/v11/trends/daily-counts?date_from=&date_to=` |
| **Seasonal Comparison** | So sánh mùa: Summer (Dec-Feb), Autumn (Mar-May), Winter (Jun-Aug), Spring (Sep-Nov) — Australia seasons. | `GET /api/v11/trends/seasonal` |
| **Year-over-Year (YoY)** | So sánh cùng kỳ năm trước: tháng 1/2025 vs tháng 1/2026. | `GET /api/v11/trends/yoy?month=1` |
| **Day-of-Week Pattern** | Phân bổ theo ngày trong tuần — kiểm tra có bias do sampling schedule. | `GET /api/v11/trends/dow` |
| **Anomaly Detection** | Highlight ngày có count > μ + 2σ (z-score > 2). | `GET /api/v11/trends/anomalies?threshold=2` |

**Giá trị nghiệp vụ:**
- Pattern mùa hè Australia (peak T9-T11 & T1) giúp lập kế hoạch phòng chống theo mùa.
- YoY comparison cho thấy chương trình kiểm soát có hiệu quả không.
- Anomaly detection cảnh báo sớm các đợt bùng phát.

---

### 🗺️ Report 3: Geographic Heatmap (Bản đồ nhiệt mật độ muỗi)

**Mục tiêu:** Trực quan hóa "hotspot" muỗi trên bản đồ.

**Các component:**

| Component | Mô tả | Thư viện |
|-----------|--------|----------|
| **Leaflet.heat Heatmap** | Heatmap overlay lên bản đồ. Intensity = số records tại mỗi GPS point. | `leaflet.heat` (cần thêm vào static/) |
| **Choropleth by LGA/City** | Tô màu theo đơn vị hành chính (LGA). Cần polygon data. | Leaflet + GeoJSON |
| **Time-lapse Heatmap** | Slider thời gian — xem heatmap thay đổi theo tháng. Animation play/pause. | `leaflet.heat` + custom slider |
| **Species-specific Heatmap** | Dropdown chọn loài → heatmap chỉ hiển thị loài đó. | Filter trước khi render |
| **Cluster Density Map** | Thay vì điểm đơn, hiển thị density contour (isoline). | `leaflet.heat` intensity gradient |

**API Endpoints:**
```
GET /api/v11/geo/heatmap?species=&month=&area=
GET /api/v11/geo/density-by-area
GET /api/v11/geo/timeseries?interval=month
```

**Giá trị nghiệp vụ:**
- 92% records có GPS → đủ data cho heatmap chất lượng.
- Time-lapse cho thấy hotspot di chuyển theo mùa.
- Species-specific map giúp target vector kiểm soát (vd: chỉ xem *Anopheles* cho chiến dịch phòng sốt rét).

---

### 🤖 Report 4: AI Model Confidence Analysis (Phân tích chất lượng AI)

**Mục tiêu:** Đánh giá độ tin cậy của AI classification và so sánh model versions.

**Các component:**

| Component | Mô tả | API Endpoint |
|-----------|--------|-------------|
| **Confidence Distribution Histogram** | Histogram phân bổ confidence (bins: 0-0.5, 0.5-0.7, 0.7-0.8, 0.8-0.9, 0.9-1.0). | `GET /api/v11/ai/confidence-dist` |
| **Model Comparison Box Plot** | Box plot confidence cho mỗi AI model (whole23, whole22-41, ...). So sánh median, Q1/Q3, outliers. | `GET /api/v11/ai/model-comparison` |
| **Low Confidence Alerts** | Danh sách records có confidence < 0.5 (cần review thủ công). | `GET /api/v11/ai/low-confidence?threshold=0.5&page=1` |
| **Confidence by Species** | Avg confidence per species — loài nào AI nhận diện tốt nhất/kém nhất. | `GET /api/v11/ai/confidence-by-species` |
| **Model Version Timeline** | Thời gian triển khai mỗi model version, kèm avg confidence. Thấy cải thiện qua các version. | `GET /api/v11/ai/model-timeline` |
| **Confusion Indicator** | So sánh `detected_name` vs `orig_detected_name` (nếu khác nhau = model correction). | `GET /api/v11/ai/corrections` |

**Giá trị nghiệp vụ:**
- Mean confidence 0.84 là khá tốt nhưng có records confidence = 0.0 cần review.
- 8 model versions → tracking model improvement over time.
- Species-level confidence cho thấy loài nào cần nhiều training data hơn.

---

### ⚠️ Report 5: Alert & Risk Assessment (Đánh giá rủi ro)

**Mục tiêu:** Chuyển từ reactive → proactive monitoring.

**Các component:**

| Component | Mô tả | API Endpoint |
|-----------|--------|-------------|
| **Risk Score Dashboard** | Composite risk score per area = weighted(density × trend × species_risk × weather_risk). | `GET /api/v11/risk/scores` |
| **Spike Detection** | Z-score based: so sánh 7-day rolling avg. Alert khi z > 2. | `GET /api/v11/risk/spikes?window=7&threshold=2` |
| **Species Risk Flagging** | Flag vector species: *Aedes aegypti* (Dengue), *Anopheles* (Malaria) → auto-elevate risk level. | `GET /api/v11/risk/vector-species` |
| **Weather Correlation** | Scatter plot: temperature/humidity vs mosquito count. Regression line. | `GET /api/v11/risk/weather-correlation` |
| **Active Alerts Board** | Bảng alert real-time: type, severity, area, trap, status (open/resolved). Sortable. | `GET /api/v11/alerts?status=open&page=1` |
| **Alert History Timeline** | Gantt-style timeline các alert theo thời gian và severity. | `GET /api/v11/alerts/timeline?date_from=&date_to=` |

**Risk Score Formula:**
```
risk_score = (
    0.35 × normalized_density +        # Mật độ muỗi hiện tại
    0.25 × trend_coefficient +          # Xu hướng tăng/giảm
    0.25 × species_danger_index +       # Có vector species không
    0.15 × weather_favorability         # Thời tiết thuận lợi cho muỗi
)
```

**Giá trị nghiệp vụ:**
- Chuyển từ "xem data" sang "hành động" — risk score trực tiếp xếp hạng ưu tiên can thiệp.
- Weather correlation giúp dự báo spike trước khi xảy ra.
- Vector species flagging bảo vệ sức khỏe cộng đồng.

---

### 📋 Report 6: Trap Performance & Coverage (Hiệu suất bẫy) — BỔ SUNG

**Mục tiêu:** Đánh giá hiệu quả lưới bẫy và tối ưu vị trí đặt.

**Các component:**

| Component | Mô tả |
|-----------|--------|
| **Trap Yield Ranking** | Xếp hạng trap theo số records/tháng. Top performers vs underperformers. |
| **Coverage Gap Analysis** | Map hiển thị vùng chưa có bẫy (GPS dead zones > X km từ trap gần nhất). |
| **Trap Activity Timeline** | Gantt chart mỗi trap — khi nào active, khi nào im lặng. |
| **Reallocation Suggestions** | Gợi ý chuyển bẫy từ vùng low-yield sang high-risk/no-coverage. |

---

### 📑 Report 7: Executive Summary Report (Báo cáo tóm tắt lãnh đạo) — BỔ SUNG

**Mục tiêu:** Báo cáo 1 trang cho decision-makers.

**Các component:**

| Component | Mô tả |
|-----------|--------|
| **Scorecard Header** | 4 KPI lớn: Total Catches, Active Areas, Risk Level, Top Threat Species |
| **Weekly/Monthly Brief** | Auto-generated text summary: "Tuần này ghi nhận X records, tăng Y% so với tuần trước. Hotspot: Z." |
| **PDF Export** | Nút "Export PDF" — render toàn bộ dashboard page thành PDF. |
| **Scheduled Email** | Cron job gửi brief hàng tuần qua email/Telegram. |

---

## 4. Đề xuất tối ưu tốc độ bổ sung

### 4.1. Database Indexes (CRITICAL — chưa có!)

```sql
-- Hiện tại raw_data không có BẤT KỲ index nào!
-- V11 phải tạo indexes ngay:

CREATE INDEX IF NOT EXISTS idx_raw_date ON raw_data(date);
CREATE INDEX IF NOT EXISTS idx_raw_city ON raw_data(city);
CREATE INDEX IF NOT EXISTS idx_raw_state ON raw_data(state);
CREATE INDEX IF NOT EXISTS idx_raw_detected ON raw_data(detected_name);
CREATE INDEX IF NOT EXISTS idx_raw_confidence ON raw_data(confidence);
CREATE INDEX IF NOT EXISTS idx_raw_aimodel ON raw_data(aimodel);
CREATE INDEX IF NOT EXISTS idx_raw_sitecode ON raw_data(sitecode_cd);
CREATE INDEX IF NOT EXISTS idx_raw_lga ON raw_data(lga);

-- Composite indexes cho các query phổ biến:
CREATE INDEX IF NOT EXISTS idx_raw_date_city ON raw_data(date, city);
CREATE INDEX IF NOT EXISTS idx_raw_date_species ON raw_data(date, detected_name);
CREATE INDEX IF NOT EXISTS idx_raw_city_species ON raw_data(city, detected_name);
CREATE INDEX IF NOT EXISTS idx_raw_gps ON raw_data(latitude, longitude);
```

**Impact dự kiến:** Giảm query time từ ~50-100ms xuống ~1-5ms cho filtered queries.

### 4.2. Parse Weather Data thành cột riêng

```sql
-- Thêm cột parsed weather vào raw_data hoặc tạo bảng phụ:
ALTER TABLE raw_data ADD COLUMN temperature_c REAL;
ALTER TABLE raw_data ADD COLUMN humidity_pct REAL;
ALTER TABLE raw_data ADD COLUMN wind_speed_ms REAL;
ALTER TABLE raw_data ADD COLUMN weather_desc TEXT;
ALTER TABLE raw_data ADD COLUMN visibility_km REAL;
```

Script Python parse:
```python
import re
def parse_weather(text):
    temp = re.search(r'Temperature:\s*([\d.]+)', text)
    humid = re.search(r'Humidity:\s*([\d.]+)', text)
    wind = re.search(r'Wind Speed:\s*([\d.]+)', text)
    desc = re.search(r'Description:\s*([^,]+)', text)
    vis = re.search(r'Visibility:\s*([\d.]+)', text)
    return {
        'temperature_c': float(temp.group(1)) if temp else None,
        'humidity_pct': float(humid.group(1)) if humid else None,
        'wind_speed_ms': float(wind.group(1)) if wind else None,
        'weather_desc': desc.group(1).strip() if desc else None,
        'visibility_km': float(vis.group(1)) if vis else None,
    }
```

### 4.3. Materialized Views (Pre-aggregated Tables)

```sql
-- Pre-compute aggregations cho dashboard load nhanh hơn:

-- Monthly summary per species per area
CREATE TABLE IF NOT EXISTS agg_monthly_species AS
SELECT 
    year, month, city,
    detected_name,
    COUNT(*) as record_count,
    AVG(CAST(confidence AS REAL)) as avg_confidence
FROM raw_data
GROUP BY year, month, city, detected_name;

-- Daily totals for trend chart
CREATE TABLE IF NOT EXISTS agg_daily_totals AS
SELECT 
    date,
    COUNT(*) as record_count,
    COUNT(DISTINCT detected_name) as species_count,
    AVG(CAST(confidence AS REAL)) as avg_confidence
FROM raw_data
GROUP BY date;

-- Area summary for KPI cards
CREATE TABLE IF NOT EXISTS agg_area_summary AS
SELECT 
    city,
    state,
    COUNT(*) as total_records,
    COUNT(DISTINCT detected_name) as species_count,
    COUNT(DISTINCT sitecode_cd) as trap_count,
    MIN(date) as first_record,
    MAX(date) as last_record
FROM raw_data
GROUP BY city, state;
```

**Impact:** KPI & chart endpoints return in <1ms (read from pre-computed table).  
**Trade-off:** Need to rebuild agg tables after new data import. Script `rebuild_aggregations.py` nên chạy trong ETL pipeline.

### 4.4. Backend Architecture

```
V10 (hiện tại):
  api_server_v9.py → 1 gzip blob → client xử lý mọi thứ

V11 (đề xuất):
  api_server_v11.py
  ├── /api/v11/kpi            → SELECT from agg_area_summary (cached 60s)
  ├── /api/v11/table           → Paginated query with server-side filter
  ├── /api/v11/species/*       → 5 sub-endpoints
  ├── /api/v11/trends/*        → 6 sub-endpoints
  ├── /api/v11/geo/*           → 3 sub-endpoints
  ├── /api/v11/ai/*            → 6 sub-endpoints
  ├── /api/v11/risk/*          → 4 sub-endpoints
  ├── /api/v11/alerts/*        → 2 sub-endpoints
  ├── /api/v11/export/pdf      → Server-side PDF generation
  └── /api/v11/meta/refresh    → Trigger agg table rebuild
```

### 4.5. Response Caching Strategy

| Cache Level | TTL | Scope |
|-------------|-----|-------|
| **L1: In-memory dict** | 60s | KPI, filters, species breakdown |
| **L2: Gzip compressed** | 300s | Full data endpoints |
| **L3: Materialized views** | Until data import | Aggregated tables |
| **ETags** | Per-query | Browser cache validation |

### 4.6. Frontend Optimization

| Optimization | Detail |
|-------------|--------|
| **Fix CDN → static/** | Cập nhật `dashboard_v10.html` reference sang `static/*.js` |
| **Lazy-load tabs** | Chỉ load data cho tab đang active, defer các tab khác |
| **Web Worker** | Xử lý large JSON parse trong worker thread |
| **Virtual scrolling** | Table > 100 rows → virtual scroll thay DOM render |
| **Chart.js deferred** | Chỉ render chart khi visible (IntersectionObserver) |

---

## 5. Kiến trúc backend V11 đề xuất

### 5.1. File structure

```
api_server_v11.py
├── Blueprint: /api/v11/
│   ├── routes_kpi.py
│   ├── routes_species.py
│   ├── routes_trends.py
│   ├── routes_geo.py
│   ├── routes_ai.py
│   ├── routes_risk.py
│   ├── routes_alerts.py
│   └── routes_export.py
├── db.py                    # Connection pool + query helpers
├── cache.py                 # L1/L2 cache manager
├── aggregation_builder.py   # Rebuild materialized views
└── weather_parser.py        # Parse weather text → structured data
```

### 5.2. Unified query builder

```python
def build_filtered_query(base_sql, params):
    """Add WHERE clauses based on request params."""
    conditions = []
    values = []
    
    if params.get('area'):
        conditions.append("city = ?")
        values.append(params['area'])
    if params.get('species'):
        conditions.append("detected_name = ?")
        values.append(params['species'])
    if params.get('date_from'):
        conditions.append("date >= ?")
        values.append(params['date_from'])
    if params.get('date_to'):
        conditions.append("date <= ?")
        values.append(params['date_to'])
    if params.get('model'):
        conditions.append("aimodel = ?")
        values.append(params['model'])
    if params.get('min_confidence'):
        conditions.append("CAST(confidence AS REAL) >= ?")
        values.append(float(params['min_confidence']))
    
    where = " AND ".join(conditions)
    if where:
        base_sql += f" WHERE {where}"
    
    return base_sql, values
```

---

## 6. Kiến trúc frontend V11 đề xuất

### 6.1. Tab-based layout

```
┌──────────────────────────────────────────────────────────┐
│  Mosquito Trap Dashboard V11                    [Ready]  │
├──────────────────────────────────────────────────────────┤
│  [Overview] [Species] [Trends] [Heatmap] [AI] [Risk]   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│  │ Total   │ │ Species │ │ Areas   │ │ Risk    │       │
│  │ 10,340  │ │   39    │ │   30+   │ │ Medium  │       │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
│                                                          │
│  ┌─── Filters ──────────────────────────────────────┐   │
│  │ Area: [___▼] Species: [___▼] Date: [__] to [__]  │   │
│  │ Model: [___▼] Min Confidence: [___] [Reset]       │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  [Tab-specific content renders here]                     │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 6.2. Thư viện cần thêm

| Library | Purpose | Size | Local? |
|---------|---------|------|--------|
| `leaflet.heat` | Heatmap overlay | ~10KB | ✅ Download to static/ |
| `html2canvas` | PDF/Image export | ~40KB | ✅ Download to static/ |
| `jspdf` | PDF generation | ~70KB | ✅ Download to static/ |

Tổng cộng thêm ~120KB — acceptable.

---

## 7. Lộ trình triển khai

### Phase 1: Foundation Fix (1-2 ngày)

- [ ] Fix `dashboard_v10.html` → reference `static/` thay vì CDN
- [ ] Tạo **tất cả database indexes** (hiện KHÔNG có!)
- [ ] Parse weather data → cột riêng
- [ ] Fix `api_server_v9.py` route `/` → serve `dashboard_v10.html`
- [ ] Implement **tất cả** endpoints mà `dashboard_v10.html` đang gọi (table, kpi, chart/bar, chart/line, map, filters/areas, filters/traps)
- [ ] Test V10 hoạt động end-to-end

### Phase 2: Core Reports (3-5 ngày)

- [ ] Build Species Distribution (Report 1) — backend + frontend
- [ ] Build Temporal Trends (Report 2) — backend + frontend
- [ ] Build Geographic Heatmap (Report 3) — backend + frontend
- [ ] Build AI Confidence Analysis (Report 4) — backend + frontend
- [ ] Materialized views + rebuild script

### Phase 3: Advanced Reports (2-3 ngày)

- [ ] Build Risk Assessment (Report 5) — risk score engine + frontend
- [ ] Build Trap Performance (Report 6) — backend + frontend
- [ ] Build Executive Summary (Report 7) — auto-text + PDF export

### Phase 4: Polish & Release (1-2 ngày)

- [ ] Tab navigation UX
- [ ] Lazy loading
- [ ] Mobile responsive refinement
- [ ] Performance testing (target: all endpoints < 20ms)
- [ ] Archive & upload release tarball
- [ ] Update documentation

**Tổng ước tính: 7-12 ngày phát triển.**

---

## 8. Phụ lục — SQL Queries mẫu

### Species Breakdown
```sql
SELECT 
    detected_name,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM raw_data), 1) as pct,
    ROUND(AVG(CAST(confidence AS REAL)), 3) as avg_confidence
FROM raw_data
WHERE detected_name != '' AND detected_name IS NOT NULL
GROUP BY detected_name
ORDER BY count DESC
LIMIT 15;
```

### Shannon Diversity Index per City
```sql
WITH city_total AS (
    SELECT city, COUNT(*) as total FROM raw_data GROUP BY city
),
city_species AS (
    SELECT city, detected_name, COUNT(*) as n 
    FROM raw_data GROUP BY city, detected_name
)
SELECT 
    cs.city,
    ct.total,
    COUNT(DISTINCT cs.detected_name) as species_count,
    -SUM((CAST(cs.n AS REAL) / ct.total) * LN(CAST(cs.n AS REAL) / ct.total)) as shannon_h
FROM city_species cs
JOIN city_total ct ON cs.city = ct.city
WHERE cs.city != ''
GROUP BY cs.city
ORDER BY shannon_h DESC;
```

### Monthly Trend with Moving Average
```sql
WITH monthly AS (
    SELECT 
        year || '-' || PRINTF('%02d', CAST(month AS INTEGER)) as ym,
        COUNT(*) as cnt
    FROM raw_data
    GROUP BY ym
    ORDER BY ym
)
SELECT 
    ym,
    cnt,
    AVG(cnt) OVER (ORDER BY ym ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as ma3
FROM monthly;
```

### Anomaly Detection (Z-Score)
```sql
WITH daily AS (
    SELECT date, COUNT(*) as cnt FROM raw_data GROUP BY date
),
stats AS (
    SELECT AVG(cnt) as mu, 
           SQRT(AVG(cnt*cnt) - AVG(cnt)*AVG(cnt)) as sigma 
    FROM daily
)
SELECT d.date, d.cnt, 
       ROUND((d.cnt - s.mu) / NULLIF(s.sigma, 0), 2) as z_score
FROM daily d, stats s
WHERE ABS((d.cnt - s.mu) / NULLIF(s.sigma, 0)) > 2
ORDER BY z_score DESC;
```

### Model Confidence Comparison
```sql
SELECT 
    aimodel,
    COUNT(*) as records,
    ROUND(AVG(CAST(confidence AS REAL)), 4) as avg_conf,
    ROUND(MIN(CAST(confidence AS REAL)), 4) as min_conf,
    ROUND(MAX(CAST(confidence AS REAL)), 4) as max_conf,
    -- Pseudo-median using percentile
    MIN(date) as first_used,
    MAX(date) as last_used
FROM raw_data
WHERE confidence != '' AND confidence IS NOT NULL
GROUP BY aimodel
ORDER BY avg_conf DESC;
```

### Risk Score per Area
```sql
WITH area_density AS (
    SELECT city, COUNT(*) as density FROM raw_data 
    WHERE date >= date('now', '-30 days') GROUP BY city
),
area_trend AS (
    SELECT city,
        (SELECT COUNT(*) FROM raw_data r2 
         WHERE r2.city = r1.city AND r2.date >= date('now', '-7 days'))
        * 1.0 /
        NULLIF((SELECT COUNT(*) FROM raw_data r3 
         WHERE r3.city = r1.city AND r3.date BETWEEN date('now', '-14 days') AND date('now', '-7 days')), 0)
        as week_ratio
    FROM raw_data r1 GROUP BY city
),
area_vectors AS (
    SELECT city,
        SUM(CASE WHEN detected_name IN ('Aedes aegypti', 'Anopheles annulipes', 'Anopheles bancroftii') THEN 1 ELSE 0 END) as vector_count
    FROM raw_data GROUP BY city
)
SELECT 
    d.city,
    d.density,
    COALESCE(t.week_ratio, 1.0) as trend,
    COALESCE(v.vector_count, 0) as vectors,
    ROUND(
        0.35 * MIN(d.density / 100.0, 1.0) +
        0.25 * MIN(COALESCE(t.week_ratio, 1.0) / 2.0, 1.0) +
        0.25 * MIN(COALESCE(v.vector_count, 0) / 50.0, 1.0) +
        0.15 * 0.5,  -- placeholder weather
    3) as risk_score
FROM area_density d
LEFT JOIN area_trend t ON d.city = t.city
LEFT JOIN area_vectors v ON d.city = v.city
ORDER BY risk_score DESC;
```

---

## Tóm tắt

| Hạng mục | V10 (hiện tại) | V11 (đề xuất) |
|----------|----------------|----------------|
| **Reports** | 1 (Overview) | **7 reports** (Species, Trends, Heatmap, AI, Risk, Trap, Executive) |
| **Charts** | 2 (line + bar) | **15+ chart types** (donut, stacked bar, heatmap, box plot, scatter, calendar, ...) |
| **Indexes** | ❌ Không có | ✅ 12+ indexes |
| **Cache** | Gzip blob | ✅ L1/L2/L3 + ETag |
| **Filters** | Area + Trap | ✅ Area + Species + Date range + Model + Confidence |
| **Endpoints** | 2 (/api/data, /api/summary) | ✅ 26+ specialized endpoints |
| **Weather** | Raw text | ✅ Parsed columns |
| **Aggregations** | Client-side | ✅ Server-side materialized views |
| **Export** | CSV (v9) | ✅ CSV + PNG + PDF |
| **Risk Engine** | Basic spike rule | ✅ Composite risk score |
| **Static assets** | ❌ CDN | ✅ Local static/ |

---

*Báo cáo này dựa trên phân tích thực tế 100% source code và database hiện có. Mọi query SQL đã được thiết kế cho schema raw_data thực tế (10,340 rows, 21 columns, 39 species, 8 AI models).*
