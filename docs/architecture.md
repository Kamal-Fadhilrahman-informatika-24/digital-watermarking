# Arsitektur

Aplikasi dibagi menjadi tiga lapis. Lapis inti tidak mengimpor Flask, sehingga dapat diuji dan dipakai dari skrip terminal.

```
Browser ──► routes/ (Flask blueprint) ──► watermark/service.py ──► watermark/ (algoritma, metrik, serangan, laporan)
                │                                   │
            templates/                        Storage (folder uploads/ dan outputs/)
```

## Lapis dan tanggung jawabnya

| Lapis | Berkas | Tugas |
|---|---|---|
| Tampilan | `templates/`, `static/` | HTML/CSS/JS murni, tanpa CDN. |
| Route | `routes/main_routes.py`, `watermark_routes.py`, `testing_routes.py` | Membaca form, memvalidasi input, memanggil `service`, merender halaman. Memakai pola POST-Redirect-GET agar refresh tidak mengirim ulang form. |
| Orkestrasi | `watermark/service.py` | Alur lengkap satu permintaan: decode → validasi → embed → simpan → baca ulang dari disk → verifikasi → hitung metrik → simpan metadata job. `Storage` (dataclass) menampung folder kerja sehingga test dapat memakai folder sementara. |
| Algoritma | `dct_watermark.py`, `lsb_watermark.py`, `payload.py`, `key_utils.py` | Penyisipan dan ekstraksi. |
| Pengujian | `attacks.py`, `attack_engine.py`, `evaluation.py`, `metrics.py`, `report.py` | Serangan, ekstraksi ulang, metrik, grafik, XLSX. |
| Pendukung | `config.py`, `utils.py`, `errors.py`, `results.py`, `methods.py`, `synthetic.py` | Parameter, validasi gambar, exception, dataclass hasil, registri metode, dataset sintetis. |

## Alur satu permintaan Embed

1. `POST /embed` menerima file, teks, secret key, dan metode.
2. `utils.decode_image` memeriksa tanda tangan PNG/JPEG, memverifikasi dengan Pillow, dan membatasi jumlah piksel.
3. Citra terlalu besar diperkecil ke sisi terpanjang 1024 px.
4. Metode dipilih lewat `methods.get_method(key)`.
5. Hasil disimpan sebagai `outputs/watermarked/<job_id>.png`, lalu **dibaca ulang dari disk** dan diekstraksi untuk verifikasi.
6. PSNR dihitung, metadata (tanpa secret key) disimpan sebagai `<job_id>.json`.
7. Browser diarahkan ke `/result/<job_id>`.

## Alur Attack Testing

`attack_engine.run_all_attacks` untuk tiap dari 9 kondisi: terapkan serangan → **tulis file** (JPEG memakai `cv2.imencode` sungguhan) → baca ulang → pulihkan geometri bila crop/resize → ekstraksi → hitung PSNR/NC/BER → tentukan status. Setelah itu `find_duplicate_outputs` memeriksa hash SHA-256 bahwa semua file serangan memang berbeda.

## Penyimpanan

| Folder | Isi | Di-commit? |
|---|---|---|
| `uploads/` | citra asli yang diunggah (nama acak) | tidak |
| `outputs/watermarked/` | citra ber-watermark + JSON metadata | tidak |
| `outputs/attacks/<run_id>/` | 9 file hasil serangan per run | tidak |
| `outputs/charts/`, `outputs/reports/` | grafik PNG, XLSX, CSV, JSON | tidak |
| `test_data/original/` | dataset | ya |

Berkas sementara dibersihkan otomatis berdasarkan umur (`utils.cleanup_old_files`).

## Rute

| Rute | Metode | Fungsi |
|---|---|---|
| `/`, `/about` | GET | halaman statis |
| `/embed` | GET, POST | form dan proses embed |
| `/result/<job_id>`, `/download/<job_id>` | GET | hasil dan unduhan PNG |
| `/detect` | GET, POST | ekstraksi |
| `/testing`, `/testing/run/<run_id>` | GET, POST / GET | attack testing |
| `/comparison`, `/comparison/run` | GET / POST | perbandingan dataset |
| `/report/<name>` | GET | unduh XLSX (nama divalidasi regex) |
| `/files/<category>/<filename>` | GET | penyaji gambar (kategori dibatasi daftar putih) |
