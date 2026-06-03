import os
import json
import re
import tempfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from pypdf import PdfReader


TERMS_PDF_URL = (
    "https://raw.githubusercontent.com/davutkara1985-create/"
    "is-takip-uygulamasi3/0d5489ad4f2ef7c2478c0c742f6185cfc7564622/"
    "terimler-sozlugu-2022-09-22.pdf"
)

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def load_local_secrets():
    try:
        import tomllib
    except ModuleNotFoundError:
        return

    possible_paths = [
        Path(".streamlit/secrets.toml"),
        Path("secrets.toml")
    ]

    for path in possible_paths:
        if not path.exists():
            continue

        data = tomllib.loads(path.read_text(encoding="utf-8"))

        for key in [
            "OPENAI_API_KEY", "OPENAI_MODEL",
            "X_BEARER_TOKEN", "X_USERNAME", "X_USER_ID", "X_API_BASE",
            "INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_BUSINESS_ACCOUNT_ID", "META_GRAPH_VERSION",
            "LINKEDIN_ACCESS_TOKEN", "LINKEDIN_ORG_URN", "LINKEDIN_ORG_ID", "LINKEDIN_VERSION",
            "BLUESKY_ACTOR", "BLUESKY_API_BASE",
            "NSOCIAL_API_URL", "NSOCIAL_API_TOKEN",
        ]:
            value = data.get(key)
            if value and not os.getenv(key):
                os.environ[key] = str(value)

        break


load_local_secrets()

app = FastAPI(title="TÜRKAK Kurumsal İçerik Asistanı API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class ContentRequest(BaseModel):
    rawText: str
    outputs: list[str]
    provider: str = "general"


class SocialPerformanceSyncRequest(BaseModel):
    since: str = "2026-05-01"
    posts: list[dict[str, Any]]
    officialAccounts: dict[str, str] = {}


@lru_cache(maxsize=1)
def load_terms_text() -> str:
    try:
        response = requests.get(TERMS_PDF_URL, timeout=30)
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        reader = PdfReader(tmp_path)
        pages = []

        for page in reader.pages[:30]:
            text = page.extract_text() or ""
            pages.append(text)

        text = "\n".join(pages)
        text = re.sub(r"\s+", " ", text).strip()

        return text[:18000]

    except Exception as exc:
        print("Terimler sözlüğü okunamadı:", exc)
        return ""


def build_prompt(raw_text: str, outputs: list[str], terms_text: str) -> str:
    output_labels = {
        "corporate_news": "Kurumsal haber metni oluştur",
        "social_media": "Sosyal medya metni oluştur",
        "title": "Başlık öner",
        "spot": "Spot metin öner",
    }

    selected_outputs = [output_labels.get(x, x) for x in outputs]

    return f"""
Sen TÜRKAK Kurumsal İletişim Müdürlüğü için çalışan bir kurumsal içerik asistanısın.

Kullanıcının istediği çıktı türleri:
{json.dumps(selected_outputs, ensure_ascii=False, indent=2)}

Kurumsal dil kuralları:
- Metinler resmi, sade, açıklayıcı ve kurumsal olmalı.
- Gereksiz abartılı ifadeler kullanılmamalı.
- TÜRKAK adı doğru ve tutarlı kullanılmalı.
- İngilizce ülke adında Turkey yerine Türkiye tercih edilmeli.
- Türkçe “denetim” karşılığı İngilizce kullanımda assessment olarak düşünülmeli.
- Türkçe “değerlendirme” karşılığı İngilizce kullanımda evaluation olarak düşünülmeli.
- “Local Accreditation, Global Acceptance” yerine “Accredited once, accepted everywhere” tercih edilmeli.
- Kurumsal haber metninde ziyaretin/toplantının amacı, teknik bilgi paylaşımı, iş birliği ve kurumsal katkı vurgusu bulunmalı.
- Sosyal medya metni kısa, etkili, kurumsal ve paylaşılabilir olmalı.
- Başlıklar haber diliyle uyumlu olmalı.
- Spot metin kısa ve tek paragraf olmalı.

Terimler sözlüğünden çıkarılan referans metin:
{terms_text}

Ham metin:
{raw_text}

Cevabı sadece geçerli JSON olarak ver. Markdown kullanma.

JSON şeması:
{{
  "corporate_news": "Kurumsal haber metni burada",
  "social_media": "Sosyal medya metni burada",
  "title_suggestions": ["Başlık 1", "Başlık 2", "Başlık 3"],
  "spot_text": "Spot metin burada",
  "term_notes": ["Terim uyarısı 1", "Terim uyarısı 2"]
}}
"""


def safe_json_parse(text: str) -> dict:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)

        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass

    return {
        "corporate_news": text,
        "social_media": "",
        "title_suggestions": [],
        "spot_text": "",
        "term_notes": ["Model yanıtı JSON formatında alınamadı; ham metin gösterildi."],
    }


