from __future__ import annotations

from pathlib import Path
import json
import time
import datetime as dt
import os
import urllib.parse
import requests
from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent
APP_STORAGE_DIR = (os.getenv("APP_STORAGE_DIR", "") or "").strip()
if APP_STORAGE_DIR:
    STORAGE_DIR = Path(APP_STORAGE_DIR).expanduser().resolve()
else:
    STORAGE_DIR = PROJECT_DIR

DATA_DIR = STORAGE_DIR / "data"
USERS_DATA_DIR = DATA_DIR / "users"
load_dotenv(PROJECT_DIR / ".env")

USER_FILE_NAMES = {
    "scheduled": "scheduled_posts.json",
    "queue": "queue.json",
    "archive": "archive.json",
    "accounts": "accounts.json",
    "worker_log": "worker.log",
}

SCHEDULED_FILE = DATA_DIR / USER_FILE_NAMES["scheduled"]
QUEUE_FILE = DATA_DIR / USER_FILE_NAMES["queue"]
ARCHIVE_FILE = DATA_DIR / USER_FILE_NAMES["archive"]
ACCOUNTS_FILE = DATA_DIR / USER_FILE_NAMES["accounts"]
WORKER_LOG_FILE = DATA_DIR / USER_FILE_NAMES["worker_log"]
ACTIVE_USER_ID = ""

META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v19.0").strip() or "v19.0"
X_POST_URL = (os.getenv("X_POST_URL") or "https://api.x.com/2/tweets").strip()
MAX_ATTEMPTS = 5
NEEDS_AUTH_RETRY_MINUTES = 15
ERROR_RETRY_STEPS_MINUTES = [1, 2, 4, 8, 15]
INSTAGRAM_PUBLISH_WAIT_SECONDS = [2, 3, 5]
WORKER_POLL_SECONDS = max(1.0, float((os.getenv("WORKER_POLL_SECONDS") or "3").strip()))
MAX_ITEM_LOGS = 40
MAX_WORKER_LOG_LINES = 1500

DATA_DIR.mkdir(exist_ok=True)
USERS_DATA_DIR.mkdir(exist_ok=True)


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def now() -> dt.datetime:
    return dt.datetime.now()


def parse_iso(s: str) -> dt.datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None


def iso(d: dt.datetime | None) -> str:
    if not d:
        return ""
    return d.replace(microsecond=0).isoformat()


def trim_log_file(path: Path, max_lines: int):
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) <= max_lines:
            return
        path.write_text("\n".join(lines[-max_lines:]) + "\n", encoding="utf-8")
    except Exception:
        return


def append_worker_log(level: str, message: str, item_id: str = "", status: str = "", platforms: list | None = None):
    stamp = iso(now())
    rec = {
        "at": stamp,
        "level": level,
        "message": message,
    }
    if ACTIVE_USER_ID:
        rec["user_id"] = ACTIVE_USER_ID
    if item_id:
        rec["item_id"] = item_id
    if status:
        rec["status"] = status
    if platforms:
        rec["platforms"] = platforms

    # Keep stdout trace for terminal observers and persist to file for UI/debugging.
    prefix = f"[user:{ACTIVE_USER_ID}] " if ACTIVE_USER_ID else ""
    print(f"{prefix}[{level}] {message}")
    try:
        with WORKER_LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        return


def add_item_log(item: dict, platform: str, ok: bool, message: str, t: dt.datetime):
    logs = item.setdefault("logs", [])
    entry = {
        "platform": platform or "-",
        "ok": bool(ok),
        "message": message,
        "at": iso(t),
    }

    if logs:
        last = logs[-1]
        same = (
            last.get("platform") == entry["platform"]
            and bool(last.get("ok")) == entry["ok"]
            and last.get("message") == entry["message"]
        )
        if same:
            last["at"] = entry["at"]
            last["repeat"] = int(last.get("repeat", 1) or 1) + 1
            item["logs"] = logs[-MAX_ITEM_LOGS:]
            return

    logs.append(entry)
    item["logs"] = logs[-MAX_ITEM_LOGS:]


def post_with_retry(
    url: str,
    data: dict,
    timeout: int = 40,
    attempts: int = 3,
    *,
    json_body: bool = False,
    headers: dict | None = None,
) -> tuple[requests.Response | None, str]:
    last_err = ""
    for i in range(max(1, attempts)):
        try:
            if json_body:
                return requests.post(url, json=data, headers=headers or {}, timeout=timeout), ""
            return requests.post(url, data=data, headers=headers or {}, timeout=timeout), ""
        except requests.exceptions.RequestException as exc:
            raw = (str(exc) or "").strip()
            if not raw:
                raw = repr(exc)
            last_err = f"{exc.__class__.__name__}: {raw}"
            if i < attempts - 1:
                time.sleep(1 + (i * 2))
    return None, last_err or "network_error"


