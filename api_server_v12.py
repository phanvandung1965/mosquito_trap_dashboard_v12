"""
Mosquito Trap Dashboard — API Server V12.1
============================================
Full-featured backend with 30+ endpoints, L1 in-memory cache, materialized views.
Port: 7808 (configurable via MOSQ_PORT env var).

Usage:
    python api_server_v12.py
    MOSQ_PORT=8000 MOSQ_DEBUG=1 python api_server_v12.py
"""

from flask import Flask, jsonify, request, send_from_directory, make_response, session, redirect, url_for
from flask_cors import CORS
import sqlite3
import os
import json
import time
import math
import re
import gzip
from functools import wraps

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'super-secret-mosquito-key-1234'
app.permanent_session_lifetime = timedelta(minutes=5)
CORS(app)

project_path = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(project_path, 'data', 'mosquito_trap_dashboard.db')
report_prefs_path = os.path.join(project_path, 'data', 'report_v12_1_prefs.json')
TABLE_NAME = 'raw_data'
APP_PORT = int(os.environ.get('MOSQ_PORT', '7808'))
APP_DEBUG = os.environ.get('MOSQ_DEBUG', '0').strip().lower() in ('1', 'true', 'yes', 'on')
APP_HOST = os.environ.get('MOSQ_HOST', '0.0.0.0')
DEBUG_DB_PATH = os.environ.get('MOSQ_DB_PATH', '').strip()
if DEBUG_DB_PATH:
    db_path = DEBUG_DB_PATH

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Get a new database connection (short-lived per request)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-8000")  # 8MB cache
    return conn


def query_db(sql, args=(), one=False):
    """Execute a query and return results as list of dicts."""
    conn = get_db()
    try:
        cur = conn.execute(sql, args)
        rows = cur.fetchall()
        if one:
            return dict(rows[0]) if rows else None
        return [dict(r) for r in rows]
    finally:
        conn.close()


def execute_db(sql, args=()):
    """Execute a write statement."""
    conn = get_db()
    try:
        conn.execute(sql, args)
        conn.commit()
    finally:
        conn.close()


def get_default_report_prefs():
    return {
        'title': 'Trap Samples Report',
        'sub': 'Mosquito Trap Dashboard V12.1',
        'sub2': 'Biểu mẫu tổng hợp mẫu bẫy theo định dạng in ấn',
        'code': 'TSR-V12.1',
        'note': 'Báo cáo này đang map từ dữ liệu dashboard hiện có sang form trap samples để tiện in, rà soát và xuất PDF. Các cột chưa có dữ liệu nguồn trực tiếp sẽ để trống để người dùng điền tay hoặc bổ sung ở bước import chuẩn hoá sau.'
    }


def read_report_prefs():
    prefs = get_default_report_prefs()
    try:
        if os.path.exists(report_prefs_path):
            with open(report_prefs_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                for key in prefs.keys():
                    if key in data and data[key] is not None:
                        prefs[key] = str(data[key])
    except Exception:
        pass
    return prefs


def write_report_prefs(payload):
    prefs = get_default_report_prefs()
    if isinstance(payload, dict):
        for key in prefs.keys():
            if key in payload and payload[key] is not None:
                prefs[key] = str(payload[key]).strip()
    os.makedirs(os.path.dirname(report_prefs_path), exist_ok=True)
    with open(report_prefs_path, 'w', encoding='utf-8') as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)
    return prefs


# ---------------------------------------------------------------------------
# L1 In-Memory Cache
# ---------------------------------------------------------------------------

_cache = {}
DEFAULT_TTL = 60  # seconds
LONG_TTL = 300


def cache_key_from_request(prefix):
    """Build a cache key from the route + query string."""
    qs = request.query_string.decode('utf-8')
    return f"{prefix}:{qs}"


