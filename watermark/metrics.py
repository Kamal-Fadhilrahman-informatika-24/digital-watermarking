import numpy as np
from PIL import Image
import math

def calculate_psnr(original_path, watermarked_path):
    orig_img = Image.open(original_path).convert('L')
    img1 = np.array(orig_img, dtype=np.float32)
    
    wm_img = Image.open(watermarked_path).convert('L')
    # Menyamakan ukuran jika terjadi selisih piksel saat pemrosesan
    if wm_img.size != orig_img.size:
        wm_img = wm_img.resize(orig_img.size, Image.Resampling.LANCZOS)
    img2 = np.array(wm_img, dtype=np.float32)
    
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return 100.0
    return 20 * math.log10(255.0 / math.sqrt(mse))

def calculate_ber(original_bits, extracted_bits):
    if not original_bits or not extracted_bits:
        return 1.0
    errors = sum(1 for a, b in zip(original_bits, extracted_bits) if a != b)
    return errors / len(original_bits)

def calculate_nc(original_bits, extracted_bits):
    if not original_bits or not extracted_bits:
        return 0.0
    orig = np.array([int(b) for b in original_bits])
    ext = np.array([int(b) for b in extracted_bits])
    denom = np.sqrt(np.sum(orig**2)) * np.sqrt(np.sum(ext**2))
    if denom == 0:
        return 0.0
    return np.sum(orig * ext) / denom