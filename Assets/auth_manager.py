import json
import os
import threading
import time
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import requests

FIREBASE_API_KEY = "AIzaSyA-ULQFhAgiO5TUyQkCKIp_aNJ0EUM6kRA"
FIREBASE_AUTH_DOMAIN = "meteor-dodge-game.firebaseapp.com"
FIREBASE_PROJECT_ID = "meteor-dodge-game"
FIREBASE_APP_ID = "1:387220208655:web:6977f2c563c2fec847377a"

SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pilot_session.json")


class AuthManager:
    def __init__(self):
        self.api_key = FIREBASE_API_KEY
        self.current_user = None  # {"uid": ..., "email": ..., "display_name": ..., "is_guest": ...}
        self.auth_server = None
        self.auth_thread = None
        self.auth_event = threading.Event()
        self.auth_result = None
        self.status_message = ""
        self.load_session()

    def load_session(self):
        """Loads cached session from disk if available."""
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, "r", encoding="utf-8") as f:
                    self.current_user = json.load(f)
                    self.status_message = f"Logged in as {self.current_user.get('email', 'Pilot')}"
            except Exception:
                self.current_user = None

    def save_session(self):
        """Saves current session token/profile to disk."""
        if self.current_user:
            try:
                with open(SESSION_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.current_user, f, indent=2)
            except Exception:
                pass
        else:
            if os.path.exists(SESSION_FILE):
                try:
                    os.remove(SESSION_FILE)
                except OSError:
                    pass

    def sign_out(self):
        """Logs out the current user."""
        self.current_user = None
        self.save_session()
        self.status_message = "Signed out"

    def sign_in_as_guest(self):
        """Enables quick guest pilot play with persistent local profile."""
        import uuid
        guest_id = f"guest_{uuid.uuid4().hex[:8]}"
        self.current_user = {
            "uid": guest_id,
            "email": f"{guest_id}@meteor.space",
            "display_name": f"Guest Pilot ({guest_id[-4:].upper()})",
            "is_guest": True,
        }
        self.save_session()
        self.status_message = f"Active as {self.current_user['display_name']}"
        return True, "Guest mode active"

    def sign_up_email(self, email, password):
        """Registers a new account using Firebase Identity Toolkit REST API."""
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        try:
            r = requests.post(url, json=payload, timeout=8)
            data = r.json()
            if r.status_code == 200:
                self.current_user = {
                    "uid": data["localId"],
                    "email": data["email"],
                    "id_token": data.get("idToken"),
                    "refresh_token": data.get("refreshToken"),
                    "display_name": email.split("@")[0],
                    "is_guest": False,
                }
                self.save_session()
                self.status_message = f"Welcome, {self.current_user['display_name']}!"
                return True, "Success"
            else:
                err_msg = data.get("error", {}).get("message", "Registration failed")
                if err_msg == "OPERATION_NOT_ALLOWED":
                    err_msg = "Email/Password provider not enabled in Firebase. Use Google or Guest Sign-In."
                elif err_msg == "EMAIL_EXISTS":
                    err_msg = "An account with this email already exists."
                elif "WEAK_PASSWORD" in err_msg:
                    err_msg = "Password should be at least 6 characters."
                return False, err_msg
        except Exception as e:
            return False, f"Network error: {e}"

    def sign_in_email(self, email, password):
        """Signs in with email and password via Firebase REST API."""
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={self.api_key}"
        payload = {"email": email, "password": password, "returnSecureToken": True}
        try:
            r = requests.post(url, json=payload, timeout=8)
            data = r.json()
            if r.status_code == 200:
                self.current_user = {
                    "uid": data["localId"],
                    "email": data["email"],
                    "id_token": data.get("idToken"),
                    "refresh_token": data.get("refreshToken"),
                    "display_name": data.get("displayName") or email.split("@")[0],
                    "is_guest": False,
                }
                self.save_session()
                self.status_message = f"Welcome back, {self.current_user['display_name']}!"
                return True, "Success"
            else:
                err_msg = data.get("error", {}).get("message", "Sign in failed")
                if err_msg == "EMAIL_NOT_FOUND" or err_msg == "INVALID_PASSWORD" or err_msg == "INVALID_LOGIN_CREDENTIALS":
                    err_msg = "Invalid email or password."
                elif err_msg == "OPERATION_NOT_ALLOWED":
                    err_msg = "Email/Password provider disabled in Firebase Console. Use Google Sign-in."
                return False, err_msg
        except Exception as e:
            return False, f"Network error: {e}"

    def start_google_sign_in(self, on_complete_callback=None):
        """Opens a local browser portal to sign in securely with Google via Firebase Auth."""
        self.auth_event.clear()
        self.auth_result = None
        self.status_message = "Waiting for Google login in browser..."

        parent = self

        class AuthHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Silence terminal logs

            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path in ("/", "/auth"):
                    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Meteor Space Dodge - Google Sign-In</title>
    <style>
        body {{
            background: #060b1c;
            color: #f0f4ff;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            margin: 0;
        }}
        .card {{
            background: #0d1530;
            border: 1px solid #1f3264;
            border-radius: 12px;
            padding: 36px 44px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.6);
            max-width: 420px;
        }}
        h1 {{
            color: #59dcff;
            font-size: 24px;
            margin-bottom: 8px;
        }}
        p {{
            color: #9ab0d4;
            font-size: 14px;
            line-height: 1.5;
            margin-bottom: 24px;
        }}
        button {{
            background: #ffffff;
            color: #222222;
            border: none;
            padding: 12px 24px;
            font-size: 16px;
            font-weight: 600;
            border-radius: 6px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 12px;
            transition: transform 0.15s, background 0.15s;
        }}
        button:hover {{
            background: #f0f4ff;
            transform: scale(1.02);
        }}
        #status {{
            margin-top: 18px;
            font-size: 13px;
            color: #ffd741;
        }}
    </style>
    <script type="module">
        import {{ initializeApp }} from "https://www.gstatic.com/firebasejs/10.13.0/firebase-app.js";
        import {{ getAuth, GoogleAuthProvider, signInWithPopup }} from "https://www.gstatic.com/firebasejs/10.13.0/firebase-auth.js";

        const firebaseConfig = {{
            apiKey: "{parent.api_key}",
            authDomain: "{FIREBASE_AUTH_DOMAIN}",
            projectId: "{FIREBASE_PROJECT_ID}",
            appId: "{FIREBASE_APP_ID}"
        }};

        const app = initializeApp(firebaseConfig);
        const auth = getAuth(app);
        const provider = new GoogleAuthProvider();

        window.loginWithGoogle = async function() {{
            const status = document.getElementById("status");
            status.innerText = "Opening Google login...";
            try {{
                const result = await signInWithPopup(auth, provider);
                const user = result.user;
                status.innerText = "Authorized! Syncing with Meteor Space Dodge...";
                const idToken = await user.getIdToken();
                await fetch("/callback", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{
                        uid: user.uid,
                        email: user.email,
                        displayName: user.displayName || user.email.split("@")[0],
                        idToken: idToken
                    }})
                }});
                status.innerText = "Success! You can now close this tab and return to the game.";
                status.style.color = "#59dcff";
            }} catch (error) {{
                status.innerText = "Login error: " + error.message;
                status.style.color = "#ff4b55";
            }}
        }};
    </script>
