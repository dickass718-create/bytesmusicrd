import json
import mimetypes
import os
import traceback
import sqlite3
import secrets
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from ytmusicapi import YTMusic

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
PORT = int(os.environ.get("PORT", "8000"))
DB = ROOT / "bytesmusic.db"

MAX_BODY_BYTES = 64 * 1024
MAX_USERNAME_LENGTH = 32
MIN_PASSWORD_LENGTH = 4
MAX_PASSWORD_LENGTH = 256


def db():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA busy_timeout=10000")
    c.execute("PRAGMA journal_mode=WAL")
    return c


def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT UNIQUE NOT NULL,
      password_hash TEXT NOT NULL,
      recovery_hash TEXT NOT NULL,
      recovery_salt TEXT NOT NULL,
      is_admin INTEGER NOT NULL DEFAULT 0,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS sessions (
      token TEXT PRIMARY KEY,
      user_id INTEGER NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      video_id TEXT NOT NULL,
      title TEXT,
      artist TEXT,
      thumbnail TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS likes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      video_id TEXT NOT NULL,
      title TEXT,
      artist TEXT,
      thumbnail TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(user_id, video_id)
    );
    CREATE TABLE IF NOT EXISTS playlists (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      description TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS playlist_items (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      playlist_id INTEGER NOT NULL,
      video_id TEXT NOT NULL,
      title TEXT,
      artist TEXT,
      thumbnail TEXT,
      added_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Migrate existing DB: add is_admin column if missing
    cols = [r[1] for r in c.execute("PRAGMA table_info(users)").fetchall()]
    if "is_admin" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    # First user becomes admin automatically
    first = c.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    if first and not c.execute("SELECT id FROM users WHERE is_admin=1").fetchone():
        c.execute("UPDATE users SET is_admin=1 WHERE id=?", (first[0],))
    c.commit()
    c.close()


def hash_password(value, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = pbkdf2_hmac("sha256", value.encode(), salt.encode(), 180000).hex()
    return digest, salt


def check_password(value, digest, salt):
    candidate = hash_password(value, salt)[0]
    return compare_digest(candidate, digest)


def validate_username(username):
    if not isinstance(username, str):
        return False
    if not 2 <= len(username) <= MAX_USERNAME_LENGTH:
        return False
    return all(ch.isalnum() or ch in "_-" for ch in username)


def validate_password(password):
    return isinstance(password, str) and MIN_PASSWORD_LENGTH <= len(password) <= MAX_PASSWORD_LENGTH


def user_from_token(token):
    if not token:
        return None
    c = db()
    row = c.execute(
        "SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token=?", (token,)
    ).fetchone()
    c.close()
    return row


def admin_from_token(token):
    u = user_from_token(token)
    if not u or not u["is_admin"]:
        return None
    return u


def body(handler):
    try:
        n = int(handler.headers.get("Content-Length", "0"))
    except ValueError:
        raise ValueError("Invalid Content-Length")
    if n > MAX_BODY_BYTES:
        raise ValueError("Request body is too large")
    raw = handler.rfile.read(n) if n else b"{}"
    try:
        parsed = json.loads(raw or b"{}")
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Request body must be a JSON object")
    return parsed


def send_json(handler, payload, status=200):
    raw = json.dumps(payload, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(raw)


def search_music(query):
    ytm = YTMusic()
    rows = ytm.search(query, filter="songs", limit=25)
    result = []
    for x in rows:
        vid = x.get("videoId")
        if not vid:
            continue
        artists = x.get("artists") or []
        result.append({
            "videoId": vid,
            "title": x.get("title") or "Unknown",
            "artist": ", ".join(a.get("name", "") for a in artists),
            "duration": x.get("duration", ""),
            "thumbnail": (x.get("thumbnails") or [{}])[-1].get("url", ""),
        })
    return result


# ---- Admin stats helpers ----

def admin_stats():
    c = db()
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_history = c.execute("SELECT COUNT(*) FROM history").fetchone()[0]
    total_likes = c.execute("SELECT COUNT(*) FROM likes").fetchone()[0]
    total_playlists = c.execute("SELECT COUNT(*) FROM playlists").fetchone()[0]
    total_playlist_items = c.execute("SELECT COUNT(*) FROM playlist_items").fetchone()[0]

    # Unique songs (by video_id) across history + likes
    unique_songs = c.execute(
        "SELECT COUNT(DISTINCT video_id) FROM (SELECT video_id FROM history UNION SELECT video_id FROM likes)"
    ).fetchone()[0]

    # Unique artists
    unique_artists = c.execute(
        "SELECT COUNT(DISTINCT artist) FROM (SELECT artist FROM history WHERE artist IS NOT NULL AND artist!='' UNION SELECT artist FROM likes WHERE artist IS NOT NULL AND artist!='')"
    ).fetchone()[0]

    # Most played (most frequent in history)
    most_played = [
        dict(r) for r in c.execute(
            """SELECT video_id, title, artist, thumbnail, COUNT(*) as plays
               FROM history GROUP BY video_id ORDER BY plays DESC LIMIT 10"""
        ).fetchall()
    ]

    # Most liked
    most_liked = [
        dict(r) for r in c.execute(
            """SELECT video_id, title, artist, thumbnail, COUNT(*) as likes
               FROM likes GROUP BY video_id ORDER BY likes DESC LIMIT 10"""
        ).fetchall()
    ]

    # Recently added songs (latest history entries)
    recent_songs = [
        dict(r) for r in c.execute(
            "SELECT * FROM history ORDER BY id DESC LIMIT 10"
        ).fetchall()
    ]

    # Recent users
    recent_users = [
        dict(r) for r in c.execute(
            "SELECT id, username, is_admin, created_at FROM users ORDER BY id DESC LIMIT 10"
        ).fetchall()
    ]

    # Plays over last 7 days (by date)
    plays_by_day = [
        {"date": r[0], "plays": r[1]} for r in c.execute(
            """SELECT DATE(created_at) as d, COUNT(*) as p
               FROM history WHERE created_at >= datetime('now','-7 days')
               GROUP BY d ORDER BY d"""
        ).fetchall()
    ]

    c.close()
    return {
        "total_users": total_users,
        "total_songs": unique_songs,
        "total_artists": unique_artists,
        "total_playlists": total_playlists,
        "total_playlist_items": total_playlist_items,
        "total_plays": total_history,
        "total_likes": total_likes,
        "most_played": most_played,
        "most_liked": most_liked,
        "recent_songs": recent_songs,
        "recent_users": recent_users,
        "plays_by_day": plays_by_day,
    }


def main():
    init_db()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            print("[%s] %s" % (self.log_date_time_string(), fmt % args))

        def do_GET(self):
            try:
                p = urlparse(self.path)
                q = parse_qs(p.query)
                if p.path == "/api/health":
                    return send_json(self, {"ok": True, "app": "BytesMusic"})
                if p.path == "/api/search":
                    query = (q.get("q") or [""])[0].strip()
                    if not query:
                        return send_json(self, {"results": []})
                    if len(query) > 200:
                        return send_json(self, {"error": "Search query is too long."}, 400)
                    return send_json(self, {"results": search_music(query)})
                if p.path == "/api/auth/me":
                    u = user_from_token(self.headers.get("Authorization", "").removeprefix("Bearer "))
                    return send_json(self, {"user": dict(u) if u else None})
                if p.path == "/api/history":
                    u = user_from_token(self.headers.get("Authorization", "").removeprefix("Bearer "))
                    if not u:
                        return send_json(self, {"history": []})
                    c = db()
                    rows = [dict(r) for r in c.execute(
                        "SELECT * FROM history WHERE user_id=? ORDER BY id DESC LIMIT 100", (u["id"],)
                    )]
                    c.close()
                    return send_json(self, {"history": rows})
                if p.path == "/api/likes":
                    u = user_from_token(self.headers.get("Authorization", "").removeprefix("Bearer "))
                    if not u:
                        return send_json(self, {"likes": []})
                    c = db()
                    rows = [dict(r) for r in c.execute(
                        "SELECT * FROM likes WHERE user_id=? ORDER BY id DESC", (u["id"],)
                    )]
                    c.close()
                    return send_json(self, {"likes": rows})
                if p.path == "/api/playlists":
                    u = user_from_token(self.headers.get("Authorization", "").removeprefix("Bearer "))
                    if not u:
                        return send_json(self, {"playlists": []})
                    c = db()
                    rows = [dict(r) for r in c.execute(
                        "SELECT * FROM playlists WHERE user_id=? ORDER BY id DESC", (u["id"],)
                    )]
                    c.close()
                    return send_json(self, {"playlists": rows})

                # ---- Admin API ----
                if p.path == "/api/admin/stats":
                    u = admin_from_token(self.headers.get("Authorization", "").removeprefix("Bearer "))
                    if not u:
                        return send_json(self, {"error": "Admin access required"}, 403)
                    return send_json(self, admin_stats())

                if p.path == "/api/admin/users":
                    u = admin_from_token(self.headers.get("Authorization", "").removeprefix("Bearer "))
                    if not u:
                        return send_json(self, {"error": "Admin access required"}, 403)
                    c = db()
                    rows = [dict(r) for r in c.execute(
                        "SELECT id, username, is_admin, created_at FROM users ORDER BY id DESC"
                    )]
                    c.close()
                    return send_json(self, {"users": rows})

                if p.path == "/api/admin/history":
                    u = admin_from_token(self.headers.get("Authorization", "").removeprefix("Bearer "))
                    if not u:
                        return send_json(self, {"error": "Admin access required"}, 403)
                    c = db()
                    rows = [dict(r) for r in c.execute(
                        "SELECT h.*, u.username FROM history h LEFT JOIN users u ON h.user_id=u.id ORDER BY h.id DESC LIMIT 200"
                    )]
                    c.close()
                    return send_json(self, {"history": rows})

                if p.path == "/api/admin/likes":
                    u = admin_from_token(self.headers.get("Authorization", "").removeprefix("Bearer "))
                    if not u:
                        return send_json(self, {"error": "Admin access required"}, 403)
                    c = db()
                    rows = [dict(r) for r in c.execute(
                        "SELECT l.*, u.username FROM likes l LEFT JOIN users u ON l.user_id=u.id ORDER BY l.id DESC LIMIT 200"
                    )]
                    c.close()
                    return send_json(self, {"likes": rows})

                # ---- Static file serving ----
                if p.path == "/admin":
                    file = (STATIC / "admin.html").resolve()
                else:
                    file = (STATIC / ("index.html" if p.path == "/" else p.path.lstrip("/"))).resolve()
                if STATIC not in file.parents and file != STATIC:
                    return send_json(self, {"error": "not found"}, 404)
                if not file.exists() or not file.is_file():
                    return send_json(self, {"error": "not found"}, 404)
                data = file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", mimetypes.guess_type(file.name)[0] or "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except ValueError as e:
                send_json(self, {"error": str(e)}, 400)
            except Exception:
                traceback.print_exc()
                send_json(self, {"error": "Internal server error"}, 500)

        def do_POST(self):
            try:
                p = urlparse(self.path)
                data = body(self)
                if p.path == "/api/auth/register":
                    username = str(data.get("username", "")).strip()
                    password = str(data.get("password", ""))
                    recovery = str(data.get("recovery", ""))
                    if not validate_username(username) or not validate_password(password) or not recovery.strip():
                        return send_json(self, {"error": "Use a valid username, password and recovery answer."}, 400)
                    ph, ps = hash_password(password)
                    rh, rs = hash_password(recovery.lower())
                    c = db()
                    try:
                        # First user becomes admin
                        user_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                        is_admin = 1 if user_count == 0 else 0
                        c.execute(
                            "INSERT INTO users(username,password_hash,recovery_hash,recovery_salt,is_admin) VALUES(?,?,?,?,?)",
                            (username, ph + ":" + ps, rh, rs, is_admin),
                        )
                        c.commit()
                    except sqlite3.IntegrityError:
                        c.close()
                        return send_json(self, {"error": "Username already exists."}, 409)
                    uid = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()[0]
                    token = secrets.token_urlsafe(32)
                    c.execute("INSERT INTO sessions(token,user_id) VALUES(?,?)", (token, uid))
                    c.commit()
                    c.close()
                    return send_json(self, {"token": token, "username": username, "is_admin": is_admin})

                if p.path == "/api/auth/login":
                    username = str(data.get("username", "")).strip()
                    password = str(data.get("password", ""))
                    if not validate_username(username) or not validate_password(password):
                        return send_json(self, {"error": "Invalid username or password."}, 401)
                    c = db()
                    u = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
                    c.close()
                    if not u:
                        return send_json(self, {"error": "Invalid username or password."}, 401)
                    digest, salt = u["password_hash"].split(":", 1)
                    if not check_password(password, digest, salt):
                        return send_json(self, {"error": "Invalid username or password."}, 401)
                    token = secrets.token_urlsafe(32)
                    c = db()
                    c.execute("INSERT INTO sessions(token,user_id) VALUES(?,?)", (token, u["id"]))
                    c.commit()
                    c.close()
                    return send_json(self, {"token": token, "username": username, "is_admin": u["is_admin"]})

                if p.path == "/api/auth/reset":
                    username = str(data.get("username", "")).strip()
                    recovery = str(data.get("recovery", "")).lower()
                    newpw = str(data.get("password", ""))
                    if not validate_username(username) or not validate_password(newpw) or not recovery.strip():
                        return send_json(self, {"error": "Invalid password reset details."}, 400)
                    c = db()
                    u = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
                    if not u:
                        c.close()
                        return send_json(self, {"error": "Account not found."}, 404)
                    if not check_password(recovery, u["recovery_hash"], u["recovery_salt"]):
                        c.close()
                        return send_json(self, {"error": "Recovery answer is incorrect."}, 401)
                    ph, ps = hash_password(newpw)
                    c.execute("UPDATE users SET password_hash=? WHERE id=?", (ph + ":" + ps, u["id"]))
                    c.commit()
                    c.close()
                    return send_json(self, {"ok": True})

                if p.path == "/api/auth/logout":
                    token = self.headers.get("Authorization", "").removeprefix("Bearer ")
                    c = db()
                    c.execute("DELETE FROM sessions WHERE token=?", (token,))
                    c.commit()
                    c.close()
                    return send_json(self, {"ok": True})

                token = self.headers.get("Authorization", "").removeprefix("Bearer ")
                u = user_from_token(token)

                if p.path == "/api/history":
                    if not u:
                        return send_json(self, {"error": "Login required"}, 401)
                    video_id = str(data.get("videoId", "")).strip()
                    if not video_id:
                        return send_json(self, {"error": "videoId is required"}, 400)
                    c = db()
                    c.execute(
                        "INSERT INTO history(user_id,video_id,title,artist,thumbnail) VALUES(?,?,?,?,?)",
                        (u["id"], video_id, data.get("title"), data.get("artist"), data.get("thumbnail")),
                    )
                    c.commit()
                    c.close()
                    return send_json(self, {"ok": True})

                if p.path == "/api/likes":
                    if not u:
                        return send_json(self, {"error": "Login required"}, 401)
                    video_id = str(data.get("videoId", "")).strip()
                    if not video_id:
                        return send_json(self, {"error": "videoId is required"}, 400)
                    c = db()
                    c.execute(
                        "INSERT OR IGNORE INTO likes(user_id,video_id,title,artist,thumbnail) VALUES(?,?,?,?,?)",
                        (u["id"], video_id, data.get("title"), data.get("artist"), data.get("thumbnail")),
                    )
                    c.commit()
                    c.close()
                    return send_json(self, {"ok": True})

                if p.path == "/api/playlists":
                    if not u:
                        return send_json(self, {"error": "Login required"}, 401)
                    name = str(data.get("name", "")).strip()
                    if not name:
                        return send_json(self, {"error": "Playlist name is required"}, 400)
                    c = db()
                    c.execute(
                        "INSERT INTO playlists(user_id,name,description) VALUES(?,?,?)",
                        (u["id"], name, data.get("description", "")),
                    )
                    c.commit()
                    c.close()
                    return send_json(self, {"ok": True})

                # ---- Admin actions ----
                if p.path == "/api/admin/users/toggle-admin":
                    admin = admin_from_token(token)
                    if not admin:
                        return send_json(self, {"error": "Admin access required"}, 403)
                    target_id = data.get("userId")
                    c = db()
                    target = c.execute("SELECT * FROM users WHERE id=?", (target_id,)).fetchone()
                    if not target:
                        c.close()
                        return send_json(self, {"error": "User not found"}, 404)
                    if target["id"] == admin["id"]:
                        c.close()
                        return send_json(self, {"error": "Cannot change your own admin status"}, 400)
                    c.execute("UPDATE users SET is_admin=? WHERE id=?", (0 if target["is_admin"] else 1, target_id))
                    c.commit()
                    c.close()
                    return send_json(self, {"ok": True})

                if p.path == "/api/admin/users/delete":
                    admin = admin_from_token(token)
                    if not admin:
                        return send_json(self, {"error": "Admin access required"}, 403)
                    target_id = data.get("userId")
                    c = db()
                    target = c.execute("SELECT * FROM users WHERE id=?", (target_id,)).fetchone()
                    if not target:
                        c.close()
                        return send_json(self, {"error": "User not found"}, 404)
                    if target["id"] == admin["id"]:
                        c.close()
                        return send_json(self, {"error": "Cannot delete your own account"}, 400)
                    c.execute("DELETE FROM history WHERE user_id=?", (target_id,))
                    c.execute("DELETE FROM likes WHERE user_id=?", (target_id,))
                    c.execute("DELETE FROM sessions WHERE user_id=?", (target_id,))
                    c.execute("DELETE FROM playlist_items WHERE playlist_id IN (SELECT id FROM playlists WHERE user_id=?)", (target_id,))
                    c.execute("DELETE FROM playlists WHERE user_id=?", (target_id,))
                    c.execute("DELETE FROM users WHERE id=?", (target_id,))
                    c.commit()
                    c.close()
                    return send_json(self, {"ok": True})

                send_json(self, {"error": "not found"}, 404)
            except ValueError as e:
                send_json(self, {"error": str(e)}, 400)
            except Exception:
                traceback.print_exc()
                send_json(self, {"error": "Internal server error"}, 500)

    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"BytesMusic -> http://localhost:{PORT}")
    print("Catalog -> ytmusicapi (unauthenticated YouTube Music public search)")
    server.serve_forever()


if __name__ == "__main__":
    main()
