import numpy as np
from PIL import Image

def dct_1d(x):
    N = len(x)
    n = np.arange(N)
    k = n.reshape((N, 1))
    return np.dot(np.cos(np.pi / N * (n + 0.5) * k), x)

def idct_1d(X):
    N = len(X)
    k = np.arange(N)
    n = k.reshape((N, 1))
    return X[0] + 2 * np.sum(X[1:] * np.cos(np.pi / N * k[1:] * (n + 0.5)), axis=0)

def dct2(image):
    return np.apply_along_axis(dct_1d, 0, np.apply_along_axis(dct_1d, 1, image))

def idct2(image):
    return np.apply_along_axis(idct_1d, 0, np.apply_along_axis(idct_1d, 1, image))

def embed_watermark(image_path, watermark_text, secret_key, output_path):
    # Membaca gambar dan mengubah ke grayscale menggunakan Pillow
    img = Image.open(image_path).convert('L')
    img_arr = np.float32(img)
    
    # Terapkan DCT 2D Pure NumPy
    dct_img = dct2(img_arr)
    
    # Atur Seed Pseudo-Noise berdasarkan Kunci Rahasia
    np.random.seed(int(secret_key))
    binary_watermark = ''.join(format(ord(i), '08b') for i in watermark_text)
    
    alpha = 15.0  # Kekuatan watermark
    rows, cols = dct_img.shape
    
    for i, bit in enumerate(binary_watermark):
        r = np.random.randint(5, rows // 2)
        c = np.random.randint(5, cols // 2)
        noise = np.random.randn()
        
        if bit == '1':
            dct_img[r, c] += alpha * noise
        else:
            dct_img[r, c] -= alpha * noise
            
    # Kembalikan dengan Inverse DCT
    idct_img = idct2(dct_img)
    
    # Simpan gambar hasil watermark
    final_img = Image.fromarray(np.clip(idct_img, 0, 255).astype(np.uint8))
    final_img.save(output_path)
    return True