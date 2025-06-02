import os
import time
import configparser
import torch
import cv2
import numpy as np
import asyncio
import datetime
import io
import threading
import platform
import customtkinter as ctk
import sys
from pathlib import Path
from PIL import Image
from ultralytics.utils.plotting import Annotator, colors
from models.common import DetectMultiBackend
from utils.general import non_max_suppression
from aiohttp import ClientSession, FormData

# Perbaikan untuk masalah path Windows
if platform.system() == "Windows":
    import pathlib

    temp = pathlib.PosixPath
    pathlib.PosixPath = pathlib.WindowsPath
APP_APPEARANCE_MODE = "System"
APP_COLOR_THEME = "dark-blue"


class ImageThumbnail(ctk.CTkFrame):
    """Widget thumbnail untuk menampilkan gambar deteksi dengan metadata"""

    def __init__(self, master, image_path, width=200, height=200, **kwargs):
        super().__init__(master, **kwargs)
        self.image_path = image_path
        self.width = width
        self.height = height

        # Konfigurasi grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Ekstrak metadata dari nama file
        filename = os.path.basename(image_path)
        parts = filename.split("_")

        if len(parts) >= 2:
            self.label = parts[0]
            # Coba parse timestamp dari nama file
            try:
                timestamp_str = "_".join(parts[1:]).split(".")[0]
                self.timestamp = datetime.datetime.strptime(
                    timestamp_str, "%Y-%m-%d_%H-%M-%S"
                )
                self.timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            except:
                self.timestamp_str = "Waktu tidak diketahui"
        else:
            self.label = "Tidak diketahui"
            self.timestamp_str = "Waktu tidak diketahui"

        # Muat dan ubah ukuran gambar
        self.load_image()

        # Buat label gambar
        self.image_label = ctk.CTkLabel(self, text="", image=self.tk_image)
        self.image_label.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # Buat label info
        self.info_label = ctk.CTkLabel(
            self,
            text=f"{self.label}\n{self.timestamp_str}",
            justify="center",
            font=("Helvetica", 12),
        )
        self.info_label.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="ew")

        # Bind event klik
        self.image_label.bind("<Button-1>", self.on_click)
        self.info_label.bind("<Button-1>", self.on_click)

    def load_image(self):
        """Muat dan ubah ukuran gambar"""
        try:
            # Muat gambar dengan OpenCV untuk menangani berbagai format
            cv_img = cv2.imread(self.image_path)
            if cv_img is None:
                self.create_error_image()
                return

            # Konversi dari BGR ke RGB
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)

            # Ubah ukuran gambar dengan mempertahankan rasio aspek
            h, w = cv_img.shape[:2]
            aspect = w / h

            if aspect > 1:  # Lebih lebar dari tinggi
                new_w = min(w, self.width)
                new_h = int(new_w / aspect)
            else:  # Lebih tinggi dari lebar
                new_h = min(h, self.height)
                new_w = int(new_h * aspect)

            resized = cv2.resize(cv_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # Buat gambar PIL dan kemudian CTkImage
            pil_img = Image.fromarray(resized)
            self.tk_image = ctk.CTkImage(pil_img, size=(new_w, new_h))

        except Exception as e:
            print(f"Error memuat gambar {self.image_path}: {e}")
            self.create_error_image()

    def create_error_image(self):
        """Buat placeholder untuk gambar yang gagal dimuat"""
        error_img = (
            np.ones((self.height, self.width, 3), dtype=np.uint8) * 200
        )  # Abu-abu terang
        # Tambahkan teks error
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            error_img,
            "Error Gambar",
            (10, self.height // 2),
            font,
            0.7,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )

        pil_img = Image.fromarray(error_img)
        self.tk_image = ctk.CTkImage(pil_img, size=(self.width, self.height))

    def on_click(self, event):
        """Tangani event klik untuk membuka gambar ukuran penuh"""
        ImageViewerWindow(
            self.winfo_toplevel(), self.image_path, self.label, self.timestamp_str
        )


class ImageViewerWindow(ctk.CTkToplevel):
    """Jendela penampil gambar ukuran penuh"""

    def __init__(self, master, image_path, label, timestamp, **kwargs):
        super().__init__(master, **kwargs)
        self.title(f"Penampil Gambar - {label}")
        self.geometry("1080x720")  # Jendela lebih lebar
        self.minsize(800, 600)
        # Posisikan jendela di tengah
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (1080 / 2)
        y = (screen_height / 2) - (720 / 2)
        self.geometry(f"+{int(x)}+{int(y)}")

        # Gunakan mode tampilan yang sama dengan induk
        ctk.set_appearance_mode(APP_APPEARANCE_MODE)
        ctk.set_default_color_theme(APP_COLOR_THEME)

        # Konfigurasi grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Buat frame untuk gambar
        self.image_frame = ctk.CTkFrame(self)
        self.image_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.image_frame.grid_columnconfigure(0, weight=1)
        self.image_frame.grid_rowconfigure(0, weight=1)

        # Muat gambar penuh
        try:
            cv_img = cv2.imread(image_path)
            cv_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(cv_img)

            # Hitung ukuran agar sesuai dengan jendela sambil mempertahankan rasio aspek
            window_w, window_h = 780, 500  # Sedikit lebih kecil dari ukuran jendela
            img_w, img_h = pil_img.size
            aspect = img_w / img_h

            if aspect > 1:  # Lebih lebar dari tinggi
                new_w = min(img_w, window_w)
                new_h = int(new_w / aspect)
            else:  # Lebih tinggi dari lebar
                new_h = min(img_h, window_h)
                new_w = int(new_h * aspect)

            self.tk_image = ctk.CTkImage(pil_img, size=(new_w, new_h))

            # Tampilkan gambar
            self.image_label = ctk.CTkLabel(
                self.image_frame, text="", image=self.tk_image
            )
            self.image_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        except Exception as e:
            error_label = ctk.CTkLabel(
                self.image_frame, text=f"Error memuat gambar: {e}"
            )
            error_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # Panel info
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=1)

        # Detail gambar
        details_text = (
            f"Label: {label}\n"
            f"Waktu: {timestamp}\n"
            f"File: {os.path.basename(image_path)}"
        )

        details_label = ctk.CTkLabel(
            info_frame, text=details_text, justify="left", font=("Helvetica", 12)
        )
        details_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        # Tombol tutup
        close_button = ctk.CTkButton(
            info_frame, text="Tutup", command=self.destroy, width=100
        )
        close_button.grid(row=0, column=1, padx=20, pady=10, sticky="e")

        # Jadikan jendela modal
        self.transient(master)
        self.focus_force()
        self.grab_set()


