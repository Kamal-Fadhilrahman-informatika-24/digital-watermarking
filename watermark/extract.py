import numpy as np
from PIL import Image
from watermark.embed import dct2

def extract_watermark(watermarked_image_path, secret_key, watermark_length_bytes=8):
    img = Image.open(watermarked_image_path).convert('L')
    img_arr = np.float32(img)
    dct_img = dct2(img_arr)
    
    np.random.seed(int(secret_key))
    total_bits = watermark_length_bytes * 8
    extracted_bits = []
    
    rows, cols = dct_img.shape
    for _ in range(total_bits):
        r = np.random.randint(5, rows // 2)
        c = np.random.randint(5, cols // 2)
        val = dct_img[r, c]
        
        # Threshold decision
        if val > 0:
            extracted_bits.append('1')
        else:
            extracted_bits.append('0')
            
    binary_str = ''.join(extracted_bits)
    chars = [binary_str[i:i+8] for i in range(0, len(binary_str), 8)]
    text = ''.join([chr(int(b, 2)) for b in chars if len(b) == 8])
    return text, binary_str