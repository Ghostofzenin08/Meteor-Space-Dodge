import os
import psycopg2
from psycopg2.extras import RealDictCursor
import threading

NEON_DB_URL = os.environ.get(
    "METEOR_DODGE_DB_URL",
    "postgresql://neondb_owner:npg_3Mwy8uNStxsb@ep-empty-shape-atx8rqzu-pooler.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require"
)


class DatabaseManager:
    def __init__(self, db_url=None):
        self.db_url = db_url or NEON_DB_URL
        self._lock = threading.Lock()
        self.is_connected = False
        self.init_db()

    def _get_connection(self):
        """Creates a fresh connection to Neon PostgreSQL."""
        url = self.db_url
        if "channel_binding=" in url:
            url = url.split("&channel_binding=")[0].split("?channel_binding=")[0]
            if "?" not in url and "sslmode=require" in self.db_url:
                url += "?sslmode=require"
        return psycopg2.connect(url, connect_timeout=8)

    def init_db(self):
        """Initializes tables in Neon DB."""
        def _task():
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS meteor_dodge_users (
                                id SERIAL PRIMARY KEY,
                                user_uid VARCHAR(128) UNIQUE NOT NULL,
                                email VARCHAR(255),
                                display_name VARCHAR(128),
                                high_score INT DEFAULT 0,
                                highest_level INT DEFAULT 1,
                                meteors_dodged INT DEFAULT 0,
                                games_played INT DEFAULT 0,
                                volume FLOAT DEFAULT 0.6,
                                controls VARCHAR(32) DEFAULT 'Arrows',
                                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                            );
                            CREATE INDEX IF NOT EXISTS idx_meteor_high_score 
                            ON meteor_dodge_users (high_score DESC);
                        """)
                    conn.commit()
                self.is_connected = True
                print("[NeonDB] Connected and verified table schema.")
            except Exception as e:
                self.is_connected = False
                print(f"[NeonDB] Connection warning: {e}")

        # Run init in background thread so startup doesn't hang
        threading.Thread(target=_task, daemon=True).start()

    def get_user_data(self, user_uid, email="", initial_seed=None):
        """Fetches or creates a user record synchronously (used during login/load)."""
        defaults = {
            "high_score": 0,
            "highest_level": 1,
            "meteors_dodged": 0,
            "games_played": 0,
            "volume": 0.6,
            "controls": "Arrows",
        }
        if initial_seed:
            defaults.update(initial_seed)

        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT high_score, highest_level, meteors_dodged, games_played, volume, controls, email, display_name
                        FROM meteor_dodge_users
                        WHERE user_uid = %s
                        """,
                        (user_uid,)
                    )
                    row = cur.fetchone()
                    if row:
                        self.is_connected = True
                        return {
                            "high_score": row["high_score"] or 0,
                            "highest_level": row["highest_level"] or 1,
                            "meteors_dodged": row["meteors_dodged"] or 0,
                            "games_played": row["games_played"] or 0,
                            "volume": float(row["volume"] if row["volume"] is not None else 0.6),
                            "controls": row["controls"] or "Arrows",
                        }

                    # Create new user record
                    display = email.split("@")[0] if email and "@" in email else (user_uid[:10] if user_uid else "Pilot")
                    cur.execute(
                        """
                        INSERT INTO meteor_dodge_users (
                            user_uid, email, display_name, high_score, highest_level,
                            meteors_dodged, games_played, volume, controls
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_uid) DO NOTHING
                        """,
                        (
                            user_uid,
                            email or "guest@meteor.space",
                            display,
                            defaults["high_score"],
                            defaults["highest_level"],
                            defaults["meteors_dodged"],
                            defaults["games_played"],
                            defaults["volume"],
                            defaults["controls"],
                        )
                    )
                    conn.commit()
                    self.is_connected = True
                    return defaults
        except Exception as e:
            print(f"[NeonDB] Error fetching user data: {e}")
            return defaults

    def save_user_data_async(self, user_uid, data, email="", callback=None):
        """Asynchronously persists user game stats to Neon PostgreSQL."""
        def _save():
            try:
                with self._get_connection() as conn:
                    with conn.cursor() as cur:
                        display = email.split("@")[0] if email and "@" in email else "Pilot"
                        cur.execute(
                            """
                            INSERT INTO meteor_dodge_users (
                                user_uid, email, display_name, high_score, highest_level,
                                meteors_dodged, games_played, volume, controls, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                            ON CONFLICT (user_uid) DO UPDATE SET
                                high_score = GREATEST(meteor_dodge_users.high_score, EXCLUDED.high_score),
                                highest_level = GREATEST(meteor_dodge_users.highest_level, EXCLUDED.highest_level),
                                meteors_dodged = EXCLUDED.meteors_dodged,
                                games_played = EXCLUDED.games_played,
                                volume = EXCLUDED.volume,
                                controls = EXCLUDED.controls,
                                updated_at = CURRENT_TIMESTAMP;
                            """,
                            (
                                user_uid,
                                email or "guest@meteor.space",
                                display,
                                int(data.get("high_score", 0)),
                                int(data.get("highest_level", 1)),
                                int(data.get("meteors_dodged", 0)),
                                int(data.get("games_played", 0)),
                                float(data.get("volume", 0.6)),
                                str(data.get("controls", "Arrows")),
                            )
                        )
                        conn.commit()
                self.is_connected = True
                if callback:
                    callback(True, None)
            except Exception as e:
                self.is_connected = False
                print(f"[NeonDB] Async save warning: {e}")
                if callback:
                    callback(False, str(e))

        threading.Thread(target=_save, daemon=True).start()

    def get_leaderboard(self, limit=10):
        """Fetches top pilots leaderboard synchronously or returns empty list on timeout."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT display_name, high_score, highest_level, meteors_dodged
                        FROM meteor_dodge_users
                        ORDER BY high_score DESC
                        LIMIT %s;
                        """,
                        (limit,)
                    )
                    rows = cur.fetchall()
                    self.is_connected = True
                    return rows
        except Exception as e:
            print(f"[NeonDB] Failed to load leaderboard: {e}")
            return []
