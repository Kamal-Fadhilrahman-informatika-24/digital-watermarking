# Digital Watermarking: Robust DCT Image Protection

Aplikasi web (Flask) untuk menyisipkan watermark teks ke dalam citra digital, mengekstraksinya kembali, lalu mengukur ketahanannya terhadap manipulasi citra. Proyek ini dibuat untuk tugas mata kuliah **Keamanan Informasi** (topik *Digital Watermarking*) dan bersifat akademik, bukan produk komersial.

Metode utama adalah **DCT Robust** (domain frekuensi, ekstraksi blind, dikendalikan secret key). Sebagai fitur pengayaan tersedia **LSB Fragile** sebagai pembanding: metode ini sengaja rapuh, sehingga perbedaan ketahanan keduanya bisa dilihat dari data.

Semua angka (PSNR, NC, BER, status SUCCESS/FAIL) dihitung dari file hasil serangan yang benar-benar dibuat dan dibaca ulang. Tidak ada nilai yang ditulis manual.

---

## 1. Tujuan Pembelajaran

- Memahami perbedaan watermark di domain spasial (LSB) dan domain frekuensi (DCT).
- Memahami peran secret key dalam menentukan posisi penyisipan.
- Mengukur kualitas visual (PSNR) dan ketahanan watermark (NC, BER) secara kuantitatif.
- Menguji ketahanan terhadap kompresi JPEG, cropping, resize, noise, brightness, dan contrast.

## 2. Fitur Utama

| Halaman | Fungsi |
|---|---|
| **Home** (`/`) | Ringkasan proyek dan alur kerja. |
| **Watermark** (`/embed`) | Upload citra, isi teks watermark dan secret key, pilih metode, lalu unduh hasilnya. Menampilkan citra asli vs ber-watermark, PSNR, dan hasil verifikasi ekstraksi. |
| **Detect** (`/detect`) | Ekstraksi watermark dari citra (upload baru atau hasil embed sebelumnya). Menampilkan teks, status, dan opsional NC/BER jika teks asli diisi. |
| **Attack Testing** (`/testing`) | Menjalankan 9 kondisi uji, menyimpan tiap hasil serangan sebagai file berbeda, mengekstraksi ulang, lalu menampilkan tabel, grafik, dan tombol unduh XLSX. |
| **Comparison** (`/comparison`) | Membandingkan DCT Robust dan LSB Fragile pada seluruh dataset. |
| **About** (`/about`) | Deskripsi proyek, metode, metrik, dan strategi serangan. |

## 3. Fitur Pengayaan

- **LSB Fragile** sebagai pembanding terhadap DCT Robust (bukan pengganti).
- Laporan **XLSX** 5 sheet dan **4 grafik** Matplotlib (Attack vs PSNR, NC, BER, keberhasilan).
- Skrip terminal untuk evaluasi dataset penuh.
- Format payload berversi dengan header + CRC32, sehingga watermark yang salah tidak pernah tampil sebagai "berhasil".

## 4. Teknologi

Python 3, Flask, OpenCV (`cv2.dct` / `cv2.idct`), NumPy, Pillow, openpyxl, Matplotlib, pytest. Tanpa database, Docker, Node.js, ataupun API berbayar. Frontend memakai HTML, CSS, dan JavaScript murni (tanpa CDN).

## 5. Struktur Folder

