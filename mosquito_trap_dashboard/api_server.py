
from flask import Flask, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)  # Allow all origins for simplicity

# Define paths
workspace_root = '/home/dung/.openclaw/workspace-VP2_codex/'
project_path = os.path.join(workspace_root, 'projects/mosquito_trap_dashboard')
db_path = os.path.join(project_path, 'data/mosquito_trap_dashboard.db')
TABLE_NAME = 'raw_data'

def get_db_connection():
    """Creates a database connection."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/api/data', methods=['GET'])
def get_data():
    """Endpoint to fetch all data from the raw_data table."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (TABLE_NAME,))
        if cursor.fetchone() is None:
            return jsonify({"error": f"Table '{TABLE_NAME}' not found in the database."}), 404

        # Fetch all rows from the table
        cursor.execute(f"SELECT * FROM {TABLE_NAME}")
        rows = cursor.fetchall()
        
        # Convert rows to a list of dictionaries
        data = [dict(row) for row in rows]
        
        return jsonify(data)

    except Exception as e:
        # Log the error for debugging
        print(f"Error fetching data: {e}")
        return jsonify({"error": "An internal error occurred while fetching data."}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Running on port 8788 to avoid conflict with simple HTTP server
    port = 8788
    print(f"Starting API server at http://127.0.0.1:{port}")
    print(f"Data will be available at http://127.0.0.1:{port}/api/data")
    app.run(host='0.0.0.0', port=port, debug=True)
