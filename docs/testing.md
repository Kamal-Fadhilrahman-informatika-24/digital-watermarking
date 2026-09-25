# Pengujian

## Menjalankan

```bash
source .venv/bin/activate
pytest -v                       # 141 pengujian, sekitar 15–35 detik
pytest tests/test_dct.py -v     # satu berkas saja
pytest -k "wrong_key"           # berdasarkan nama
```

`pytest.ini` mengatur `pythonpath = .`, jadi jalankan dari folder utama proyek.

## Prinsip

- Tidak ada mock untuk algoritma. Test membuat citra nyata, menyisipkan, menyerang, lalu mengekstraksi.
- Metrik dibandingkan dengan **rumus yang dihitung manual** (misalnya PSNR untuk selisih tetap 1, 5, 10).
- Test web memakai folder sementara (`tmp_path`), sehingga tidak menyentuh `uploads/` dan `outputs/` asli.
- Kunci di test adalah kunci uji, bukan secret asli.

## Cakupan

| Berkas | Yang dibuktikan |
|---|---|
| `test_dct.py` | Piksel benar-benar berubah; PSNR > 35 dB; koefisien DC tidak berubah tetapi mid-frequency berubah; ekstraksi mengembalikan teks persis dengan BER 0 dan NC 1; fungsi ekstraksi tidak menerima citra asli (blind); key salah gagal; citra tanpa watermark tidak terdeteksi; deterministik untuk key sama; pola berbeda untuk key berbeda; UTF-8; citra kecil → `CapacityError`; input tidak dimodifikasi di tempat. |
| `test_lsb.py` | Perubahan maksimum 1 tingkat piksel; key salah gagal; rapuh terhadap JPEG 90/70/50 dan noise; DCT bertahan pada serangan yang mematahkan LSB pada citra yang sama. |
| `test_metrics.py` | MSE/PSNR/NC/BER sesuai rumus; PSNR tak hingga bila identik; NC turun saat bit dibalik; bit yang hilang dihitung sebagai error. |
| `test_payload.py` | Round-trip; header rusak ditolak; satu bit salah pada body tertangkap CRC32; batas panjang. |
| `test_attacks.py` | JPEG benar-benar berkas JPEG dengan ukuran menurun menurut kualitas; crop selaras grid 8; statistik noise ≈ σ; brightness/contrast sesuai rumus; 9 file serangan berbeda (hash); PSNR di baris hasil sama dengan hitungan ulang dari file; DCT lolos serangan wajib; LSB gagal. |
| `test_report.py` | Evaluasi dataset (baris = citra × metode × serangan); grafik PNG asli; XLSX 5 sheet; JSON dengan PSNR tak hingga; secret key tidak ada di hasil. |
| `test_security.py` | Determinisme key; tidak ada secret di source; `.gitignore` dan `.env.example`; upload palsu/rusak/kosong/terlalu besar/ekstensi salah; path traversal → 404; halaman error tanpa traceback; secret tidak bocor ke halaman, log, JSON, XLSX; field secret bertipe password. |
| `test_synthetic.py` | Setiap jenis citra sintetis valid (uint8), deterministik per seed, dan tidak datar. |
| `test_web.py` | Semua halaman 200; alur embed → download → detect (key benar/salah) → attack testing (termasuk file serangan di subfolder) → XLSX → comparison. |

## Checklist uji manual sebelum demo

- [ ] `pip install -r requirements.txt` berhasil di venv baru.
- [ ] `python app.py` menampilkan `Running on http://127.0.0.1:5001`.
- [ ] Embed foto sendiri: PSNR tampil, citra asli dan ber-watermark tampil berdampingan.
- [ ] Detect dengan key benar → SUCCESS dan teks tampil; key salah → pesan "Watermark tidak valid atau secret key salah."
- [ ] Attack Testing: 9 baris, pratinjau tiap file berbeda, 4 grafik, XLSX terunduh dan terbuka di Excel/Numbers.
- [ ] Comparison: tabel DCT vs LSB dan temuan tampil.
- [ ] `pytest -v` semua hijau.
- [ ] `python scripts/run_evaluation.py` selesai dan `outputs/reports/watermark_testing.xlsx` terbentuk.
- [ ] Dataset sudah diganti dengan foto sendiri (jika diminta dosen) dan evaluasi dijalankan ulang.

## Hasil acuan (dataset sintetis)

Lihat tabel di README bagian 18. Angka akan berubah jika dataset diganti, jadi jalankan ulang evaluasi sebelum menyalin angka ke laporan.