```
digital-watermarking/
├── app.py                    # application factory Flask
├── requirements.txt
├── pytest.ini
├── .env.example              # contoh konfigurasi (tanpa secret asli)
├── watermark/                # logika inti (tidak bergantung pada Flask)
│   ├── config.py             # semua parameter di satu tempat
│   ├── dct_watermark.py      # DCT Robust (embed + ekstraksi blind)
│   ├── lsb_watermark.py      # LSB Fragile
│   ├── key_utils.py          # secret key -> seed -> posisi blok/koefisien/piksel
│   ├── payload.py            # header (magic+versi+panjang) + teks + CRC32
│   ├── metrics.py            # MSE, PSNR, NC, BER
│   ├── attacks.py            # JPEG, crop, resize, noise, brightness, contrast
│   ├── attack_engine.py      # jalankan serangan, simpan file, ekstraksi, hitung metrik
│   ├── evaluation.py         # evaluasi seluruh dataset x metode x serangan
│   ├── report.py             # ringkasan, grafik, XLSX
│   ├── service.py            # orkestrasi untuk route Flask
│   ├── synthetic.py          # pembuat citra uji sintetis
│   └── utils.py, errors.py, results.py, methods.py
├── routes/                   # blueprint Flask (main, watermark, testing)
├── templates/  static/       # tampilan
├── scripts/                  # generate_test_dataset, run_evaluation, generate_report
├── tests/                    # pytest (141 pengujian)
├── test_data/original/       # dataset (image01..image05.png)
├── test_data/watermarked/    # hasil embed dataset (tidak di-commit)
├── test_data/attacks/        # hasil serangan dataset (tidak di-commit)
├── uploads/                  # upload sementara (tidak di-commit)
├── outputs/                  # hasil embed, serangan, grafik, laporan (tidak di-commit)
└── docs/                     # arsitektur, algoritma, pengujian, outline presentasi
```

## 6. Persyaratan Sistem

- Python 3 (diuji pada Python 3.12; disarankan 3.10 atau lebih baru). Jika `python3 --version` di Mac Anda menampilkan versi lama, pasang Python terbaru dari python.org.
- macOS, Linux, atau Windows. Panduan di bawah memakai macOS.
- Tidak perlu koneksi internet setelah dependensi terpasang.
- Seluruh pengujian lulus pada dua susunan paket: OpenCV 4.13 / NumPy 2.4 dan OpenCV 5.0 / NumPy 2.5 (hasil evaluasi identik).

## 7. Instalasi (macOS Monterey)

Buka Terminal, masuk ke folder proyek, lalu jalankan:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Jika `python3` belum ada, pasang dari python.org atau `brew install python`.

## 8. Menjalankan Aplikasi

```bash
source .venv/bin/activate
python app.py
```

Terminal akan menampilkan `Running on http://127.0.0.1:5001`. Buka alamat itu di browser. Tekan `Ctrl+C` untuk berhenti.

## 9. Konfigurasi

Konfigurasi bersifat opsional. Aplikasi membaca variabel lingkungan (*environment variable*) langsung dari terminal; berkas `.env` **tidak** dibaca otomatis. `.env.example` hanya contoh daftar variabel, dan `.env` sudah masuk `.gitignore` jika Anda ingin menyimpan catatan lokal.

```bash
export FLASK_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
export FLASK_DEBUG=0
python app.py
```

| Variabel | Fungsi |
|---|---|
| `FLASK_SECRET_KEY` | Kunci sesi Flask. Jika kosong, aplikasi membuat kunci acak setiap kali dijalankan (aman untuk demo; sesi lama tidak berlaku setelah restart). |
| `FLASK_DEBUG` | `0` (bawaan) atau `1` untuk mode debug lokal. Jangan dipakai di jaringan publik. |
| `WATERMARK_SECRET_KEY` | Hanya dipakai skrip terminal `run_evaluation.py`. |

Parameter algoritma (kekuatan penyisipan, ukuran blok, parameter serangan, batas upload) ada di `watermark/config.py`.

> `FLASK_SECRET_KEY` (kunci sesi Flask) berbeda dengan **secret key watermark**. Secret key watermark diketik pengguna di form, tidak pernah disimpan ke disk, log, JSON, atau XLSX.

## 10. Cara Penggunaan

