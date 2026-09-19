"""
Konfigurasi proyek Vision LLM.

PENTING: jangan taruh API key langsung di sini. Set lewat environment variable:

    PowerShell : $env:GEMINI_API_KEY = "kunci_anda"
    CMD        : set GEMINI_API_KEY=kunci_anda
    Bash/Linux : export GEMINI_API_KEY="kunci_anda"
"""

import os

# --- Gemini API ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Cek daftar model terbaru di: https://ai.google.dev/gemini-api/docs/models
GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

REQUEST_TIMEOUT = 60  # detik, batas waktu tunggu respons Gemini

# --- Kamera ---
CAMERA_INDEX = 0          # ganti kalau webcam bukan yang pertama
CAMERA_WIDTH = 960
CAMERA_HEIGHT = 720
CAMERA_FPS_INTERVAL = 0.05  # jeda antar frame yang dikirim ke UI (detik)
JPEG_QUALITY = 70          # kompresi frame yang dikirim ke UI (0-100)

# --- Window aplikasi ---
WINDOW_TITLE = "Vision LLM Camera Analyzer"
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800

# --- Text-to-Speech ---
TTS_LANG = "id"

# --- Referensi pose (fitur lanjutan, lihat README) ---
REFERENCE_POSES_DIR = os.path.join(os.path.dirname(__file__), "assets", "reference_poses")