</head>
<body>
    <div class="card">
        <h1>☄️ Meteor Space Dodge</h1>
        <p>Authenticate your pilot account to sync high scores and achievements to the global Neon database.</p>
        <button onclick="loginWithGoogle()">
            <svg width="18" height="18" viewBox="0 0 18 18"><path fill="#4285F4" d="M17.64 9.2c0-.63-.06-1.25-.16-1.84H9v3.49h4.84a4.14 4.14 0 0 1-1.8 2.71v2.26h2.92c1.71-1.57 2.68-3.89 2.68-6.62z"/><path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.84.87-3.04.87-2.34 0-4.32-1.58-5.03-3.71H.96v2.33C2.44 15.98 5.48 18 9 18z"/><path fill="#FBBC05" d="M3.97 10.72A5.39 5.39 0 0 1 3.69 9c0-.6.1-1.18.28-1.72V4.95H.96A8.99 8.99 0 0 0 0 9c0 1.45.35 2.82.96 4.05l3.01-2.33z"/><path fill="#EA4335" d="M9 3.58c1.32 0 2.51.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0 5.48 0 2.44 2.02.96 4.95l3.01 2.33c.71-2.13 2.69-3.7 5.03-3.7z"/></svg>
            Sign in with Google
        </button>
        <div id="status">Click the button above to authorize</div>
    </div>
</body>
</html>"""
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(html.encode("utf-8"))
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == "/callback":
                    length = int(self.headers.get("Content-Length", 0))
                    body = self.rfile.read(length).decode("utf-8")
                    try:
                        data = json.loads(body)
                        parent.current_user = {
                            "uid": data["uid"],
                            "email": data.get("email", ""),
                            "display_name": data.get("displayName", "Pilot"),
                            "id_token": data.get("idToken"),
                            "is_guest": False,
                        }
                        parent.save_session()
                        parent.status_message = f"Welcome, {parent.current_user['display_name']}!"
                        parent.auth_result = (True, "Google login successful")
                    except Exception as err:
                        parent.auth_result = (False, f"Callback error: {err}")

                    parent.auth_event.set()
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b'{"status": "ok"}')

        def _run_server():
            try:
                server = HTTPServer(("localhost", 8484), AuthHandler)
                server.timeout = 1.0
                start_time = time.time()
                while not self.auth_event.is_set() and time.time() - start_time < 120:
                    server.handle_request()
                server.server_close()
            except Exception as ex:
                self.auth_result = (False, f"Server error: {ex}")
                self.auth_event.set()

            if on_complete_callback:
                on_complete_callback(self.current_user is not None, self.status_message)

        t = threading.Thread(target=_run_server, daemon=True)
        t.start()

        # Open user's default browser
        webbrowser.open("http://localhost:8484/auth")
        return True
