import os
import json
import re
import tempfile
from functools import lru_cache
from pathlib import Path

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

        for key in ["OPENAI_API_KEY", "OPENAI_MODEL"]:
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


@app.get("/health")
def health():
    return {"ok": True}