@app.post("/ai-content")
def ai_content(req: ContentRequest):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY tanımlı değil.")

    if not req.rawText.strip():
        raise HTTPException(status_code=400, detail="Ham metin boş olamaz.")

    if not req.outputs:
        raise HTTPException(status_code=400, detail="En az bir çıktı türü seçilmelidir.")

    terms_text = load_terms_text()
    prompt = build_prompt(req.rawText, req.outputs, terms_text)

    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", OPENAI_MODEL),
            input=prompt,
        )

        result_text = response.output_text
        result_json = safe_json_parse(result_text)

        return {
            "ok": True,
            "provider": "general",
            "result": result_json,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


SOCIAL_PERFORMANCE_START_DATE = "2026-05-01"
SUPPORTED_SOCIAL_CHANNELS = ["X (Twitter)", "Instagram", "LinkedIn", "Nsocial", "Bluesky"]


def _safe_int(value: Any) -> int:
    try:
        if value is None or value == "":
            return 0
        return max(0, int(float(value)))
    except Exception:
        return 0


def _date_only(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if len(text) >= 10:
        return text[:10]
    return text


def _iso_to_ms(date_text: str) -> int:
    base = datetime.fromisoformat(f"{date_text}T00:00:00+00:00")
    return int(base.timestamp() * 1000)


def _normalize(text: Any) -> str:
    return re.sub(r"[^a-z0-9çğıöşü]+", " ", str(text or "").casefold()).strip()


def _url_or_id_candidates(post: dict[str, Any], channel: str) -> list[str]:
    values: list[str] = []

    platform_urls = post.get("platformUrls") or post.get("platformRefs") or {}
    if isinstance(platform_urls, str):
        for line in platform_urls.splitlines():
            raw = line.strip()
            if not raw:
                continue
            if ":" in raw:
                label, ref = raw.split(":", 1)
                if _normalize(label) in _normalize(channel) or _normalize(channel) in _normalize(label):
                    values.append(ref.strip())
            else:
                values.append(raw)
    elif isinstance(platform_urls, dict):
        if platform_urls.get(channel):
            values.append(str(platform_urls[channel]))

    if post.get("mediaUrl"):
        values.append(str(post.get("mediaUrl")))

    return [v for v in values if v]


def _text_matches(post: dict[str, Any], provider_item: dict[str, Any]) -> bool:
    provider_text = _normalize(" ".join([
        str(provider_item.get("text") or ""),
        str(provider_item.get("caption") or ""),
        str(provider_item.get("title") or ""),
    ]))

    if not provider_text:
        return False

    for field in ["title", "shortDescription", "detailContent"]:
        needle = _normalize(post.get(field))
        if needle and len(needle) >= 12 and needle[:80] in provider_text:
            return True

    title_words = [w for w in _normalize(post.get("title")).split() if len(w) > 3]
    if title_words:
        hits = sum(1 for word in title_words[:8] if word in provider_text)
        return hits >= max(2, min(4, len(title_words[:8]) // 2))

    return False


def _refs_match(post: dict[str, Any], channel: str, provider_item: dict[str, Any]) -> bool:
    refs = [_normalize(x) for x in _url_or_id_candidates(post, channel)]
    if not refs:
        return False

    haystack = _normalize(" ".join([
        str(provider_item.get("id") or ""),
        str(provider_item.get("url") or ""),
        str(provider_item.get("uri") or ""),
        str(provider_item.get("urn") or ""),
    ]))

    return any(ref and (ref in haystack or haystack in ref) for ref in refs)


def _find_matching_provider_item(post: dict[str, Any], channel: str, provider_items: list[dict[str, Any]]) -> dict[str, Any] | None:
    post_date = _date_only(post.get("publishDate"))

    for item in provider_items:
        if _refs_match(post, channel, item):
            return item

    same_day = [item for item in provider_items if _date_only(item.get("createdAt")) == post_date]

    for item in same_day:
        if _text_matches(post, item):
            return item

    if len(same_day) == 1:
        return same_day[0]

    return None


def _merge_metrics(post: dict[str, Any], metrics: dict[str, Any], source: str) -> dict[str, Any]:
    updated = dict(post)

    for key in ["reach", "impressions", "views", "likes", "shares", "clicks"]:
        incoming = _safe_int(metrics.get(key))
        current = _safe_int(updated.get(key))
        updated[key] = incoming if incoming > 0 or current == 0 else current

    now = datetime.now(timezone.utc).isoformat()
    note = metrics.get("note") or "Otomatik performans ölçümü yapıldı."

    updated["performanceNote"] = str(note)
    updated["performanceSource"] = source
    updated["lastPerformanceSyncAt"] = now

    return updated


def _request_json(url: str, headers: dict[str, str] | None = None, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = requests.get(url, headers=headers or {}, params=params or {}, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_x_items(since: str) -> tuple[list[dict[str, Any]], list[str]]:
    token = os.getenv("X_BEARER_TOKEN")
    username = os.getenv("X_USERNAME", "turkak").lstrip("@")
    user_id = os.getenv("X_USER_ID")
    base_url = os.getenv("X_API_BASE", "https://api.x.com/2").rstrip("/")
    warnings: list[str] = []

    if not token:
        return [], ["X_BEARER_TOKEN tanımlı olmadığı için X verisi alınmadı."]

    headers = {"Authorization": f"Bearer {token}"}

    try:
        if not user_id:
            user_data = _request_json(f"{base_url}/users/by/username/{username}", headers=headers)
            user_id = user_data.get("data", {}).get("id")

        if not user_id:
            return [], ["X_USER_ID bulunamadı."]

        params = {
            "max_results": 100,
            "exclude": "retweets,replies",
            "tweet.fields": "created_at,public_metrics,organic_metrics,non_public_metrics",
            "start_time": f"{since}T00:00:00Z",
        }

        data = _request_json(f"{base_url}/users/{user_id}/tweets", headers=headers, params=params)
        items = []

        for tweet in data.get("data", []) or []:
            public = tweet.get("public_metrics") or {}
            organic = tweet.get("organic_metrics") or {}
            non_public = tweet.get("non_public_metrics") or {}
            impressions = _safe_int(public.get("impression_count") or organic.get("impression_count") or non_public.get("impression_count"))
            metrics = {
                "reach": 0,
                "impressions": impressions,
                "views": impressions,
                "likes": public.get("like_count"),
                "shares": _safe_int(public.get("retweet_count")) + _safe_int(public.get("quote_count")),
                "clicks": public.get("reply_count"),
                "note": "X API üzerinden otomatik güncellendi.",
            }
            tweet_id = str(tweet.get("id"))
            items.append({
                "id": tweet_id,
                "url": f"https://x.com/{username}/status/{tweet_id}",
                "text": tweet.get("text", ""),
                "createdAt": tweet.get("created_at", ""),
                "metrics": metrics,
            })

        return items, warnings
    except Exception as exc:
        return [], [f"X verisi alınamadı: {exc}"]


def fetch_instagram_items(since: str) -> tuple[list[dict[str, Any]], list[str]]:
    token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    graph_version = os.getenv("META_GRAPH_VERSION", "v21.0")
    base_url = f"https://graph.facebook.com/{graph_version}"

    if not token or not account_id:
        return [], ["INSTAGRAM_ACCESS_TOKEN veya INSTAGRAM_BUSINESS_ACCOUNT_ID tanımlı olmadığı için Instagram verisi alınmadı."]

    warnings: list[str] = []
    items: list[dict[str, Any]] = []

    try:
        media = _request_json(
            f"{base_url}/{account_id}/media",
            params={
                "fields": "id,caption,timestamp,permalink,like_count,comments_count,media_type",
                "limit": 100,
                "access_token": token,
            },
        )

        for entry in media.get("data", []) or []:
            if _date_only(entry.get("timestamp")) < since:
                continue

            insight_values: dict[str, int] = {}
            try:
                insights = _request_json(
                    f"{base_url}/{entry.get('id')}/insights",
                    params={
                        "metric": "reach,impressions,shares,saved,views,total_interactions",
                        "access_token": token,
                    },
                )
                for metric in insights.get("data", []) or []:
                    values = metric.get("values") or []
                    if values:
                        insight_values[metric.get("name", "")] = _safe_int(values[0].get("value"))
            except Exception as exc:
                warnings.append(f"Instagram insight alınamadı ({entry.get('id')}): {exc}")

            comments = _safe_int(entry.get("comments_count"))
            metrics = {
                "reach": insight_values.get("reach", 0),
                "impressions": insight_values.get("impressions", 0),
                "views": insight_values.get("views", 0),
                "likes": entry.get("like_count", 0),
                "shares": insight_values.get("shares", 0),
                "clicks": comments,
                "note": "Instagram Graph API üzerinden otomatik güncellendi. Tıklama alanında yorum sayısı gösterilir.",
            }
            items.append({
                "id": str(entry.get("id")),
                "url": entry.get("permalink", ""),
                "caption": entry.get("caption", ""),
                "createdAt": entry.get("timestamp", ""),
                "metrics": metrics,
            })

        return items, warnings
    except Exception as exc:
        return [], [f"Instagram verisi alınamadı: {exc}"]


def fetch_linkedin_items(since: str) -> tuple[list[dict[str, Any]], list[str]]:
    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    org = os.getenv("LINKEDIN_ORG_URN") or os.getenv("LINKEDIN_ORG_ID")
    version = os.getenv("LINKEDIN_VERSION", "202605")

    if org and not str(org).startswith("urn:li:"):
        org = f"urn:li:organization:{org}"

    if not token or not org:
        return [], ["LINKEDIN_ACCESS_TOKEN veya LINKEDIN_ORG_URN/ID tanımlı olmadığı için LinkedIn verisi alınmadı."]

    headers = {
        "Authorization": f"Bearer {token}",
        "Linkedin-Version": version,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }
    base_url = "https://api.linkedin.com/rest"
    warnings: list[str] = []
    items: list[dict[str, Any]] = []

    try:
        post_data = _request_json(
            f"{base_url}/posts",
            headers=headers,
            params={"q": "author", "author": org, "count": 100},
        )

        for post in post_data.get("elements", []) or []:
            urn = post.get("id") or post.get("urn") or post.get("ugcPost") or post.get("share")
            created_ms = post.get("createdAt") or post.get("created", {}).get("time")
            created_at = ""
            if created_ms:
                created_at = datetime.fromtimestamp(int(created_ms) / 1000, tz=timezone.utc).isoformat()

            if _date_only(created_at) < since:
                continue

            stats_params = {
                "q": "organizationalEntity",
                "organizationalEntity": org,
            }
            urn_text = str(urn or "")
            if ":ugcPost:" in urn_text:
                stats_params["ugcPosts[0]"] = urn_text
            elif ":share:" in urn_text:
                stats_params["shares"] = f"List({urn_text})"
            else:
                continue

            stats = _request_json(f"{base_url}/organizationalEntityShareStatistics", headers=headers, params=stats_params)
            total = ((stats.get("elements") or [{}])[0].get("totalShareStatistics") or {})

            metrics = {
                "reach": total.get("uniqueImpressionsCount", 0),
                "impressions": total.get("impressionCount", 0),
                "views": total.get("impressionCount", 0),
                "likes": total.get("likeCount", 0),
                "shares": total.get("shareCount", 0),
                "clicks": total.get("clickCount", 0),
                "note": "LinkedIn API üzerinden otomatik güncellendi.",
            }
            commentary = post.get("commentary") or post.get("text") or ""
            if isinstance(commentary, dict):
                commentary = commentary.get("text", "")

            items.append({
                "id": urn_text,
                "urn": urn_text,
                "url": post.get("permalink") or "",
                "text": commentary,
                "createdAt": created_at,
                "metrics": metrics,
            })

        return items, warnings
    except Exception as exc:
        return [], [f"LinkedIn verisi alınamadı: {exc}"]


def fetch_bluesky_items(since: str) -> tuple[list[dict[str, Any]], list[str]]:
    actor = os.getenv("BLUESKY_ACTOR", "turkak.org.tr")
    base_url = os.getenv("BLUESKY_API_BASE", "https://public.api.bsky.app").rstrip("/")
    warnings: list[str] = []
    items: list[dict[str, Any]] = []
    cursor = None

    try:
        while True:
            params = {"actor": actor, "limit": 100, "filter": "posts_no_replies"}
            if cursor:
                params["cursor"] = cursor

            data = _request_json(f"{base_url}/xrpc/app.bsky.feed.getAuthorFeed", params=params)
            feed = data.get("feed") or []

            for row in feed:
                post = row.get("post") or {}
                record = post.get("record") or {}
                created_at = record.get("createdAt") or post.get("indexedAt") or ""
                if _date_only(created_at) < since:
                    continue

                uri = post.get("uri", "")
                rkey = uri.rstrip("/").split("/")[-1] if uri else ""
                metrics = {
                    "reach": 0,
                    "impressions": 0,
                    "views": 0,
                    "likes": post.get("likeCount", 0),
                    "shares": _safe_int(post.get("repostCount")) + _safe_int(post.get("quoteCount")),
                    "clicks": post.get("replyCount", 0),
                    "note": "Bluesky public API üzerinden otomatik güncellendi. Erişim/gösterim verisi public API'de bulunmadığı için 0 bırakıldı.",
                }
                items.append({
                    "id": uri,
                    "uri": uri,
                    "url": f"https://bsky.app/profile/{actor}/post/{rkey}" if rkey else "",
                    "text": record.get("text", ""),
                    "createdAt": created_at,
                    "metrics": metrics,
                })

            cursor = data.get("cursor")
            if not cursor or not feed or all(_date_only((row.get("post") or {}).get("record", {}).get("createdAt")) < since for row in feed):
                break

        return items, warnings
    except Exception as exc:
        return [], [f"Bluesky verisi alınamadı: {exc}"]


def fetch_nsocial_items(since: str) -> tuple[list[dict[str, Any]], list[str]]:
    api_url = os.getenv("NSOCIAL_API_URL")
    token = os.getenv("NSOCIAL_API_TOKEN")

    if not api_url:
        return [], ["NSOCIAL_API_URL tanımlı olmadığı için Nsocial verisi alınmadı."]

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        data = _request_json(api_url, headers=headers, params={"since": since})
        raw_items = data.get("data", data if isinstance(data, list) else [])
        items = []

        for item in raw_items:
            metrics = item.get("metrics") or item
            items.append({
                "id": str(item.get("id") or item.get("url") or ""),
                "url": item.get("url", ""),
                "text": item.get("text") or item.get("caption") or item.get("title") or "",
                "createdAt": item.get("createdAt") or item.get("created_at") or item.get("date") or "",
                "metrics": {
                    "reach": metrics.get("reach", 0),
                    "impressions": metrics.get("impressions", 0),
                    "views": metrics.get("views", 0),
                    "likes": metrics.get("likes", 0),
                    "shares": metrics.get("shares", 0),
                    "clicks": metrics.get("clicks", metrics.get("comments", 0)),
                    "note": "Nsocial API üzerinden otomatik güncellendi.",
                },
            })

        return items, []
    except Exception as exc:
        return [], [f"Nsocial verisi alınamadı: {exc}"]


def fetch_provider_items(channel: str, since: str) -> tuple[list[dict[str, Any]], list[str]]:
    if channel == "X (Twitter)":
        return fetch_x_items(since)
    if channel == "Instagram":
        return fetch_instagram_items(since)
    if channel == "LinkedIn":
        return fetch_linkedin_items(since)
    if channel == "Bluesky":
        return fetch_bluesky_items(since)
    if channel == "Nsocial":
        return fetch_nsocial_items(since)
    return [], [f"{channel} için sağlayıcı tanımlı değil."]


@app.post("/social-performance/sync")
def social_performance_sync(req: SocialPerformanceSyncRequest):
    since = req.since or SOCIAL_PERFORMANCE_START_DATE
    provider_cache: dict[str, list[dict[str, Any]]] = {}
    warnings: list[str] = []
    updated_posts: list[dict[str, Any]] = []

    for channel in SUPPORTED_SOCIAL_CHANNELS:
        items, provider_warnings = fetch_provider_items(channel, since)
        provider_cache[channel] = items
        warnings.extend(provider_warnings)

    for post in req.posts:
        if _date_only(post.get("publishDate")) < since:
            continue
        if post.get("status") != "Yayınlandı":
            continue

        updated = dict(post)
        changed = False

        for channel in post.get("channels") or []:
            provider_items = provider_cache.get(channel, [])
            match = _find_matching_provider_item(post, channel, provider_items)
            if not match:
                continue

            updated = _merge_metrics(updated, match.get("metrics") or {}, channel)
            changed = True

        if changed:
            updated_posts.append(updated)

    return {
        "ok": True,
        "since": since,
        "updatedCount": len(updated_posts),
        "updatedPosts": updated_posts,
        "warnings": warnings,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/health")
def health():
    return {"ok": True}
