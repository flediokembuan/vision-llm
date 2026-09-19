"""
Modul text-to-speech: mengubah teks hasil analisis jadi suara.
Dipanggil di background thread supaya tidak memblokir UI.
"""

import os
import tempfile
import threading
import time

import pygame
from gtts import gTTS

import config


def speak_async(text: str):
    """Jalankan TTS di thread terpisah, fire-and-forget."""
    if not text or text.startswith("[Error]"):
        return
    threading.Thread(target=_speak, args=(text,), daemon=True).start()


def _speak(text: str):
    temp_file = None
    try:
        tts = gTTS(text=text, lang=config.TTS_LANG)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_file = fp.name
        tts.save(temp_file)

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.music.unload()

    except Exception as e:
        print("TTS Error:", e)
    finally:
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