def is_permanent_publish_error(message: str) -> bool:
    msg = (message or "").strip().lower()
    if msg.startswith("needs_media") or msg.startswith("needs_config"):
        return True
    permanent_signatures = [
        "publish_error: boş içerik",
        "only photo or video can be accepted as media type",
        "medya url html dönüyor",
        "medya image değil",
        "medya video değil",
        "x medya yükleme entegrasyonu henüz tamamlanmadı",
    ]
    return any(sig in msg for sig in permanent_signatures)


def is_auth_publish_error(message: str) -> bool:
    msg = (message or "").strip().lower()
    if not msg:
        return False
    auth_signatures = [
        "error validating access token",
        "invalid oauth access token",
        "access token has expired",
        "session has been invalidated",
        "invalid access token",
        "requires valid app id",
        "the user changed their password",
    ]
    return any(sig in msg for sig in auth_signatures)


def next_error_retry_minutes(attempts: int) -> int:
    idx = max(0, min(attempts - 1, len(ERROR_RETRY_STEPS_MINUTES) - 1))
    return int(ERROR_RETRY_STEPS_MINUTES[idx])


def get_public_base_url() -> str:
    for key in ("PUBLIC_BASE_URL", "APP_PUBLIC_URL", "NGROK_PUBLIC_URL"):
        value = (os.getenv(key) or "").strip().rstrip("/")
        if value:
            return value

    redirect_uri = (os.getenv("META_REDIRECT_URI") or "").strip()
    if redirect_uri:
        parsed = urllib.parse.urlparse(redirect_uri)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}"

    return ""


def build_public_media_url(path_or_url: str) -> tuple[str, str]:
    value = (path_or_url or "").strip()
    if not value:
        return "", "needs_media: instagram için görsel gerekli."

    if value.startswith(("http://", "https://")):
        return value, ""

    base = get_public_base_url()
    if not base:
        return "", "needs_config: PUBLIC_BASE_URL veya META_REDIRECT_URI ayarlanmalı."

    return f"{base}/{value.lstrip('/')}", ""


