# Release Notes - Mosquito Trap Dashboard v10.0

**Release Date:** 2026-04-02

## ✨ New Features & Major Improvements

### 🚀 Performance Overhaul: Server-Side Processing

This is a major architectural upgrade that fundamentally changes how the dashboard loads and processes data, resulting in a massive performance boost.

- **Before (v9.01):** The dashboard loaded the entire 6.8MB+ dataset into the browser at once, causing slow initial load times and high memory usage, especially on mobile devices.
- **After (v10.0):** All heavy data processing (filtering, sorting, aggregation, pagination) is now done on the server. The browser only receives small, manageable chunks of data as needed.

**Key Changes:**
1.  **Server-Side Pagination:** The main data table now loads data page by page. This means the initial load is nearly instantaneous, regardless of the total number of records.
2.  **Server-Side Filtering & KPIs:** All filters (Area, Trap ID) and Key Performance Indicators (KPIs) are calculated directly on the database, returning only the necessary results to the frontend.
3.  **Optimized Chart & Map Loading:** Chart and map data is now pre-aggregated on the server, dramatically reducing the amount of data transferred and the rendering time in the browser.

### ⚡ Self-Hosted Assets (CDN Independence)

- All external JavaScript and CSS libraries (Chart.js, Leaflet, etc.) are now hosted locally within the project (`static/` directory).
- **Benefit:** This improves initial load times, increases reliability (no dependency on external CDNs), and allows the dashboard to function fully in offline or restricted network environments.

## ⚙️ Backend Changes

- **New API Endpoints:** A suite of new, fast API endpoints has been created:
  - `/api/table` (for paginated data)
  - `/api/kpi`
  - `/api/chart/bar` & `/api/chart/line`
  - `/api/map`
  - `/api/filters/areas` & `/api/filters/traps`
- **Database Optimization:** Added indexes to `date`, `area`, and `trap` columns in the `raw_data` table to ensure high-speed query performance.
- **Codebase:** The `api_server.py` has been completely rewritten to support these new features. The previous version is backed up as `api_server_v9.py`.

## 🎨 Frontend Changes

- `dashboard_v10.html` has been updated to communicate with the new server-side APIs.
- Implemented UI for table pagination (Next/Previous buttons).
- Removed the old client-side data processing logic, resulting in a lighter, faster JavaScript footprint.
