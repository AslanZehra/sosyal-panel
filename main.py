from __future__ import annotations

from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
from pathlib import Path
import json
import os
import uuid
import datetime as dt
import urllib.parse

import requests
from dotenv import load_dotenv

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
META_LOGIN_SCOPE = (
    os.getenv(
        "META_LOGIN_SCOPE",
        "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish",
    ).strip()
    or "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish"
)

# -----------------------------
# Paths & storage
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
APP_STORAGE_DIR = (os.getenv("APP_STORAGE_DIR", "") or "").strip()
if APP_STORAGE_DIR:
    STORAGE_DIR = Path(APP_STORAGE_DIR).expanduser().resolve()
else:
    STORAGE_DIR = BASE_DIR

DATA_DIR = STORAGE_DIR / "data"
UPLOADS_DIR = STORAGE_DIR / "uploads"
DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

SCHEDULED_FILE = DATA_DIR / "scheduled_posts.json"
DRAFTS_FILE = DATA_DIR / "draft_posts.json"
QUEUE_FILE = DATA_DIR / "queue.json"
ARCHIVE_FILE = DATA_DIR / "archive.json"
ACCOUNTS_FILE = DATA_DIR / "accounts.json"
META_PENDING_FILE = DATA_DIR / "meta_pending.json"
WORKER_LOG_FILE = DATA_DIR / "worker.log"

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


def load_accounts() -> dict:
    raw = load_json(ACCOUNTS_FILE, {})
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


def save_accounts(data: dict) -> None:
    defaults = default_accounts()
    out = {}
    for platform, cfg in defaults.items():
        existing = data.get(platform, {})
        if not isinstance(existing, dict):
            existing = {}
        out[platform] = {**cfg, **existing}
    save_json(ACCOUNTS_FILE, out)


def ensure_files():
    if not SCHEDULED_FILE.exists():
        save_json(SCHEDULED_FILE, [])
    if not DRAFTS_FILE.exists():
        save_json(DRAFTS_FILE, [])
    if not QUEUE_FILE.exists():
        save_json(QUEUE_FILE, [])
    if not ARCHIVE_FILE.exists():
        save_json(ARCHIVE_FILE, [])
    if not ACCOUNTS_FILE.exists():
        save_json(ACCOUNTS_FILE, default_accounts())
    if not META_PENDING_FILE.exists():
        save_json(META_PENDING_FILE, {})


def infer_media_kind(filename: str) -> str:
    fn = (filename or "").lower()
    if fn.endswith((".mp4", ".mov", ".mkv", ".webm", ".avi")):
        return "video"
    if fn.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic")):
        return "image"
    return "file"


