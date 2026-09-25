# Outline Presentasi dan Demo

Pembagian waktu 5 / 7 / 3 / 5 menit (total 20 menit). Sesuaikan dengan ketentuan dosen.

## 1. Pendahuluan dan konsep (5 menit)

- Masalah: klaim kepemilikan citra digital dan pelacakan penyalahgunaan.
- Watermark vs enkripsi vs steganografi (satu kalimat masing-masing).
- Dua metode: **DCT Robust** (utama) dan **LSB Fragile** (pembanding).
- Diagram blok 8×8 di halaman Home: DC tidak disentuh, pasangan mid-frequency dipakai.
- Peran secret key: menentukan blok, pasangan koefisien, dan posisi LSB.

## 2. Demo langsung (7 menit)

1. **Embed**: upload foto, teks watermark, secret key, metode DCT. Tunjukkan PSNR dan perbandingan citra.
2. **Detect** dengan key benar → SUCCESS. Ulangi dengan key salah → gagal. Tekankan bahwa citra asli tidak diperlukan (blind).
3. **Attack Testing**: jalankan 9 kondisi; buka dua atau tiga file hasil serangan (JPEG 50, crop, noise) untuk menunjukkan bahwa file-nya nyata dan berbeda.
4. **Comparison**: DCT vs LSB pada dataset; tunjukkan grafik Attack vs BER.
5. Unduh XLSX dan buka.

Cadangan jika demo gagal: siapkan tangkapan layar tiap langkah dan file XLSX hasil evaluasi.

## 3. Hasil dan analisis (3 menit)

- DCT: 5/5 pada JPEG 90/70/50, crop, resize, noise; PSNR sekitar 40 dB.
- LSB: PSNR sangat tinggi tanpa serangan, tetapi gagal pada hampir semua serangan.
- Trade-off imperceptibility vs robustness (kekuatan S = 24, hasil penyapuan 8/12/16/24).
- Keterbatasan yang jujur: crop offset sembarang, rotasi, JPEG ≤ 30.

## 4. Tanya jawab (5 menit)

Pertanyaan yang mungkin muncul dan jawaban singkatnya:

| Pertanyaan | Jawaban |
|---|---|
| Kenapa tidak mengubah koefisien DC? | DC membawa energi rata-rata blok; mengubahnya cepat terlihat sebagai blok berpetak. |
| Kenapa mid-frequency? | Frekuensi rendah terlihat, frekuensi tinggi hilang saat kompresi JPEG. |
| Apakah butuh citra asli untuk ekstraksi? | Tidak, ekstraksi blind; hanya butuh citra dan secret key. |
| Apa gunanya secret key? | Menentukan posisi penyisipan; key salah menghasilkan hasil tidak valid (diuji). |
| Kenapa LSB gagal setelah JPEG? | JPEG mengubah nilai piksel, sedangkan LSB hanya menyimpan satu bit per piksel tanpa pengulangan. |
| Kenapa NC LSB sekitar 0,42 bukan 0? | Untuk dua deret bit acak, NC berada di sekitar 0,5; jadi dibaca bersama BER. |
| Bagaimana crop dan resize ditangani? | Ukuran asli diketahui; crop ditempel ke kanvas asli dan area hilang dilewati; resize dikembalikan ke ukuran asli. |
| Apakah angka hasil pengujian dikarang? | Tidak; dihitung dari file hasil serangan yang dibaca ulang, dan diuji di `tests/test_attacks.py`. |