1. **Watermark**: upload PNG/JPG/JPEG (maks. 8 MB, sisi terpendek minimal 128 px), isi teks (maks. 64 byte) dan secret key, pilih metode, klik *Embed*. Hasil bisa diunduh sebagai PNG.
2. **Detect**: unggah citra ber-watermark (atau pakai hasil embed tadi), masukkan secret key yang sama. Key salah akan menghasilkan pesan "Watermark tidak valid atau secret key salah."
3. **Attack Testing**: pilih hasil embed (atau upload baru), masukkan secret key, klik *Run All Tests*. Halaman hasil memuat tabel 9 kondisi, pratinjau tiap file serangan, 4 grafik, dan tombol unduh XLSX.
4. **Comparison**: masukkan secret key dan jalankan perbandingan pada seluruh isi `test_data/original/`.

Citra di atas 1024 px pada sisi terpanjang diperkecil otomatis sebelum diproses, dan ukuran yang dipakai ditampilkan di halaman hasil.

## 11. Algoritma DCT Robust

1. Konversi BGR → YCrCb; watermark hanya masuk ke kanal Y (luminans).
2. Bagi kanal Y menjadi blok 8×8, lalu terapkan `cv2.dct`.
3. Koefisien **DC (0,0) tidak pernah diubah**.
4. Untuk tiap blok yang dipilih, dipakai satu pasangan koefisien mid-frequency dari `[(2,3)/(3,2), (1,4)/(4,1), (2,4)/(4,2)]`. Pasangan yang dipakai per blok ditentukan secret key.
5. Bit `1` dipaksa membuat `A − B ≥ +S`, bit `0` membuat `A − B ≤ −S` dengan kekuatan `S = 24`.
6. Payload diulang di banyak blok: header diulang 16 kali, isi diulang sebanyak kapasitas (minimal 5 kali, kalau tidak citra ditolak sebagai terlalu kecil).
7. Ekstraksi **blind**: hanya butuh citra ber-watermark dan secret key. Bit dibaca dengan *soft voting* atas seluruh pengulangan, lalu divalidasi header (magic `DW01`) dan CRC32.

Nilai `S = 24` dipilih dari percobaan penyapuan kekuatan (8, 12, 16, 24). Kekuatan lebih kecil memberi PSNR lebih tinggi tetapi gagal pada JPEG 50. Detail ada di `docs/algorithm.md`.

## 12. Algoritma LSB Fragile

Bit payload (format sama dengan DCT) ditulis ke bit terendah nilai piksel pada posisi yang diturunkan dari secret key. Tiap bit ditulis satu kali tanpa pengulangan, sehingga perubahan sekecil apa pun merusak watermark. Ini disengaja: LSB dipakai untuk memperlihatkan mengapa domain frekuensi lebih tahan serangan.

## 13. Peran Secret Key

Secret key → SHA-256 → seed → generator acak terpisah untuk tiap keperluan (urutan blok, pilihan pasangan koefisien, posisi LSB) lewat string `context` yang ikut di-hash. Akibatnya:

- key yang sama selalu memberi posisi yang sama (deterministik);
- key berbeda memberi pola yang tidak berkorelasi, sehingga ekstraksi dengan key salah gagal;
- kunci tidak muncul di file keluaran mana pun (diuji di `tests/test_security.py`).

## 14. Metrik

- **PSNR** = `10·log10(255² / MSE)` dalam dB. Bernilai tak hingga bila MSE = 0. Dihitung antara citra asli dan citra ber-watermark, serta antara citra asli dan citra setelah serangan.
- **NC** = `Σ(w·w′) / √(Σw² · Σw′²)` pada bit payload asli `w` dan hasil ekstraksi `w′`. Untuk dua deret bit acak yang saling bebas, NC berada di sekitar 0,5 (bukan 0), sehingga NC harus dibaca bersama BER.
- **BER** = jumlah bit berbeda ÷ total bit payload.
- **Status**: `SUCCESS` hanya bila header valid, CRC valid, dan teks hasil ekstraksi sama persis dengan teks asli.

