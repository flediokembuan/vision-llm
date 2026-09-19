# Vision LLM Camera Analyzer

Aplikasi desktop yang menganalisis apa yang dilihat kamera lewat Gemini API,
membacakan hasilnya (TTS), dan menampilkannya dalam UI custom (bukan Tkinter) —
dibangun pakai **PyWebView**: logikanya Python, tampilannya HTML/CSS/JS.

## Struktur proyek

```
vision-llm-project/
├── main.py              entry point, membuka window PyWebView
├── api.py                jembatan Python <-> JavaScript
├── camera.py             capture webcam di background thread
├── gemini_client.py      kirim frame + prompt ke Gemini API
├── tts_engine.py         ubah teks jadi suara (gTTS + pygame)
├── config.py             API key & konstanta
├── requirements.txt
├── assets/reference_poses/   taruh gambar meme referensi pose di sini (lihat bawah)
└── ui/
    └── index.html         tampilan (Neon Grid City + maskot gedung)
```

## Cara menjalankan

1. Install dependency:
   ```
   pip install -r requirements.txt
   ```

2. Set API key Gemini (jangan ditulis langsung di kode):
   ```
   # PowerShell
   $env:GEMINI_API_KEY = "kunci_anda"

   # CMD
   set GEMINI_API_KEY=kunci_anda

   # Bash / Linux / Mac
   export GEMINI_API_KEY="kunci_anda"
   ```

3. Jalankan:
   ```
   python main.py
   ```

## Cara kerja alur data

```
[Webcam] --cv2--> camera.py (thread capture terus-menerus)
                      |
                      |-- get_frame_data_uri() --> dipoll UI tiap 80ms --> <img id="camFeed">
                      |
                      '-- get_latest_frame() ---> dipakai saat tombol Analisis ditekan
                                                        |
                                                        v
                                              gemini_client.py --> Gemini API
                                                        |
                                                        v
                                              tts_engine.py (suarakan hasil)
                                                        |
                                                        v
                                          hasil balik ke UI (teks, jumlah objek, waktu)
```

UI memanggil Python lewat `window.pywebview.api.<method>(...)`, yang selalu
mengembalikan Promise (karena pemanggilannya asinkron), jadi di JS dipakai
`await` atau `.then()`.

## Status fitur

- ✅ Kamera live streaming ke UI
- ✅ Analisis objek via Gemini API (dengan jumlah objek, jika Gemini konsisten menjawab JSON) — **manual**, dipicu tombol Analisis
- ✅ Text-to-speech otomatis untuk tiap hasil analisis objek
- ✅ Maskot bereaksi & progress bar saat memproses
- ✅ **Referensi Pose** — jalan **otomatis & terus-menerus** di background pakai
  MediaPipe Pose, TIDAK menunggu tombol apa pun. Begitu pose kamu cocok
  dengan salah satu pose yang dikenali, gambar referensinya langsung muncul.

## Fitur Referensi Pose — cara kerja & pose yang sudah disiapkan

Beda dari analisis objek (manual lewat tombol, karena manggil Gemini API),
deteksi pose jalan **otomatis** di `pose_detector.py`, TIDAK menunggu tombol
apa pun. Dua model MediaPipe dipakai bergantian karena butuh info yang beda:

| Pose        | Gambar         | Dideteksi lewat         | Cara kerja                                   |
|-------------|----------------|--------------------------|-----------------------------------------------|
| `mikir`     | `mikir.jpg`    | MediaPipe **Pose**       | pergelangan tangan dekat pelipis               |
| `waduh`     | `waduh.jpg`    | MediaPipe **Pose**       | pergelangan tangan di atas ubun-ubun           |
| `mantap`    | `mantap.jpg`   | MediaPipe **Hands**      | jempol terangkat, 4 jari lain mengepal         |
| `nonjok`    | `nonjok.jpg`   | MediaPipe **Hands**      | tangan mengepal penuh & besar di frame (dekat kamera) |

Alurnya:
1. `pose_detector.py` mengecek frame kamera ~3x per detik di background thread.
2. Dicoba dulu gestur tangan (mantap/nonjok) lewat MediaPipe Hands, karena
   itu butuh detail jari yang tidak dimiliki model Pose.
3. Kalau tidak ada gestur tangan yang cocok, dicoba pose tubuh (mikir/waduh)
   lewat MediaPipe Pose.
4. UI (`ui/index.html`) memanggil `pywebview.api.get_pose_reference()` tiap
   400ms, dan langsung menampilkan gambar begitu pose cocok — tanpa klik apa pun.

**Soal akurasi (penting dibaca):** `mikir` dan `waduh` cukup andal karena
cuma butuh posisi pergelangan tangan relatif ke kepala. Tapi `mantap` dan
terutama `nonjok` pakai aturan geometris sederhana (bukan model terlatih),
jadi kadang meleset tergantung sudut & jarak tangan ke kamera. Kalau kurang
akurat:
- Untuk `mantap`: sesuaikan angka `0.06` di `_is_thumbs_up()` (perkecil kalau
  susah kepicu, perbesar kalau salah deteksi).
- Untuk `nonjok`: sesuaikan `FIST_SIZE_THRESHOLD` di bagian atas
  `pose_detector.py` (defaultnya `0.35`) — perkecil kalau tangan kamu perlu
  terlalu dekat ke kamera dulu baru kepicu.

**Catatan instalasi**: `mediapipe` kadang butuh Python versi tertentu
(paling stabil di Python 3.9–3.11 saat tulisan ini dibuat). Kalau
`pip install mediapipe` gagal, cek versi Python kamu dengan `python --version`.
