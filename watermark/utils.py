"""Fungsi bantu: konversi teks <-> bit (UTF-8)."""


def text_to_bits(text):
    return ''.join(format(b, '08b') for b in text.encode('utf-8'))


def bits_to_text(bits):
    usable = len(bits) - len(bits) % 8
    data = bytes(int(bits[i:i + 8], 2) for i in range(0, usable, 8))
    return data.decode('utf-8', errors='replace')
