from __future__ import annotations

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session
from pathlib import Path
from functools import wraps
import json
import os
import shutil
import sqlite3
import uuid
import datetime as dt
import urllib.parse
import hashlib
import secrets
import smtplib
from email.message import EmailMessage

import requests
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

from ai_routes import ai_bp

# -----------------------------
# ENV (Meta)
# -----------------------------
load_dotenv()

META_APP_ID = os.getenv("META_APP_ID", "").strip()
META_APP_SECRET = os.getenv("META_APP_SECRET", "").strip()
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", "").strip()
META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v19.0").strip() or "v19.0"
X_ME_URL = (os.getenv("X_ME_URL") or "https://api.x.com/2/users/me").strip()
SMTP_HOST = (os.getenv("SMTP_HOST") or "").strip()
SMTP_PORT = int((os.getenv("SMTP_PORT") or "587").strip() or "587")
SMTP_USERNAME = (os.getenv("SMTP_USERNAME") or "").strip()
SMTP_PASSWORD = (os.getenv("SMTP_PASSWORD") or "").strip()
SMTP_FROM_EMAIL = (os.getenv("SMTP_FROM_EMAIL") or "").strip()
SMTP_USE_TLS = (os.getenv("SMTP_USE_TLS") or "1").strip() not in {"0", "false", "False"}
SMTP_USE_SSL = (os.getenv("SMTP_USE_SSL") or "0").strip() in {"1", "true", "True"}
PASSWORD_RESET_TTL_MINUTES = max(10, int((os.getenv("PASSWORD_RESET_TTL_MINUTES") or "60").strip() or "60"))
META_LOGIN_SCOPE = (
    os.getenv(
        "META_LOGIN_SCOPE",
        "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish",
    ).strip()
    or "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish"
)
LAUNCH_ENABLED_PLATFORMS = ("instagram", "facebook")
LAUNCH_ENABLED_SCHEDULE_MODES = {"now", "one_shot", "interval", "campaign"}

# -----------------------------
# Paths & storage
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
APP_STORAGE_DIR = (os.getenv("APP_STORAGE_DIR", "") or "").strip()
if APP_STORAGE_DIR:
    STORAGE_DIR = Path(APP_STORAGE_DIR).expanduser().resolve()
else:
    STORAGE_DIR = BASE_DIR

ROOT_DATA_DIR = STORAGE_DIR / "data"
ROOT_UPLOADS_DIR = STORAGE_DIR / "uploads"
USERS_DATA_DIR = ROOT_DATA_DIR / "users"
ROOT_DATA_DIR.mkdir(exist_ok=True)
ROOT_UPLOADS_DIR.mkdir(exist_ok=True)
USERS_DATA_DIR.mkdir(exist_ok=True)

USER_DB_FILE = ROOT_DATA_DIR / "mysocial.db"
META_PENDING_FILE = ROOT_DATA_DIR / "meta_pending.json"

LEGACY_SCHEDULED_FILE = ROOT_DATA_DIR / "scheduled_posts.json"
LEGACY_DRAFTS_FILE = ROOT_DATA_DIR / "draft_posts.json"
LEGACY_QUEUE_FILE = ROOT_DATA_DIR / "queue.json"
LEGACY_ARCHIVE_FILE = ROOT_DATA_DIR / "archive.json"
LEGACY_ACCOUNTS_FILE = ROOT_DATA_DIR / "accounts.json"
LEGACY_WORKER_LOG_FILE = ROOT_DATA_DIR / "worker.log"

USER_FILE_NAMES = {
    "scheduled": "scheduled_posts.json",
    "drafts": "draft_posts.json",
    "queue": "queue.json",
    "archive": "archive.json",
    "accounts": "accounts.json",
    "worker_log": "worker.log",
}

# -----------------------------
# Helpers
# -----------------------------
def _now() -> dt.datetime:
    return dt.datetime.now()


def _parse_dt_local(s: str) -> dt.datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None


def _parse_date_local(s: str) -> dt.date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s)
    except Exception:
        return None


def _iso(d: dt.datetime | None) -> str:
    if not d:
        return ""
    return d.replace(microsecond=0).isoformat()


def _format_local_dt(value: str) -> str:
    parsed = _parse_dt_local(value)
    if not parsed:
        return (value or "").strip() or "-"
    return parsed.strftime("%d.%m.%Y %H:%M")


def _sanitize_secret_text(value: str) -> str:
    text = str(value or "")
    if META_APP_SECRET:
        text = text.replace(META_APP_SECRET, "[redacted]")
        text = text.replace(urllib.parse.quote(META_APP_SECRET, safe=""), "[redacted]")
    return text


def _meta_error_message(exc: Exception, fallback: str) -> str:
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        status = exc.response.status_code
        try:
            payload = exc.response.json()
        except Exception:
            payload = None

        detail = ""
        if isinstance(payload, dict):
            err = payload.get("error")
            if isinstance(err, dict):
                detail = (
                    err.get("message")
                    or err.get("error_user_msg")
                    or err.get("error_subcode")
                    or ""
                )
            if not detail:
                detail = payload.get("message") or ""
        if not detail:
            detail = exc.response.text or fallback

        detail = _sanitize_secret_text(detail).strip()
        return f"{fallback} ({status}): {detail[:500]}"

    return _sanitize_secret_text(fallback)


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def default_accounts() -> dict:
    return {
        "facebook": {
            "enabled": False,
            "status": "not_connected",
            "account_name": "",
            "page_id": "",
            "page_access_token": "",
            "meta_user_access_token": "",
            "note": "",
            "updated_at": "",
        },
        "instagram": {
            "enabled": False,
            "status": "not_connected",
            "account_name": "",
            "ig_business_id": "",
            "access_token": "",
            "note": "",
            "updated_at": "",
        },
        "x": {
            "enabled": False,
            "status": "not_connected",
            "account_name": "",
            "access_token": "",
            "note": "",
            "updated_at": "",
        },
        "youtube": {
            "enabled": False,
            "status": "not_connected",
            "account_name": "",
            "access_token": "",
            "note": "",
            "updated_at": "",
        },
        "tiktok": {
            "enabled": False,
            "status": "not_connected",
            "account_name": "",
            "access_token": "",
            "note": "",
            "updated_at": "",
        },
    }


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(USER_DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_user_db() -> None:
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT UNIQUE NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                used_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON password_reset_tokens(user_id)"
        )