class GalleryWindow(ctk.CTkToplevel):
    """Jendela galeri untuk melihat gambar deteksi"""

    def __init__(self, master, detection_folder="detected", **kwargs):
        super().__init__(master, **kwargs)
        self.title("Galeri Deteksi")
        self.geometry("1080x720")
        self.minsize(800, 600)

        # Gunakan mode tampilan yang sama dengan induk
        ctk.set_appearance_mode(APP_APPEARANCE_MODE)
        ctk.set_default_color_theme(APP_COLOR_THEME)

        # Posisikan jendela di tengah
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (900 / 2)
        y = (screen_height / 2) - (700 / 2)
        self.geometry(f"+{int(x)}+{int(y)}")

        self.detection_folder = detection_folder
        self.current_page = 0
        self.images_per_page = 12  # Grid 4x3
        self.filter_label = None

        # Konfigurasi grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Bar filter
        self.grid_rowconfigure(1, weight=1)  # Galeri
        self.grid_rowconfigure(2, weight=0)  # Navigasi

        # Buat komponen UI
        self.create_filter_bar()
        self.create_gallery_view()
        self.create_navigation_bar()

        # Muat gambar
        self.load_images()

        # Jadikan jendela muncul di depan
        self.transient(master)
        self.focus_force()

    def create_filter_bar(self):
        """Buat kontrol filter di bagian atas"""
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        filter_frame.grid_columnconfigure(4, weight=1)  # Dorong semuanya ke kiri

        # Filter label
        ctk.CTkLabel(filter_frame, text="Filter berdasarkan label:").grid(
            row=0, column=0, padx=(10, 5), pady=10, sticky="w"
        )
        self.label_filter = ctk.CTkEntry(filter_frame, width=120)
        self.label_filter.grid(row=0, column=1, padx=5, pady=10, sticky="w")

        # Filter tanggal
        ctk.CTkLabel(filter_frame, text="Filter berdasarkan tanggal:").grid(
            row=0, column=2, padx=(20, 5), pady=10, sticky="w"
        )
        self.date_filter = ctk.CTkEntry(
            filter_frame, width=120, placeholder_text="YYYY-MM-DD"
        )
        self.date_filter.grid(row=0, column=3, padx=5, pady=10, sticky="w")

        # Tombol terapkan filter
        apply_button = ctk.CTkButton(
            filter_frame, text="Terapkan Filter", command=self.apply_filters
        )
        apply_button.grid(row=0, column=4, padx=20, pady=10, sticky="w")

        # Tombol reset
        reset_button = ctk.CTkButton(
            filter_frame, text="Reset", command=self.reset_filters
        )
        reset_button.grid(row=0, column=5, padx=(5, 10), pady=10, sticky="e")

    def create_gallery_view(self):
        """Buat tampilan galeri yang dapat di-scroll"""
        # Buat frame dengan scrollbar
        self.gallery_container = ctk.CTkFrame(self)
        self.gallery_container.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.gallery_container.grid_columnconfigure(0, weight=1)
        self.gallery_container.grid_rowconfigure(0, weight=1)

        # Buat frame yang dapat di-scroll
        self.gallery_frame = ctk.CTkScrollableFrame(self.gallery_container)
        self.gallery_frame.grid(row=0, column=0, sticky="nsew")

        # Konfigurasi grid untuk thumbnail (4 kolom)
        for i in range(4):
            self.gallery_frame.grid_columnconfigure(i, weight=1)

    def create_navigation_bar(self):
        """Buat kontrol navigasi di bagian bawah"""
        nav_frame = ctk.CTkFrame(self)
        nav_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="ew")
        nav_frame.grid_columnconfigure(0, weight=1)
        nav_frame.grid_columnconfigure(3, weight=1)

        # Tombol halaman sebelumnya
        self.prev_button = ctk.CTkButton(
            nav_frame,
            text="← Sebelumnya",
            command=self.previous_page,
            state="disabled",
            width=100,
        )
        self.prev_button.grid(row=0, column=1, padx=5, pady=10)

        # Indikator halaman
        self.page_label = ctk.CTkLabel(nav_frame, text="Halaman 1 dari 1")
        self.page_label.grid(row=0, column=2, padx=20, pady=10)

        # Tombol halaman berikutnya
        self.next_button = ctk.CTkButton(
            nav_frame,
            text="Berikutnya →",
            command=self.next_page,
            state="disabled",
            width=100,
        )
        self.next_button.grid(row=0, column=3, padx=5, pady=10)

        # Label status
        self.status_label = ctk.CTkLabel(nav_frame, text="Tidak ada gambar ditemukan")
        self.status_label.grid(row=0, column=0, padx=20, pady=10, sticky="w")

    def load_images(self):
        """Muat gambar dari folder deteksi"""
        # Hapus thumbnail yang ada
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

        # Dapatkan semua file gambar
        image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp"]
        image_files = []

        for ext in image_extensions:
            image_files.extend(glob.glob(os.path.join(self.detection_folder, ext)))

        # Urutkan berdasarkan waktu modifikasi (terbaru dulu)
        image_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        # Terapkan filter jika diatur
        if self.filter_label:
            image_files = [
                f
                for f in image_files
                if self.filter_label.lower() in os.path.basename(f).lower()
            ]

        if hasattr(self, "filter_date") and self.filter_date:
            image_files = [
                f for f in image_files if self.filter_date in os.path.basename(f)
            ]

        self.all_images = image_files
        self.total_pages = max(
            1, (len(image_files) + self.images_per_page - 1) // self.images_per_page
        )

        # Perbarui status
        if len(image_files) == 0:
            self.status_label.configure(text="Tidak ada gambar ditemukan")
        else:
            self.status_label.configure(text=f"Ditemukan {len(image_files)} gambar")

        # Perbarui kontrol halaman
        self.current_page = min(self.current_page, max(0, self.total_pages - 1))
        self.update_page_controls()

        # Tampilkan halaman saat ini
        self.display_current_page()

    def display_current_page(self):
        """Tampilkan thumbnail untuk halaman saat ini"""
        # Hapus thumbnail yang ada
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()

        if not self.all_images:
            # Tampilkan status kosong
            empty_label = ctk.CTkLabel(
                self.gallery_frame,
                text="Tidak ada gambar deteksi ditemukan.\nObjek yang terdeteksi akan muncul di sini.",
                font=("Helvetica", 14),
                justify="center",
            )
            empty_label.grid(
                row=0, column=0, columnspan=4, padx=20, pady=50, sticky="nsew"
            )
            return

        # Hitung indeks awal dan akhir
        start_idx = self.current_page * self.images_per_page
        end_idx = min(start_idx + self.images_per_page, len(self.all_images))

        # Buat thumbnail
        for i, img_path in enumerate(self.all_images[start_idx:end_idx]):
            row = i // 4
            col = i % 4

            thumbnail = ImageThumbnail(
                self.gallery_frame,
                img_path,
                width=180,
                height=180,
                fg_color=("#e0e0e0", "#2d2d2d"),  # Warna mode terang/gelap
                corner_radius=8,
            )
            thumbnail.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

    def update_page_controls(self):
        """Perbarui kontrol navigasi halaman"""
        self.page_label.configure(
            text=f"Halaman {self.current_page + 1} dari {self.total_pages}"
        )

        # Aktifkan/nonaktifkan tombol navigasi
        if self.current_page <= 0:
            self.prev_button.configure(state="disabled")
        else:
            self.prev_button.configure(state="normal")

        if self.current_page >= self.total_pages - 1:
            self.next_button.configure(state="disabled")
        else:
            self.next_button.configure(state="normal")

    def next_page(self):
        """Pergi ke halaman berikutnya"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.display_current_page()
            self.update_page_controls()

    def previous_page(self):
        """Pergi ke halaman sebelumnya"""
        if self.current_page > 0:
            self.current_page -= 1
            self.display_current_page()
            self.update_page_controls()

    def apply_filters(self):
        """Terapkan filter ke galeri"""
        self.filter_label = self.label_filter.get().strip()
        self.filter_date = self.date_filter.get().strip()
        self.current_page = 0
        self.load_images()

    def reset_filters(self):
        """Reset semua filter"""
        self.label_filter.delete(0, "end")
        self.date_filter.delete(0, "end")
        self.filter_label = None
        self.filter_date = None
        self.current_page = 0
        self.load_images()


class DetectionEngine:
    """Menangani semua fungsi terkait deteksi"""

    def __init__(self, config_manager):
        self.config = config_manager
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.target_detected_start_time = None
        self.running = False
        self.cap = None
        self.sending_data = False  # Flag untuk melacak saat mengirim data
        self.is_ready = False  # Flag untuk melacak jika mesin siap

    def load_model(self, log_callback=None):
        """Muat model YOLO"""
        try:
            if log_callback:
                log_callback("Memuat model YOLO...\n")

            self.model = DetectMultiBackend(
                self.config.get("yolo_weights"), device=self.device
            )

            if log_callback:
                log_callback("Mesin Deteksi Siap\n")

            self.is_ready = True
            return self.model
        except Exception as e:
            if log_callback:
                log_callback(f"Error memuat model: {e}\n")
            raise

    def detect(self, frame):
        """Jalankan deteksi YOLO pada frame dengan mirroring"""
        # Mirror (flip) gambar sebelum diproses
        mirrored_frame = cv2.flip(frame, 1)  # 1 untuk flip horizontal

        # Simpan dimensi asli
        original_h, original_w = mirrored_frame.shape[:2]

        # Ubah ukuran dan normalisasi gambar
        img_resized = cv2.resize(mirrored_frame, (640, 640))
        img_tensor = (
            torch.from_numpy(img_resized)
            .to(self.device)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .float()
            / 255.0
        )

        # Jalankan inferensi
        with torch.no_grad():
            pred = self.model(img_tensor)
            pred = non_max_suppression(
                pred, conf_thres=float(self.config.get("min_conf_threshold"))
            )

        # Proses deteksi
        detections = []
        annotator = Annotator(mirrored_frame, line_width=2)

        # Faktor skala
        x_scale = original_w / 640
        y_scale = original_h / 640

        for det in pred[0]:
            if det is not None and len(det):
                *xyxy, conf, cls = det
                label = self.model.names[int(cls)]
                detections.append(label)

                if self.config.get("annotate") == "1":
                    # Skala koordinat bounding box ke ukuran asli
                    xyxy = [
                        int(xyxy[0] * x_scale),
                        int(xyxy[1] * y_scale),
                        int(xyxy[2] * x_scale),
                        int(xyxy[3] * y_scale),
                    ]
                    img_label = f"{label} {conf:.2f}"
                    annotator.box_label(xyxy, img_label, color=colors(int(cls), True))

        # Dapatkan hasil anotasi
        result = (
            annotator.result() if self.config.get("annotate") == "1" else mirrored_frame
        )

        return [result, detections]

    def process_frame(self, frame, targets, save_image=False, log_callback=None):
        """Proses satu frame dengan logika deteksi"""
        # Lewati pemrosesan jika kita sedang mengirim data
        if self.sending_data:
            return frame

        # Jalankan deteksi
        processed_frame, detections = self.detect(frame)
        # Periksa setiap target
        targetz = targets.split(",")
        if(self.target_detected_start_time == None):
            self.target_detected_start_time = {target: None for target in targetz}
        for i in range(len(targetz)):
            target = targetz[i].strip()
            # Periksa deteksi target
            if target in detections:
                current_time = time.time()
                if self.target_detected_start_time[target] is None:
                    self.target_detected_start_time[target] = current_time
                elif current_time - self.target_detected_start_time[target] >= int(
                    self.config.get("min_detect_time")
                ):
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    log_message = f"{target} terdeteksi pada: {timestamp}\n"

                    if log_callback:
                        log_callback(log_message)

                    # Simpan gambar jika diaktifkan
                    if save_image:
                        try:
                            os.makedirs("detected", exist_ok=True)
                            cv2.imwrite(
                                f"detected/{target}_{timestamp}.jpg", processed_frame
                            )
                            if log_callback:
                                log_callback("Gambar berhasil disimpan\n")
                        except Exception as e:
                            if log_callback:
                                log_callback(f"Error menyimpan gambar: {e}\n")

                    # Periksa apakah pengiriman data ke server diaktifkan
                    if self.config.get("send_data_enabled", "1") == "1":
                        # Atur flag untuk menunjukkan kita sedang mengirim data
                        self.sending_data = True

                        # Gunakan thread terpisah untuk mengirim data
                        threading.Thread(
                            target=self.send_data_sync,
                            args=(
                                processed_frame.copy(),
                                target,
                                timestamp,
                                log_callback,
                            ),
                            daemon=True,
                        ).start()

                    self.target_detected_start_time[target] = None

        return processed_frame

    def send_data_sync(self, img, label, timestamp, log_callback=None):
        """Wrapper sinkron untuk mengirim data ke server"""
        try:
            # Buat event loop baru untuk thread ini
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Jalankan fungsi async di event loop thread ini
            loop.run_until_complete(self.send_data(img, label, timestamp, log_callback))
            loop.close()
        except Exception as e:
            if log_callback:
                log_callback(f"Error dalam send_data_sync: {e}\n")
        finally:
            # Reset flag pengiriman saat selesai
            self.sending_data = False

    async def send_data(self, img, label, timestamp, log_callback=None):
        """Kirim data deteksi ke server"""
        try:
            server_endpoint = self.config.get("server_image_endpoint")
            data_endpoint = self.config.get("server_data_endpoint")

            if not server_endpoint or not data_endpoint:
                msg = "Endpoint server tidak dikonfigurasi\n"
                if log_callback:
                    log_callback(msg)
                return

            # Validate required config values
            required_configs = ["longitude", "latitude"]
            for config_key in required_configs:
                if not self.config.get(config_key):
                    msg = f"Konfigurasi {config_key} tidak ditemukan\n"
                    if log_callback:
                        log_callback(msg)
                    return

            # Kompres gambar
            if img is None or not isinstance(img, np.ndarray):
                msg = "Gambar tidak valid\n"
                if log_callback:
                    log_callback(msg)
                return

            _, img_encoded = cv2.imencode(
                ".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            )
            img_bytes = img_encoded.tobytes()

            if log_callback:
                log_callback(f"Mengirim data ke server: {server_endpoint}\n")

            async with ClientSession() as session:
                # First request - send image
                form = FormData()
                form.add_field(
                    "image",
                    img_bytes,
                    filename=f"{label}_{timestamp}.jpg",
                    content_type="image/jpeg",
                )

                headers = {"X-Label": label, "X-Timestamp": timestamp}
                async with session.post(
                    server_endpoint, data=form, headers=headers
                ) as response:
                    response.raise_for_status()
                    if log_callback:
                        log_callback(f"Respons image server: {await response.text()}\n")

                # Second request - send metadata
                formdata = FormData()
                fname = f"{label}_{timestamp}"
                formdata.add_field(
                    "long",
                    str(self.config.get("longitude")),  # Ensure string
                )
                formdata.add_field(
                    "lat",
                    str(self.config.get("latitude")),  # Ensure string
                )
                formdata.add_field("plaintext", fname)
                formdata.add_field("image", fname + ".jpg")

                async with session.post(data_endpoint, data=formdata) as response:
                    response.raise_for_status()
                    if log_callback:
                        log_callback(f"Respons data server: {await response.text()}\n")
        except Exception as e:
            msg = f"Error mengirim data: {e}\n"
            if log_callback:
                log_callback(msg)


class CameraManager:
    """Mengelola operasi kamera"""

    def __init__(self):
        self.camera_index = 0
        self.available_cameras = []

    def detect_available_cameras(self, max_to_check=5):
        """Deteksi kamera yang tersedia di sistem"""
        cameras = []
        for i in range(max_to_check):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append(i)
                cap.release()
        self.available_cameras = cameras
        return cameras

    def open_camera(self, camera_index):
        """Buka kamera dengan indeks yang ditentukan"""
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            # Atur resolusi kamera
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            return cap
        return None


class ConfigManager:
    """Mengelola konfigurasi aplikasi"""

    def __init__(self, config_path="config/config.ini"):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.load_config()

    def load_config(self):
        """Muat konfigurasi dari file"""

        # Muat konfigurasi pengguna jika ada
        user_config = Path(self.config_path)
        if user_config.exists():
            self.config.read(self.config_path)

    def get(self, key, default=None):
        """Dapatkan nilai konfigurasi"""
        try:
            return self.config["DEFAULT"][key]
        except (KeyError, configparser.NoSectionError):
            return default

    def set(self, key, value):
        """Atur nilai konfigurasi"""
        if "DEFAULT" not in self.config:
            self.config["DEFAULT"] = {}
        self.config["DEFAULT"][key] = str(value)

    def save(self):
        """Simpan konfigurasi ke file"""
        with open(self.config_path, "w") as f:
            self.config.write(f)


class App(ctk.CTk):
    """Kelas aplikasi utama"""

    def __init__(self):
        super().__init__()

        # Inisialisasi manajer
        self.config_manager = ConfigManager()
        self.camera_manager = CameraManager()

        # Status aplikasi
        self.show_video = True
        self.save_image = False
        self.detection_thread = None
        self.engine_loading = False

        # Siapkan UI
        self.setup_app()
        self.setup_ui()

        # Inisialisasi kamera
        self.camera_manager.detect_available_cameras()
        self.update_camera_dropdown()

        # Tampilkan pesan awal
        self.video_label.configure(text="Memulai Mesin Deteksi...")

        # Inisialisasi mesin deteksi di thread latar belakang
        self.detection_engine = DetectionEngine(self.config_manager)
        threading.Thread(target=self.initialize_engine, daemon=True).start()

    def initialize_engine(self):
        """Inisialisasi mesin deteksi di latar belakang"""
        self.engine_loading = True
        try:
            self.detection_engine.load_model(self.log)
        except Exception as e:
            self.after(
                0, lambda: self.log(f"Gagal menginisialisasi mesin deteksi: {e}\n")
            )
        finally:
            self.engine_loading = False
            # Perbarui UI untuk menunjukkan mesin siap
            self.after(
                0, lambda: self.video_label.configure(text="Tidak ada feed kamera")
            )

    def setup_app(self):
        """Siapkan jendela aplikasi"""
        app_name = self.config_manager.get("app_name", "Deteksi YOLO")
        self.title(app_name)
        self.geometry("1200x720")
        self.minsize(800, 600)

        # Konfigurasi layout grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        # Posisikan jendela di tengah
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (1080 / 2)
        y = (screen_height / 2) - (720 / 2)
        self.geometry(f"+{int(x)}+{int(y)}")

    def setup_ui(self):
        """Inisialisasi semua komponen UI"""
        # Frame video utama - buat lebih kecil
        self.video_frame = ctk.CTkFrame(self)
        self.video_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.video_frame.grid_rowconfigure(0, weight=1)
        self.video_frame.grid_columnconfigure(0, weight=1)

        # Label video
        self.video_label = ctk.CTkLabel(self.video_frame, text="Tidak ada feed kamera")
        self.video_label.grid(row=0, column=0, sticky="nsew")

        # Frame panel kontrol
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        # Konfigurasi grid frame kontrol untuk 2 kolom
        self.control_frame.grid_columnconfigure(0, weight=1)
        self.control_frame.grid_columnconfigure(1, weight=1)
        self.control_frame.grid_rowconfigure(
            7, weight=1
        )  # Spacer untuk mendorong tombol ke bawah

        # Kolom Kiri (Kolom 0)
        # Pemilihan kamera
        self.camera_label = ctk.CTkLabel(self.control_frame, text="Pilih Kamera:")
        self.camera_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.camera_dropdown = ctk.CTkOptionMenu(
            self.control_frame, values=["Kamera 0"], command=self.change_camera
        )
        self.camera_dropdown.grid(row=1, column=0, padx=5, pady=5, sticky="ew")

        # Target deteksi
        self.detection_label = ctk.CTkLabel(self.control_frame, text="Target Deteksi:")
        self.detection_label.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        target_value = self.config_manager.get("target", "-")
        self.detection_target_display = ctk.CTkLabel(
            self.control_frame,
            text=target_value,
            fg_color=("#e9e9e9", "#2b2b2b"),  # Warna mode terang/gelap
            corner_radius=6,
            padx=10,
            pady=8,
        )
        self.detection_target_display.grid(row=3, column=0, padx=5, pady=5, sticky="ew")

        # Info perangkat
        self.device_label = ctk.CTkLabel(
            self.control_frame,
            text=f"Menggunakan: {'GPU' if torch.cuda.is_available() else 'CPU'}",
        )
        self.device_label.grid(row=4, column=0, padx=5, pady=5, sticky="w")

        # Switch kontrol
        self.show_video_switch = ctk.CTkSwitch(
            self.control_frame, text="Tampilkan Video", command=self.toggle_show_video
        )
        self.show_video_switch.grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.show_video_switch.select()

        self.save_image_switch = ctk.CTkSwitch(
            self.control_frame, text="Simpan Gambar", command=self.toggle_save_image
        )
        self.save_image_switch.grid(row=6, column=0, padx=5, pady=5, sticky="w")

        # Kolom Kanan (Kolom 1)
        # Tombol deteksi
        self.detection_button = ctk.CTkButton(
            self.control_frame,
            text="Mulai Deteksi",
            command=self.toggle_detection,
            fg_color="#dc3545",  # Warna merah saat berhenti
            hover_color="#c82333",
            height=40,  # Buat tombol lebih tinggi untuk visibilitas lebih baik
        )
        self.detection_button.grid(row=0, column=1, padx=5, pady=15, sticky="ew")

        # Tombol Bersihkan Log
        self.clear_button = ctk.CTkButton(
            self.control_frame, text="Bersihkan Log", command=self.clear_log
        )
        self.clear_button.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Tombol pengaturan
        self.settings_button = ctk.CTkButton(
            self.control_frame,
            text="Pengaturan",
            command=self.open_settings,
            fg_color="#2b579a",
            hover_color="#1e3f6f",
        )
        self.settings_button.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Tombol galeri
        self.gallery_button = ctk.CTkButton(
            self.control_frame,
            text="Lihat Galeri",
            command=self.open_gallery_view,
            fg_color="#2b579a",
            hover_color="#1e3f6f",
        )
        self.gallery_button.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Indikator status untuk pengiriman data
        self.status_label = ctk.CTkLabel(
            self.control_frame,
            text="Status: Siap",
            fg_color="#333333",
            corner_radius=8,
            padx=10,
            pady=5,
        )
        self.status_label.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Tampilkan status server
        send_data_enabled = self.config_manager.get("send_data_enabled", "1") == "1"
        server_status = "AKTIF" if send_data_enabled else "NONAKTIF"
        server_color = "#28a745" if send_data_enabled else "#dc3545"

        self.server_status_label = ctk.CTkLabel(
            self.control_frame,
            text=f"Server: {server_status}",
            fg_color=server_color,
            corner_radius=8,
            padx=10,
            pady=5,
        )
        self.server_status_label.grid(row=5, column=1, padx=5, pady=5, sticky="ew")

        # Output log
        self.output_log = ctk.CTkTextbox(self)
        self.output_log.grid(
            row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew"
        )

    def open_gallery_view(self):
        """Buka jendela tampilan galeri"""
        # Folder deteksi adalah tempat gambar disimpan
        detection_folder = "detected"

        # Buka jendela galeri
        self.gallery_window = GalleryWindow(self, detection_folder)

        # Log bahwa galeri telah dibuka
        self.log("Membuka galeri deteksi...\n")

    def update_camera_dropdown(self):
        """Perbarui dropdown kamera dengan kamera yang tersedia"""
        cameras = self.camera_manager.available_cameras
        if cameras:
            self.camera_dropdown.configure(values=[f"Kamera {i}" for i in cameras])
            self.camera_dropdown.set(f"Kamera {cameras[0]}")
        else:
            self.camera_dropdown.configure(values=["Tidak ada kamera ditemukan"])
            self.camera_dropdown.set("Tidak ada kamera ditemukan")
            self.detection_button.configure(state="disabled")

    def change_camera(self, choice):
        """Tangani perubahan pemilihan kamera"""
        try:
            camera_num = int(choice.split()[-1])
            self.camera_manager.camera_index = camera_num
            self.log(f"Memilih kamera {camera_num}\n")
        except Exception as e:
            self.log(f"Error memilih kamera: {e}\n")

    def toggle_show_video(self):
        """Toggle tampilan video"""
        self.show_video = self.show_video_switch.get()

    def toggle_save_image(self):
        """Toggle penyimpanan gambar yang terdeteksi"""
        self.save_image = self.save_image_switch.get()
        # Teruskan pengaturan save_image ke mesin deteksi
        self.detection_engine.save_image = self.save_image

    def log(self, message):
        """Tambahkan pesan ke log"""
        self.output_log.insert("0.0", message)

    def clear_log(self):
        """Bersihkan log"""
        self.output_log.delete("0.0", "end")

    def open_settings(self):
        """Buka jendela pengaturan"""
        config_window = ConfigWindow(self, self.config_manager)

        # Jadikan jendela muncul di depan jendela utama
        config_window.transient(self)  # Atur sebagai jendela transien
        config_window.focus_force()  # Paksa fokus
        config_window.grab_set()  # Jadikan modal

    def reload_config(self):
        """Muat ulang konfigurasi setelah perubahan pengaturan"""
        # Muat ulang konfigurasi
        self.config_manager.load_config()

        # Perbarui elemen UI
        app_name = self.config_manager.get("app_name", "Deteksi YOLO")
        self.title(app_name)

        # Perbarui tampilan target deteksi
        target_value = self.config_manager.get("target", "-")
        self.detection_target_display.configure(text=target_value)

        # Perbarui indikator status server
        send_data_enabled = self.config_manager.get("send_data_enabled", "1") == "1"
        server_status = "AKTIF" if send_data_enabled else "NONAKTIF"
        server_color = "#28a745" if send_data_enabled else "#dc3545"
        self.server_status_label.configure(
            text=f"Server: {server_status}", fg_color=server_color
        )

        self.initialize_engine()

        # Log reload
        self.log("Konfigurasi dimuat ulang\n")

    def update_status(self, status_text, is_sending=False):
        """Perbarui indikator status"""
        if is_sending:
            self.status_label.configure(
                text=f"Status: {status_text}", fg_color="#e67e22"
            )
        else:
            self.status_label.configure(
                text=f"Status: {status_text}", fg_color="#333333"
            )
        self.update_idletasks()  # Paksa pembaruan UI

    def show_black_screen(self):
        """Tampilkan layar hitam di pratinjau video"""
        # Buat gambar hitam
        black_img = np.zeros((480, 640, 3), dtype=np.uint8)
        img_pil = Image.fromarray(black_img)
        img_tk = ctk.CTkImage(img_pil, size=(640, 480))
        self.video_label.configure(image=img_tk, text="")
        self.video_label.image = img_tk

    def detection_loop(self, targets):
        """Loop deteksi utama yang berjalan di thread terpisah"""
        # Inisialisasi kamera
        camera_index = self.camera_manager.camera_index
        cap = self.camera_manager.open_camera(camera_index)

        if not cap:
            self.log(f"Error: Tidak dapat membuka kamera {camera_index}\n")
            self.after(0, self.stop_detection)
            return

        # Mulai loop deteksi
        frame_count = 0
        frame_skip = int(self.config_manager.get("frame_skip", "10"))
        self.detection_engine.running = True

        try:
            while self.detection_engine.running:
                ret, frame = cap.read()
                if not ret:
                    self.log("Error membaca frame dari kamera\n")
                    break

                # Perbarui indikator status jika mengirim data
                if self.detection_engine.sending_data:
                    self.after(0, lambda: self.update_status("Kirim Data", True))
                else:
                    self.after(0, lambda: self.update_status("Berjalan"))

                frame_count += 1
                if frame_count % frame_skip == 0:
                    # Proses frame
                    processed_frame = self.detection_engine.process_frame(
                        frame, targets, self.save_image, self.log
                    )

                    # Perbarui UI jika diaktifkan
                    if self.show_video:
                        try:
                            img_pil = Image.fromarray(
                                cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                            )
                            # Ukuran gambar lebih kecil (480x360 bukan 640x480)
                            img_tk = ctk.CTkImage(img_pil, size=(480, 360))
                            self.after(
                                0,
                                lambda img=img_tk: self.video_label.configure(
                                    image=img, text=""
                                ),
                            )
                            self.after(
                                0,
                                lambda img=img_tk: setattr(
                                    self.video_label, "image", img
                                ),
                            )
                        except Exception as e:
                            self.after(
                                0, lambda e=e: self.log(f"Error memperbarui UI: {e}\n")
                            )

                # Delay kecil untuk mencegah penggunaan CPU tinggi
                time.sleep(0.01)

        except Exception as e:
            self.after(0, lambda e=e: self.log(f"Error kamera: {str(e)}\n"))
        finally:
            # Pembersihan
            if cap and cap.isOpened():
                cap.release()
            self.detection_engine.running = False

            # Reset UI di thread utama
            self.after(0, self.stop_detection)

    def toggle_detection(self):
        """Toggle antara memulai dan menghentikan deteksi"""
        if self.detection_engine.running:
            # Saat ini berjalan, jadi hentikan deteksi
            self.stop_detection()
        else:
            # Saat ini berhenti, jadi mulai deteksi
            self.start_detection()

    def start_detection(self):
        """Mulai proses deteksi"""
        if self.detection_engine.running:
            return

        # Periksa apakah mesin masih dimuat
        if self.engine_loading or not self.detection_engine.is_ready:
            self.log("Mesin deteksi masih menginisialisasi. Harap tunggu...\n")
            return

        # Perbarui target dari konfigurasi
        target = self.config_manager.get("target", "perampokan")

        # Perbarui tampilan tombol
        self.detection_button.configure(
            text="Hentikan Deteksi",
            fg_color="#28a745",  # Warna hijau saat berjalan
            hover_color="#218838",
        )
        self.camera_dropdown.configure(state="disabled")

        # Hapus teks "Tidak ada feed kamera"
        self.video_label.configure(text="")

        # Mulai thread deteksi
        self.detection_thread = threading.Thread(
            target=self.detection_loop, args=(target,), daemon=True
        )
        self.detection_thread.start()

        self.log("Memulai deteksi...\n")
        self.update_status("Berjalan")

    def stop_detection(self):
        """Hentikan proses deteksi"""
        self.detection_engine.running = False

        # Perbarui tampilan tombol
        self.detection_button.configure(
            text="Mulai Deteksi",
            fg_color="#dc3545",  # Warna merah saat berhenti
            hover_color="#c82333",
        )
        self.camera_dropdown.configure(state="normal")

        # Tampilkan layar hitam
        self.show_black_screen()

        self.log("Menghentikan deteksi...\n")
        self.update_status("Berhenti")


class ConfigWindow(ctk.CTkToplevel):
    """Jendela konfigurasi untuk pengaturan"""

    def __init__(self, master, config_manager):
        super().__init__(master)
        self.title("Pengaturan Konfigurasi")
        self.geometry("1080x720")  # Jendela lebih lebar
        self.minsize(800, 600)

        # Gunakan mode tampilan yang sama dengan induk
        ctk.set_appearance_mode(APP_APPEARANCE_MODE)
        ctk.set_default_color_theme(APP_COLOR_THEME)

        # Posisikan jendela di tengah
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width / 2) - (1080 / 2)
        y = (screen_height / 2) - (720 / 2)
        self.geometry(f"+{int(x)}+{int(y)}")

        self.master = master
        self.config_manager = config_manager

        # Jadikan jendela dapat diubah ukurannya
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)  # Bobot yang sama untuk kedua kolom
        self.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # Buat elemen UI
        self.create_widgets()

    def create_widgets(self):
        # Kolom Kiri - Pengaturan Dasar
        left_frame = ctk.CTkFrame(self)
        left_frame.grid(row=0, column=0, padx=10, pady=5, sticky="nsew", rowspan=6)
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # Nama Aplikasi
        ctk.CTkLabel(left_frame, text="Nama Aplikasi:").grid(
            row=0, column=0, padx=20, pady=(20, 0), sticky="w"
        )
        self.app_name = ctk.CTkEntry(left_frame)
        self.app_name.insert(0, self.config_manager.get("app_name", "Deteksi YOLO"))
        self.app_name.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="ew")

        # Kelas Target
        ctk.CTkLabel(left_frame, text="Target Deteksi:").grid(
            row=1, column=0, padx=20, pady=(10, 0), sticky="w"
        )
        self.target = ctk.CTkEntry(left_frame)
        self.target.insert(0, self.config_manager.get("target", "perampokan"))
        self.target.grid(row=1, column=1, padx=20, pady=(10, 0), sticky="ew")

        # Path Model
        ctk.CTkLabel(left_frame, text="Path Model YOLO:").grid(
            row=2, column=0, padx=20, pady=(10, 0), sticky="w"
        )
        self.model_frame = ctk.CTkFrame(left_frame)
        self.model_frame.grid(row=2, column=1, padx=20, pady=(10, 0), sticky="ew")
        self.model_frame.grid_columnconfigure(0, weight=1)
        self.yolo_weights = ctk.CTkEntry(self.model_frame)
        self.yolo_weights.insert(
            0, self.config_manager.get("yolo_weights", "yolo-model/default.pt")
        )
        self.yolo_weights.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            self.model_frame, text="Telusuri", width=80, command=self.browse_model
        ).grid(row=0, column=1, padx=(10, 0))

        # Ambang Batas Kepercayaan
        ctk.CTkLabel(left_frame, text="Ambang Batas Kepercayaan Min:").grid(
            row=3, column=0, padx=20, pady=(10, 0), sticky="w"
        )
        self.conf_thresh = ctk.CTkSlider(
            left_frame, from_=0.1, to=0.9, number_of_steps=8
        )
        self.conf_thresh.set(
            float(self.config_manager.get("min_conf_threshold", "0.5"))
        )
        self.conf_thresh.grid(row=3, column=1, padx=20, pady=(10, 0), sticky="ew")
        self.conf_label = ctk.CTkLabel(
            left_frame,
            text=f"{float(self.config_manager.get('min_conf_threshold', '0.5')):.1f}",
        )
        self.conf_label.grid(row=3, column=2, padx=(0, 20), pady=(10, 0))
        self.conf_thresh.configure(
            command=lambda v: self.conf_label.configure(text=f"{float(v):.1f}")
        )

        # Waktu Deteksi
        ctk.CTkLabel(left_frame, text="Waktu Deteksi Min (detik):").grid(
            row=4, column=0, padx=20, pady=(10, 0), sticky="w"
        )
        self.detect_time = ctk.CTkEntry(left_frame)
        self.detect_time.insert(0, self.config_manager.get("min_detect_time", "5"))
        self.detect_time.grid(row=4, column=1, padx=20, pady=(10, 0), sticky="ew")

        # Lewati Frame
        ctk.CTkLabel(left_frame, text="Lewati Frame (Performa):").grid(
            row=5, column=0, padx=20, pady=(10, 0), sticky="w"
        )
        self.frame_skip = ctk.CTkSlider(left_frame, from_=1, to=30, number_of_steps=29)
        self.frame_skip.set(int(self.config_manager.get("frame_skip", "10")))
        self.frame_skip.grid(row=5, column=1, padx=20, pady=(10, 0), sticky="ew")
        self.skip_label = ctk.CTkLabel(
            left_frame, text=self.config_manager.get("frame_skip", "10")
        )
        self.skip_label.grid(row=5, column=2, padx=(0, 20), pady=(10, 0))
        self.frame_skip.configure(
            command=lambda v: self.skip_label.configure(text=str(int(v)))
        )

        # Kolom Kanan - Pengaturan Server dan Switch
        right_frame = ctk.CTkFrame(self)
        right_frame.grid(row=0, column=1, padx=10, pady=5, sticky="nsew", rowspan=6)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure((0, 1, 2, 3, 4, 5), weight=1)

        # Endpoint Server
        ctk.CTkLabel(right_frame, text="Endpoint API Gambar:").grid(
            row=0, column=0, padx=20, pady=(20, 0), sticky="w"
        )
        self.img_endpoint = ctk.CTkEntry(right_frame)
        self.img_endpoint.insert(
            0,
            self.config_manager.get(
                "server_image_endpoint", "http://localhost:3000/recv-image"
            ),
        )
        self.img_endpoint.grid(row=0, column=1, padx=20, pady=(20, 0), sticky="ew")

        ctk.CTkLabel(right_frame, text="Endpoint API Data:").grid(
            row=1, column=0, padx=20, pady=(10, 0), sticky="w"
        )
        self.data_endpoint = ctk.CTkEntry(right_frame)
        self.data_endpoint.insert(
            0,
            self.config_manager.get(
                "server_data_endpoint", "http://localhost:3000/print-text"
            ),
        )
        self.data_endpoint.grid(row=1, column=1, padx=20, pady=(10, 0), sticky="ew")

        # Bagian Switch
        switches_frame = ctk.CTkFrame(right_frame)
        switches_frame.grid(
            row=2, column=0, columnspan=2, padx=20, pady=(20, 0), sticky="ew"
        )

        # Switch Anotasi
        self.annotate = ctk.CTkSwitch(switches_frame, text="Tampilkan Anotasi Deteksi")
        self.annotate.grid(row=0, column=0, padx=20, pady=10, sticky="w")
        (
            self.annotate.select()
            if self.config_manager.get("annotate", "1") == "1"
            else self.annotate.deselect()
        )

        # Switch Kirim Data
        self.send_data_switch = ctk.CTkSwitch(
            switches_frame, text="Kirim Data ke Server"
        )
        self.send_data_switch.grid(row=1, column=0, padx=20, pady=10, sticky="w")
        (
            self.send_data_switch.select()
            if self.config_manager.get("send_data_enabled", "1") == "1"
            else self.send_data_switch.deselect()
        )

        # Tambahkan label deskripsi untuk switch kirim data
        self.send_data_desc = ctk.CTkLabel(
            right_frame,
            text="Saat diaktifkan, objek yang terdeteksi akan dikirim ke endpoint server yang dikonfigurasi di atas.",
            wraplength=350,
            justify="left",
            text_color="#999999",
        )
        self.send_data_desc.grid(
            row=3, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="w"
        )

        # Bagian informasi tambahan
        info_frame = ctk.CTkFrame(right_frame)
        info_frame.grid(
            row=4, column=0, columnspan=2, padx=20, pady=(10, 0), sticky="ew"
        )

        info_text = ctk.CTkLabel(
            info_frame,
            text="Pengaturan deteksi mempengaruhi bagaimana model mengidentifikasi objek dalam feed video. "
            "Sesuaikan ambang batas kepercayaan untuk menyeimbangkan antara positif palsu dan deteksi yang terlewat.",
            wraplength=350,
            justify="left",
            text_color="#999999",
        )
        info_text.pack(padx=10, pady=10)

        # Tombol Simpan - Dipusatkan di bagian bawah
        save_frame = ctk.CTkFrame(self, fg_color="transparent")
        save_frame.grid(row=6, column=0, columnspan=2, pady=20, sticky="ew")
        save_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            save_frame,
            text="Simpan Konfigurasi",
            command=self.save_config,
            width=200,
            height=40,
            fg_color="#2b579a",
            hover_color="#1e3f6f",
        ).grid(row=0, column=0)

    def browse_model(self):
        from tkinter import filedialog

        filepath = filedialog.askopenfilename(filetypes=[("Model PyTorch", "*.pt")])
        if filepath:
            self.yolo_weights.delete(0, ctk.END)
            self.yolo_weights.insert(0, filepath)

    def save_config(self):
        # Perbarui konfigurasi
        self.config_manager.set("target", self.target.get())
        self.config_manager.set("app_name", self.app_name.get())
        self.config_manager.set("yolo_weights", self.yolo_weights.get())
        self.config_manager.set(
            "min_conf_threshold", str(round(self.conf_thresh.get(), 1))
        )
        self.config_manager.set("min_detect_time", self.detect_time.get())
        self.config_manager.set("annotate", "1" if self.annotate.get() else "0")
        self.config_manager.set("frame_skip", str(int(self.frame_skip.get())))
        self.config_manager.set("server_image_endpoint", self.img_endpoint.get())
        self.config_manager.set("server_data_endpoint", self.data_endpoint.get())
        self.config_manager.set(
            "send_data_enabled", "1" if self.send_data_switch.get() else "0"
        )

        # Simpan ke file
        self.config_manager.save()

        # Muat ulang konfigurasi di aplikasi utama
        self.master.reload_config()
        self.destroy()


if __name__ == "__main__":
    # Buat direktori detected jika belum ada
    os.makedirs("detected", exist_ok=True)

    # Buat direktori config jika belum ada
    os.makedirs("config", exist_ok=True)

    # Impor glob di sini untuk menghindari impor melingkar
    import glob

    # Mulai aplikasi
    app = App()
    app.mainloop()

    """
    
    python -m PyInstaller --onefile --icon=icon.png --add-data "yolo-model;yolo-model" --add-data "config;config" --add-data "models;models" --add-data "utils;utils" --add-data "detected;detected" main.py export.py

    """