## 15. Skenario Serangan

Sembilan kondisi uji, semuanya dijalankan pada file yang benar-benar ditulis ke disk lalu dibaca ulang:

| Serangan | Parameter |
|---|---|
| Tanpa serangan | kontrol |
| JPEG | kualitas 90, 70, 50 (berkas `.jpg` asli lewat `cv2.imencode`) |
| Cropping | 10% dari lebar dan tinggi (5% tiap sisi) |
| Resize | 75% dari ukuran asli |
| Gaussian noise | σ = 5, seed tetap agar dapat direproduksi |
| Brightness | +20 |
| Contrast | ×1,2 (+20%) |

**Catatan strategi (penting untuk laporan):**

- *Cropping*: offset dibulatkan ke kelipatan 8 piksel agar grid blok DCT tetap selaras. Citra hasil crop ditempelkan kembali ke kanvas berukuran asli pada posisi semula, dan blok di area yang hilang dianggap hilang (erasure). Ini mengasumsikan ukuran asli dan posisi crop diketahui.
- *Resize*: citra dikembalikan ke ukuran asli (`INTER_CUBIC`) sebelum ekstraksi karena metode membaca grid blok 8×8. Di halaman Detect, ukuran asli dapat diisi secara manual.
- Crop dengan offset sembarang dan rotasi **tidak** ditangani (lihat bagian Keterbatasan).

## 16. Dataset

`test_data/original/` berisi lima citra PNG 512×512 (`image01.png` … `image05.png`) bertema lanskap, potret, objek, warna, dan dokumen. Citra ini **sintetis**, dibuat secara deterministik oleh `watermark/synthetic.py`, agar repositori tidak membawa foto berhak cipta.

Untuk laporan akhir, **ganti dengan foto milik Anda sendiri** (PNG/JPG, minimal 5 citra, disarankan 512×512 atau lebih):

```bash
# opsi A: salin foto Anda ke test_data/original/ sebagai image01.png ... image05.png
# opsi B: buat ulang dataset sintetis
python scripts/generate_test_dataset.py --force
```

Uji tambahan pada foto nyata (`grace_hopper.jpg` bawaan Matplotlib, 512×600) menghasilkan PSNR 39,4 dB dan seluruh 9 kondisi uji berstatus SUCCESS dengan NC = 1,0 dan BER = 0,0.

## 17. Evaluasi Dataset dan Laporan

```bash
export WATERMARK_SECRET_KEY="isi-kunci-anda"     # atau lewati; skrip akan meminta lewat prompt
python scripts/run_evaluation.py
python scripts/generate_report.py                # bangun ulang XLSX/grafik dari hasil terakhir
```

Keluaran di `outputs/`:

- `reports/watermark_testing.xlsx` (sheet: Summary, DCT Results, LSB Results, Attack Results, Dataset)
- `reports/watermark_testing.csv` dan `reports/last_evaluation.json`
- `charts/attack_vs_psnr.png`, `attack_vs_nc.png`, `attack_vs_ber.png`, `attack_vs_success.png`

Secret key tidak pernah ditulis ke keluaran mana pun.

## 18. Hasil Pengujian (dataset sintetis 5 citra, teks "KAMAL FADHILRAHMAN")

Rata-rata seluruh citra. PSNR = citra asli vs citra setelah serangan. Data ini berasal dari `scripts/run_evaluation.py` dan akan berbeda jika dataset diganti.

