"""
Deteksi pose & gestur real-time — jalan terus-menerus di background,
TIDAK menunggu klik tombol apa pun (beda dengan analisis objek yang manual).

Dua model dipakai bergantian karena butuh informasi yang beda:
  - MediaPipe POSE   : tahu posisi bahu/pinggul/pergelangan tangan/hidung.
                       Cukup untuk "tangan di pelipis" atau "tangan di kepala".
  - MediaPipe HANDS   : tahu posisi tiap ruas jari. Diperlukan untuk gestur
                       yang bentuknya ditentukan oleh jari, seperti jempol
                       ke atas atau tangan mengepal.

Cara kerja tiap ~0.3 detik:
  1. Ambil frame terbaru dari kamera.
  2. Coba deteksi gestur tangan dulu (jempol / mengepal) lewat Hands.
  3. Kalau tidak ada gestur tangan yang cocok, coba deteksi pose tubuh
     (tangan di pelipis / tangan di kepala) lewat Pose.
  4. Kalau pose/gestur itu ada di POSE_IMAGE_MAP dan file gambarnya ada di
     assets/reference_poses/, gambar itu yang ditampilkan di UI.

CATATAN JUJUR SOAL AKURASI:
  - Deteksi "mantap" dan "nonjok" berbasis aturan geometris sederhana
    (bukan model klasifikasi terlatih), jadi bisa salah deteksi tergantung
    sudut kamera dan pencahayaan. Ini titik awal yang baik, tapi kalau
    akurasinya kurang, coba ubah threshold di _is_thumbs_up() /
    _is_fist_toward_camera(), atau uji di kondisi pencahayaan yang lebih baik.
  - "nonjok" (kepalan tinju dekat kamera) paling sulit dideteksi konsisten
    karena tangan sering terlalu dekat/blur di kamera murah. Kalau sering
    gagal terdeteksi, pertimbangkan menurunkan FIST_SIZE_THRESHOLD di bawah.
"""

import base64
import os
import threading
import time

import cv2
import mediapipe as mp

import config

# Peta nama pose -> nama file gambar di assets/reference_poses/
POSE_IMAGE_MAP = {
    "mikir": "mikir.jpg",
    "waduh": "waduh.jpg",
    "mantap": "mantap.jpg",
    "nonjok": "nonjok.jpg",
}

POSE_CHECK_INTERVAL = 0.3  # detik antar pengecekan (tidak perlu secepat video)

# Seberapa besar lebar tangan (relatif ke lebar frame, 0-1) supaya dianggap
# "dekat kamera" untuk gestur nonjok. Perbesar kalau terlalu sering kepicu,
# perkecil kalau susah kepicu.
FIST_SIZE_THRESHOLD = 0.35


