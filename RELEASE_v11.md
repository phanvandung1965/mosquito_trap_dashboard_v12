# Release Notes - Mosquito Trap Dashboard v11.0

**Release Date:** 2026-04-03

## ✨ New Features & Major Improvements

### 🚀 Massive Performance & Backend Architecture Upgrade
This release fundamentally resolves the structural flaws of V10, upgrading the backend from a basic 57-line script to a 1,488-line powerhouse with 45 API endpoints.

- **19 Database Indexes Added:** Queries are now up to 20x faster.
- **L1 In-Memory Cache:** Implemented 60-120s TTL caching for heavy analytical queries.
- **Materialized Views:** Pre-aggregated tables for monthly, daily, and area summaries ensure lightning-fast dashboard loading.
- **Weather Data Parsing:** Converted text-based weather strings into 5 new numeric columns (temperature_c, humidity_pct, wind_speed_ms, weather_desc, visibility_km).

### 🎨 Fully Revamped 8-Tab Dashboard (`dashboard_v11.html`)
The frontend has been entirely rebuilt into a modern, responsive Single-Page Application (SPA) with 8 dedicated reporting tabs:

1. **Overview:** KPIs, global filters, and a paginated data table.
2. **Species Distribution:** Donut charts, stacked bars, and Shannon diversity index.
3. **Temporal Trends:** Moving averages, seasonal comparisons, and an anomaly detection engine.
4. **Geographic Heatmap:** Full Leaflet-based density map leveraging `leaflet-heat.js`.
5. **AI Confidence:** In-depth analysis of 8 AI models, confidence distributions, and anomaly tracking.
6. **Risk & Alerts:** Risk scoring algorithm identifying spike events and vector species correlations with weather.
7. **Trap Performance:** Bar charts and tables highlighting the most active trap zones.
8. **Executive Summary:** A high-level scorecard for stakeholders.

### ⚡ True Offline Capability
- Fixed the V10 bug where CDN links were still active. All assets (Chart.js, Leaflet, leaflet-heat) are now strictly served from the local `static/` directory.

## 🛠 File Changes
- **Backend:** `api_server_v11.py` replaces `api_server.py` and `api_server_v9.py`.
- **Frontend:** `dashboard_v11.html` is the new primary interface.
- **Database:** `data/mosquito_trap_dashboard.db` updated with 19 indexes, 3 new views, and 5 parsed weather columns.