| Serangan | DCT PSNR | DCT NC | DCT BER | DCT | LSB PSNR | LSB NC | LSB BER | LSB |
|---|---|---|---|---|---|---|---|---|
| Tanpa serangan | 40,56 | 1,0000 | 0,0000 | 5/5 | 86,64 | 1,0000 | 0,0000 | 5/5 |
| JPEG 90 | 35,58 | 1,0000 | 0,0000 | 5/5 | 37,30 | 0,4234 | 0,4946 | 0/5 |
| JPEG 70 | 34,07 | 1,0000 | 0,0000 | 5/5 | 35,73 | 0,4230 | 0,4991 | 0/5 |
| JPEG 50 | 33,34 | 1,0000 | 0,0000 | 5/5 | 34,46 | 0,4451 | 0,4991 | 0/5 |
| Crop 10% | 40,45 | 1,0000 | 0,0000 | 5/5 | 86,52 | 0,9014 | 0,0670 | 0/5 |
| Resize 75% | 35,75 | 1,0000 | 0,0000 | 5/5 | 36,69 | 0,4465 | 0,4848 | 0/5 |
| Noise σ=5 | 33,22 | 1,0000 | 0,0000 | 5/5 | 34,13 | 0,4597 | 0,4902 | 0/5 |
| Brightness +20 | 22,32 | 0,9988 | 0,0009 | 4/5 | 22,35 | 0,9362 | 0,0759 | 3/5 |
| Contrast +20% | 26,33 | 0,9913 | 0,0063 | 4/5 | 26,52 | 0,4219 | 0,4893 | 0/5 |

Yang dapat dibaca dari tabel:

- DCT lolos 5/5 pada JPEG 90/70/50, crop, resize, dan noise σ=5. Pada brightness dan contrast satu dari lima citra gagal dengan BER sangat kecil (di bawah 0,01 rata-rata).
- LSB sempurna tanpa serangan dan PSNR-nya jauh lebih tinggi (86,64 dB vs 40,56 dB), tetapi gagal pada semua serangan berbasis pemrosesan ulang. Ini trade-off imperceptibility vs robustness.
- Pada LSB, BER mendekati 0,5 dan NC sekitar 0,42–0,46 berarti hasil ekstraksi setara tebakan acak.
- LSB berstatus FAIL pada crop walau BER-nya kecil (0,067), karena satu bit salah sudah membuat CRC gagal. Contoh mengapa status memakai CRC, bukan hanya BER.
- Di brightness +20, LSB "lolos" 3/5 secara kebetulan: menambah nilai genap tidak mengubah LSB kecuali ada clipping. Hasil ini tidak menunjukkan ketahanan.

## 19. Unit Test

```bash
pytest -v
```

141 pengujian, sekitar 15–35 detik tergantung mesin:

| Berkas | Jumlah | Cakupan |
|---|---|---|
| `test_dct.py` | 17 | embed, ekstraksi blind, key salah, DC tidak berubah, kapasitas, UTF-8 |
| `test_lsb.py` | 9 | embed, key salah, kerapuhan terhadap JPEG/noise, perbandingan dengan DCT |
| `test_metrics.py` | 13 | PSNR, NC, BER, MSE dibandingkan dengan rumus manual |
| `test_payload.py` | 6 | header, CRC32, batas panjang |
| `test_attacks.py` | 14 | tiap serangan, attack engine, file hasil serangan berbeda semua |
| `test_report.py` | 8 | ringkasan, grafik PNG, XLSX, JSON, kunci tidak bocor |
| `test_security.py` | 44 | determinisme key, upload, path traversal, halaman error, kebocoran secret |
| `test_web.py` | 19 | alur embed → detect → attack → comparison lewat Flask test client |
| `test_synthetic.py` | 11 | pembuat citra sintetis: semua jenis valid, uint8, deterministik |

Kunci di berkas test adalah kunci uji (dummy), bukan secret asli.

## 20. Keamanan

