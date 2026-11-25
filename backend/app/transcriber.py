"""Speech-to-text via Gemini (handles mixed Hindi + English)."""
import base64
import io
import os
import wave

import httpx

SAMPLE_RATE = 16000
PROMPT = (
    "Transcribe this audio exactly as spoken. The speaker may mix Hindi and English. "
    "Write Hindi words in Devanagari script and English words in Latin script. "
    "Output ONLY the transcript text. If there is no clear speech, output nothing."
)


def pcm_to_wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    return buf.getvalue()


def is_silent(pcm: bytes, threshold: int = 300) -> bool:
    import array

    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    if not samples:
        return True
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    return rms < threshold


async def transcribe(pcm: bytes) -> str:
    if not pcm or is_silent(pcm):
        return ""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {
                        "inline_data": {
                            "mime_type": "audio/wav",
                            "data": base64.b64encode(pcm_to_wav(pcm)).decode(),
                        }
                    },
                ]
            }
        ]
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=body, headers={"x-goog-api-key": key})
    if r.status_code != 200:
        raise RuntimeError(f"Gemini error {r.status_code}: {r.text[:200]}")
    try:
        parts = r.json()["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts).strip()
    except (KeyError, IndexError):
        return ""