def infer_media_kind(value: str) -> str:
    v = (value or "").strip().lower()
    if any(v.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic")):
        return "image"
    if any(v.endswith(ext) for ext in (".mp4", ".mov", ".mkv", ".webm", ".avi")):
        return "video"
    return ""


def extract_media_candidates(item: dict) -> list[dict]:
    media = item.get("media") or []
    if not isinstance(media, list):
        return []

    out = []
    for m in media:
        if not isinstance(m, dict):
            continue
        kind = (m.get("kind") or "").strip().lower()
        path = (m.get("path") or "").strip()
        if not path:
            continue
        if kind not in ("image", "video"):
            kind = infer_media_kind(path)
        if kind not in ("image", "video"):
            continue
        out.append({"kind": kind, "path": path})
    return out


def validate_public_media_url(media_url: str, expected_kind: str) -> tuple[bool, str]:
    try:
        res = requests.get(media_url, timeout=20, allow_redirects=True, stream=True)
        status = int(res.status_code or 0)
        ctype = (res.headers.get("content-type") or "").strip().lower()
        res.close()
    except Exception as exc:
        return False, f"publish_error: medya URL erişim hatası: {exc}"

    if status >= 400:
        return False, f"publish_error: medya URL erişilemiyor (HTTP {status})"
    if "text/html" in ctype:
        return (
            False,
            "publish_error: medya URL HTML dönüyor. Ngrok uyarı sayfası veya yanlış PUBLIC_BASE_URL olabilir.",
        )
    if expected_kind == "image" and not ctype.startswith("image/"):
        return False, f"publish_error: medya image değil (content-type: {ctype or '-'})"
    if expected_kind == "video" and not ctype.startswith("video/"):
        return False, f"publish_error: medya video değil (content-type: {ctype or '-'})"
    return True, ""


def get_targets_for_platform(item: dict, platform: str) -> list[dict]:
    targets_map = item.get("targets") or {}
    if not isinstance(targets_map, dict):
        return []
    targets = targets_map.get(platform) or []
    if not isinstance(targets, list):
        return []
    out = []
    for t in targets:
        if not isinstance(t, dict):
            continue
        kind = (t.get("kind") or "").strip().lower()
        target_id = (t.get("id") or "").strip()
        if kind not in ("page", "group", "self"):
            continue
        out.append({"kind": kind, "id": target_id})
    return out


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


def activate_user_storage(user_dir: Path) -> None:
    global SCHEDULED_FILE, QUEUE_FILE, ARCHIVE_FILE, ACCOUNTS_FILE, WORKER_LOG_FILE, ACTIVE_USER_ID
    ACTIVE_USER_ID = user_dir.name
    SCHEDULED_FILE = user_dir / USER_FILE_NAMES["scheduled"]
    QUEUE_FILE = user_dir / USER_FILE_NAMES["queue"]
    ARCHIVE_FILE = user_dir / USER_FILE_NAMES["archive"]
    ACCOUNTS_FILE = user_dir / USER_FILE_NAMES["accounts"]
    WORKER_LOG_FILE = user_dir / USER_FILE_NAMES["worker_log"]


def iter_user_dirs() -> list[Path]:
    if not USERS_DATA_DIR.exists():
        return []
    return sorted([path for path in USERS_DATA_DIR.iterdir() if path.is_dir()], key=lambda path: path.name)


def ensure_files():
    if not SCHEDULED_FILE.exists():
        save_json(SCHEDULED_FILE, [])
    if not QUEUE_FILE.exists():
        save_json(QUEUE_FILE, [])
    if not ARCHIVE_FILE.exists():
        save_json(ARCHIVE_FILE, [])
    if not ACCOUNTS_FILE.exists():
        save_json(ACCOUNTS_FILE, default_accounts())
    if not WORKER_LOG_FILE.exists():
        WORKER_LOG_FILE.write_text("", encoding="utf-8")
    trim_log_file(WORKER_LOG_FILE, MAX_WORKER_LOG_LINES)


def normalize_accounts(raw: dict) -> dict:
    defaults = default_accounts()
    if not isinstance(raw, dict):
        return defaults

    out = {}
    for platform, cfg in defaults.items():
        existing = raw.get(platform, {})
        if not isinstance(existing, dict):
            existing = {}
        out[platform] = {**cfg, **existing}
    return out


def has_platform_auth(accounts: dict, platform: str) -> bool:
    platform = (platform or "").strip().lower()
    cfg = accounts.get(platform) or {}
    if not cfg.get("enabled"):
        return False
    if cfg.get("status") != "connected":
        return False

    if platform == "facebook":
        return bool(cfg.get("page_id") and cfg.get("page_access_token"))

    if platform == "instagram":
        token = cfg.get("access_token") or (accounts.get("facebook", {}).get("page_access_token"))
        return bool(cfg.get("ig_business_id") and token)

    return bool(cfg.get("access_token"))


def build_message(item: dict) -> str:
    text = (item.get("text") or "").strip()
    hashtags = (item.get("hashtags") or "").strip()
    if text and hashtags:
        return f"{text}\n\n{hashtags}"
    return text or hashtags


def publish_facebook(item: dict, accounts: dict) -> tuple[bool, str]:
    fb = accounts.get("facebook") or {}
    page_id = (fb.get("page_id") or "").strip()
    page_token = (fb.get("page_access_token") or "").strip()

    if not page_id or not page_token:
        return False, "needs_auth: facebook page_id/page_access_token eksik"

    message = build_message(item)
    media_candidates = extract_media_candidates(item)
    image_candidates = [m for m in media_candidates if m.get("kind") == "image"]
    video_candidates = [m for m in media_candidates if m.get("kind") == "video"]

    if not message and not media_candidates:
        return False, "publish_error: boş içerik"

    configured = get_targets_for_platform(item, "facebook")
    if not configured:
        configured = [{"kind": "page", "id": page_id}]

    def call_facebook(url: str, payload: dict, timeout: int = 30, attempts: int = 3) -> tuple[bool, str, dict]:
        try:
            res, post_err = post_with_retry(url, payload, timeout=timeout, attempts=attempts)
            if res is None:
                return False, f"network:{post_err}", {}
            pl = res.json() if res.text else {}
            if res.status_code >= 400:
                err = pl.get("error", {}).get("message") or res.text or "facebook_error"
                return False, err, pl
            return True, "", pl
        except Exception as exc:
            return False, str(exc), {}

    results = []
    ok_count = 0
    for target in configured:
        kind = target.get("kind") or "page"
        raw_id = (target.get("id") or "").strip()
        target_id = page_id if kind == "self" else (raw_id or page_id)
        if not target_id:
            results.append(f"{kind}:missing_id")
            continue

        # Mixed media and multi-video are not supported as a single Facebook post in this worker yet.
        if video_candidates and len(media_candidates) > 1:
            results.append(f"{kind}:{target_id}:fail:publish_error: facebook çoklu karışık/video medya henüz desteklenmiyor")
            continue

        # 1) Single video => /videos
        if video_candidates and len(media_candidates) == 1:
            video = video_candidates[0]
            media_url, url_err = build_public_media_url(video.get("path") or "")
            if url_err:
                results.append(f"{kind}:{target_id}:fail:{url_err}")
                continue
            valid, media_err = validate_public_media_url(media_url, "video")
            if not valid:
                results.append(f"{kind}:{target_id}:fail:{media_err}")
                continue

            v_url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{target_id}/videos"
            v_payload = {
                "file_url": media_url,
                "published": "true",
                "access_token": page_token,
            }
            if message:
                v_payload["description"] = message

            ok, err, pl = call_facebook(v_url, v_payload, timeout=90, attempts=3)
            if not ok:
                results.append(f"{kind}:{target_id}:fail:{err}")
                continue
            post_id = str(pl.get("id") or pl.get("post_id") or "unknown").strip() or "unknown"
            ok_count += 1
            results.append(f"{kind}:{target_id}:ok:video:{post_id}")
            continue

        # 2) Image-only single/multi
        if image_candidates:
            prepared_urls = []
            image_err = ""
            for media in image_candidates[:10]:
                media_url, url_err = build_public_media_url(media.get("path") or "")
                if url_err:
                    image_err = url_err
                    break
                valid, media_err = validate_public_media_url(media_url, "image")
                if not valid:
                    image_err = media_err
                    break
                prepared_urls.append(media_url)

            if image_err:
                results.append(f"{kind}:{target_id}:fail:{image_err}")
                continue
            if not prepared_urls:
                results.append(f"{kind}:{target_id}:fail:publish_error: geçerli foto bulunamadı")
                continue

            # 2.a) Single image => /photos
            if len(prepared_urls) == 1:
                p_url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{target_id}/photos"
                p_payload = {
                    "url": prepared_urls[0],
                    "published": "true",
                    "access_token": page_token,
                }
                if message:
                    p_payload["caption"] = message
                ok, err, pl = call_facebook(p_url, p_payload)
                if not ok:
                    results.append(f"{kind}:{target_id}:fail:{err}")
                    continue
                post_id = str(pl.get("id") or "unknown").strip() or "unknown"
                ok_count += 1
                results.append(f"{kind}:{target_id}:ok:photo:{post_id}")
                continue

            # 2.b) Multiple images => create unpublished photos then /feed with attached_media
            media_refs = []
            album_failed = ""
            for media_url in prepared_urls:
                create_url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{target_id}/photos"
                create_payload = {
                    "url": media_url,
                    "published": "false",
                    "access_token": page_token,
                }
                ok, err, pl = call_facebook(create_url, create_payload)
                media_id = str(pl.get("id") or "").strip()
                if not ok or not media_id:
                    album_failed = err or "facebook album media id dönmedi"
                    break
                media_refs.append(media_id)

            if album_failed:
                results.append(f"{kind}:{target_id}:fail:{album_failed}")
                continue

            feed_url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{target_id}/feed"
            feed_payload = {
                "access_token": page_token,
            }
            if message:
                feed_payload["message"] = message
            for idx, media_id in enumerate(media_refs):
                feed_payload[f"attached_media[{idx}]"] = json.dumps({"media_fbid": media_id}, ensure_ascii=False)

            ok, err, pl = call_facebook(feed_url, feed_payload)
            if not ok:
                results.append(f"{kind}:{target_id}:fail:{err}")
                continue
            post_id = str(pl.get("id") or "unknown").strip() or "unknown"
            ok_count += 1
            results.append(f"{kind}:{target_id}:ok:album:{post_id}:{len(media_refs)}")
            continue

        # 3) Text-only feed
        f_url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{target_id}/feed"
        f_payload = {
            "message": message,
            "access_token": page_token,
        }
        ok, err, pl = call_facebook(f_url, f_payload)
        if not ok:
            results.append(f"{kind}:{target_id}:fail:{err}")
            continue
        post_id = str(pl.get("id") or "unknown").strip() or "unknown"
        ok_count += 1
        results.append(f"{kind}:{target_id}:ok:feed:{post_id}")

    if ok_count == 0:
        first_err = next((r for r in results if ":fail:" in r), "facebook_error")
        return False, f"publish_error: {first_err}"
    return True, f"published: facebook targets={ok_count}/{len(configured)} details={' | '.join(results)}"


def publish_instagram(item: dict, accounts: dict) -> tuple[bool, str]:
    ig = accounts.get("instagram") or {}
    fb = accounts.get("facebook") or {}

    ig_business_id = (ig.get("ig_business_id") or "").strip()
    access_token = (ig.get("access_token") or "").strip()
    if not access_token or access_token.upper().startswith("DUMMY"):
        access_token = (fb.get("page_access_token") or "").strip()

    if not ig_business_id or not access_token:
        return False, "needs_auth: instagram ig_business_id/access_token eksik"

    candidates = extract_media_candidates(item)
    if not candidates:
        return False, "needs_media: instagram için en az 1 foto/video yükleyin."

    fmt = (item.get("format") or "normal").strip().lower()

    caption = build_message(item)
    if not caption:
        caption = "."

    # 1) Convert local paths to public URL and validate content-type.
    media_items = []
    for c in candidates[:10]:
        media_url, url_err = build_public_media_url(c["path"])
        if url_err:
            return False, url_err
        valid, media_err = validate_public_media_url(media_url, c["kind"])
        if not valid:
            return False, media_err
        media_items.append({"kind": c["kind"], "url": media_url})

    if not media_items:
        return False, "needs_media: instagram için geçerli medya bulunamadı."

    def create_container(payload: dict) -> tuple[bool, str]:
        create_url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{ig_business_id}/media"
        res, post_err = post_with_retry(create_url, payload, timeout=50, attempts=3)
        if res is None:
            return False, f"network: {post_err}"
        pl = res.json() if res.text else {}
        if res.status_code >= 400:
            err = pl.get("error", {}).get("message") or res.text or "instagram_media_create_error"
            return False, err
        cid = (pl.get("id") or "").strip()
        if not cid:
            return False, "instagram creation id dönmedi"
        return True, cid

    def publish_container(creation_id: str) -> tuple[bool, str]:
        publish_url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{ig_business_id}/media_publish"
        last_err = ""
        for idx, wait_s in enumerate([0] + INSTAGRAM_PUBLISH_WAIT_SECONDS):
            if idx > 0:
                time.sleep(wait_s)
            publish_res, post_err = post_with_retry(
                publish_url,
                {"creation_id": creation_id, "access_token": access_token},
                timeout=50,
                attempts=3,
            )
            if publish_res is None:
                last_err = f"network: {post_err}"
                continue
            publish_payload = publish_res.json() if publish_res.text else {}
            if publish_res.status_code < 400:
                post_id = publish_payload.get("id") or creation_id
                return True, post_id

            err = publish_payload.get("error", {}).get("message") or publish_res.text or "instagram_publish_error"
            last_err = err
            lowered = err.lower()
            transient = (
                "media id is not available" in lowered
                or "media is not ready" in lowered
                or "please wait" in lowered
                or "try again" in lowered
            )
            if not transient:
                return False, err
        return False, last_err or "instagram media publish timeout"

    try:
        # Story currently supports single media container (image/video).
        if fmt == "story":
            if len(media_items) != 1:
                return False, "needs_media: story için tek foto/video yükleyin."
            media = media_items[0]
            payload = {
                "access_token": access_token,
                "media_type": "STORIES",
            }
            if media["kind"] == "image":
                payload["image_url"] = media["url"]
            else:
                payload["video_url"] = media["url"]

            ok, creation_id = create_container(payload)
            if not ok:
                return False, f"publish_error: {creation_id}"
            ok, publish_val = publish_container(creation_id)
            if not ok:
                return False, f"publish_error: {publish_val}"
            return True, f"published: instagram:story:{publish_val}"

        # 2) Multi media => Instagram carousel (mixed image/video supported by API when account supports it).
        if len(media_items) > 1:
            child_ids = []
            for media in media_items:
                data = {
                    "is_carousel_item": "true",
                    "access_token": access_token,
                }
                if media["kind"] == "image":
                    data["image_url"] = media["url"]
                else:
                    data["video_url"] = media["url"]
                    data["media_type"] = "VIDEO"
                ok, val = create_container(data)
                if not ok:
                    return False, f"publish_error: {val}"
                child_ids.append(val)

            ok, parent_creation = create_container(
                {
                    "media_type": "CAROUSEL",
                    "children": ",".join(child_ids),
                    "caption": caption,
                    "access_token": access_token,
                }
            )
            if not ok:
                return False, f"publish_error: {parent_creation}"

            ok, publish_val = publish_container(parent_creation)
            if not ok:
                return False, f"publish_error: {publish_val}"
            return True, f"published: instagram:{publish_val}"

        # 3) Single media publish.
        media = media_items[0]
        payload = {"caption": caption, "access_token": access_token}
        if media["kind"] == "image":
            payload["image_url"] = media["url"]
        else:
            payload["video_url"] = media["url"]
            if fmt == "short":
                payload["media_type"] = "REELS"
                payload["share_to_feed"] = "true"

        ok, creation_id = create_container(payload)
        if not ok:
            return False, f"publish_error: {creation_id}"
        ok, publish_val = publish_container(creation_id)
        if not ok:
            return False, f"publish_error: {publish_val}"
        return True, f"published: instagram:{publish_val}"
    except Exception as exc:
        return False, f"publish_error: {exc}"


def publish_x(item: dict, accounts: dict) -> tuple[bool, str]:
    cfg = accounts.get("x") or {}
    raw_token = (cfg.get("access_token") or "").strip()
    if not raw_token:
        return False, "needs_auth: x access_token eksik"

    token = raw_token
    if raw_token.lower().startswith("bearer "):
        token = raw_token.split(" ", 1)[1].strip()
    if not token:
        return False, "needs_auth: x access_token geçersiz"

    message = build_message(item)
    if not message:
        return False, "publish_error: boş içerik"

    media_candidates = extract_media_candidates(item)
    if media_candidates:
        return False, "publish_error: x medya yükleme entegrasyonu henüz tamamlanmadı."

    try:
        res, post_err = post_with_retry(
            X_POST_URL,
            {"text": message},
            timeout=25,
            attempts=3,
            json_body=True,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        if res is None:
            return False, f"publish_error: x network: {post_err}"

        payload = res.json() if res.text else {}
        if res.status_code >= 400:
            detail = payload
            if isinstance(payload, dict):
                errs = payload.get("errors")
                if isinstance(errs, list) and errs:
                    detail = errs[0].get("detail") or errs[0].get("message") or str(errs[0])
            return False, f"publish_error: x {detail}"

        post_id = (
            (payload.get("data") or {}).get("id")
            if isinstance(payload, dict)
            else None
        ) or "unknown"
        return True, f"published: x:{post_id}"
    except Exception as exc:
        return False, f"publish_error: x {exc}"


def publish_not_implemented(platform: str) -> tuple[bool, str]:
    return False, f"needs_auth: {platform} gerçek API entegrasyonu henüz tamamlanmadı."


def try_publish(item: dict, accounts: dict, t: dt.datetime) -> tuple[str, dict]:
    item.setdefault("logs", [])
    item.setdefault("delivered_platforms", [])
    item.setdefault("attempts", 0)
    item["attempts"] = int(item.get("attempts", 0) or 0) + 1
    item["last_attempt_at"] = iso(t)
    item.setdefault("last_error", "")

    fmt = (item.get("format") or "normal").strip().lower()
    if fmt == "story":
        platforms_raw = item.get("platforms") or []
        normalized = [str(p).strip().lower() for p in platforms_raw if str(p).strip()]
        if normalized != ["instagram"]:
            if "instagram" in normalized:
                item["platforms"] = ["instagram"]
                add_item_log(item, "system", True, "normalize: story için sadece instagram bırakıldı.", t)
            else:
                item["platforms"] = []
                add_item_log(item, "system", False, "publish_error: story için instagram seçili değil.", t)

        media = item.get("media") or []
        if isinstance(media, list) and len(media) > 1:
            item["media"] = media[:1]
            add_item_log(item, "system", True, "normalize: story için medya 1 dosyaya indirildi.", t)

    platforms = item.get("platforms") or []
    if not platforms:
        item["status"] = "failed"
        item["last_error"] = "publish_error: platform seçimi yok"
        add_item_log(item, "-", False, item["last_error"], t)
        return "failed", item

    delivered = set(item.get("delivered_platforms") or [])
    needs_auth = False
    has_error = False
    permanent_error = False
    last_fail_message = ""

    for platform in platforms:
        if platform in delivered:
            continue

        platform = (platform or "").strip().lower()
        if not has_platform_auth(accounts, platform):
            needs_auth = True
            last_fail_message = "needs_auth: bu platform için token/bağlantı yok (accounts.json)."
            add_item_log(item, platform, False, last_fail_message, t)
            continue

        if platform == "facebook":
            ok, msg = publish_facebook(item, accounts)
        elif platform == "instagram":
            ok, msg = publish_instagram(item, accounts)
        elif platform == "x":
            ok, msg = publish_x(item, accounts)
        else:
            ok, msg = publish_not_implemented(platform)

        add_item_log(item, platform, ok, msg, t)

        if ok:
            delivered.add(platform)
        else:
            last_fail_message = msg
            if msg.startswith("needs_auth") or is_auth_publish_error(msg):
                if not msg.startswith("needs_auth"):
                    last_fail_message = f"needs_auth: {msg}"
                needs_auth = True
            else:
                has_error = True
                if is_permanent_publish_error(msg):
                    permanent_error = True

    item["delivered_platforms"] = sorted(delivered)

    if len(delivered) == len(platforms):
        item["status"] = "sent"
        item["sent_at"] = iso(t)
        item["last_error"] = ""
        item["retry_after"] = ""
        return "sent", item

    if needs_auth:
        item["status"] = "needs_auth"
        item["last_error"] = last_fail_message or "needs_auth"
        item["retry_after"] = iso(t + dt.timedelta(minutes=NEEDS_AUTH_RETRY_MINUTES))
        return "keep", item

    if has_error:
        attempts = int(item.get("attempts", 0) or 0)
        item["last_error"] = last_fail_message or "publish_error"
        if permanent_error:
            item["status"] = "failed"
            item["retry_after"] = ""
            return "failed", item
        if attempts >= MAX_ATTEMPTS:
            item["status"] = "failed"
            item["retry_after"] = ""
            return "failed", item
        item["status"] = "error"
        item["retry_after"] = iso(t + dt.timedelta(minutes=next_error_retry_minutes(attempts)))
        return "keep", item

    # should not happen, keep safely
    item["status"] = "queued"
    item["last_error"] = "retry_unknown_state"
    item["retry_after"] = iso(t + dt.timedelta(minutes=1))
    return "keep", item


def make_queue_item_from_job(job: dict, t: dt.datetime, scheduled_at: str) -> dict:
    return {
        "id": f"q_{job.get('id')}_{int(t.timestamp())}",
        "source_job_id": job.get("id"),
        "created_at": iso(t),
        "scheduled_at": scheduled_at,
        "text": job.get("text", ""),
        "hashtags": job.get("hashtags", ""),
        "platforms": job.get("platforms", []),
        "format": job.get("format", "normal"),
        "media_mode": job.get("media_mode", "mixed"),
        "media": job.get("media", []),
        "targets": job.get("targets", {}),
        "archive_after_send": True,
        "status": "queued",
        "logs": [],
        "attempts": 0,
        "retry_after": "",
        "delivered_platforms": [],
        "last_error": "",
    }


def next_run_skip_missed(current_run: dt.datetime, now_time: dt.datetime, step_min: int) -> dt.datetime:
    step = max(1, int(step_min or 1))
    candidate = current_run + dt.timedelta(minutes=step)
    if candidate > now_time:
        return candidate

    step_seconds = step * 60
    lag_seconds = max(0, int((now_time - candidate).total_seconds()))
    jumps = (lag_seconds // step_seconds) + 1
    return candidate + dt.timedelta(minutes=step * jumps)


def move_due_jobs_to_queue(scheduled: list, queue: list, t: dt.datetime) -> int:
    moved_count = 0

    for job in scheduled:
        jtype = (job.get("type") or "").strip().lower()
        status = (job.get("status") or "").strip().lower()

        if jtype == "one_shot" and status == "scheduled":
            due = parse_iso(job.get("schedule_at", ""))
            if due and due <= t:
                queue.append(make_queue_item_from_job(job, t, iso(due)))
                job["status"] = "queued"
                moved_count += 1

        if jtype == "interval" and status == "active":
            next_run = parse_iso(job.get("next_run_at", "")) or parse_iso(job.get("start_at", "")) or t
            if next_run <= t:
                queue.append(make_queue_item_from_job(job, t, iso(next_run)))
                try:
                    step = int(job.get("interval_min", 60) or 60)
                except Exception:
                    step = 60
                if step < 1:
                    step = 1
                job["next_run_at"] = iso(next_run_skip_missed(next_run, t, step))
                moved_count += 1

        if jtype == "interval_range" and status == "active":
            next_run = parse_iso(job.get("next_run_at", "")) or parse_iso(job.get("start_at", "")) or t
            end_at = parse_iso(job.get("end_at", ""))

            if end_at and next_run > end_at:
                job["status"] = "completed"
                moved_count += 1
                continue

            if next_run <= t:
                queue.append(make_queue_item_from_job(job, t, iso(next_run)))
                try:
                    step = int(job.get("interval_min", 60) or 60)
                except Exception:
                    step = 60
                if step < 1:
                    step = 1
                next_value = next_run_skip_missed(next_run, t, step)
                job["next_run_at"] = iso(next_value)
                if end_at and next_value > end_at:
                    job["status"] = "completed"
                moved_count += 1

    return moved_count


def mark_scheduled_sent_if_needed(scheduled: list, queue_item: dict, t: dt.datetime) -> bool:
    source_job_id = (queue_item.get("source_job_id") or "").strip()
    if not source_job_id:
        return False

    changed = False
    for job in scheduled:
        if str(job.get("id", "")) != source_job_id:
            continue

        jtype = (job.get("type") or "").strip().lower()
        if jtype == "one_shot":
            if job.get("status") != "sent":
                job["status"] = "sent"
                job["sent_at"] = iso(t)
                changed = True
        elif jtype == "interval":
            job["last_sent_at"] = iso(t)
            changed = True
        elif jtype == "interval_range":
            job["last_sent_at"] = iso(t)
            changed = True

    return changed


def mark_scheduled_auth_required_if_needed(scheduled: list, queue_item: dict, t: dt.datetime) -> bool:
    source_job_id = (queue_item.get("source_job_id") or "").strip()
    if not source_job_id:
        return False

    changed = False
    last_error = (queue_item.get("last_error") or "needs_auth").strip() or "needs_auth"
    for job in scheduled:
        if str(job.get("id", "")) != source_job_id:
            continue

        if (job.get("status") or "").strip().lower() != "needs_auth":
            job["status"] = "needs_auth"
            changed = True
        if (job.get("last_error") or "").strip() != last_error:
            job["last_error"] = last_error
            changed = True
        if (job.get("updated_at") or "").strip() != iso(t):
            job["updated_at"] = iso(t)
            changed = True

    return changed


def mark_accounts_auth_required_if_needed(accounts: dict, queue_item: dict, t: dt.datetime) -> bool:
    failed_platforms = {
        str(platform).strip().lower()
        for platform in (queue_item.get("platforms") or [])
        if str(platform).strip()
    }
    failed_platforms -= {
        str(platform).strip().lower()
        for platform in (queue_item.get("delivered_platforms") or [])
        if str(platform).strip()
    }
    if not failed_platforms:
        return False

    changed = False
    last_error = (queue_item.get("last_error") or "needs_auth").strip() or "needs_auth"
    stamp = iso(t)
    for platform in failed_platforms:
        cfg = accounts.get(platform)
        if not isinstance(cfg, dict):
            continue

        if (cfg.get("status") or "").strip().lower() != "needs_auth":
            cfg["status"] = "needs_auth"
            changed = True
        if (cfg.get("note") or "").strip() != last_error:
            cfg["note"] = last_error
            changed = True
        if (cfg.get("updated_at") or "").strip() != stamp:
            cfg["updated_at"] = stamp
            changed = True
        accounts[platform] = cfg

    return changed


def main_loop():
    logged_start_for: set[str] = set()

    while True:
        try:
            user_dirs = iter_user_dirs()
            for user_dir in user_dirs:
                activate_user_storage(user_dir)
                ensure_files()

                if ACTIVE_USER_ID not in logged_start_for:
                    append_worker_log("info", "worker started. watching scheduled + queue")
                    logged_start_for.add(ACTIVE_USER_ID)

                scheduled = load_json(SCHEDULED_FILE, [])
                queue = load_json(QUEUE_FILE, [])
                archive = load_json(ARCHIVE_FILE, [])
                accounts = normalize_accounts(load_json(ACCOUNTS_FILE, {}))

                t = now()
                changed = False
                accounts_changed = False

                moved_count = move_due_jobs_to_queue(scheduled, queue, t)
                if moved_count > 0:
                    changed = True
                    append_worker_log("info", f"moved_due_jobs={moved_count}")

                kept = []
                for item in queue:
                    status = (item.get("status") or "queued").strip().lower()
                    retry_after = parse_iso(item.get("retry_after", ""))

                    if status not in ("queued", "needs_auth", "error"):
                        kept.append(item)
                        continue

                    if retry_after and retry_after > t:
                        kept.append(item)
                        continue

                    decision, processed = try_publish(item, accounts, t)
                    changed = True

                    if decision == "sent":
                        archive.append(processed)
                        if mark_scheduled_sent_if_needed(scheduled, processed, t):
                            changed = True
                        append_worker_log(
                            "sent",
                            f"item_sent id={processed.get('id')}",
                            item_id=str(processed.get("id", "")),
                            status=processed.get("status", ""),
                            platforms=processed.get("platforms") or [],
                        )
                    elif decision == "failed":
                        archive.append(processed)
                        append_worker_log(
                            "failed",
                            f"item_failed id={processed.get('id')} err={processed.get('last_error', '')}",
                            item_id=str(processed.get("id", "")),
                            status=processed.get("status", ""),
                            platforms=processed.get("platforms") or [],
                        )
                    else:
                        kept.append(processed)
                        if (processed.get("status") or "").strip().lower() == "needs_auth":
                            if mark_scheduled_auth_required_if_needed(scheduled, processed, t):
                                changed = True
                            if mark_accounts_auth_required_if_needed(accounts, processed, t):
                                accounts_changed = True
                        append_worker_log(
                            "retry",
                            f"item_retry id={processed.get('id')} status={processed.get('status')} retry={processed.get('retry_after')}",
                            item_id=str(processed.get("id", "")),
                            status=processed.get("status", ""),
                            platforms=processed.get("platforms") or [],
                        )

                if changed or accounts_changed:
                    save_json(SCHEDULED_FILE, scheduled)
                    save_json(QUEUE_FILE, kept)
                    save_json(ARCHIVE_FILE, archive)
                    if accounts_changed:
                        save_json(ACCOUNTS_FILE, accounts)
                    trim_log_file(WORKER_LOG_FILE, MAX_WORKER_LOG_LINES)

        except Exception as e:
            append_worker_log("error", f"worker error: {e}")

        time.sleep(WORKER_POLL_SECONDS)


if __name__ == "__main__":
    main_loop()
