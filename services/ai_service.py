"""AI service wrapper with retries, timeouts and typed errors."""
from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any

import streamlit as st
from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI, RateLimitError


class AIServiceError(RuntimeError):
    """Base AI service exception safe to show to users."""


class AIConfigurationError(AIServiceError):
    """Raised when API settings are missing or invalid."""


@dataclass(frozen=True)
class AIConfig:
    """Runtime AI configuration."""

    api_key: str
    model: str
    timeout_seconds: float = 30.0
    max_retries: int = 2


def get_ai_config() -> AIConfig:
    """Load AI settings from Streamlit secrets first, then environment variables."""
    api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
    model = st.secrets.get("OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    timeout_seconds = float(st.secrets.get("OPENAI_TIMEOUT", os.getenv("OPENAI_TIMEOUT", 30)))
    max_retries = int(st.secrets.get("OPENAI_MAX_RETRIES", os.getenv("OPENAI_MAX_RETRIES", 2)))
    if not api_key:
        raise AIConfigurationError("OPENAI_API_KEY tanımlı değil.")
    return AIConfig(api_key=api_key, model=model, timeout_seconds=timeout_seconds, max_retries=max_retries)


def _client(config: AIConfig) -> OpenAI:
    """Build an OpenAI client with a request timeout."""
    return OpenAI(api_key=config.api_key, timeout=config.timeout_seconds, max_retries=0)


def _extract_text(response: Any) -> str:
    """Extract text from OpenAI Responses API output."""
    text = getattr(response, "output_text", None)
    if text:
        return str(text)
    return str(response)


def _safe_json(text: str) -> dict[str, Any]:
    """Parse model JSON output and provide a fallback payload."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {"text": text, "term_notes": ["Model yanıtı JSON formatında alınamadı."]}


def call_ai(prompt: str, *, json_mode: bool = False) -> str | dict[str, Any]:
    """Call the AI model with retry, timeout, invalid-key and rate-limit handling."""
    config = get_ai_config()
    client = _client(config)
    last_error: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            response = client.responses.create(model=config.model, input=prompt)
            text = _extract_text(response)
            return _safe_json(text) if json_mode else text
        except AuthenticationError as exc:
            raise AIConfigurationError("OpenAI API anahtarı geçersiz veya yetkisiz.") from exc
        except (APITimeoutError, APIConnectionError, RateLimitError) as exc:
            last_error = exc
            if attempt >= config.max_retries:
                break
            time.sleep((2**attempt) + random.uniform(0, 0.4))
        except APIStatusError as exc:
            raise AIServiceError(f"AI servisi hata döndürdü: HTTP {exc.status_code}") from exc
        except Exception as exc:
            last_error = exc
            if attempt >= config.max_retries:
                break
            time.sleep((2**attempt) + random.uniform(0, 0.4))

    raise AIServiceError(f"AI servisine ulaşılamadı: {last_error}")


def build_corporate_prompt(raw_text: str, outputs: list[str]) -> str:
    """Build TÜRKAK corporate content prompt for the content assistant."""
    return f"""
Sen TÜRKAK Kurumsal İletişim Müdürlüğü için çalışan kurumsal içerik asistanısın.
Dil: Resmi, sade, açıklayıcı ve kurumsal.
Terminoloji:
- İngilizce ülke adında Turkey yerine Türkiye kullan.
- Türkçe denetim için İngilizcede assessment, değerlendirme için evaluation tercih edilir.
- Local Accreditation, Global Acceptance yerine Accredited once, accepted everywhere kullan.

İstenen çıktılar: {', '.join(outputs)}
Ham metin:
{raw_text}

Cevabı geçerli JSON olarak ver:
{{
  "corporate_news": "...",
  "social_media": "...",
  "title_suggestions": ["...", "...", "..."],
  "spot_text": "...",
  "term_notes": ["..."]
}}
""".strip()


def generate_corporate_content(raw_text: str, outputs: list[str]) -> dict[str, Any]:
    """Generate corporate news/social media/title/spot content."""
    if not raw_text.strip():
        raise AIServiceError("Ham metin boş olamaz.")
    if not outputs:
        raise AIServiceError("En az bir çıktı türü seçilmelidir.")
    return call_ai(build_corporate_prompt(raw_text, outputs), json_mode=True)  # type: ignore[return-value]


def generate_daily_summary(context: dict[str, Any]) -> str:
    """Generate a short daily dashboard summary from current application data."""
    prompt = f"""
TÜRKAK Kurumsal İletişim İş Yönetim Sistemi için günün kısa özetini yaz.
Yalnızca 4-6 cümle kullan, aksiyon odaklı ve kurumsal Türkçe yaz.
Veri:
{json.dumps(context, ensure_ascii=False, indent=2)}
""".strip()
    return str(call_ai(prompt))


def generate_idea_content(title: str, description: str) -> dict[str, Any]:
    """Generate content text and image prompt for a content idea."""
    prompt = f"""
TÜRKAK için aşağıdaki içerik fikrini kurumsal iletişim çıktısına dönüştür.
Başlık: {title}
Açıklama: {description}

Geçerli JSON döndür:
{{
  "text": "LinkedIn/web için kurumsal metin",
  "image_prompt": "Kurumsal görsel üretimi için Türkçe prompt"
}}
""".strip()
    return call_ai(prompt, json_mode=True)  # type: ignore[return-value]


def chatbot_reply(question: str, context: dict[str, Any]) -> str:
    """Generate context-aware sidebar chatbot reply."""
    prompt = f"""
Sen TÜRKAK İş Yönetim Sistemi içinde çalışan kısa cevap veren yardımcı botsun.
Sadece verilen uygulama bağlamına dayan. Emin değilsen bunu belirt.
Bağlam:
{json.dumps(context, ensure_ascii=False, indent=2)}

Soru: {question}
""".strip()
    return str(call_ai(prompt))
