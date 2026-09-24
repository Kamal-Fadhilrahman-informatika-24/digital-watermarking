from PIL import Image, ImageEnhance
import numpy as np

def attack_jpeg(image_path, output_path, quality=50):
    img = Image.open(image_path)
    img.save(output_path, "JPEG", quality=quality)

def attack_gaussian_noise(image_path, output_path, std=15):
    img = Image.open(image_path).convert('RGB')
    arr = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, std, arr.shape)
    noisy = np.clip(arr + noise, 0, 255).astype(np.uint8)
    Image.fromarray(noisy).save(output_path)

def attack_brightness(image_path, output_path, factor=1.3):
    img = Image.open(image_path)
    enhancer = ImageEnhance.Brightness(img)
    enhancer.enhance(factor).save(output_path)

def attack_crop(image_path, output_path, crop_fraction=0.1):
    img = Image.open(image_path)
    w, h = img.size
    box = (int(w * crop_fraction), int(h * crop_fraction), int(w * (1 - crop_fraction)), int(h * (1 - crop_fraction)))
    cropped = img.crop(box)
    cropped.resize((w, h), Image.Resampling.LANCZOS).save(output_path)