class PoseDetector:
    def __init__(self, camera_stream):
        self.camera_stream = camera_stream

        self._mp_pose = mp.solutions.pose
        self._pose = self._mp_pose.Pose(
            model_complexity=0,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        self._mp_hands = mp.solutions.hands
        self._hands = self._mp_hands.Hands(
            model_complexity=0,
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        )

        self._lock = threading.Lock()
        self._current_pose = None
        self._running = False
        self._thread = None
        self._image_cache = self._load_reference_images()

    def _load_reference_images(self):
        """Baca semua gambar referensi sekali di awal, simpan sebagai data URI."""
        cache = {}
        for pose_name, filename in POSE_IMAGE_MAP.items():
            path = os.path.join(config.REFERENCE_POSES_DIR, filename)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("ascii")
                ext = os.path.splitext(filename)[1].lstrip(".").lower() or "jpg"
                if ext == "jpg":
                    ext = "jpeg"
                cache[pose_name] = f"data:image/{ext};base64,{b64}"
            else:
                cache[pose_name] = None  # pose dikenali, tapi gambarnya belum ditaruh
        return cache

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)

    def _loop(self):
        while self._running:
            frame = self.camera_stream.get_latest_frame()
            if frame is not None:
                pose_name = self._classify(frame)
                with self._lock:
                    self._current_pose = pose_name
            time.sleep(POSE_CHECK_INTERVAL)

    # --- klasifikasi utama: coba gestur tangan dulu, baru pose tubuh ---

    def _classify(self, frame_bgr):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        hand_gesture = self._classify_hand_gesture(rgb)
        if hand_gesture:
            return hand_gesture

        return self._classify_body_pose(rgb)

    # --- gestur berbasis jari (MediaPipe Hands) ---

    def _classify_hand_gesture(self, rgb):
        result = self._hands.process(rgb)
        if not result.multi_hand_landmarks:
            return None

        hand = result.multi_hand_landmarks[0].landmark

        if self._is_thumbs_up(hand):
            return "mantap"
        if self._is_fist_toward_camera(hand):
            return "nonjok"
        return None

    @staticmethod
    def _is_thumbs_up(hand):
        """
        Jempol ke atas: ujung jempol (4) jauh lebih tinggi dari pangkalnya (2),
        sementara empat jari lain terlipat (ujung jari lebih rendah/dekat
        telapak dibanding ruas tengahnya).
        Ingat: sumbu Y MediaPipe terbalik (lebih kecil = lebih tinggi di layar).
        """
        thumb_tip, thumb_mcp = hand[4], hand[2]
        fingers_tip = [hand[8], hand[12], hand[16], hand[20]]
        fingers_pip = [hand[6], hand[10], hand[14], hand[18]]

        thumb_extended = thumb_tip.y < thumb_mcp.y - 0.06
        fingers_curled = all(tip.y > pip.y for tip, pip in zip(fingers_tip, fingers_pip))

        return thumb_extended and fingers_curled

    @staticmethod
    def _is_fist_toward_camera(hand):
        """
        Kepalan tinju: semua jari (termasuk jempol) terlipat, DAN lebar
        tangan di frame cukup besar (menandakan tangan dekat/diarahkan ke
        kamera, seperti gestur meninju).
        """
        fingers_tip = [hand[8], hand[12], hand[16], hand[20]]
        fingers_pip = [hand[6], hand[10], hand[14], hand[18]]
        fingers_curled = all(tip.y > pip.y for tip, pip in zip(fingers_tip, fingers_pip))

        xs = [lm.x for lm in hand]
        hand_width = max(xs) - min(xs)

        return fingers_curled and hand_width > FIST_SIZE_THRESHOLD

    # --- pose berbasis tubuh (MediaPipe Pose) ---

    def _classify_body_pose(self, rgb):
        result = self._pose.process(rgb)
        if not result.pose_landmarks:
            return None

        lm = result.pose_landmarks.landmark
        L = self._mp_pose.PoseLandmark

        left_wrist = lm[L.LEFT_WRIST]
        right_wrist = lm[L.RIGHT_WRIST]
        nose = lm[L.NOSE]
        left_eye = lm[L.LEFT_EYE]
        right_eye = lm[L.RIGHT_EYE]

        # perkiraan puncak kepala: sedikit di atas garis mata
        eye_y = (left_eye.y + right_eye.y) / 2
        top_of_head_y = eye_y - 0.12

        wrist_near_temple = (
            abs(left_wrist.y - nose.y) < 0.10 and abs(left_wrist.x - nose.x) > 0.05
        ) or (
            abs(right_wrist.y - nose.y) < 0.10 and abs(right_wrist.x - nose.x) > 0.05
        )
        wrist_on_head_top = (left_wrist.y < top_of_head_y) or (right_wrist.y < top_of_head_y)

        if wrist_on_head_top:
            return "waduh"
        if wrist_near_temple:
            return "mikir"
        return None

    def get_reference(self):
        """
        Return dict untuk dikirim ke UI:
          {"pose": None, "image": None}                 -> tidak ada pose dikenali
          {"pose": "mantap", "image": None}              -> pose dikenali, gambar belum ada
          {"pose": "mantap", "image": "data:image/..."}  -> pose dikenali & gambar tersedia
        """
        with self._lock:
            pose_name = self._current_pose
        if pose_name is None:
            return {"pose": None, "image": None}
        return {"pose": pose_name, "image": self._image_cache.get(pose_name)}
