import cv2
import os
from ultralytics import YOLO
import time

# --- PENGATURAN YANG BISA DISESUAIKAN ---

# Path ke file model .pt hasil training Anda
# Pastikan file ini ada di direktori yang sama dengan skrip, atau ubah path-nya.
MODEL_PATH = "best.pt"

# Ambang batas kepercayaan (confidence threshold)
# Deteksi dengan skor di bawah nilai ini akan diabaikan.
CONFIDENCE_THRESHOLD = 0.4

# Indeks kamera
# 0 biasanya untuk webcam bawaan. Jika Anda punya lebih dari satu kamera, coba ganti ke 1, 2, dst.
CAMERA_INDEX = 2

# --- AKHIR DARI PENGATURAN ---


def run_live_inference():
    """
    Fungsi utama untuk menjalankan inferensi dari kamera secara real-time.
    """
    # 1. Periksa dan Muat Model
    print(f"🧠 Memuat model dari: {MODEL_PATH}...")
    if not os.path.exists(MODEL_PATH):
        print(f"❌ ERROR: File model tidak ditemukan di '{MODEL_PATH}'")
        print(
            "Pastikan Anda sudah meletakkan file 'best.pt' di lokasi yang benar atau perbarui variabel MODEL_PATH."
        )
        return

    try:
        model = YOLO(MODEL_PATH)
        print("✅ Model berhasil dimuat.")
    except Exception as e:
        print(f"❌ ERROR: Gagal memuat model. Kesalahan: {e}")
        return

    # 2. Inisialisasi Kamera
    print(f"📹 Mencoba membuka kamera dengan indeks {CAMERA_INDEX}...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"❌ ERROR: Gagal membuka kamera.")
        print(
            "Pastikan kamera terhubung dan tidak sedang digunakan oleh aplikasi lain."
        )
        return

    print("✅ Kamera berhasil dibuka. Tekan 'q' pada jendela video untuk keluar.")

    # Variabel untuk menghitung FPS (Frames Per Second)
    fps_start_time = 0
    frame_count = 0

    # 3. Loop Inferensi Real-time
    while True:
        # Baca satu frame dari kamera
        success, frame = cap.read()

        if not success:
            print("⚠️ Gagal membaca frame dari kamera. Mengakhiri program.")
            break

        # Jalankan inferensi pada frame
        # stream=True direkomendasikan untuk video agar lebih efisien secara memori
        results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False, stream=True)

        # Proses hasil inferensi
        for r in results:
            # Ambil frame yang sudah diberi anotasi (kotak, label, masker)
            annotated_frame = r.plot()

            # Hitung FPS
            frame_count += 1
            if fps_start_time == 0:
                fps_start_time = time.time()

            elapsed_time = time.time() - fps_start_time
            if elapsed_time > 1:  # Update FPS setiap 1 detik
                fps = frame_count / elapsed_time
                # Reset counter
                fps_start_time = time.time()
                frame_count = 0
            else:
                fps = frame_count / elapsed_time if elapsed_time > 0 else 0

            # Tampilkan FPS di pojok kiri atas frame
            cv2.putText(
                annotated_frame,
                f"FPS: {fps:.2f}",
                (10, 30),  # Posisi teks
                cv2.FONT_HERSHEY_SIMPLEX,
                1,  # Ukuran font
                (0, 255, 0),  # Warna (hijau)
                2,  # Ketebalan
            )

            # Tampilkan frame yang sudah diolah
            cv2.imshow("YOLOv8 Live Inference", annotated_frame)

        # Cek jika tombol 'q' ditekan untuk keluar dari loop
        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("Keluar dari program...")
            break

    # 4. Bersihkan
    cap.release()
    cv2.destroyAllWindows()
    print("Sumber daya kamera dan jendela telah dilepaskan.")


if __name__ == "__main__":
    run_live_inference()
