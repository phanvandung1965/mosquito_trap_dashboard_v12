from flask import Flask, jsonify, send_from_directory, make_response
from flask_cors import CORS
import sqlite3
import os
import gzip
import json

app = Flask(__name__)
CORS(app)

project_path = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(project_path, 'data', 'mosquito_trap_dashboard.db')
TABLE_NAME = 'raw_data'
APP_PORT = int(os.environ.get('MOSQ_PORT', '7807'))
APP_DEBUG = os.environ.get('MOSQ_DEBUG', '0').strip().lower() in ('1', 'true', 'yes', 'on')
APP_HOST = os.environ.get('MOSQ_HOST', '0.0.0.0')
DEBUG_DB_PATH = os.environ.get('MOSQ_DB_PATH', '').strip()
if DEBUG_DB_PATH:
    db_path = DEBUG_DB_PATH


def _run_mode_label():
    return 'development' if APP_DEBUG else 'production'


def get_db_connection():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# In-memory cache. Rebuilt on first request after process start.
_api_cache = {"gz": None, "raw_len": 0, "rows": 0, "summary": None}


SQL_DASHBOARD_DATA = f"""
SELECT
    date,
    COALESCE(NULLIF(city, ''), NULLIF(location_name, ''), NULLIF(state, ''), NULLIF(subregion, ''), NULLIF(lga, ''), 'Unknown Area') AS area,
    COALESCE(NULLIF(sitecode_cd, ''), NULLIF(agency_cd, ''), NULLIF(name, ''), 'Unknown Trap') AS trap,
    COALESCE(NULLIF(detected_name, ''), NULLIF(orig_detected_name, ''), 'Unknown Species') AS mosquito_name,
    1 AS number_of_mosquitoes,
    latitude,
    longitude
FROM {TABLE_NAME}
"""


def _build_dashboard_payload():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TABLE_NAME,))
        if cursor.fetchone() is None:
            return None, (jsonify({"error": f"Table '{TABLE_NAME}' not found in the database."}), 404)

        # Fast summary for above-the-fold KPI load
        if _api_cache["summary"] is None:
            cursor.execute(f"""
                SELECT
                    COUNT(*) AS total_records,
                    COUNT(DISTINCT COALESCE(NULLIF(city, ''), NULLIF(location_name, ''), NULLIF(state, ''), NULLIF(subregion, ''), NULLIF(lga, ''), 'Unknown Area')) AS total_areas,
                    COUNT(DISTINCT COALESCE(NULLIF(sitecode_cd, ''), NULLIF(agency_cd, ''), NULLIF(name, ''), 'Unknown Trap')) AS total_traps,
                    COUNT(*) AS total_mosquitoes
                FROM {TABLE_NAME}
            """)
            _api_cache["summary"] = dict(cursor.fetchone())

        cursor.execute(SQL_DASHBOARD_DATA)
        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        raw_json = json.dumps(data, separators=(',', ':'))
        gz = gzip.compress(raw_json.encode('utf-8'), compresslevel=6)

        _api_cache["gz"] = gz
        _api_cache["raw_len"] = len(raw_json)
        _api_cache["rows"] = len(data)
        return gz, None
    finally:
        if conn:
            conn.close()


@app.route('/api/data', methods=['GET'])
def get_data():
    """Return only the compact fields actually needed by the dashboard."""
    try:
        gz = _api_cache["gz"]
        if gz is None:
            gz, error_response = _build_dashboard_payload()
            if error_response is not None:
                return error_response

        resp = make_response(gz)
        resp.headers['Content-Type'] = 'application/json'
        resp.headers['Content-Encoding'] = 'gzip'
        resp.headers['Content-Length'] = str(len(gz))
        resp.headers['Cache-Control'] = 'public, max-age=300'
        resp.headers['X-Data-Rows'] = str(_api_cache["rows"])
        resp.headers['X-Raw-Bytes'] = str(_api_cache["raw_len"])
        return resp
    except Exception as e:
        print(f"Error fetching data: {e}")
        return jsonify({"error": "An internal error occurred while fetching data."}), 500


@app.route('/api/summary', methods=['GET'])
def get_summary():
    try:
        if _api_cache["summary"] is None:
            gz, error_response = _build_dashboard_payload()
            if error_response is not None:
                return error_response
        return jsonify(_api_cache["summary"])
    except Exception as e:
        print(f"Error fetching summary: {e}")
        return jsonify({"error": "An internal error occurred while fetching summary."}), 500


@app.route('/')
def serve_dashboard():
    return send_from_directory(project_path, 'dashboard_v9.01.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(project_path, filename)


if __name__ == '__main__':
    print(f"Starting API server at http://127.0.0.1:{APP_PORT} ({_run_mode_label()})")
    print(f"  - Dashboard: http://127.0.0.1:{APP_PORT}/")
    print(f"  - API Data:  http://127.0.0.1:{APP_PORT}/api/data")
    print(f"  - Debug: {'ON' if APP_DEBUG else 'OFF'} (set MOSQ_DEBUG=1 to enable)")
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG, use_reloader=APP_DEBUG)
