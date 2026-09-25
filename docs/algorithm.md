# Algoritma

## 1. Format payload

```
| MAGIC "DW01" (4 B) | VERSION (1 B) | LENGTH (1 B) |   header = 48 bit
| teks UTF-8 (LENGTH B) | CRC32 (4 B) |                  body
```

- Header diulang **16 kali** pada 768 blok pertama menurut urutan acak dari secret key.
- Body diulang sebanyak yang muat pada blok sisanya (minimal **5 kali**, jika kurang citra ditolak dengan `CapacityError`).
- Ekstraksi memvalidasi magic, versi, panjang, lalu CRC32. Teks hanya dianggap valid jika semuanya cocok.

## 2. DCT Robust

**Penyisipan**

1. BGR → YCrCb; hanya kanal Y yang diubah.
2. Bagi menjadi blok 8×8 penuh (piksel tepi yang tidak membentuk blok penuh tidak disentuh).
3. Urutan blok = permutasi acak dari secret key (`generate_block_positions`). Tiap blok mendapat satu pasangan koefisien dari daftar `COEFFICIENT_PAIRS` yang juga dipilih key.
4. `cv2.dct` → atur selisih `A − B` bila belum memenuhi margin:
   - bit 1: `A − B ≥ +S`
   - bit 0: `A − B ≤ −S`

   Koreksi dibagi dua (`A += shift`, `B −= shift`) sehingga perubahan tiap koefisien minimal. `S = EMBED_STRENGTH = 24`.
5. `cv2.idct` → bulatkan dan clip ke 0..255 → YCrCb → BGR.

Koefisien DC (0,0) tidak pernah diubah. Pasangan yang dipakai: (2,3)/(3,2), (1,4)/(4,1), (2,4)/(4,2), yaitu mid-frequency: cukup tahan kompresi, tidak terlalu terlihat.

**Ekstraksi blind** (tanpa citra asli)

1. Hitung ulang urutan blok dan pasangan dari secret key.
2. Untuk tiap blok yang membawa bit tertentu, hitung `d = A − B`.
3. **Soft voting**: jumlahkan `d` yang sudah di-clip pada `±3·S` untuk semua pengulangan satu bit; jumlah positif → bit 1. Clip mencegah satu blok yang rusak parah mendominasi hasil.
4. Baca header, validasi, baca body sepanjang `LENGTH`, validasi CRC32.

Pada crop, blok di luar area sah (`valid_region`) tidak ikut dihitung.

## 3. LSB Fragile

Bit payload yang sama ditulis ke LSB nilai piksel (array BGR yang dipipihkan) pada posisi berbeda-beda hasil turunan secret key (`generate_lsb_positions`), satu bit satu posisi, tanpa pengulangan. Tidak ada koreksi apa pun, jadi kerusakan satu bit sudah menggagalkan CRC.

## 4. Turunan secret key

```
seed = SHA-256("digital-watermarking|" + context + "|" + secret_key)  →  random.Random(seed)
```

`context` berbeda untuk urutan blok, pilihan pasangan, dan posisi LSB, sehingga satu key menghasilkan beberapa aliran acak yang saling bebas. Key kosong ditolak.

## 5. Pemilihan kekuatan S

Percobaan pada 5 citra sintetis (teks 18 byte), dengan JPEG asli, crop, resize, noise, brightness, contrast:

| S | rata-rata PSNR | JPEG 70 | JPEG 50 |
|---|---|---|---|
| 8 | 46,5 dB | gagal | gagal |
| 12 | 44,7 dB | lolos | gagal |
| 16 | 43,1 dB | lolos | gagal |
| **24** | **40,5 dB** | **lolos 5/5** | **lolos 5/5** |

S = 24 dipilih karena spesifikasi mewajibkan JPEG 50. Harganya PSNR lebih rendah. Pada foto nyata (512×600) PSNR 39,4 dB dan selisih citra tidak terlihat mata.

## 6. Strategi geometri

| Serangan | Pemulihan sebelum ekstraksi |
|---|---|
| Crop | Offset dibulatkan ke kelipatan 8. Hasil crop ditempel ke kanvas ukuran asli pada posisi semula; area kosong ditandai `valid_region` dan dilewati saat voting. |
| Resize | Diskalakan kembali ke ukuran asli dengan `INTER_CUBIC`. |

Keduanya mengasumsikan ukuran asli (dan posisi crop) diketahui, seperti dijelaskan di README dan halaman About. Crop dengan offset sembarang dan rotasi tidak ditangani.
