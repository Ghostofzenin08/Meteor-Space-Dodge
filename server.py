import os
import sys
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add Assets directory to path to reuse DB and Auth managers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "Assets")
if ASSETS_DIR not in sys.path:
    sys.path.insert(0, ASSETS_DIR)

from db_manager import DatabaseManager, NEON_DB_URL
from auth_manager import AuthManager, FIREBASE_PROJECT_ID

app = Flask(__name__)
CORS(app)

db = DatabaseManager()
auth = AuthManager()

# Dashboard HTML template
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meteor Space Dodge - Backend Cloud Services</title>
    <style>
        :root {
            --bg-color: #050a1b;
            --card-bg: #0d1633;
            --border-color: #1c2b54;
            --cyan: #59dcff;
            --gold: #ffd741;
            --red: #ff4b55;
            --text-main: #f0f4ff;
            --text-muted: #8c9dc3;
        }
        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 30px 20px;
        }
        .container {
            max-width: 960px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            margin-bottom: 40px;
        }
        h1 {
            color: var(--cyan);
            font-size: 32px;
            margin: 0 0 10px 0;
            letter-spacing: 1px;
        }
        .badge {
            display: inline-block;
            background: rgba(89, 220, 255, 0.15);
            color: var(--cyan);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            border: 1px solid rgba(89, 220, 255, 0.3);
            margin: 5px;
        }
        .badge.online {
            background: rgba(52, 211, 153, 0.15);
            color: #34d399;
            border-color: rgba(52, 211, 153, 0.3);
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 30px;
        }
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        }
        h2 {
            margin-top: 0;
            font-size: 20px;
            color: var(--gold);
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th, td {
            text-align: left;
            padding: 10px 8px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            font-size: 14px;
        }
        th {
            color: var(--text-muted);
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
        }
        tr:first-child td {
            color: var(--gold);
            font-weight: 600;
        }
        .endpoint {
            font-family: monospace;
            background: #070d22;
            padding: 4px 8px;
            border-radius: 4px;
            color: var(--cyan);
        }
        .method {
            font-weight: bold;
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 4px;
            margin-right: 6px;
        }
        .method.get { background: #1a4d70; color: #a5e0ff; }
        .method.post { background: #1c5238; color: #87e0a8; }
        .api-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 16px;
        }
        .api-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 14px;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>☄️ Meteor Space Dodge</h1>
            <p style="color: #ffd741; margin-bottom: 6px; font-weight: 600;">Developed by ZeninXParth (Ghostofzenin08 x parthongit89)</p>
            <p style="color: var(--text-muted); margin-bottom: 15px;">Flask Backend Services & Cloud Synchronization | <a href="https://zeninxparth.itch.io" target="_blank" style="color: var(--cyan); text-decoration: none;">zeninxparth.itch.io</a></p>
            <div>
                <span class="badge online">Neon DB: Connected</span>
                <span class="badge">Firebase: {{ firebase_project }}</span>
                <span class="badge">Status: 200 OK</span>
            </div>
        </header>

        <div class="grid">
            <div class="card">
                <h2>🏆 Neon DB Top Pilots</h2>
                {% if leaderboard %}
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Pilot</th>
                            <th>High Score</th>
                            <th>Level</th>
                            <th>Dodged</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for pilot in leaderboard %}
                        <tr>
                            <td>#{{ loop.index }}</td>
                            <td>{{ pilot.display_name }}</td>
                            <td>{{ pilot.high_score }}</td>
                            <td>Lv {{ pilot.highest_level }}</td>
                            <td>{{ pilot.meteors_dodged }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <p style="color: var(--text-muted);">No scores recorded in Neon DB yet.</p>
                {% endif %}
            </div>

            <div class="card">
                <h2>🔌 REST API Endpoints</h2>
                <div class="api-list">
                    <div class="api-item">
                        <span><span class="method get">GET</span> <span class="endpoint">/api/health</span></span>
                        <span style="color: var(--text-muted);">Service health & DB check</span>
                    </div>
                    <div class="api-item">
                        <span><span class="method get">GET</span> <span class="endpoint">/api/leaderboard</span></span>
                        <span style="color: var(--text-muted);">Top pilots leaderboard</span>
                    </div>
                    <div class="api-item">
                        <span><span class="method get">GET</span> <span class="endpoint">/api/user/&lt;uid&gt;</span></span>
                        <span style="color: var(--text-muted);">Fetch user progression</span>
                    </div>
                    <div class="api-item">
                        <span><span class="method post">POST</span> <span class="endpoint">/api/user/sync</span></span>
                        <span style="color: var(--text-muted);">Save/Sync player stats</span>
                    </div>
                    <div class="api-item">
                        <span><span class="method post">POST</span> <span class="endpoint">/api/auth/login</span></span>
                        <span style="color: var(--text-muted);">Firebase Email sign-in</span>
                    </div>
                    <div class="api-item">
                        <span><span class="method post">POST</span> <span class="endpoint">/api/auth/register</span></span>
                        <span style="color: var(--text-muted);">Firebase Email register</span>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""


@app.route("/", methods=["GET"])
def index():
    """Web dashboard showing Neon DB status and top leaderboard."""
    leaderboard = db.get_leaderboard(limit=10)
    return render_template_string(
        DASHBOARD_HTML,
        leaderboard=leaderboard,
        firebase_project=FIREBASE_PROJECT_ID
    )


@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint validating server and Neon PostgreSQL status."""
    return jsonify({
        "status": "healthy",
        "service": "Meteor Space Dodge Backend",
        "neon_db_connected": db.is_connected,
        "firebase_project": FIREBASE_PROJECT_ID,
    }), 200


@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    """Returns top pilots from Neon DB."""
    limit = request.args.get("limit", default=10, type=int)
    limit = max(1, min(limit, 50))
    rows = db.get_leaderboard(limit=limit)
    return jsonify({
        "success": True,
        "count": len(rows),
        "leaderboard": rows,
    }), 200


@app.route("/api/user/<user_uid>", methods=["GET"])
def get_user_stats(user_uid):
    """Fetches user stats by UID from Neon PostgreSQL."""
    email = request.args.get("email", default="")
    data = db.get_user_data(user_uid, email=email)
    return jsonify({
        "success": True,
        "user_uid": user_uid,
        "data": data,
    }), 200


@app.route("/api/user/sync", methods=["POST"])
def sync_user_stats():
    """Updates user score and statistics in Neon DB."""
    body = request.get_json() or {}
    user_uid = body.get("user_uid")
    if not user_uid:
        return jsonify({"success": False, "error": "Missing user_uid"}), 400

    data = body.get("data", {})
    email = body.get("email", "")

    db.save_user_data_async(user_uid, data, email=email)
    return jsonify({
        "success": True,
        "message": "Stats queued for sync with Neon DB",
        "user_uid": user_uid,
    }), 200


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Registers a new user through Firebase and synchronizes with Neon DB."""
    body = request.get_json() or {}
    email = body.get("email", "").strip()
    password = body.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password required"}), 400

    success, msg = auth.sign_up_email(email, password)
    if not success:
        return jsonify({"success": False, "error": msg}), 400

    user = auth.current_user
    # Seed new user in Neon DB
    initial_stats = body.get("initial_stats")
    db_stats = db.get_user_data(user["uid"], email=user["email"], initial_seed=initial_stats)

    return jsonify({
        "success": True,
        "user": user,
        "data": db_stats,
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticates user through Firebase and loads stats from Neon DB."""
    body = request.get_json() or {}
    email = body.get("email", "").strip()
    password = body.get("password", "")

    if not email or not password:
        return jsonify({"success": False, "error": "Email and password required"}), 400

    success, msg = auth.sign_in_email(email, password)
    if not success:
        return jsonify({"success": False, "error": msg}), 401

    user = auth.current_user
    db_stats = db.get_user_data(user["uid"], email=user["email"])

    return jsonify({
        "success": True,
        "user": user,
        "data": db_stats,
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Meteor Space Dodge Flask backend starting on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
