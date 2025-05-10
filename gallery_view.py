import os
import glob
import datetime
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
import numpy as np
from typing import List, Tuple, Optional


class ImageThumbnail(ctk.CTkFrame):
    """Widget thumbnail untuk menampilkan gambar terdeteksi dengan metadata"""

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
            # Coba parsing timestamp dari nama file
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

            # Ubah ukuran gambar sambil mempertahankan aspek rasio
            h, w = cv_img.shape[:2]
            aspect = w / h

            if aspect > 1:  # Lebih lebar daripada tinggi
                new_w = min(w, self.width)
                new_h = int(new_w / aspect)
            else:  # Lebih tinggi daripada lebar
                new_h = min(h, self.height)
                new_w = int(new_h * aspect)

            resized = cv2.resize(cv_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

            # Buat gambar PIL lalu CTkImage
            pil_img = Image.fromarray(resized)
            self.tk_image = ctk.CTkImage(pil_img, size=(new_w, new_h))

        except Exception as e:
            print(f"Gagal memuat gambar {self.image_path}: {e}")
            self.create_error_image()

    def create_error_image(self):
        """Buat placeholder untuk gambar yang gagal dimuat"""
        error_img = (
            np.ones((self.height, self.width, 3), dtype=np.uint8) * 200
        )  # Abu-abu muda
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
        self.geometry("800x600")
        self.minsize(600, 400)

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

            # Hitung ukuran agar pas dengan jendela sambil pertahankan aspek rasio
            window_w, window_h = 780, 500  # Sedikit lebih kecil dari ukuran jendela
            img_w, img_h = pil_img.size
            aspect = img_w / img_h

            if aspect > 1:  # Lebih lebar daripada tinggi
                new_w = min(img_w, window_w)
                new_h = int(new_w / aspect)
            else:  # Lebih tinggi daripada lebar
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
                self.image_frame, text=f"Gagal memuat gambar: {e}"
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

        # Buat jendela modal
        self.transient(master)
        self.focus_force()
        self.grab_set()


class GalleryWindow(ctk.CTkToplevel):
    """Jendela galeri untuk melihat gambar yang terdeteksi"""

    def __init__(self, master, detection_folder="detected", **kwargs):
        super().__init__(master, **kwargs)
        self.title("Galeri Deteksi")
        self.geometry("900x700")
        self.minsize(800, 600)

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

        # Buat jendela muncul di depan
        self.transient(master)
        self.focus_force()

    def create_filter_bar(self):
        """Buat kontrol filter di bagian atas"""
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
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
        """Buat tampilan galeri yang bisa di-scroll"""
        # Buat frame dengan scrollbar
        self.gallery_container = ctk.CTkFrame(self)
        self.gallery_container.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.gallery_container.grid_columnconfigure(0, weight=1)
        self.gallery_container.grid_rowconfigure(0, weight=1)

        # Buat frame yang bisa di-scroll
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

        # Terapkan filter jika disetel
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
            # Tampilkan keadaan kosong
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


# Fungsi untuk membuka galeri dari aplikasi utama
def open_gallery(parent, detection_folder="detected"):
    """Buka jendela galeri"""
    gallery = GalleryWindow(parent, detection_folder)
    return gallery


if __name__ == "__main__":
    root = ctk.CTk()
    gallery = GalleryWindow(root)
    root.mainloop()
