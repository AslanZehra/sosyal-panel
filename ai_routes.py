# ai_routes.py
import os
import re
import requests
from flask import Blueprint, jsonify, request


ai_bp = Blueprint("ai_bp", __name__)

def _tr_slug(s: str) -> str:
    s = (s or "").lower()
    s = (
        s.replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )
    return s

def make_hashtags(topic: str, platform: str = "instagram", limit: int = 12):
    s = _tr_slug(topic)
    words = re.findall(r"[a-z0-9]+", s)
    words = [w for w in words if len(w) >= 3]

    uniq = []
    for w in words:
        if w not in uniq:
            uniq.append(w)

    tags = ["#" + w for w in uniq[:limit]]

    p = (platform or "").lower()
    if p == "instagram":
        tags += ["#kesfet", "#kesfetteyiz"]
    elif p == "tiktok":
        tags += ["#fyp", "#foryou"]

    out = []
    for t in tags:
        if t not in out:
            out.append(t)
    return out[:limit]

def extract_responses_text(resp_json: dict) -> str:
    if isinstance(resp_json, dict):
        ot = resp_json.get("output_text")
        if isinstance(ot, str) and ot.strip():
            return ot

    out = resp_json.get("output")
    if isinstance(out, list) and out:
        chunks = []
        for item in out:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for c in content:
                if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                    txt = c.get("text") or ""
                    if txt:
                        chunks.append(txt)
        if chunks:
            return "\n".join(chunks)

    return ""

def _fallback_text(topic: str, tone: str):
    tone = (tone or "samimi").lower()
    return {
        "samimi": f"{topic} hakkında kısa bir not: bugün tam zamanı.\nSen ne düşünüyorsun?",
        "kurumsal": f"{topic} ile ilgili güncel bilgilendirme.\nDetaylar için bizimle iletişime geçebilirsiniz.",
        "enerjik": f"{topic}! Hazır mısın? Hadi birlikte yükseltelim.",
        "satış": f"{topic} için fırsatı kaçırma.\nHemen bilgi al, avantajları yakala.",
    }.get(tone, f"{topic} hakkında kısa bir paylaşım.")

def _call_openai(prompt: str):
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5.2-mini").strip()

    if not api_key:
        return None

    r = requests.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json={
            "model": model,
            "instructions": "You are a Turkish social media copywriter.",
            "input": prompt,
        },
        timeout=30,
    )
    r.raise_for_status()
    text = extract_responses_text(r.json()).strip()
    return text or None

@ai_bp.post("/api/ai/text")
def api_ai_text():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    tone = (data.get("tone") or "samimi").strip()
    platform = (data.get("platform") or "instagram").strip()
    fmt = (data.get("format") or "normal").strip()
    language = (data.get("language") or "tr").strip()

    if not topic:
        return jsonify({"error": "topic_required"}), 400

    fallback = _fallback_text(topic, tone)

    prompt = (
        f"Dil: {language}\nPlatform: {platform}\nFormat: {fmt}\nTon: {tone}\nBrief: {topic}\n\n"
        "Sadece CAPTION üret.\n"
        "- normal: 2-4 paragraf\n"
        "- short/reels: kısa ve vurucu\n"
        "- story: 1-2 satır + CTA\n"
        "Sadece metni döndür."
    )

    try:
        text = _call_openai(prompt)
        if not text:
            return jsonify({"text": fallback, "mode": "fallback"})
        return jsonify({"text": text.strip(), "mode": "ai"})
    except Exception:
        return jsonify({"text": fallback, "mode": "fallback"})

@ai_bp.post("/api/ai/hashtags")
def api_ai_hashtags():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    platform = (data.get("platform") or "instagram").strip()
    limit = data.get("limit", 12)

    try:
        limit = int(limit)
        if limit < 5:
            limit = 5
        if limit > 25:
            limit = 25
    except Exception:
        limit = 12

    if not topic:
        return jsonify({"error": "topic_required"}), 400

    fallback_tags = make_hashtags(topic, platform=platform, limit=limit)

    prompt = (
        f"Platform: {platform}\nKonu: {topic}\n"
        f"{limit} adet hashtag üret. Sadece hashtagleri ver. Tek satırda boşlukla ayır."
    )

    try:
        text = _call_openai(prompt)
        if not text:
            return jsonify({"hashtags": fallback_tags, "mode": "fallback"})

        tags = re.findall(r"#\w+", text)
        uniq = []
        for t in tags:
            if t not in uniq:
                uniq.append(t)

        uniq = uniq[:limit] if uniq else fallback_tags
        return jsonify({"hashtags": uniq, "mode": "ai"})
    except Exception:
        return jsonify({"hashtags": fallback_tags, "mode": "fallback"})
