import os
from PIL import Image

target_dir = "test_data/original"
size = (800, 600)

for filename in os.listdir(target_dir):
    if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        img_path = os.path.join(target_dir, filename)
        with Image.open(img_path) as img:
            img_resized = img.resize(size, Image.Resampling.LANCZOS)
            # Simpan kembali sebagai RGB JPEG
            img_resized.convert("RGB").save(img_path, "JPEG", quality=95)
print("Semua gambar berhasil disesuaikan ukurannya ke 800x600!")