def get_user_by_email(email: str):
    with get_db_connection() as conn:
        return conn.execute("SELECT id, email, password_hash, created_at FROM users WHERE email = ?", ((email or "").strip().lower(),)).fetchone()


def get_user_by_id(user_id: int):
    with get_db_connection() as conn:
        return conn.execute("SELECT id, email, password_hash, created_at FROM users WHERE id = ?", (int(user_id),)).fetchone()


def create_user(email: str, password: str) -> int:
    stamp = _iso(_now())
    with get_db_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users(email, password_hash, created_at) VALUES(?,?,?)",
            ((email or "").strip().lower(), generate_password_hash(password), stamp),
        )
        conn.commit()
        return int(cur.lastrowid)


def update_user_password(user_id: int, password: str) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (generate_password_hash(password), int(user_id)),
        )
        conn.commit()


def _password_reset_token_hash(raw_token: str) -> str:
    return hashlib.sha256((raw_token or "").encode("utf-8")).hexdigest()


def create_password_reset_token(user_id: int) -> tuple[str, str]:
    raw_token = secrets.token_urlsafe(32)
    token_hash = _password_reset_token_hash(raw_token)
    created_at = _now()
    expires_at = created_at + dt.timedelta(minutes=PASSWORD_RESET_TTL_MINUTES)
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO password_reset_tokens(user_id, token_hash, expires_at, created_at, used_at)
            VALUES(?,?,?,?,NULL)
            """,
            (int(user_id), token_hash, _iso(expires_at), _iso(created_at)),
        )
        conn.commit()
    return raw_token, _iso(expires_at)


def get_password_reset_token(raw_token: str):
    token_hash = _password_reset_token_hash(raw_token)
    with get_db_connection() as conn:
        return conn.execute(
            """
            SELECT prt.id, prt.user_id, prt.expires_at, prt.created_at, prt.used_at, u.email
            FROM password_reset_tokens prt
            JOIN users u ON u.id = prt.user_id
            WHERE prt.token_hash = ?
            """,
            (token_hash,),
        ).fetchone()


def mark_password_reset_token_used(token_id: int) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE id = ?",
            (_iso(_now()), int(token_id)),
        )
        conn.commit()


def invalidate_password_reset_tokens_for_user(user_id: int) -> None:
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
            (_iso(_now()), int(user_id)),
        )
        conn.commit()


def password_reset_token_error(token_row) -> str:
    if not token_row:
        return "Şifre sıfırlama bağlantısı geçersiz."
    if (token_row["used_at"] or "").strip():
        return "Bu şifre sıfırlama bağlantısı zaten kullanılmış."
    expires_at = _parse_dt_local(token_row["expires_at"] or "")
    if not expires_at or expires_at < _now():
        return "Şifre sıfırlama bağlantısının süresi dolmuş."
    return ""


def is_local_request_host() -> bool:
    host = (request.host or "").split(":", 1)[0].strip().lower()
    return host in {"127.0.0.1", "localhost"}


def send_password_reset_email(target_email: str, reset_link: str) -> tuple[bool, str]:
    if not SMTP_HOST or not SMTP_FROM_EMAIL:
        return False, "smtp_not_configured"

    msg = EmailMessage()
    msg["Subject"] = "MySocial Panel | Sifre Sifirlama"
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = target_email
    msg.set_content(
        "\n".join(
            [
                "MySocial Panel sifreni sifirlamak icin asagidaki baglantiyi kullan:",
                "",
                reset_link,
                "",
                f"Bu baglanti {PASSWORD_RESET_TTL_MINUTES} dakika boyunca gecerli kalir.",
                "Eger bu talebi sen yapmadiysan bu e-postayi yok sayabilirsin.",
            ]
        )
    )

    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20) as server:
                if SMTP_USERNAME:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
                if SMTP_USE_TLS:
                    server.starttls()
                if SMTP_USERNAME:
                    server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
        return True, "sent"
    except Exception as exc:
        return False, str(exc)


def current_user_id() -> int | None:
    raw = session.get("user_id")
    try:
        return int(raw) if raw else None
    except Exception:
        return None


def current_user_email() -> str:
    return (session.get("user_email") or "").strip()


def user_data_dir(user_id: int | None = None) -> Path:
    uid = int(user_id or current_user_id() or 0)
    if uid < 1:
        raise RuntimeError("Geçerli kullanıcı bulunamadı.")
    path = USERS_DATA_DIR / str(uid)
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_uploads_dir(user_id: int | None = None) -> Path:
    uid = int(user_id or current_user_id() or 0)
    if uid < 1:
        raise RuntimeError("Geçerli kullanıcı bulunamadı.")
    path = ROOT_UPLOADS_DIR / str(uid)
    path.mkdir(parents=True, exist_ok=True)
    return path


def user_file(key: str, user_id: int | None = None) -> Path:
    filename = USER_FILE_NAMES[key]
    return user_data_dir(user_id) / filename


def user_has_meaningful_data(user_id: int) -> bool:
    if load_json(user_file("queue", user_id), []):
        return True
    if load_json(user_file("archive", user_id), []):
        return True
    if load_json(user_file("scheduled", user_id), []):
        return True
    if load_json(user_file("drafts", user_id), []):
        return True
    return load_accounts(user_id) != default_accounts()


def ensure_user_files(user_id: int | None = None) -> None:
    uid = int(user_id or current_user_id() or 0)
    if uid < 1:
        return
    if not user_file("scheduled", uid).exists():
        save_json(user_file("scheduled", uid), [])
    if not user_file("drafts", uid).exists():
        save_json(user_file("drafts", uid), [])
    if not user_file("queue", uid).exists():
        save_json(user_file("queue", uid), [])
    if not user_file("archive", uid).exists():
        save_json(user_file("archive", uid), [])
    if not user_file("accounts", uid).exists():
        save_json(user_file("accounts", uid), default_accounts())
    if not user_file("worker_log", uid).exists():
        user_file("worker_log", uid).write_text("", encoding="utf-8")
    user_uploads_dir(uid)


def migrate_legacy_data_if_needed(user_id: int) -> int:
    ensure_user_files(user_id)
    if user_has_meaningful_data(user_id):
        return 0

    other_user_dirs = [p for p in USERS_DATA_DIR.iterdir() if p.is_dir() and p.name != str(user_id)]
    if other_user_dirs:
        return 0

    migrated = 0
    legacy_map = {
        "scheduled": LEGACY_SCHEDULED_FILE,
        "drafts": LEGACY_DRAFTS_FILE,
        "queue": LEGACY_QUEUE_FILE,
        "archive": LEGACY_ARCHIVE_FILE,
        "accounts": LEGACY_ACCOUNTS_FILE,
        "worker_log": LEGACY_WORKER_LOG_FILE,
    }
    for key, source in legacy_map.items():
        if not source.exists():
            continue
        target = user_file(key, user_id)
        if source.resolve() == target.resolve():
            continue
        try:
            shutil.copy2(source, target)
            migrated += 1
        except Exception:
            continue
    return migrated


def login_user_session(user_row) -> None:
    session["user_id"] = int(user_row["id"])
    session["user_email"] = (user_row["email"] or "").strip().lower()
    ensure_user_files(int(user_row["id"]))


def logout_user_session() -> None:
    session.pop("user_id", None)
    session.pop("user_email", None)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user_id():
            return redirect(url_for("login"))
        ensure_user_files()
        return view(*args, **kwargs)

    return wrapped


def load_queue_items(user_id: int | None = None) -> list[dict]:
    items = load_json(user_file("queue", user_id), [])
    if not isinstance(items, list):
        return []
    return items


def load_accounts(user_id: int | None = None) -> dict:
    ensure_user_files(user_id)
    raw = load_json(user_file("accounts", user_id), {})
    defaults = default_accounts()
    if not isinstance(raw, dict):
        return defaults

    merged = {}
    for platform, cfg in defaults.items():
        existing = raw.get(platform, {})
        if not isinstance(existing, dict):
            existing = {}
        merged[platform] = {**cfg, **existing}
    return merged


def save_accounts(data: dict, user_id: int | None = None) -> None:
    defaults = default_accounts()
    out = {}
    for platform, cfg in defaults.items():
        existing = data.get(platform, {})
        if not isinstance(existing, dict):
            existing = {}
        out[platform] = {**cfg, **existing}
    save_json(user_file("accounts", user_id), out)


def has_saved_platform_auth(accounts: dict, platform: str) -> bool:
    cfg = accounts.get(platform) or {}
    if not cfg.get("enabled"):
        return False
    if cfg.get("status") != "connected":
        return False

    if platform == "facebook":
        return bool(cfg.get("page_id") and cfg.get("page_access_token"))

    if platform == "instagram":
        token = (cfg.get("access_token") or "").strip() or (accounts.get("facebook", {}).get("page_access_token") or "").strip()
        return bool(cfg.get("ig_business_id") and token)

    return bool((cfg.get("access_token") or "").strip())


def ensure_files():
    ROOT_DATA_DIR.mkdir(exist_ok=True)
    ROOT_UPLOADS_DIR.mkdir(exist_ok=True)
    USERS_DATA_DIR.mkdir(exist_ok=True)
    init_user_db()
    if not META_PENDING_FILE.exists():
        save_json(META_PENDING_FILE, {})


def infer_media_kind(filename: str) -> str:
    fn = (filename or "").lower()
    if fn.endswith((".mp4", ".mov", ".mkv", ".webm", ".avi")):
        return "video"
    if fn.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic")):
        return "image"
    return "file"


def save_uploads(files, user_id: int | None = None) -> list[dict]:
    uid = int(user_id or current_user_id() or 0)
    if uid < 1:
        return []
    out = []
    uploads_dir = user_uploads_dir(uid)
    for f in files:
        if not f or not getattr(f, "filename", ""):
            continue
        original = Path(f.filename).name
        ext = Path(original).suffix.lower()
        safe_name = f"{uuid.uuid4().hex}{ext}"
        abs_path = uploads_dir / safe_name
        f.save(abs_path)
        out.append({
            "kind": infer_media_kind(original),
            "path": f"uploads/{uid}/{safe_name}",
            "name": original,
        })
    return out


def filter_media_by_mode(media: list[dict], media_mode: str) -> list[dict]:
    if media_mode == "image":
        return [m for m in media if m.get("kind") == "image"]
    if media_mode == "video":
        return [m for m in media if m.get("kind") == "video"]
    return media


def parse_targets(raw: str, platforms: list[str]) -> dict:
    out = {}
    if not isinstance(platforms, list):
        return out
    platform_set = {str(p).strip().lower() for p in platforms if str(p).strip()}
    text = (raw or "").strip()
    if not text:
        return out

    for line in text.splitlines():
        ln = (line or "").strip()
        if not ln:
            continue
        parts = [p.strip().lower() for p in ln.split(":") if p.strip()]
        if len(parts) == 1 and "facebook" in platform_set and parts[0].isdigit():
            out.setdefault("facebook", []).append({"kind": "group", "id": parts[0]})
            continue
        if len(parts) != 3:
            continue
        platform, kind, target_id = parts
        if platform not in platform_set:
            continue
        if kind not in ("page", "group", "self"):
            continue
        if kind != "self" and not target_id:
            continue
        out.setdefault(platform, []).append({"kind": kind, "id": target_id})

    return out


def validate_post_payload(text: str, hashtags: str, platforms: list[str], fmt: str, media: list[dict]) -> list[str]:
    errors: list[str] = []
    selected = [str(p).strip().lower() for p in (platforms or []) if str(p).strip()]
    selected_set = set(selected)
    fmt = (fmt or "normal").strip().lower()
    media = media or []

    if not selected:
        errors.append("En az bir platform seçmelisin.")
        return errors

    launch_blocked = [p for p in selected if p not in LAUNCH_ENABLED_PLATFORMS]
    if launch_blocked:
        errors.append("Hızlı yayında şu an sadece Facebook ve Instagram açık.")

    if "instagram" in selected_set and not media:
        errors.append("Instagram için en az 1 foto/video seçmelisin.")

    if fmt == "story":
        if len(media) != 1:
            errors.append("Story formatında tek medya seçmelisin.")
        if "facebook" in selected_set:
            errors.append("Story formatı şu an sadece Instagram için gerçek story olarak destekleniyor.")

    if "facebook" in selected_set and not (text.strip() or hashtags.strip() or media):
        errors.append("Facebook için metin/hashtag veya medya gerekir.")

    return errors


def test_x_token(raw_token: str) -> tuple[bool, str, dict]:
    token = (raw_token or "").strip()
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()
    if not token:
        return False, "X token boş.", {}

    try:
        res = requests.get(
            X_ME_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        payload = res.json() if res.text else {}
    except Exception as exc:
        return False, f"X token test hatası: {exc}", {}

    if res.status_code >= 400:
        detail = payload
        if isinstance(payload, dict):
            errs = payload.get("errors")
            if isinstance(errs, list) and errs:
                detail = errs[0].get("detail") or errs[0].get("message") or str(errs[0])
        return False, f"X token geçersiz: {detail}", {}

    data = payload.get("data") if isinstance(payload, dict) else {}
    if not isinstance(data, dict):
        data = {}
    user_name = (data.get("username") or data.get("name") or "").strip()
    user_id = (data.get("id") or "").strip()
    label = user_name or user_id or "ok"
    return True, f"X token doğrulandı: {label}", data


def _meta_graph_url(path: str) -> str:
    return f"https://graph.facebook.com/{META_GRAPH_VERSION}/{path.lstrip('/')}"


def get_token_scopes(user_token: str) -> list[str]:
    token = (user_token or "").strip()
    if not token or not META_APP_ID or not META_APP_SECRET:
        return []
    try:
        res = requests.get(
            "https://graph.facebook.com/debug_token",
            params={
                "input_token": token,
                "access_token": f"{META_APP_ID}|{META_APP_SECRET}",
            },
            timeout=20,
        )
        res.raise_for_status()
        payload = res.json()
        scopes = payload.get("data", {}).get("scopes") or []
        if isinstance(scopes, list):
            return [str(s).strip() for s in scopes if str(s).strip()]
    except Exception:
        return []
    return []


def get_token_debug_data(user_token: str) -> dict:
    token = (user_token or "").strip()
    if not token or not META_APP_ID or not META_APP_SECRET:
        return {}
    try:
        res = requests.get(
            "https://graph.facebook.com/debug_token",
            params={
                "input_token": token,
                "access_token": f"{META_APP_ID}|{META_APP_SECRET}",
            },
            timeout=20,
        )
        res.raise_for_status()
        payload = res.json()
        data = payload.get("data") or {}
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def exchange_for_long_lived_meta_token(user_access_token: str) -> tuple[str, str]:
    token = (user_access_token or "").strip()
    if not token:
        return "", "Meta user access token boş."
    if not META_APP_ID or not META_APP_SECRET:
        return token, ""

    try:
        res = requests.get(
            _meta_graph_url("/oauth/access_token"),
            params={
                "grant_type": "fb_exchange_token",
                "client_id": META_APP_ID,
                "client_secret": META_APP_SECRET,
                "fb_exchange_token": token,
            },
            timeout=25,
        )
        payload = res.json() if res.text else {}
    except Exception as exc:
        return token, str(exc)

    if res.status_code >= 400:
        err = payload.get("error", {}).get("message") if isinstance(payload, dict) else ""
        return token, err or res.text or "long_lived_token_exchange_failed"

    long_lived = (payload.get("access_token") or "").strip() if isinstance(payload, dict) else ""
    if not long_lived:
        return token, "Long-lived token dönmedi."
    return long_lived, ""


def discover_pages_from_debug_targets(user_access_token: str) -> list[dict]:
    data = get_token_debug_data(user_access_token)
    granular = data.get("granular_scopes") or []
    if not isinstance(granular, list):
        return []

    page_ids: list[str] = []
    for item in granular:
        if not isinstance(item, dict):
            continue
        scope = (item.get("scope") or "").strip()
        if scope not in ("pages_show_list", "pages_manage_posts", "pages_read_engagement"):
            continue
        tids = item.get("target_ids") or []
        if not isinstance(tids, list):
            continue
        for tid in tids:
            sid = str(tid).strip()
            if sid and sid not in page_ids:
                page_ids.append(sid)

    pages: list[dict] = []
    for page_id in page_ids:
        try:
            res = requests.get(
                _meta_graph_url(f"/{page_id}"),
                params={
                    "fields": "id,name,access_token,instagram_business_account{id,username},connected_instagram_account{id,username}",
                    "access_token": user_access_token,
                },
                timeout=25,
            )
            res.raise_for_status()
            page = res.json() if res.text else {}
            if not isinstance(page, dict):
                continue
            if not page.get("id"):
                continue
            if not page.get("instagram_business_account") and page.get("connected_instagram_account"):
                page["instagram_business_account"] = page.get("connected_instagram_account")
            pages.append(page)
        except Exception:
            continue

    return pages


def reactivate_scheduled_jobs_after_auth(accounts: dict, user_id: int | None = None) -> int:
    scheduled = load_json(user_file("scheduled", user_id), [])
    if not isinstance(scheduled, list):
        return 0

    updated_at = _iso(_now())
    changed = 0
    for job in scheduled:
        status = (job.get("status") or "").strip().lower()
        if status not in {"needs_auth", "paused_auth"}:
            continue

        platforms = [str(p).strip().lower() for p in (job.get("platforms") or []) if str(p).strip()]
        if not platforms:
            continue
        if not all(has_saved_platform_auth(accounts, platform) for platform in platforms):
            continue

        jtype = (job.get("type") or "").strip().lower()
        if jtype == "one_shot":
            job["status"] = "scheduled"
        elif jtype in {"interval", "interval_range", "recurring"}:
            job["status"] = "active"
        else:
            continue

        job["last_error"] = ""
        job["updated_at"] = updated_at
        changed += 1

    if changed:
        save_json(user_file("scheduled", user_id), scheduled)
    return changed


def save_meta_page_selection(page: dict, user_access_token: str, user_id: int | None = None) -> dict:
    accounts = load_accounts(user_id)
    fb = accounts.get("facebook", {})
    fb.update({
        "enabled": True,
        "status": "connected",
        "account_name": page.get("name", ""),
        "page_id": page.get("id", ""),
        "page_access_token": page.get("access_token", ""),
        "meta_user_access_token": user_access_token,
        "updated_at": _iso(_now()),
    })
    accounts["facebook"] = fb

    ig = page.get("instagram_business_account") or {}
    if isinstance(ig, dict) and ig.get("id"):
        insta = accounts.get("instagram", {})
        insta.update({
            "enabled": True,
            "status": "connected",
            "account_name": ig.get("username", insta.get("account_name", "")),
            "ig_business_id": ig.get("id", ""),
            "access_token": insta.get("access_token") or page.get("access_token", ""),
            "updated_at": _iso(_now()),
            "note": "Meta page üzerinden bağlandı",
        })
        accounts["instagram"] = insta

    save_accounts(accounts, user_id)
    reactivated_jobs = reactivate_scheduled_jobs_after_auth(accounts, user_id)
    return {
        "page_id": fb.get("page_id"),
        "account_name": fb.get("account_name"),
        "connected_at": fb.get("updated_at"),
        "reactivated_jobs": reactivated_jobs,
    }


def refresh_instagram_from_page(accounts: dict, user_id: int | None = None) -> tuple[bool, str]:
    fb = accounts.get("facebook", {})
    page_id = (fb.get("page_id") or "").strip()
    page_token = (fb.get("page_access_token") or "").strip()
    user_token = (fb.get("meta_user_access_token") or "").strip()

    if not page_id or not page_token:
        return False, "Instagram yenileme için önce Facebook Page bağlantısı gerekir."

    scopes = set(get_token_scopes(user_token))
    required_scopes = {"pages_show_list", "instagram_basic", "instagram_content_publish"}
    missing = sorted(required_scopes - scopes) if scopes else sorted(required_scopes)
    if missing:
        miss = ", ".join(missing)
        return False, f"Eksik Meta izinleri: {miss}. Önce 'Yetkiyi Yenile' yap."

    try:
        res = requests.get(
            _meta_graph_url(f"/{page_id}"),
            params={
                "fields": "name,instagram_business_account{id,username},connected_instagram_account{id,username}",
                "access_token": page_token,
            },
            timeout=25,
        )
        res.raise_for_status()
        payload = res.json()
    except Exception as exc:
        return False, f"Instagram bilgisi alınamadı: {exc}"

    ig = payload.get("instagram_business_account") or payload.get("connected_instagram_account") or {}
    if not isinstance(ig, dict) or not ig.get("id"):
        insta = accounts.get("instagram", {})
        insta.update({
            "enabled": False,
            "status": "not_connected",
            "ig_business_id": "",
            "updated_at": _iso(_now()),
            "note": "Bu Facebook sayfasına bağlı Instagram Business hesabı bulunamadı.",
        })
        accounts["instagram"] = insta
        save_accounts(accounts, user_id)
        return False, "Bu Facebook sayfasına bağlı Instagram Business hesabı bulunamadı."

    insta = accounts.get("instagram", {})
    current_ig_token = (insta.get("access_token") or "").strip()
    if not current_ig_token or current_ig_token.upper().startswith("DUMMY"):
        current_ig_token = page_token
    insta.update({
        "enabled": True,
        "status": "connected",
        "account_name": ig.get("username", insta.get("account_name", "")),
        "ig_business_id": ig.get("id", ""),
        "access_token": current_ig_token,
        "updated_at": _iso(_now()),
        "note": "Facebook Page üzerinden yenilendi.",
    })
    accounts["instagram"] = insta
    save_accounts(accounts, user_id)
    return True, f"Instagram bağlandı: {insta.get('account_name') or insta.get('ig_business_id')}"


# -----------------------------
# App init
# -----------------------------
ensure_files()
app = Flask(__name__)
app.secret_key = (os.getenv("FLASK_SECRET_KEY") or os.getenv("SECRET_KEY") or "dev-secret-change-me").strip()
app.register_blueprint(ai_bp)
app.jinja_env.filters["local_dt"] = _format_local_dt


@app.context_processor
def inject_current_user():
    uid = current_user_id()
    if not uid:
        return {"current_user": None}
    return {
        "current_user": {
            "id": uid,
            "email": current_user_email(),
        }
    }


@app.before_request
def enforce_login_for_app():
    endpoint = (request.endpoint or "").strip()
    if not endpoint:
        return None
    if endpoint == "static" or request.path.startswith("/static/"):
        return None
    if endpoint in {
        "home",
        "login",
        "register",
        "forgot_password",
        "reset_password",
        "pricing",
        "privacy",
        "terms",
        "robots_txt",
        "sitemap_xml",
        "uploaded_file",
        "meta_callback",
        "meta_select_page",
    }:
        return None
    if current_user_id():
        ensure_user_files()
        return None
    return redirect(url_for("login"))


# -----------------------------
# AUTH
# -----------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user_id():
        return redirect(url_for("app_home"))

    form_error = ""
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        if not email:
            form_error = "E-posta zorunlu."
        elif len(password) < 6:
            form_error = "Şifre en az 6 karakter olmalı."
        elif password != password2:
            form_error = "Şifreler eşleşmiyor."
        elif get_user_by_email(email):
            form_error = "Bu e-posta ile kayıtlı hesap var."
        else:
            user_id = create_user(email, password)
            user = get_user_by_id(user_id)
            login_user_session(user)
            migrate_legacy_data_if_needed(user_id)
            return redirect(url_for("app_home"))

    return render_template("auth_register.html", form_error=form_error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user_id():
        return redirect(url_for("app_home"))

    form_error = ""
    form_success = (request.args.get("msg") or "").strip()
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = get_user_by_email(email)

        if not user or not check_password_hash(user["password_hash"], password):
            form_error = "E-posta veya şifre hatalı."
        else:
            login_user_session(user)
            migrate_legacy_data_if_needed(int(user["id"]))
            return redirect(url_for("app_home"))

    return render_template("auth_login.html", form_error=form_error, form_success=form_success)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user_id():
        return redirect(url_for("app_home"))

    form_error = ""
    form_success = ""
    debug_reset_link = ""

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        if not email:
            form_error = "E-posta zorunlu."
        else:
            form_success = "Bu e-posta kayıtlıysa şifre sıfırlama bağlantısı gönderildi."
            user = get_user_by_email(email)
            if user:
                raw_token, _ = create_password_reset_token(int(user["id"]))
                reset_link = url_for("reset_password", token=raw_token, _external=True)
                sent, reason = send_password_reset_email(email, reset_link)
                if not sent and is_local_request_host():
                    debug_reset_link = reset_link
                    form_success = "E-posta altyapısı kurulu değil. Lokal test için aşağıdaki sıfırlama bağlantısını kullan."
                elif not sent:
                    form_success = "Bu e-posta kayıtlıysa şifre sıfırlama bağlantısı gönderildi."

    return render_template(
        "auth_forgot_password.html",
        form_error=form_error,
        form_success=form_success,
        debug_reset_link=debug_reset_link,
    )


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    if current_user_id():
        logout_user_session()

    token_row = get_password_reset_token(token)
    token_error = password_reset_token_error(token_row)
    form_error = ""

    if request.method == "POST" and not token_error:
        password = request.form.get("password") or ""
        password2 = request.form.get("password2") or ""

        if len(password) < 6:
            form_error = "Şifre en az 6 karakter olmalı."
        elif password != password2:
            form_error = "Şifreler eşleşmiyor."
        else:
            update_user_password(int(token_row["user_id"]), password)
            invalidate_password_reset_tokens_for_user(int(token_row["user_id"]))
            mark_password_reset_token_used(int(token_row["id"]))
            return redirect(
                url_for(
                    "login",
                    msg="Şifren güncellendi. Yeni şifrenle giriş yapabilirsin.",
                )
            )

    return render_template(
        "auth_reset_password.html",
        token_error=token_error,
        form_error=form_error,
        token=token,
    )


@app.post("/logout")
@login_required
def logout():
    logout_user_session()
    return redirect(url_for("login"))


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    if current_user_id():
        return redirect(url_for("app_home"))
    return render_template("public_home.html")


@app.route("/app")
@app.route("/dashboard")
@login_required
def app_home():
    return render_template("index.html")


@app.route("/pricing")
def pricing():
    return render_template("pricing.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/robots.txt")
def robots_txt():
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: {request.url_root.rstrip('/')}/sitemap.xml",
            "",
        ]
    )
    return app.response_class(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap_xml():
    base = (os.getenv("PUBLIC_BASE_URL") or request.url_root.rstrip("/")).rstrip("/")
    pages = [
        ("", "weekly"),
        ("/pricing", "monthly"),
        ("/privacy", "yearly"),
        ("/terms", "yearly"),
        ("/login", "monthly"),
        ("/register", "monthly"),
        ("/forgot-password", "monthly"),
    ]
    rows = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    stamp = _iso(_now())
    for path, changefreq in pages:
        rows.extend(
            [
                "  <url>",
                f"    <loc>{base}{path}</loc>",
                f"    <lastmod>{stamp}</lastmod>",
                f"    <changefreq>{changefreq}</changefreq>",
                "  </url>",
            ]
        )
    rows.append("</urlset>")
    return app.response_class("\n".join(rows), mimetype="application/xml")


# -----------------------------
# ACCOUNTS
# -----------------------------
@app.route("/accounts", methods=["GET", "POST"])
@login_required
def accounts():
    data = load_accounts()

    if request.method == "POST":
        action = (request.form.get("action") or "upsert").strip().lower()
        platform = (request.form.get("platform") or "").strip().lower()

        if platform not in data:
            return redirect(url_for("accounts"))

        if action == "disconnect":
            data[platform] = default_accounts()[platform]
            save_accounts(data)
            return redirect(url_for("accounts"))

        item = data.get(platform, {})
        account_name = (request.form.get("account_name") or "").strip()
        note = (request.form.get("note") or "").strip()
        access_token = (request.form.get("access_token") or "").strip()
        enabled = (request.form.get("enabled") or "1").strip() == "1"

        item["enabled"] = enabled
        item["note"] = note
        item["updated_at"] = _iso(_now())

        if account_name:
            item["account_name"] = account_name

        if access_token:
            if platform == "facebook":
                item["page_access_token"] = access_token
            else:
                item["access_token"] = access_token
            item["status"] = "connected"
        elif item.get("status") != "connected":
            item["status"] = "not_connected"

        data[platform] = item
        save_accounts(data)
        return redirect(url_for("accounts"))

    parsed_redirect = urllib.parse.urlparse(META_REDIRECT_URI) if META_REDIRECT_URI else None
    meta_app_domain = parsed_redirect.netloc if parsed_redirect else ""
    return render_template(
        "accounts.html",
        accounts=data,
        meta_redirect_uri=META_REDIRECT_URI,
        meta_app_domain=meta_app_domain,
    )


@app.route("/auth/meta/refresh-instagram")
@login_required
def meta_refresh_instagram():
    accounts_data = load_accounts()
    ok, message = refresh_instagram_from_page(accounts_data, current_user_id())
    level = "ok" if ok else "warn"
    return redirect(url_for("accounts", msg=message, level=level))


@app.route("/auth/x/test")
@login_required
def x_test_token_route():
    accounts_data = load_accounts()
    xcfg = accounts_data.get("x", {})
    token = (xcfg.get("access_token") or "").strip()
    if not token:
        return redirect(url_for("accounts", msg="Önce X token girip kaydet.", level="warn"))

    ok, message, meta = test_x_token(token)
    if ok:
        xcfg["enabled"] = True
        xcfg["status"] = "connected"
        xcfg["updated_at"] = _iso(_now())
        if meta.get("username"):
            xcfg["account_name"] = meta.get("username")
        elif meta.get("name"):
            xcfg["account_name"] = meta.get("name")
        xcfg["note"] = f"X user id: {meta.get('id', '-')}"
    else:
        xcfg["status"] = "not_connected"
        xcfg["updated_at"] = _iso(_now())
    accounts_data["x"] = xcfg
    save_accounts(accounts_data)
    return redirect(url_for("accounts", msg=message, level="ok" if ok else "warn"))


# -----------------------------
# META LOGIN
# -----------------------------
@app.route("/auth/meta/start")
@login_required
def meta_start():
    if not META_APP_ID or not META_APP_SECRET or not META_REDIRECT_URI:
        return "Meta ENV eksik: META_APP_ID / META_APP_SECRET / META_REDIRECT_URI gerekli", 500

    state = uuid.uuid4().hex
    pending = load_json(META_PENDING_FILE, {})
    if not isinstance(pending, dict):
        pending = {}
    pending[state] = {"created_at": _iso(_now()), "user_id": current_user_id()}
    save_json(META_PENDING_FILE, pending)

    params = {
        "client_id": META_APP_ID,
        "redirect_uri": META_REDIRECT_URI,
        "scope": META_LOGIN_SCOPE,
        "auth_type": "rerequest",
        "response_type": "code",
        "state": state,
    }
    url = "https://www.facebook.com/" + META_GRAPH_VERSION + "/dialog/oauth?" + urllib.parse.urlencode(params)
    return redirect(url)


@app.route("/auth/meta/callback")
def meta_callback():
    if request.args.get("error"):
        err = request.args.get("error_message") or request.args.get("error_description") or request.args.get("error")
        return f"Meta login hatasi: {err}", 400

    code = request.args.get("code")
    if not code:
        return "Meta'dan code gelmedi", 400

    state = (request.args.get("state") or "").strip()
    pending = load_json(META_PENDING_FILE, {})
    if not isinstance(pending, dict):
        pending = {}

    if state and state not in pending:
        return "Meta state hatasi. /auth/meta/start ile akışı tekrar başlat.", 400

    pending_state = pending.get(state) or {}
    target_user_id = int(pending_state.get("user_id") or current_user_id() or 0)
    if target_user_id < 1:
        return redirect(url_for("login"))

    token_url = "https://graph.facebook.com/" + META_GRAPH_VERSION + "/oauth/access_token"
    params = {
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "redirect_uri": META_REDIRECT_URI,
        "code": code,
    }

    try:
        token_res = requests.get(token_url, params=params, timeout=25)
        token_res.raise_for_status()
        token_payload = token_res.json()
    except Exception as exc:
        return _meta_error_message(exc, "Meta token alma hatasi"), 400

    user_access_token = (token_payload.get("access_token") or "").strip()
    if not user_access_token:
        return redirect(
            url_for(
                "accounts",
                msg="Meta erişim anahtarı alınamadı. Lütfen yeniden bağlanmayı dene.",
                level="warn",
            )
        )

    long_lived_user_token, exchange_err = exchange_for_long_lived_meta_token(user_access_token)
    active_user_token = long_lived_user_token or user_access_token

    try:
        pages_res = requests.get(
            _meta_graph_url("/me/accounts"),
            params={
                "access_token": active_user_token,
                "fields": "id,name,access_token,instagram_business_account{id,username}",
            },
            timeout=25,
        )
        pages_res.raise_for_status()
        pages_payload = pages_res.json()
    except Exception as exc:
        return _meta_error_message(exc, "Page listesi alinmadi"), 400

    pages = pages_payload.get("data") or []
    if not pages:
        pages = discover_pages_from_debug_targets(active_user_token)
    if not pages:
        return redirect(
            url_for(
                "accounts",
                msg="Yönetici olduğun Facebook Sayfası bulunamadı. Facebook penceresinde 'Ayarları düzenle' deyip Sayfalar erişimini aç.",
                level="warn",
            )
        )

    if len(pages) == 1:
        selection = save_meta_page_selection(pages[0], active_user_token, target_user_id)
        if state:
            pending.pop(state, None)
            save_json(META_PENDING_FILE, pending)
        msg = "Meta bağlantısı yenilendi."
        if selection.get("reactivated_jobs"):
            msg += f" {selection.get('reactivated_jobs')} zamanlanmış iş tekrar aktif edildi."
        level = "ok"
        if exchange_err:
            msg += f" Long-lived token exchange uyarısı: {exchange_err}"
            level = "warn"
        return redirect(url_for("accounts", msg=msg, level=level))

    if not state:
        state = uuid.uuid4().hex

    pending[state] = {
        "created_at": _iso(_now()),
        "user_id": target_user_id,
        "user_access_token": active_user_token,
        "pages": pages,
    }
    save_json(META_PENDING_FILE, pending)

    return render_template("meta_pages.html", pages=pages, state=state)


@app.post("/auth/meta/select_page")
def meta_select_page():
    state = (request.form.get("state") or "").strip()
    page_id = (request.form.get("page_id") or "").strip()

    if not state or not page_id:
        return "Eksik seçim verisi", 400

    pending = load_json(META_PENDING_FILE, {})
    if not isinstance(pending, dict) or state not in pending:
        return "Seçim süresi doldu. /auth/meta/start ile tekrar başlat.", 400

    payload = pending.get(state) or {}
    pages = payload.get("pages") or []
    selected = next((p for p in pages if str(p.get("id", "")) == page_id), None)
    if not selected:
        return "Seçilen Page bulunamadı.", 400

    target_user_id = int(payload.get("user_id") or current_user_id() or 0)
    if target_user_id < 1:
        return redirect(url_for("login"))

    selection = save_meta_page_selection(selected, payload.get("user_access_token", ""), target_user_id)
    pending.pop(state, None)
    save_json(META_PENDING_FILE, pending)
    msg = "Meta sayfası bağlandı."
    if selection.get("reactivated_jobs"):
        msg += f" {selection.get('reactivated_jobs')} zamanlanmış iş tekrar aktif edildi."
    return redirect(url_for("accounts", msg=msg, level="ok"))


# -----------------------------
# CREATE / PREPARE
# -----------------------------
@app.route("/prepare", methods=["GET", "POST"])
@app.route("/create", methods=["GET", "POST"])
@login_required
def prepare():
    form_data = request.form if request.method == "POST" else {}
    if request.method == "POST":
        action = (request.form.get("action") or "submit").strip().lower()
        schedule_mode = (request.form.get("schedule_mode") or "now").strip().lower()

        text = (request.form.get("post_text") or "").strip()
        hashtags = (request.form.get("hashtags") or "").strip()
        platforms = request.form.getlist("platforms")
        fmt = (request.form.get("format") or "normal").strip()
        media_mode = (request.form.get("media_mode") or "mixed").strip()
        targets_raw = (request.form.get("targets") or "").strip()

        if schedule_mode not in LAUNCH_ENABLED_SCHEDULE_MODES:
            return render_template(
                "prepare.html",
                form_error="Geçersiz gönderim modu seçildi.",
                form_data=form_data,
            ), 400

        media_files = request.files.getlist("media")
        media = filter_media_by_mode(save_uploads(media_files, current_user_id()), media_mode)

        base = {
            "id": uuid.uuid4().hex,
            "created_at": _iso(_now()),
            "text": text,
            "hashtags": hashtags,
            "platforms": platforms,
            "format": fmt,
            "media_mode": media_mode,
            "media": media,
            "targets": parse_targets(targets_raw, platforms),
            "targets_raw": targets_raw,
            "archive_after_send": True,
        }

        errors = validate_post_payload(text, hashtags, platforms, fmt, media)
        if errors:
            return render_template(
                "prepare.html",
                form_error=" ".join(errors),
                form_data=form_data,
            ), 400

        if action == "draft":
            drafts = load_json(user_file("drafts"), [])
            drafts.append({**base, "status": "draft", "schedule_mode": schedule_mode})
            save_json(user_file("drafts"), drafts)
            return redirect(url_for("drafts"))

        if schedule_mode == "now":
            queue = load_json(user_file("queue"), [])
            queue_item = {
                **base,
                "status": "queued",
                "scheduled_at": _iso(_now()),
                "logs": [],
                "attempts": 0,
                "retry_after": "",
                "delivered_platforms": [],
            }
            queue.append(queue_item)
            save_json(user_file("queue"), queue)
            return redirect(url_for("tasks"))

        if schedule_mode == "interval":
            try:
                interval_min = int((request.form.get("interval_min") or "60").strip())
            except Exception:
                interval_min = 60
            if interval_min < 1:
                interval_min = 1

            start_at = _parse_dt_local(request.form.get("interval_start_at", "")) or _now()

            obj = {
                **base,
                "type": "interval",
                "status": "active",
                "interval_min": interval_min,
                "start_at": _iso(start_at),
                "next_run_at": _iso(start_at),
            }
            scheduled = load_json(user_file("scheduled"), [])
            scheduled.append(obj)
            save_json(user_file("scheduled"), scheduled)
            return redirect(url_for("tasks"))

        if schedule_mode == "campaign":
            start_at = _parse_dt_local(request.form.get("campaign_start_at", "")) or _now()
            end_date = _parse_date_local(request.form.get("campaign_end_date", ""))
            if end_date:
                end_at = dt.datetime.combine(end_date, dt.time(23, 59, 59))
            else:
                end_at = start_at + dt.timedelta(days=60)
            if end_at <= start_at:
                end_at = start_at + dt.timedelta(days=1)

            try:
                per_day_count = int((request.form.get("campaign_per_day") or "1").strip())
            except Exception:
                per_day_count = 1
            per_day_count = max(1, min(96, per_day_count))
            interval_min = max(1, int(round(1440 / per_day_count)))

            obj = {
                **base,
                "type": "interval_range",
                "status": "active",
                "start_at": _iso(start_at),
                "end_at": _iso(end_at),
                "next_run_at": _iso(start_at),
                "per_day_count": per_day_count,
                "interval_min": interval_min,
            }
            scheduled = load_json(user_file("scheduled"), [])
            scheduled.append(obj)
            save_json(user_file("scheduled"), scheduled)
            return redirect(url_for("tasks"))

        # default: one_shot
        schedule_at = _parse_dt_local(request.form.get("schedule_at", "")) or _now()
        obj = {
            **base,
            "type": "one_shot",
            "schedule_at": _iso(schedule_at),
            "status": "scheduled",
        }
        scheduled = load_json(user_file("scheduled"), [])
        scheduled.append(obj)
        save_json(user_file("scheduled"), scheduled)
        return redirect(url_for("tasks"))

    return render_template("prepare.html", form_data=form_data)


# -----------------------------
# LIST PAGES
# -----------------------------
@app.route("/tasks")
@login_required
def tasks():
    posts = load_json(user_file("scheduled"), [])
    queue = load_json(user_file("queue"), [])
    archive = load_json(user_file("archive"), [])
    posts.sort(
        key=lambda post: (
            post.get("schedule_at")
            or post.get("next_run_at")
            or post.get("start_at")
            or post.get("created_at")
            or ""
        )
    )
    return render_template(
        "tasks.html",
        posts=posts,
        queue_count=len(queue),
        archive_count=len(archive),
    )


@app.route("/drafts")
@login_required
def drafts():
    posts = load_json(user_file("drafts"), [])
    return render_template("drafts.html", posts=posts)


@app.route("/queue")
@login_required
def queue_view():
    items = load_queue_items()
    failed_count = sum(1 for item in items if (item.get("status") or "").strip().lower() in {"needs_auth", "error"})
    return render_template("queue.html", items=items, failed_count=failed_count)


@app.post("/queue/clear-failed")
@login_required
def queue_clear_failed():
    items = load_queue_items()
    kept = [item for item in items if (item.get("status") or "").strip().lower() not in {"needs_auth", "error"}]
    removed = len(items) - len(kept)
    if removed:
        save_json(user_file("queue"), kept)
        return redirect(url_for("queue_view", msg=f"{removed} hatalı kart temizlendi.", level="ok"))
    return redirect(url_for("queue_view", msg="Temizlenecek needs_auth/error kartı yok.", level="warn"))


@app.post("/queue/<item_id>/delete")
@login_required
def queue_delete(item_id: str):
    items = load_queue_items()
    kept = [item for item in items if (item.get("id") or "").strip() != item_id]
    removed = len(items) - len(kept)
    if removed:
        save_json(user_file("queue"), kept)
        return redirect(url_for("queue_view", msg="Kart kuyruktan silindi.", level="ok"))
    return redirect(url_for("queue_view", msg="Silinecek kart bulunamadı.", level="warn"))


@app.route("/archive")
@login_required
def archive_view():
    items = list(reversed(load_json(user_file("archive"), [])))
    return render_template("archive.html", items=items)


@app.route("/worker-logs")
@login_required
def worker_logs_view():
    rows = []
    worker_log_file = user_file("worker_log")
    if worker_log_file.exists():
        lines = worker_log_file.read_text(encoding="utf-8").splitlines()[-300:]
        for line in reversed(lines):
            line = (line or "").strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                rows.append({"at": "", "level": "raw", "message": line})
    return render_template("worker_logs.html", rows=rows)


# -----------------------------
# UPLOADS
# -----------------------------
@app.route("/uploads/<path:filename>")
def uploaded_file(filename: str):
    return send_from_directory(ROOT_UPLOADS_DIR, filename)


# -----------------------------
# DEBUG
# -----------------------------
@app.get("/api/debug/queue")
@login_required
def debug_queue():
    return jsonify(load_json(user_file("queue"), []))


@app.get("/api/debug/archive")
@login_required
def debug_archive():
    return jsonify(load_json(user_file("archive"), []))


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int((os.getenv("PORT") or "5050").strip())
    app.run(host="0.0.0.0", port=port, debug=False)
