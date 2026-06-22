import re

file_path = '/home/dung/.openclaw/workspace-VP2_codex/projects/mosquito_trap_dashboard/api_server_v11.py'
with open(file_path, 'r') as f:
    content = f.read()

# Add endpoints for User Management if they don't exist
if '@app.route(\'/api/v11/users\'' not in content:
    user_endpoints = """

# ===========================================================================
# User Management Endpoints (Access Control)
# ===========================================================================

@app.route('/users')
def serve_users_page():
    return send_from_directory(os.path.join(project_path, 'static'), 'users.html')

@app.route('/api/v11/users', methods=['GET'])
def get_users():
    conn = get_db()
    cur = conn.execute("SELECT id, username, role, allowed_areas FROM app_users")
    users = [dict(row) for row in cur.fetchall()]
    return jsonify(users)

@app.route('/api/v11/users', methods=['POST'])
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

@app.route('/api/v11/users/<int:user_id>', methods=['PUT'])
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

@app.route('/api/v11/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    conn = get_db()
    conn.execute("DELETE FROM app_users WHERE id=?", (user_id,))
    conn.commit()
    return jsonify({"status": "success"})
"""
    content += user_endpoints
    with open(file_path, 'w') as f:
        f.write(content)
    print("User endpoints added.")
else:
    print("User endpoints already exist.")