def cached(ttl=DEFAULT_TTL, prefix=None):
    """Decorator for caching endpoint responses."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = cache_key_from_request(prefix or f.__name__)
            now = time.time()
            if key in _cache:
                data, ts = _cache[key]
                if now - ts < ttl:
                    return jsonify(data)
            result = f(*args, **kwargs)
            # Store the raw data (before jsonify) in cache
            if isinstance(result, (dict, list)):
                _cache[key] = (result, now)
                return jsonify(result)
            return result
        return wrapper
    return decorator


def invalidate_cache(prefix=None):
    """Clear cache entries. If prefix given, only matching keys."""
    if prefix is None:
        _cache.clear()
    else:
        keys_to_del = [k for k in _cache if k.startswith(prefix)]
        for k in keys_to_del:
            del _cache[k]


# ---------------------------------------------------------------------------
# Query builder helpers
# ---------------------------------------------------------------------------

def build_where(params=None):
    """Build WHERE clauses from request args (or given dict)."""
    p = params or request.args
    conditions = []
    values = []

    if p.get('area'):
        conditions.append("city = ?")
        values.append(p['area'])
    if p.get('species'):
        conditions.append("detected_name = ?")
        values.append(p['species'])
    if p.get('date_from'):
        conditions.append("date >= ?")
        values.append(p['date_from'])
    if p.get('date_to'):
        conditions.append("date <= ?")
        values.append(p['date_to'])
    if p.get('model'):
        conditions.append("aimodel = ?")
        values.append(p['model'])
    if p.get('min_confidence'):
        conditions.append("CAST(confidence AS REAL) >= ?")
        values.append(float(p['min_confidence']))
    if p.get('state'):
        conditions.append("state = ?")
        values.append(p['state'])
    if p.get('date'):
        conditions.append("date = ?")
        values.append(p['date'])
    if p.get('year'):
        conditions.append("year = ?")
        values.append(p['year'])
    if p.get('site_code'):
        conditions.append("sitecode_cd = ?")
        values.append(p['site_code'])

    where_sql = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    return where_sql, values


def get_area_sql():
    """Standard area expression."""
    return "COALESCE(NULLIF(city, ''), NULLIF(location_name, ''), NULLIF(state, ''), NULLIF(subregion, ''), NULLIF(lga, ''), 'Unknown Area')"


def get_trap_sql():
    """Standard trap expression."""
    return "COALESCE(NULLIF(sitecode_cd, ''), NULLIF(agency_cd, ''), NULLIF(name, ''), 'Unknown Trap')"


# ---------------------------------------------------------------------------
# Static file / dashboard serving
# ---------------------------------------------------------------------------

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login')
def serve_login_page():
    if 'user_id' in session:
        return redirect('/')
    return send_from_directory(os.path.join(project_path, 'static'), 'login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/api/v12/auth/login', methods=['POST'])
def auth_login():
    data = request.json
    conn = get_db()
    cur = conn.execute("SELECT id, username, role, allowed_areas FROM app_users WHERE username=? AND password=?", 
                       (data.get('username'), data.get('password')))
    user = cur.fetchone()
    if user:
        session.permanent = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['allowed_areas'] = user['allowed_areas']
        return jsonify({"status": "success"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/api/v12/auth/me', methods=['GET'])
def auth_me():
    if 'user_id' in session:
        return jsonify({
            "id": session['user_id'],
            "username": session['username'],
            "role": session['role'],
            "allowed_areas": session['allowed_areas']
        })
    return jsonify({"error": "Not logged in"}), 401

@app.route('/')
@require_login
def serve_dashboard():
    return send_from_directory(project_path, 'dashboard_v12.html')


@app.route('/v10')
@require_login
def serve_dashboard_v10():
    return send_from_directory(project_path, 'dashboard_v10.html')


@app.route('/v12-report')
@require_login
def serve_dashboard_v12_report():
    return send_from_directory(project_path, 'dashboard_v12_1_report.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join(project_path, 'static'), filename)

@app.route('/<path:filename>')
@require_login
def serve_file(filename):
    return send_from_directory(project_path, filename)


# ===================================================================
# LEGACY V10 ENDPOINTS (backward compatibility)
# ===================================================================

@app.route('/api/data', methods=['GET'])
def legacy_data():
    """V9-compatible: return all data as gzip JSON blob."""
    area_sql = get_area_sql()
    trap_sql = get_trap_sql()
    sql = f"""
        SELECT date,
               {area_sql} AS area,
               {trap_sql} AS trap,
               COALESCE(NULLIF(detected_name, ''), NULLIF(orig_detected_name, ''), 'Unknown Species') AS mosquito_name,
               1 AS number_of_mosquitoes,
               latitude, longitude
        FROM {TABLE_NAME}
    """
    data = query_db(sql)
    raw_json = json.dumps(data, separators=(',', ':'))
    gz = gzip.compress(raw_json.encode('utf-8'), compresslevel=6)
    resp = make_response(gz)
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['Content-Encoding'] = 'gzip'
    resp.headers['Content-Length'] = str(len(gz))
    resp.headers['Cache-Control'] = 'public, max-age=300'
    resp.headers['X-Data-Rows'] = str(len(data))
    return resp


@app.route('/api/summary', methods=['GET'])
def legacy_summary():
    """V9-compatible summary."""
    area_sql = get_area_sql()
    trap_sql = get_trap_sql()
    sql = f"""
        SELECT COUNT(*) AS total_records,
               COUNT(DISTINCT {area_sql}) AS total_areas,
               COUNT(DISTINCT {trap_sql}) AS total_traps,
               COUNT(*) AS total_mosquitoes
        FROM {TABLE_NAME}
    """
    return jsonify(query_db(sql, one=True))


# V10 endpoints that dashboard_v10.html calls
@app.route('/api/kpi', methods=['GET'])
def legacy_kpi():
    """KPI for V10 dashboard."""
    area_sql = get_area_sql()
    trap_sql = get_trap_sql()
    where_sql, values = build_where()
    sql = f"""
        SELECT COUNT(*) AS total_records,
               COUNT(*) AS total_mosquitoes,
               COUNT(DISTINCT {area_sql}) AS total_areas,
               COUNT(DISTINCT {trap_sql}) AS total_traps
        FROM {TABLE_NAME} {where_sql}
    """
    return jsonify(query_db(sql, values, one=True))


@app.route('/api/table', methods=['GET'])
def legacy_table():
    """Paginated table for V10 dashboard."""
    area_sql = get_area_sql()
    trap_sql = get_trap_sql()
    where_sql, values = build_where()
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    offset = (page - 1) * limit

    count_sql = f"SELECT COUNT(*) as cnt FROM {TABLE_NAME} {where_sql}"
    total = query_db(count_sql, values, one=True)['cnt']

    data_sql = f"""
        SELECT date,
               {area_sql} AS area,
               {trap_sql} AS trap,
               COALESCE(NULLIF(detected_name, ''), 'Unknown Species') AS mosquito_name,
               1 AS number_of_mosquitoes
        FROM {TABLE_NAME} {where_sql}
        ORDER BY date DESC
        LIMIT ? OFFSET ?
    """
    rows = query_db(data_sql, values + [limit, offset])
    return jsonify({
        "data": rows,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total,
            "total_pages": max(1, math.ceil(total / limit))
        }
    })


@app.route('/api/chart/bar', methods=['GET'])
def legacy_chart_bar():
    """Top species bar chart for V10."""
    where_sql, values = build_where()
    sql = f"""
        SELECT detected_name AS species, COUNT(*) AS count
        FROM {TABLE_NAME} {where_sql}
        WHERE detected_name IS NOT NULL AND detected_name != ''
        {"AND" if not where_sql else "AND"} 1=1
        GROUP BY detected_name
        ORDER BY count DESC LIMIT 10
    """
    # Fix the WHERE clause logic
    if where_sql:
        sql = f"""
            SELECT detected_name AS species, COUNT(*) AS count
            FROM {TABLE_NAME} {where_sql}
              AND detected_name IS NOT NULL AND detected_name != ''
            GROUP BY detected_name ORDER BY count DESC LIMIT 10
        """
    else:
        sql = f"""
            SELECT detected_name AS species, COUNT(*) AS count
            FROM {TABLE_NAME}
            WHERE detected_name IS NOT NULL AND detected_name != ''
            GROUP BY detected_name ORDER BY count DESC LIMIT 10
        """
    return jsonify(query_db(sql, values))


@app.route('/api/chart/line', methods=['GET'])
def legacy_chart_line():
    """Monthly trend line chart for V10."""
    where_sql, values = build_where()
    if where_sql:
        sql = f"""
            SELECT date, COUNT(*) AS count
            FROM {TABLE_NAME} {where_sql}
            GROUP BY date ORDER BY date
        """
    else:
        sql = f"""
            SELECT date, COUNT(*) AS count
            FROM {TABLE_NAME}
            GROUP BY date ORDER BY date
        """
    return jsonify(query_db(sql, values))


@app.route('/api/map', methods=['GET'])
def legacy_map():
    """Map data for V10."""
    area_sql = get_area_sql()
    trap_sql = get_trap_sql()
    where_sql, values = build_where()
    base_cond = "latitude IS NOT NULL AND latitude != '' AND longitude IS NOT NULL AND longitude != ''"
    if where_sql:
        sql = f"""
            SELECT {area_sql} AS area, {trap_sql} AS trap,
                   CAST(latitude AS REAL) AS latitude, CAST(longitude AS REAL) AS longitude,
                   COUNT(*) AS count
            FROM {TABLE_NAME} {where_sql} AND {base_cond}
            GROUP BY latitude, longitude
        """
    else:
        sql = f"""
            SELECT {area_sql} AS area, {trap_sql} AS trap,
                   CAST(latitude AS REAL) AS latitude, CAST(longitude AS REAL) AS longitude,
                   COUNT(*) AS count
            FROM {TABLE_NAME} WHERE {base_cond}
            GROUP BY latitude, longitude
        """
    return jsonify(query_db(sql, values))


@app.route('/api/filters/areas', methods=['GET'])
def legacy_filter_areas():
    """Area filter for V10."""
    area_sql = get_area_sql()
    sql = f"SELECT DISTINCT {area_sql} AS area FROM {TABLE_NAME} ORDER BY area"
    return jsonify([r['area'] for r in query_db(sql)])


@app.route('/api/filters/traps', methods=['GET'])
def legacy_filter_traps():
    """Trap filter for V10, optionally filtered by area."""
    trap_sql = get_trap_sql()
    area = request.args.get('area', '')
    if area:
        area_sql = get_area_sql()
        sql = f"SELECT DISTINCT {trap_sql} AS trap FROM {TABLE_NAME} WHERE {area_sql} = ? ORDER BY trap"
        return jsonify([r['trap'] for r in query_db(sql, [area])])
    else:
        sql = f"SELECT DISTINCT {trap_sql} AS trap FROM {TABLE_NAME} ORDER BY trap"
        return jsonify([r['trap'] for r in query_db(sql)])


# ===================================================================
# V12 API ENDPOINTS
# ===================================================================

# --------------- KPI ---------------

@app.route('/api/v12/kpi', methods=['GET'])
@cached(ttl=60, prefix='v12_kpi')
def v12_kpi():
    where_sql, values = build_where()
    sql = f"""
        SELECT
            COUNT(*) AS total_records,
            COUNT(DISTINCT detected_name) AS total_species,
            COUNT(DISTINCT city) AS total_areas,
            COUNT(DISTINCT sitecode_cd) AS total_traps,
            ROUND(AVG(CAST(confidence AS REAL)), 3) AS avg_confidence,
            MIN(date) AS date_from,
            MAX(date) AS date_to,
            COUNT(DISTINCT aimodel) AS total_models
        FROM {TABLE_NAME} {where_sql}
    """
    return query_db(sql, values, one=True)


# --------------- TABLE (paginated + filtered) ---------------

@app.route('/api/v12/table', methods=['GET'])
@cached(ttl=30, prefix='v12_table')
def v12_table():
    where_sql, values = build_where()
    page = int(request.args.get('page', 1))
    limit = min(int(request.args.get('limit', 50)), 500)
    offset = (page - 1) * limit
    sort = request.args.get('sort', 'date')
    order = 'DESC' if request.args.get('order', 'desc').lower() == 'desc' else 'ASC'

    allowed_sorts = {'date', 'city', 'detected_name', 'confidence', 'aimodel', 'state'}
    if sort not in allowed_sorts:
        sort = 'date'

    count_sql = f"SELECT COUNT(*) as cnt FROM {TABLE_NAME} {where_sql}"
    total = query_db(count_sql, values, one=True)['cnt']

    data_sql = f"""
        SELECT date, city, state, detected_name, orig_detected_name,
               confidence, aimodel, sitecode_cd, location_name,
               latitude, longitude
        FROM {TABLE_NAME} {where_sql}
        ORDER BY {sort} {order}
        LIMIT ? OFFSET ?
    """
    rows = query_db(data_sql, values + [limit, offset])
    return {
        "data": rows,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total,
            "total_pages": max(1, math.ceil(total / limit))
        }
    }


# --------------- SPECIES ---------------

@app.route('/api/v12/species/breakdown', methods=['GET'])
@cached(ttl=60, prefix='v12_sp_breakdown')
def v12_species_breakdown():
    where_sql, values = build_where()
    sql = f"""
        SELECT
            detected_name,
            COUNT(*) AS count,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM {TABLE_NAME} {where_sql}), 1) AS pct,
            ROUND(AVG(CAST(confidence AS REAL)), 3) AS avg_confidence
        FROM {TABLE_NAME} {where_sql}
        {"AND" if where_sql else "WHERE"} detected_name IS NOT NULL AND detected_name != ''
        GROUP BY detected_name
        ORDER BY count DESC
        LIMIT 15
    """
    # Need to double the values for the subquery
    return query_db(sql, values + values)


@app.route('/api/v12/species/by-area', methods=['GET'])
@cached(ttl=60, prefix='v12_sp_byarea')
def v12_species_by_area():
    top_n = int(request.args.get('top_n', 10))
    where_sql, values = build_where()
    sql = f"""
        WITH top_species AS (
            SELECT detected_name FROM {TABLE_NAME}
            {where_sql}
            {"AND" if where_sql else "WHERE"} detected_name IS NOT NULL AND detected_name != ''
            GROUP BY detected_name ORDER BY COUNT(*) DESC LIMIT ?
        )
        SELECT city, detected_name, COUNT(*) AS count
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} detected_name IN (SELECT detected_name FROM top_species)
          AND city IS NOT NULL AND city != ''
        GROUP BY city, detected_name
        ORDER BY city, count DESC
    """
    return query_db(sql, values + [top_n] + values)


@app.route('/api/v12/species/diversity', methods=['GET'])
@cached(ttl=120, prefix='v12_sp_diversity')
def v12_species_diversity():
    where_sql, values = build_where()
    # Shannon diversity index per city
    # SQLite doesn't have LN, so we compute in Python
    sql = f"""
        SELECT city, detected_name, COUNT(*) AS n
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} city IS NOT NULL AND city != ''
          AND detected_name IS NOT NULL AND detected_name != ''
        GROUP BY city, detected_name
    """
    rows = query_db(sql, values)

    # Group by city
    city_data = {}
    for r in rows:
        city = r['city']
        if city not in city_data:
            city_data[city] = []
        city_data[city].append(r['n'])

    result = []
    for city, counts in city_data.items():
        total = sum(counts)
        species_count = len(counts)
        # Shannon H' = -Σ (pi * ln(pi))
        h = 0
        for n in counts:
            if n > 0 and total > 0:
                pi = n / total
                h -= pi * math.log(pi)
        result.append({
            "city": city,
            "total": total,
            "species_count": species_count,
            "shannon_h": round(h, 4)
        })
    result.sort(key=lambda x: x['shannon_h'], reverse=True)
    return result


@app.route('/api/v12/species/genus', methods=['GET'])
@cached(ttl=120, prefix='v12_sp_genus')
def v12_species_genus():
    where_sql, values = build_where()
    # Extract genus (first word of detected_name)
    sql = f"""
        SELECT
            CASE
                WHEN INSTR(detected_name, ' ') > 0
                THEN SUBSTR(detected_name, 1, INSTR(detected_name, ' ') - 1)
                ELSE detected_name
            END AS genus,
            COUNT(*) AS count,
            COUNT(DISTINCT detected_name) AS species_count,
            ROUND(AVG(CAST(confidence AS REAL)), 3) AS avg_confidence
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} detected_name IS NOT NULL AND detected_name != ''
        GROUP BY genus
        ORDER BY count DESC
    """
    return query_db(sql, values)


@app.route('/api/v12/species/matrix', methods=['GET'])
@cached(ttl=120, prefix='v12_sp_matrix')
def v12_species_matrix():
    """Species x Month heatmap matrix."""
    group_by = request.args.get('group_by', 'month')  # month or city
    where_sql, values = build_where()

    if group_by == 'city':
        sql = f"""
            SELECT detected_name, city AS group_val, COUNT(*) AS count
            FROM {TABLE_NAME}
            {where_sql}
            {"AND" if where_sql else "WHERE"} detected_name IS NOT NULL AND detected_name != ''
              AND city IS NOT NULL AND city != ''
            GROUP BY detected_name, city
            ORDER BY detected_name, city
        """
    else:
        sql = f"""
            SELECT detected_name,
                   year || '-' || PRINTF('%02d', CAST(month AS INTEGER)) AS group_val,
                   COUNT(*) AS count
            FROM {TABLE_NAME}
            {where_sql}
            {"AND" if where_sql else "WHERE"} detected_name IS NOT NULL AND detected_name != ''
            GROUP BY detected_name, group_val
            ORDER BY detected_name, group_val
        """
    rows = query_db(sql, values)

    # Pivot into matrix format
    species_set = sorted(set(r['detected_name'] for r in rows))
    group_set = sorted(set(r['group_val'] for r in rows))

    matrix = {}
    for r in rows:
        sp = r['detected_name']
        gv = r['group_val']
        if sp not in matrix:
            matrix[sp] = {}
        matrix[sp][gv] = r['count']

    return {
        "species": species_set,
        "groups": group_set,
        "matrix": matrix
    }


# --------------- TRENDS ---------------

@app.route('/api/v12/trends/monthly', methods=['GET'])
@cached(ttl=60, prefix='v12_tr_monthly')
def v12_trends_monthly():
    where_sql, values = build_where()
    sql = f"""
        WITH monthly AS (
            SELECT
                year || '-' || PRINTF('%02d', CAST(month AS INTEGER)) AS ym,
                COUNT(*) AS cnt
            FROM {TABLE_NAME} {where_sql}
            GROUP BY ym
            ORDER BY ym
        )
        SELECT ym, cnt,
               AVG(cnt) OVER (ORDER BY ym ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS ma3
        FROM monthly
    """
    return query_db(sql, values)


@app.route('/api/v12/trends/daily-counts', methods=['GET'])
@cached(ttl=60, prefix='v12_tr_daily')
def v12_trends_daily_counts():
    where_sql, values = build_where()
    sql = f"""
        SELECT date, COUNT(*) AS count,
               COUNT(DISTINCT detected_name) AS species_count
        FROM {TABLE_NAME} {where_sql}
        GROUP BY date ORDER BY date
    """
    return query_db(sql, values)


@app.route('/api/v12/trends/seasonal', methods=['GET'])
@cached(ttl=120, prefix='v12_tr_seasonal')
def v12_trends_seasonal():
    where_sql, values = build_where()
    sql = f"""
        SELECT
            CASE
                WHEN CAST(month AS INTEGER) IN (12, 1, 2) THEN 'Summer'
                WHEN CAST(month AS INTEGER) IN (3, 4, 5) THEN 'Autumn'
                WHEN CAST(month AS INTEGER) IN (6, 7, 8) THEN 'Winter'
                WHEN CAST(month AS INTEGER) IN (9, 10, 11) THEN 'Spring'
            END AS season,
            COUNT(*) AS count,
            COUNT(DISTINCT detected_name) AS species_count,
            ROUND(AVG(CAST(confidence AS REAL)), 3) AS avg_confidence,
            NULL AS avg_temp,
            NULL AS avg_humidity
        FROM {TABLE_NAME} {where_sql}
        GROUP BY season
        ORDER BY
            CASE season
                WHEN 'Summer' THEN 1
                WHEN 'Autumn' THEN 2
                WHEN 'Winter' THEN 3
                WHEN 'Spring' THEN 4
            END
    """
    return query_db(sql, values)


@app.route('/api/v12/trends/yoy', methods=['GET'])
@cached(ttl=120, prefix='v12_tr_yoy')
def v12_trends_yoy():
    target_month = request.args.get('month', '')
    where_sql, values = build_where()

    if target_month:
        extra = f"{'AND' if where_sql else 'WHERE'} CAST(month AS INTEGER) = ?"
        values.append(int(target_month))
    else:
        extra = ""

    sql = f"""
        SELECT year, month, COUNT(*) AS count,
               ROUND(AVG(CAST(confidence AS REAL)), 3) AS avg_confidence
        FROM {TABLE_NAME} {where_sql} {extra}
        GROUP BY year, month
        ORDER BY month, year
    """
    return query_db(sql, values)


@app.route('/api/v12/trends/dow', methods=['GET'])
@cached(ttl=120, prefix='v12_tr_dow')
def v12_trends_dow():
    where_sql, values = build_where()
    # SQLite strftime %w: 0=Sunday, 6=Saturday
    sql = f"""
        SELECT
            CAST(strftime('%w', date) AS INTEGER) AS dow_num,
            CASE CAST(strftime('%w', date) AS INTEGER)
                WHEN 0 THEN 'Sunday'
                WHEN 1 THEN 'Monday'
                WHEN 2 THEN 'Tuesday'
                WHEN 3 THEN 'Wednesday'
                WHEN 4 THEN 'Thursday'
                WHEN 5 THEN 'Friday'
                WHEN 6 THEN 'Saturday'
            END AS day_name,
            COUNT(*) AS count,
            ROUND(AVG(CAST(confidence AS REAL)), 3) AS avg_confidence
        FROM {TABLE_NAME} {where_sql}
        GROUP BY dow_num
        ORDER BY dow_num
    """
    return query_db(sql, values)


@app.route('/api/v12/trends/anomalies', methods=['GET'])
@cached(ttl=120, prefix='v12_tr_anomalies')
def v12_trends_anomalies():
    threshold = float(request.args.get('threshold', 2.0))
    where_sql, values = build_where()
    sql = f"""
        WITH daily AS (
            SELECT date, COUNT(*) AS cnt
            FROM {TABLE_NAME} {where_sql}
            GROUP BY date
        ),
        stats AS (
            SELECT AVG(cnt) AS mu,
                   SQRT(AVG(cnt*cnt) - AVG(cnt)*AVG(cnt)) AS sigma
            FROM daily
        )
        SELECT d.date, d.cnt AS count,
               ROUND(s.mu, 2) AS mean,
               ROUND(s.sigma, 2) AS std_dev,
               ROUND((d.cnt - s.mu) / NULLIF(s.sigma, 0), 2) AS z_score
        FROM daily d, stats s
        WHERE ABS((d.cnt - s.mu) / NULLIF(s.sigma, 0)) > ?
        ORDER BY z_score DESC
    """
    return query_db(sql, values + [threshold])


# --------------- GEO ---------------

@app.route('/api/v12/geo/heatmap', methods=['GET'])
@cached(ttl=60, prefix='v12_geo_heat')
def v12_geo_heatmap():
    where_sql, values = build_where()
    base_cond = "CAST(latitude AS REAL) != 0 AND CAST(longitude AS REAL) != 0 AND latitude IS NOT NULL AND latitude != ''"
    if where_sql:
        cond = f"{where_sql} AND {base_cond}"
    else:
        cond = f"WHERE {base_cond}"

    sql = f"""
        SELECT
            ROUND(CAST(latitude AS REAL), 4) AS lat,
            ROUND(CAST(longitude AS REAL), 4) AS lng,
            COALESCE(NULLIF(detected_name, ''), 'Unknown Species') AS species,
            COUNT(*) AS species_count
        FROM {TABLE_NAME} {cond}
        GROUP BY ROUND(CAST(latitude AS REAL), 4), ROUND(CAST(longitude AS REAL), 4), COALESCE(NULLIF(detected_name, ''), 'Unknown Species')
        ORDER BY lat, lng, species_count DESC
    """

    rows = query_db(sql, values)
    grouped = {}

    for r in rows:
        key = (r['lat'], r['lng'])
        if key not in grouped:
            grouped[key] = {
                'lat': r['lat'],
                'lng': r['lng'],
                'intensity': 0,
                'species_details': []
            }
        c = int(r.get('species_count') or 0)
        grouped[key]['intensity'] += c
        grouped[key]['species_details'].append({
            'name': r.get('species') or 'Unknown Species',
            'count': c
        })

    result = list(grouped.values())
    result.sort(key=lambda x: x['intensity'], reverse=True)
    return result


@app.route('/api/v12/geo/density-by-area', methods=['GET'])
@cached(ttl=120, prefix='v12_geo_density')
def v12_geo_density_by_area():
    where_sql, values = build_where()
    sql = f"""
        SELECT city, state,
               COUNT(*) AS count,
               COUNT(DISTINCT detected_name) AS species_count,
               ROUND(AVG(CAST(latitude AS REAL)), 6) AS center_lat,
               ROUND(AVG(CAST(longitude AS REAL)), 6) AS center_lng
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} city IS NOT NULL AND city != ''
          AND latitude IS NOT NULL AND latitude != ''
        GROUP BY city, state
        ORDER BY count DESC
    """
    return query_db(sql, values)


@app.route('/api/v12/geo/timeseries', methods=['GET'])
@cached(ttl=120, prefix='v12_geo_ts')
def v12_geo_timeseries():
    interval = request.args.get('interval', 'month')
    where_sql, values = build_where()

    if interval == 'day':
        time_expr = "date"
    else:
        time_expr = "year || '-' || PRINTF('%02d', CAST(month AS INTEGER))"

    sql = f"""
        SELECT {time_expr} AS period, city,
               ROUND(AVG(CAST(latitude AS REAL)), 6) AS center_lat,
               ROUND(AVG(CAST(longitude AS REAL)), 6) AS center_lng,
               COUNT(*) AS count
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} city IS NOT NULL AND city != ''
          AND latitude IS NOT NULL AND latitude != ''
        GROUP BY period, city
        ORDER BY period, count DESC
    """
    return query_db(sql, values)


# --------------- AI / CONFIDENCE ---------------

@app.route('/api/v12/ai/confidence-dist', methods=['GET'])
@cached(ttl=120, prefix='v12_ai_dist')
def v12_ai_confidence_dist():
    where_sql, values = build_where()
    sql = f"""
        SELECT
            CASE
                WHEN CAST(confidence AS REAL) < 0.5 THEN '0.0-0.5'
                WHEN CAST(confidence AS REAL) < 0.7 THEN '0.5-0.7'
                WHEN CAST(confidence AS REAL) < 0.8 THEN '0.7-0.8'
                WHEN CAST(confidence AS REAL) < 0.9 THEN '0.8-0.9'
                ELSE '0.9-1.0'
            END AS bin,
            COUNT(*) AS count,
            ROUND(AVG(CAST(confidence AS REAL)), 4) AS avg_confidence
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} confidence IS NOT NULL AND confidence != ''
        GROUP BY bin
        ORDER BY bin
    """
    return query_db(sql, values)


@app.route('/api/v12/ai/model-comparison', methods=['GET'])
@cached(ttl=120, prefix='v12_ai_models')
def v12_ai_model_comparison():
    where_sql, values = build_where()
    sql = f"""
        SELECT
            aimodel,
            COUNT(*) AS records,
            ROUND(AVG(CAST(confidence AS REAL)), 4) AS avg_conf,
            ROUND(MIN(CAST(confidence AS REAL)), 4) AS min_conf,
            ROUND(MAX(CAST(confidence AS REAL)), 4) AS max_conf,
            MIN(date) AS first_used,
            MAX(date) AS last_used,
            COUNT(DISTINCT detected_name) AS species_classified
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} aimodel IS NOT NULL AND aimodel != ''
          AND confidence IS NOT NULL AND confidence != ''
        GROUP BY aimodel
        ORDER BY avg_conf DESC
    """
    return query_db(sql, values)


@app.route('/api/v12/ai/low-confidence', methods=['GET'])
@cached(ttl=60, prefix='v12_ai_low')
def v12_ai_low_confidence():
    threshold = float(request.args.get('threshold', 0.5))
    page = int(request.args.get('page', 1))
    limit = min(int(request.args.get('limit', 50)), 200)
    offset = (page - 1) * limit
    where_sql, values = build_where()

    count_cond = f"{where_sql} {'AND' if where_sql else 'WHERE'} CAST(confidence AS REAL) < ? AND confidence IS NOT NULL AND confidence != ''"
    count_sql = f"SELECT COUNT(*) AS cnt FROM {TABLE_NAME} {count_cond}"
    total = query_db(count_sql, values + [threshold], one=True)['cnt']

    data_sql = f"""
        SELECT date, city, detected_name, orig_detected_name,
               confidence, aimodel, sitecode_cd
        FROM {TABLE_NAME}
        {count_cond}
        ORDER BY CAST(confidence AS REAL) ASC
        LIMIT ? OFFSET ?
    """
    rows = query_db(data_sql, values + [threshold, limit, offset])
    return {
        "data": rows,
        "threshold": threshold,
        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total,
            "total_pages": max(1, math.ceil(total / limit))
        }
    }


@app.route('/api/v12/ai/confidence-by-species', methods=['GET'])
@cached(ttl=120, prefix='v12_ai_sp')
def v12_ai_confidence_by_species():
    where_sql, values = build_where()
    sql = f"""
        SELECT
            detected_name,
            COUNT(*) AS records,
            ROUND(AVG(CAST(confidence AS REAL)), 4) AS avg_conf,
            ROUND(MIN(CAST(confidence AS REAL)), 4) AS min_conf,
            ROUND(MAX(CAST(confidence AS REAL)), 4) AS max_conf
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} detected_name IS NOT NULL AND detected_name != ''
          AND confidence IS NOT NULL AND confidence != ''
        GROUP BY detected_name
        ORDER BY avg_conf ASC
    """
    return query_db(sql, values)


@app.route('/api/v12/ai/model-timeline', methods=['GET'])
@cached(ttl=120, prefix='v12_ai_timeline')
def v12_ai_model_timeline():
    where_sql, values = build_where()
    sql = f"""
        SELECT
            aimodel,
            year || '-' || PRINTF('%02d', CAST(month AS INTEGER)) AS ym,
            COUNT(*) AS records,
            ROUND(AVG(CAST(confidence AS REAL)), 4) AS avg_conf
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} aimodel IS NOT NULL AND aimodel != ''
        GROUP BY aimodel, ym
        ORDER BY ym, aimodel
    """
    return query_db(sql, values)


@app.route('/api/v12/ai/corrections', methods=['GET'])
@cached(ttl=120, prefix='v12_ai_corrections')
def v12_ai_corrections():
    where_sql, values = build_where()
    sql = f"""
        SELECT detected_name, orig_detected_name, COUNT(*) AS count,
               ROUND(AVG(CAST(confidence AS REAL)), 4) AS avg_confidence,
               aimodel
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} detected_name != orig_detected_name
          AND detected_name IS NOT NULL AND detected_name != ''
          AND orig_detected_name IS NOT NULL AND orig_detected_name != ''
        GROUP BY detected_name, orig_detected_name, aimodel
        ORDER BY count DESC
    """
    return query_db(sql, values)


# --------------- RISK ---------------

@app.route('/api/v12/risk/scores', methods=['GET'])
@cached(ttl=60, prefix='v12_risk_scores')
def v12_risk_scores():
    """Composite risk score per area."""
    rows = query_db(f"""
        WITH area_density AS (
            SELECT city, COUNT(*) AS density
            FROM {TABLE_NAME}
            WHERE date >= date((SELECT MAX(date) FROM {TABLE_NAME}), '-30 days')
              AND city IS NOT NULL AND city != ''
            GROUP BY city
        ),
        area_recent AS (
            SELECT city, COUNT(*) AS recent_count
            FROM {TABLE_NAME}
            WHERE date >= date((SELECT MAX(date) FROM {TABLE_NAME}), '-7 days')
              AND city IS NOT NULL AND city != ''
            GROUP BY city
        ),
        area_prev AS (
            SELECT city, COUNT(*) AS prev_count
            FROM {TABLE_NAME}
            WHERE date BETWEEN date((SELECT MAX(date) FROM {TABLE_NAME}), '-14 days')
                          AND date((SELECT MAX(date) FROM {TABLE_NAME}), '-7 days')
              AND city IS NOT NULL AND city != ''
            GROUP BY city
        ),
        area_vectors AS (
            SELECT city,
                SUM(CASE WHEN detected_name IN (
                    'Aedes aegypti', 'Anopheles annulipes', 'Anopheles bancroftii',
                    'Aedes vigilax', 'Culex annulirostris'
                ) THEN 1 ELSE 0 END) AS vector_count,
                COUNT(*) AS total_count
            FROM {TABLE_NAME}
            WHERE city IS NOT NULL AND city != ''
            GROUP BY city
        ),
        area_weather AS (
            SELECT city,
                NULL AS avg_temp,
                NULL AS avg_humidity
            FROM {TABLE_NAME}
            WHERE 1=0
              AND city IS NOT NULL AND city != ''
              AND date >= date((SELECT MAX(date) FROM {TABLE_NAME}), '-30 days')
            GROUP BY city
        )
        SELECT
            d.city,
            d.density,
            COALESCE(r.recent_count, 0) AS recent_7d,
            COALESCE(p.prev_count, 0) AS prev_7d,
            ROUND(COALESCE(r.recent_count * 1.0 / NULLIF(p.prev_count, 0), 1.0), 2) AS week_ratio,
            COALESCE(v.vector_count, 0) AS vector_count,
            COALESCE(w.avg_temp, 0) AS avg_temp,
            COALESCE(w.avg_humidity, 0) AS avg_humidity,
            ROUND(
                0.35 * MIN(d.density / 100.0, 1.0) +
                0.25 * MIN(COALESCE(r.recent_count * 1.0 / NULLIF(p.prev_count, 0), 1.0) / 2.0, 1.0) +
                0.25 * MIN(COALESCE(v.vector_count, 0) / 50.0, 1.0) +
                0.15 * CASE
                    WHEN COALESCE(w.avg_temp, 0) BETWEEN 20 AND 35 AND COALESCE(w.avg_humidity, 0) > 50 THEN 0.8
                    WHEN COALESCE(w.avg_temp, 0) BETWEEN 15 AND 40 THEN 0.5
                    ELSE 0.2
                END,
            3) AS risk_score
        FROM area_density d
        LEFT JOIN area_recent r ON d.city = r.city
        LEFT JOIN area_prev p ON d.city = p.city
        LEFT JOIN area_vectors v ON d.city = v.city
        LEFT JOIN area_weather w ON d.city = w.city
        ORDER BY risk_score DESC
    """)
    return rows


@app.route('/api/v12/risk/spikes', methods=['GET'])
@cached(ttl=60, prefix='v12_risk_spikes')
def v12_risk_spikes():
    window = int(request.args.get('window', 7))
    threshold = float(request.args.get('threshold', 2.0))
    where_sql, values = build_where()

    sql = f"""
        WITH daily AS (
            SELECT date, COUNT(*) AS cnt
            FROM {TABLE_NAME} {where_sql}
            GROUP BY date
        ),
        rolling AS (
            SELECT date, cnt,
                AVG(cnt) OVER (ORDER BY date ROWS BETWEEN ? PRECEDING AND 1 PRECEDING) AS rolling_avg,
                SQRT(
                    AVG(cnt*cnt) OVER (ORDER BY date ROWS BETWEEN ? PRECEDING AND 1 PRECEDING) -
                    AVG(cnt) OVER (ORDER BY date ROWS BETWEEN ? PRECEDING AND 1 PRECEDING) *
                    AVG(cnt) OVER (ORDER BY date ROWS BETWEEN ? PRECEDING AND 1 PRECEDING)
                ) AS rolling_std
            FROM daily
        )
        SELECT date, cnt AS count,
               ROUND(rolling_avg, 2) AS rolling_avg,
               ROUND(rolling_std, 2) AS rolling_std,
               ROUND((cnt - rolling_avg) / NULLIF(rolling_std, 0), 2) AS z_score
        FROM rolling
        WHERE rolling_avg IS NOT NULL
          AND ABS((cnt - rolling_avg) / NULLIF(rolling_std, 0)) > ?
        ORDER BY date DESC
    """
    return query_db(sql, values + [window, window, window, window, threshold])


@app.route('/api/v12/risk/vector-species', methods=['GET'])
@cached(ttl=120, prefix='v12_risk_vectors')
def v12_risk_vector_species():
    where_sql, values = build_where()
    vector_list = [
        'Aedes aegypti', 'Aedes albopictus', 'Anopheles annulipes',
        'Anopheles bancroftii', 'Aedes vigilax', 'Culex annulirostris',
        'Culex quinquefasciatus'
    ]
    placeholders = ','.join(['?' for _ in vector_list])
    cond = f"{'AND' if where_sql else 'WHERE'} detected_name IN ({placeholders})"

    sql = f"""
        SELECT detected_name, city, COUNT(*) AS count,
               ROUND(AVG(CAST(confidence AS REAL)), 3) AS avg_confidence,
               MIN(date) AS first_seen, MAX(date) AS last_seen
        FROM {TABLE_NAME}
        {where_sql} {cond}
        GROUP BY detected_name, city
        ORDER BY count DESC
    """
    return query_db(sql, values + vector_list)


@app.route('/api/v12/risk/weather-correlation', methods=['GET'])
@cached(ttl=120, prefix='v12_risk_weather')
def v12_risk_weather_correlation():
    where_sql, values = build_where()
    sql = f"""
        SELECT
            date,
            COUNT(*) AS mosquito_count,
            NULL AS avg_temp,
            NULL AS avg_humidity,
            NULL AS avg_wind
        FROM {TABLE_NAME}
        {where_sql}
        {"AND" if where_sql else "WHERE"} 1=0
        GROUP BY date
        ORDER BY date
    """
    rows = query_db(sql, values)

    # Compute simple correlation coefficients
    if len(rows) > 2:
        counts = [r['mosquito_count'] for r in rows]
        temps = [r['avg_temp'] for r in rows]
        humids = [r['avg_humidity'] for r in rows]

        def pearson(x, y):
            n = len(x)
            if n < 2:
                return 0
            mx, my = sum(x)/n, sum(y)/n
            num = sum((xi-mx)*(yi-my) for xi, yi in zip(x, y))
            den = math.sqrt(sum((xi-mx)**2 for xi in x) * sum((yi-my)**2 for yi in y))
            return round(num / den, 4) if den > 0 else 0

        temp_corr = pearson(counts, temps)
        humidity_corr = pearson(counts, humids)
    else:
        temp_corr = 0
        humidity_corr = 0

    return {
        "data": rows,
        "correlations": {
            "temperature_vs_count": temp_corr,
            "humidity_vs_count": humidity_corr
        }
    }


# --------------- ALERTS ---------------

@app.route('/api/v12/alerts', methods=['GET'])
@cached(ttl=30, prefix='v12_alerts')
def v12_alerts():
    """Generate alerts dynamically from data patterns."""
    page = int(request.args.get('page', 1))
    limit = min(int(request.args.get('limit', 50)), 200)

    alerts = []

    # 1. Spike alerts (daily count > mean + 2σ)
    spike_rows = query_db(f"""
        WITH daily AS (
            SELECT date, COUNT(*) AS cnt FROM {TABLE_NAME} GROUP BY date
        ),
        stats AS (
            SELECT AVG(cnt) AS mu,
                   SQRT(AVG(cnt*cnt) - AVG(cnt)*AVG(cnt)) AS sigma
            FROM daily
        )
        SELECT d.date, d.cnt,
               ROUND((d.cnt - s.mu) / NULLIF(s.sigma, 0), 2) AS z_score
        FROM daily d, stats s
        WHERE (d.cnt - s.mu) / NULLIF(s.sigma, 0) > 2
        ORDER BY d.date DESC
    """)
    for r in spike_rows:
        alerts.append({
            "type": "spike",
            "severity": "high" if r['z_score'] > 3 else "medium",
            "date": r['date'],
            "message": f"Spike detected: {r['cnt']} records (z-score: {r['z_score']})",
            "value": r['cnt'],
            "z_score": r['z_score']
        })

    # 2. Low confidence alerts (daily avg confidence < 0.5)
    low_conf_rows = query_db(f"""
        SELECT date, COUNT(*) AS cnt,
               ROUND(AVG(CAST(confidence AS REAL)), 3) AS avg_conf
        FROM {TABLE_NAME}
        WHERE confidence IS NOT NULL AND confidence != ''
        GROUP BY date
        HAVING AVG(CAST(confidence AS REAL)) < 0.5
        ORDER BY date DESC
    """)
    for r in low_conf_rows:
        alerts.append({
            "type": "low_confidence",
            "severity": "low",
            "date": r['date'],
            "message": f"Low average confidence: {r['avg_conf']} ({r['cnt']} records)",
            "value": r['avg_conf']
        })

    # 3. Vector species alerts (any vector species in last 7 days)
    max_date = query_db(f"SELECT MAX(date) AS d FROM {TABLE_NAME}", one=True)['d']
    if max_date:
        vector_rows = query_db(f"""
            SELECT detected_name, city, COUNT(*) AS cnt
            FROM {TABLE_NAME}
            WHERE date >= date(?, '-7 days')
              AND detected_name IN ('Aedes aegypti', 'Anopheles annulipes', 'Anopheles bancroftii')
            GROUP BY detected_name, city
            ORDER BY cnt DESC
        """, [max_date])
        for r in vector_rows:
            alerts.append({
                "type": "vector_species",
                "severity": "high",
                "date": max_date,
                "message": f"Vector species {r['detected_name']} detected in {r['city']} ({r['cnt']} records in last 7 days)",
                "species": r['detected_name'],
                "area": r['city'],
                "value": r['cnt']
            })

    # Sort by severity then date
    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: (severity_order.get(a['severity'], 9), a.get('date', ''), ))

    total = len(alerts)
    start = (page - 1) * limit
    end = start + limit
    return {
        "alerts": alerts[start:end],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": max(1, math.ceil(total / limit))
        }
    }


@app.route('/api/v12/alerts/timeline', methods=['GET'])
@cached(ttl=60, prefix='v12_alerts_tl')
def v12_alerts_timeline():
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    conditions = []
    values = []
    if date_from:
        conditions.append("date >= ?")
        values.append(date_from)
    if date_to:
        conditions.append("date <= ?")
        values.append(date_to)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""

    # Spike timeline
    sql = f"""
        WITH daily AS (
            SELECT date, COUNT(*) AS cnt FROM {TABLE_NAME} {where} GROUP BY date
        ),
        stats AS (
            SELECT AVG(cnt) AS mu,
                   SQRT(AVG(cnt*cnt) - AVG(cnt)*AVG(cnt)) AS sigma
            FROM daily
        )
        SELECT d.date, d.cnt AS count,
               ROUND(s.mu, 2) AS mean,
               ROUND(s.sigma, 2) AS std_dev,
               ROUND((d.cnt - s.mu) / NULLIF(s.sigma, 0), 2) AS z_score,
               CASE
                   WHEN (d.cnt - s.mu) / NULLIF(s.sigma, 0) > 3 THEN 'critical'
                   WHEN (d.cnt - s.mu) / NULLIF(s.sigma, 0) > 2 THEN 'high'
                   WHEN (d.cnt - s.mu) / NULLIF(s.sigma, 0) > 1 THEN 'elevated'
                   ELSE 'normal'
               END AS level
        FROM daily d, stats s
        ORDER BY d.date
    """
    return query_db(sql, values)


# --------------- FILTERS ---------------

@app.route('/api/v12/filters/areas', methods=['GET'])
@cached(ttl=LONG_TTL, prefix='v12_flt_areas')
def v12_filter_areas():
    sql = f"""
        SELECT DISTINCT city AS value, city || ' (' || state || ')' AS label,
               COUNT(*) AS count
        FROM {TABLE_NAME}
        WHERE city IS NOT NULL AND city != ''
        GROUP BY city, state
        ORDER BY count DESC
    """
    return query_db(sql)


@app.route('/api/v12/filters/species', methods=['GET'])
@cached(ttl=LONG_TTL, prefix='v12_flt_species')
def v12_filter_species():
    sql = f"""
        SELECT DISTINCT detected_name AS value, detected_name AS label,
               COUNT(*) AS count
        FROM {TABLE_NAME}
        WHERE detected_name IS NOT NULL AND detected_name != ''
        GROUP BY detected_name
        ORDER BY count DESC
    """
    return query_db(sql)


@app.route('/api/v12/filters/models', methods=['GET'])
@cached(ttl=LONG_TTL, prefix='v12_flt_models')
def v12_filter_models():
    sql = f"""
        SELECT DISTINCT aimodel AS value, aimodel AS label,
               COUNT(*) AS count,
               ROUND(AVG(CAST(confidence AS REAL)), 3) AS avg_confidence
        FROM {TABLE_NAME}
        WHERE aimodel IS NOT NULL AND aimodel != ''
        GROUP BY aimodel
        ORDER BY count DESC
    """
    return query_db(sql)


# --------------- META ---------------

@app.route('/api/v12/meta/refresh', methods=['POST', 'GET'])
def v12_meta_refresh():
    """Rebuild materialized views and clear cache."""
    conn = get_db()
    try:
        t0 = time.time()
        results = {}

        # Rebuild agg_monthly_species
        conn.execute("DROP TABLE IF EXISTS agg_monthly_species")
        conn.execute("""
            CREATE TABLE agg_monthly_species AS
            SELECT year, month, city, detected_name,
                   COUNT(*) as record_count,
                   AVG(CAST(confidence AS REAL)) as avg_confidence
            FROM raw_data
            GROUP BY year, month, city, detected_name
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agg_ms_ym ON agg_monthly_species(year, month)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agg_ms_city ON agg_monthly_species(city)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agg_ms_species ON agg_monthly_species(detected_name)")
        cur = conn.execute("SELECT COUNT(*) FROM agg_monthly_species")
        results['agg_monthly_species'] = cur.fetchone()[0]

        # Rebuild agg_daily_totals
        conn.execute("DROP TABLE IF EXISTS agg_daily_totals")
        conn.execute("""
            CREATE TABLE agg_daily_totals AS
            SELECT date,
                   COUNT(*) as record_count,
                   COUNT(DISTINCT detected_name) as species_count,
                   AVG(CAST(confidence AS REAL)) as avg_confidence
            FROM raw_data
            GROUP BY date
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agg_dt_date ON agg_daily_totals(date)")
        cur = conn.execute("SELECT COUNT(*) FROM agg_daily_totals")
        results['agg_daily_totals'] = cur.fetchone()[0]

        # Rebuild agg_area_summary
        conn.execute("DROP TABLE IF EXISTS agg_area_summary")
        conn.execute("""
            CREATE TABLE agg_area_summary AS
            SELECT city, state,
                   COUNT(*) as total_records,
                   COUNT(DISTINCT detected_name) as species_count,
                   COUNT(DISTINCT sitecode_cd) as trap_count,
                   MIN(date) as first_record,
                   MAX(date) as last_record
            FROM raw_data
            GROUP BY city, state
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_agg_as_city ON agg_area_summary(city)")
        cur = conn.execute("SELECT COUNT(*) FROM agg_area_summary")
        results['agg_area_summary'] = cur.fetchone()[0]

        conn.commit()
        elapsed = time.time() - t0

        # Clear all caches
        invalidate_cache()

        return jsonify({
            "status": "ok",
            "message": "Materialized views rebuilt successfully",
            "tables": results,
            "elapsed_seconds": round(elapsed, 3)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        conn.close()


@app.route('/api/v12/meta/info', methods=['GET'])
def v12_meta_info():
    """Server info and stats."""
    conn = get_db()
    try:
        cur = conn.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        total_rows = cur.fetchone()[0]

        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]

        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='index' ORDER BY name")
        indexes = [r[0] for r in cur.fetchall()]

        return jsonify({
            "version": "12.1",
            "database": db_path,
            "total_rows": total_rows,
            "tables": tables,
            "indexes": indexes,
            "cache_entries": len(_cache),
            "port": APP_PORT,
            "debug": APP_DEBUG
        })
    finally:
        conn.close()


@app.route('/api/v12/report/prefs', methods=['GET'])
def v12_report_prefs_get():
    return jsonify({"status": "ok", "prefs": read_report_prefs()})


@app.route('/api/v12/report/prefs', methods=['POST'])
def v12_report_prefs_save():
    payload = request.get_json(silent=True) or {}
    prefs = write_report_prefs(payload)
    return jsonify({"status": "ok", "prefs": prefs})


@app.route('/api/v12/report/prefs/reset', methods=['POST'])
def v12_report_prefs_reset():
    prefs = write_report_prefs(get_default_report_prefs())
    return jsonify({"status": "ok", "prefs": prefs})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found", "path": request.path}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

# ===========================================================================
# User Management Endpoints (Access Control)
# ===========================================================================

@app.route('/users')
def serve_users_page():
    return send_from_directory(os.path.join(project_path, 'static'), 'users.html')

@app.route('/api/v12/users', methods=['GET'])
def get_users():
    conn = get_db()
    cur = conn.execute("SELECT id, username, role, allowed_areas FROM app_users")
    users = [dict(row) for row in cur.fetchall()]
    return jsonify(users)

@app.route('/api/v12/users', methods=['POST'])
def add_user():
    data = request.json
    conn = get_db()
    try:
        conn.execute("INSERT INTO app_users (username, password, role, allowed_areas) VALUES (?, ?, ?, ?)", 
                     (data['username'], data.get('password', '123456'), data['role'], data['allowed_areas']))
        conn.commit()
        return jsonify({"status": "success"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 400

@app.route('/api/v12/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    data = request.json
    conn = get_db()
    if data.get('password'):
        conn.execute("UPDATE app_users SET username=?, password=?, role=?, allowed_areas=? WHERE id=?", 
                     (data['username'], data['password'], data['role'], data['allowed_areas'], user_id))
    else:
        conn.execute("UPDATE app_users SET username=?, role=?, allowed_areas=? WHERE id=?", 
                     (data['username'], data['role'], data['allowed_areas'], user_id))
    conn.commit()
    return jsonify({"status": "success"})

@app.route('/api/v12/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db()
    conn.execute("DELETE FROM app_users WHERE id=?", (user_id,))
    conn.commit()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    print(f"=" * 60)
    print(f"  Mosquito Trap Dashboard — API Server V12.1")
    print(f"=" * 60)
    print(f"  URL:       http://127.0.0.1:{APP_PORT}")
    print(f"  Dashboard: http://127.0.0.1:{APP_PORT}/")
    print(f"  V10 compat: http://127.0.0.1:{APP_PORT}/v10")
    print(f"  Database:  {db_path}")
    print(f"  Debug:     {'ON' if APP_DEBUG else 'OFF'}")
    print(f"  Host:      {APP_HOST}")
    print(f"")
    print(f"  V12 Endpoints:")
    print(f"    /api/v12/kpi                  - KPI summary")
    print(f"    /api/v12/table                - Paginated data table")
    print(f"    /api/v12/species/*            - 5 species endpoints")
    print(f"    /api/v12/trends/*             - 6 trends endpoints")
    print(f"    /api/v12/geo/*                - 3 geo endpoints")
    print(f"    /api/v12/ai/*                 - 6 AI analysis endpoints")
    print(f"    /api/v12/risk/*               - 4 risk endpoints")
    print(f"    /api/v12/alerts               - Dynamic alerts")
    print(f"    /api/v12/alerts/timeline       - Alert timeline")
    print(f"    /api/v12/filters/*            - 3 filter endpoints")
    print(f"    /api/v12/meta/refresh         - Rebuild aggregations")
    print(f"    /api/v12/meta/info            - Server info")
    print(f"")
    print(f"  Legacy V10 Endpoints (backward compatible):")
    print(f"    /api/data, /api/summary, /api/kpi, /api/table")
    print(f"    /api/chart/bar, /api/chart/line, /api/map")
    print(f"    /api/filters/areas, /api/filters/traps")
    print(f"=" * 60)
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG, use_reloader=APP_DEBUG)