- Tidak ada secret yang di-hardcode; `FLASK_SECRET_KEY` dibaca dari environment atau dibuat acak.
- Upload dibatasi ekstensi (png/jpg/jpeg), ukuran (8 MB), tanda tangan file (PNG/JPEG), verifikasi Pillow, dan batas jumlah piksel terhadap decompression bomb.
- Nama file pengguna tidak dipakai di disk; file disimpan dengan ID acak 12 karakter heksadesimal.
- Route `/files/...` memakai daftar kategori yang diizinkan, cek ekstensi, dan `send_from_directory`. ID job/run divalidasi regex. Semua percobaan path traversal menghasilkan 404.
- Halaman error ramah pengguna; traceback hanya dicatat di server dan tidak pernah dikirim ke browser (kecuali mode debug).
- Berkas sementara dibersihkan otomatis berdasarkan umur.
- `.env`, `.venv`, dan isi `uploads/` serta `outputs/` masuk `.gitignore`.

## 21. Keterbatasan

- Ukuran asli dan posisi crop harus diketahui detektor untuk pemulihan crop/resize. Crop dengan offset sembarang dan rotasi tidak didukung.
- Pada percobaan penyapuan kekuatan, JPEG kualitas ≤ 30 dan noise σ = 10 masih merusak watermark DCT pada `S = 24`. Spesifikasi hanya meminta JPEG 90/70/50.
- Kapasitas bergantung ukuran citra karena payload diulang minimal 5 kali. Untuk citra persegi (dalam byte teks UTF-8, batas aplikasi 64 byte):

  | Sisi citra | 192 | 256 | 320 | 384 | 448 | 512 ke atas |
  |---|---|---|---|---|---|---|
  | Kapasitas | 0 | 2 | 16 | 34 | 55 | 64 |

  Teks bawaan "KAMAL FADHILRAHMAN" (18 byte) membutuhkan citra sekitar 340 px atau lebih. Aplikasi menampilkan pesan kapasitas jika teks terlalu panjang.
- PSNR DCT (sekitar 40 dB) lebih rendah daripada LSB. Menaikkan kekuatan menambah ketahanan tetapi menurunkan PSNR.
- Hasil pada dataset sintetis tidak otomatis berlaku untuk foto nyata; ujilah dengan foto Anda sendiri.
- Server bawaan Flask hanya untuk pengembangan dan demo lokal.

## 22. Troubleshooting

| Masalah | Solusi |
|---|---|
| `ModuleNotFoundError` | Pastikan venv aktif (`source .venv/bin/activate`) lalu `pip install -r requirements.txt`. |
| `Address already in use` (port 5000) | Di macOS, AirPlay Receiver memakai port 5000. Matikan di System Preferences → Sharing, atau jalankan `flask --app app run --port 5001`. |
| "Citra terlalu kecil" / "melebihi kapasitas" | Sisi terpendek minimal 128 px, dan teks panjang butuh citra lebih besar (lihat tabel kapasitas di bagian Keterbatasan). Perpendek teks atau pakai citra ≥ 512 px. |
| "Watermark tidak valid atau secret key salah" | Key harus sama persis (huruf besar/kecil dan spasi ikut dihitung). Pastikan file yang dideteksi adalah PNG hasil embed, bukan hasil screenshot. |
| Watermark hilang setelah dikirim lewat aplikasi chat | Aplikasi tersebut mengompres ulang dan mengubah ukuran; itu termasuk serangan. |
| `pytest` tidak menemukan modul `watermark` | Jalankan dari folder utama proyek (ada `pytest.ini` yang mengatur `pythonpath`). |

## 23. Referensi dan Anggota Tim

**Referensi yang disarankan** (lengkapi sesuai yang benar-benar Anda baca):

- Cox, I. J., Miller, M. L., Bloom, J. A., Fridrich, J., Kalker, T. *Digital Watermarking and Steganography*. Morgan Kaufmann.
- Dokumentasi OpenCV: `cv2.dct`, `cv2.idct`.
- Dokumentasi Flask dan OWASP File Upload Cheat Sheet.

**Identitas (isi sendiri sebelum dikumpulkan):**

- Nama: `________________`
- NPM: `________________`
- Kelompok / anggota: `________________`
- Dosen pengampu: `________________`

Proyek akademik. Pastikan hanya memakai citra yang Anda berhak gunakan.
