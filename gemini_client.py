"""
Klien Gemini API — mengirim satu frame kamera + prompt teks, menerima
deskripsi hasil analisis sebagai teks.
"""

import base64

import cv2
import requests

import config


class GeminiError(Exception):
    pass


def analyze_frame(frame, prompt: str) -> str:
    """
    frame  : numpy array BGR (hasil cv2.VideoCapture.read())
    prompt : instruksi teks dari pengguna

    Return : teks hasil analisis dari Gemini.
    Raises : GeminiError kalau API key belum diset atau request gagal.
    """
    if not config.GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY belum diset di environment variable.")

    ok, buffer = cv2.imencode(".jpg", frame)
    if not ok:
        raise GeminiError("Gagal meng-encode frame ke JPEG.")

    base64_img = base64.b64encode(buffer.tobytes()).decode("ascii")

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": "Jawab singkat dan jelas. " + prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": base64_img,
                        }
                    },
                ]
            }
        ]
    }

    try:
        response = requests.post(
            config.GEMINI_URL,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": config.GEMINI_API_KEY,
            },
            json=payload,
            timeout=config.REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    except requests.HTTPError as e:
        body = e.response.text[:400] if e.response is not None else ""
        raise GeminiError(f"HTTP error dari Gemini: {e}\n{body}") from e
    except (KeyError, IndexError) as e:
        raise GeminiError(f"Format respons Gemini tidak sesuai dugaan: {e}") from e
    except requests.RequestException as e:
        raise GeminiError(f"Gagal menghubungi Gemini: {e}") from e


def analyze_frame_structured(frame, user_prompt: str) -> dict:
    """
    Sama seperti analyze_frame, tapi meminta Gemini menjawab dalam format JSON
    supaya kita bisa menampilkan jumlah objek di UI (bukan cuma teks bebas).

    Return: {"jawaban": str, "jumlah_objek": int | None}
    """
    instruksi = (
        "Kamu adalah asisten analisis gambar. Jawab HANYA dalam format JSON valid, "
        "tanpa markdown, tanpa teks lain di luar JSON. Format:\n"
        '{"jawaban": "<jawaban singkat dalam bahasa Indonesia>", '
        '"jumlah_objek": <jumlah objek utama yang terlihat, sebagai angka>}\n\n'
        f"Pertanyaan pengguna: {user_prompt}"
    )

    raw_text = analyze_frame(frame, instruksi)

    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()

    try:
        import json
        parsed = json.loads(cleaned)
        return {
            "jawaban": str(parsed.get("jawaban", raw_text)),
            "jumlah_objek": parsed.get("jumlah_objek"),
        }
    except (ValueError, TypeError):
        # Gemini tidak selalu patuh JSON — fallback aman, tetap tampilkan teksnya.
        return {"jawaban": raw_text, "jumlah_objek": None}
