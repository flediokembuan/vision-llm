"""
Modul kamera.

CameraStream membuka webcam di thread terpisah dan terus-menerus menyimpan
frame terbaru. Dua hal yang dibutuhkan UI diambil dari sini:
  1. Frame sebagai JPEG base64, untuk ditampilkan live di <img> pada halaman.
  2. Frame mentah (numpy array) terbaru, untuk dikirim ke Gemini saat
     tombol "Analisis" ditekan.
"""

import threading
import time
import base64

import cv2

import config


class CameraStream:
    def __init__(self):
        self._cap = None
        self._lock = threading.Lock()
        self._latest_frame = None       # numpy array (BGR), untuk dikirim ke Gemini
        self._latest_frame_b64 = None   # data URI jpeg, untuk ditampilkan di UI
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._cap = cv2.VideoCapture(config.CAMERA_INDEX, cv2.CAP_DSHOW)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)

        if not self._cap.isOpened():
            raise RuntimeError(
                "Tidak bisa membuka kamera. Pastikan tidak dipakai aplikasi lain "
                "dan CAMERA_INDEX di config.py sudah benar."
            )

        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def _loop(self):
        while self._running:
            ok, frame = self._cap.read()
            if ok:
                encode_params = [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY]
                success, buffer = cv2.imencode(".jpg", frame, encode_params)
                if success:
                    b64 = base64.b64encode(buffer.tobytes()).decode("ascii")
                    with self._lock:
                        self._latest_frame = frame
                        self._latest_frame_b64 = f"data:image/jpeg;base64,{b64}"
            time.sleep(config.CAMERA_FPS_INTERVAL)

    def get_frame_data_uri(self):
        """Frame terbaru sebagai data URI, untuk dikirim ke <img src=...> di UI."""
        with self._lock:
            return self._latest_frame_b64

    def get_latest_frame(self):
        """Frame mentah (numpy array BGR) terbaru, untuk dianalisis oleh Gemini."""
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()