def save_uploads(files) -> list[dict]:
    out = []
    for f in files:
        if not f or not getattr(f, "filename", ""):
            continue
        original = Path(f.filename).name
        ext = Path(original).suffix.lower()
        safe_name = f"{uuid.uuid4().hex}{ext}"
        abs_path = UPLOADS_DIR / safe_name
        f.save(abs_path)
        out.append({
            "kind": infer_media_kind(original),
            "path": f"uploads/{safe_name}",
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

    not_ready = [p for p in selected if p in ("youtube", "tiktok")]
    if not_ready:
        errors.append("Bu platformlar için gerçek yayın henüz aktif değil: " + ", ".join(sorted(set(not_ready))))

    if "instagram" in selected_set and not media:
        errors.append("Instagram için en az 1 foto/video seçmelisin.")

    if "x" in selected_set and media:
        errors.append("X için şu an sadece metin gönderimi destekleniyor. Medya kaldır.")

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


def save_meta_page_selection(page: dict, user_access_token: str) -> dict:
    accounts = load_accounts()
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

    save_accounts(accounts)
    return {
        "page_id": fb.get("page_id"),
        "account_name": fb.get("account_name"),
        "connected_at": fb.get("updated_at"),
    }


def refresh_instagram_from_page(accounts: dict) -> tuple[bool, str]:
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
        save_accounts(accounts)
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
    save_accounts(accounts)
    return True, f"Instagram bağlandı: {insta.get('account_name') or insta.get('ig_business_id')}"


# -----------------------------
# App init
# -----------------------------
ensure_files()
app = Flask(__name__)
app.register_blueprint(ai_bp)


# -----------------------------
# HOME
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")


# -----------------------------
# ACCOUNTS
# -----------------------------
@app.route("/accounts", methods=["GET", "POST"])
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

    return render_template("accounts.html", accounts=data)


@app.route("/auth/meta/refresh-instagram")
def meta_refresh_instagram():
    accounts_data = load_accounts()
    ok, message = refresh_instagram_from_page(accounts_data)
    level = "ok" if ok else "warn"
    return redirect(url_for("accounts", msg=message, level=level))


@app.route("/auth/x/test")
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
def meta_start():
    if not META_APP_ID or not META_APP_SECRET or not META_REDIRECT_URI:
        return "Meta ENV eksik: META_APP_ID / META_APP_SECRET / META_REDIRECT_URI gerekli", 500

    state = uuid.uuid4().hex
    pending = load_json(META_PENDING_FILE, {})
    if not isinstance(pending, dict):
        pending = {}
    pending[state] = {"created_at": _iso(_now())}
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
        return f"Meta token alma hatasi: {exc}", 400

    user_access_token = token_payload.get("access_token")
    if not user_access_token:
        return redirect(
            url_for(
                "accounts",
                msg="Meta erişim anahtarı alınamadı. Lütfen yeniden bağlanmayı dene.",
                level="warn",
            )
        )

    try:
        pages_res = requests.get(
            _meta_graph_url("/me/accounts"),
            params={
                "access_token": user_access_token,
                "fields": "id,name,access_token,instagram_business_account{id,username}",
            },
            timeout=25,
        )
        pages_res.raise_for_status()
        pages_payload = pages_res.json()
    except Exception as exc:
        return f"Page listesi alinmadi: {exc}", 400

    pages = pages_payload.get("data") or []
    if not pages:
        return redirect(
            url_for(
                "accounts",
                msg="Yönetici olduğun Facebook Sayfası bulunamadı. Facebook penceresinde 'Ayarları düzenle' deyip Sayfalar erişimini aç.",
                level="warn",
            )
        )

    if len(pages) == 1:
        save_meta_page_selection(pages[0], user_access_token)
        if state:
            pending.pop(state, None)
            save_json(META_PENDING_FILE, pending)
        return redirect(url_for("accounts"))

    if not state:
        state = uuid.uuid4().hex

    pending[state] = {
        "created_at": _iso(_now()),
        "user_access_token": user_access_token,
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

    save_meta_page_selection(selected, payload.get("user_access_token", ""))
    pending.pop(state, None)
    save_json(META_PENDING_FILE, pending)
    return redirect(url_for("accounts"))


# -----------------------------
# CREATE / PREPARE
# -----------------------------
@app.route("/prepare", methods=["GET", "POST"])
@app.route("/create", methods=["GET", "POST"])
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

        media_files = request.files.getlist("media")
        media = filter_media_by_mode(save_uploads(media_files), media_mode)

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
            drafts = load_json(DRAFTS_FILE, [])
            drafts.append({**base, "status": "draft", "schedule_mode": schedule_mode})
            save_json(DRAFTS_FILE, drafts)
            return redirect(url_for("drafts"))

        if schedule_mode == "now":
            queue = load_json(QUEUE_FILE, [])
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
            save_json(QUEUE_FILE, queue)
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
            scheduled = load_json(SCHEDULED_FILE, [])
            scheduled.append(obj)
            save_json(SCHEDULED_FILE, scheduled)
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
            scheduled = load_json(SCHEDULED_FILE, [])
            scheduled.append(obj)
            save_json(SCHEDULED_FILE, scheduled)
            return redirect(url_for("tasks"))

        # default: one_shot
        schedule_at = _parse_dt_local(request.form.get("schedule_at", "")) or _now()
        obj = {
            **base,
            "type": "one_shot",
            "schedule_at": _iso(schedule_at),
            "status": "scheduled",
        }
        scheduled = load_json(SCHEDULED_FILE, [])
        scheduled.append(obj)
        save_json(SCHEDULED_FILE, scheduled)
        return redirect(url_for("tasks"))

    return render_template("prepare.html", form_data=form_data)


# -----------------------------
# LIST PAGES
# -----------------------------
@app.route("/tasks")
def tasks():
    posts = load_json(SCHEDULED_FILE, [])
    queue = load_json(QUEUE_FILE, [])
    archive = load_json(ARCHIVE_FILE, [])
    return render_template(
        "tasks.html",
        posts=posts,
        queue_count=len(queue),
        archive_count=len(archive),
    )


@app.route("/drafts")
def drafts():
    posts = load_json(DRAFTS_FILE, [])
    return render_template("drafts.html", posts=posts)


@app.route("/queue")
def queue_view():
    items = load_json(QUEUE_FILE, [])
    return render_template("queue.html", items=items)


@app.route("/archive")
def archive_view():
    items = list(reversed(load_json(ARCHIVE_FILE, [])))
    return render_template("archive.html", items=items)


@app.route("/worker-logs")
def worker_logs_view():
    rows = []
    if WORKER_LOG_FILE.exists():
        lines = WORKER_LOG_FILE.read_text(encoding="utf-8").splitlines()[-300:]
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
    return send_from_directory(UPLOADS_DIR, filename)


# -----------------------------
# DEBUG
# -----------------------------
@app.get("/api/debug/queue")
def debug_queue():
    return jsonify(load_json(QUEUE_FILE, []))


@app.get("/api/debug/archive")
def debug_archive():
    return jsonify(load_json(ARCHIVE_FILE, []))


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int((os.getenv("PORT") or "5050").strip())
    app.run(host="0.0.0.0", port=port, debug=False)
