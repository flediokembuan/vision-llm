"""
Kelas Api adalah jembatan antara UI (JavaScript) dan logika Python.
Semua method di kelas ini otomatis bisa dipanggil dari JS lewat:

    pywebview.api.nama_method(argumen).then(hasil => { ... })

(pywebview.api selalu mengembalikan Promise, karena panggilannya async.)
"""

import time

import camera
import gemini_client
import pose_detector
import tts_engine


class Api:
    def __init__(self):
        self.camera = camera.CameraStream()
        self.pose_detector = pose_detector.PoseDetector(self.camera)

    # --- lifecycle ---

    def start_camera(self):
        try:
            self.camera.start()
            self.pose_detector.start()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def stop_camera(self):
        self.pose_detector.stop()
        self.camera.stop()
        return {"ok": True}

    # --- dipanggil berulang oleh UI untuk update <img> feed kamera ---

    def get_camera_frame(self):
        data_uri = self.camera.get_frame_data_uri()
        return {"frame": data_uri}

    # --- dipanggil berulang oleh UI untuk update panel Referensi Pose ---
    # Ini JALAN TERUS di background begitu pose cocok, TIDAK menunggu tombol Analisis.

    def get_pose_reference(self):
        return self.pose_detector.get_reference()

    # --- dipanggil saat tombol "Analisis" ditekan ---

    def analyze(self, prompt: str):
        frame = self.camera.get_latest_frame()
        if frame is None:
            return {
                "ok": False,
                "error": "Belum ada frame kamera. Pastikan kamera sudah menyala.",
            }

        start = time.time()
        try:
            result = gemini_client.analyze_frame_structured(frame, prompt)
        except gemini_client.GeminiError as e:
            return {"ok": False, "error": str(e)}

        elapsed = round(time.time() - start, 2)

        # Suarakan hasilnya di background, tidak menunggu selesai.
        tts_engine.speak_async(result["jawaban"])

        return {
            "ok": True,
            "jawaban": result["jawaban"],
            "jumlah_objek": result["jumlah_objek"],
            "waktu_proses": elapsed,
        }
