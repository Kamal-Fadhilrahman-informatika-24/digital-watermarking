from flask import Flask, render_template, request, send_file
import os
import openpyxl
from watermark.embed import embed_watermark
from watermark.extract import extract_watermark
from watermark.metrics import calculate_psnr, calculate_ber, calculate_nc
from watermark.attacks import attack_jpeg, attack_gaussian_noise

app = Flask(__name__)
UPLOAD_FOLDER = 'test_data/images/'
RESULT_FOLDER = 'test_data/results/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['image']
        watermark_text = request.form['watermark_text'] # Misal: NPM
        secret_key = request.form['secret_key']
        
        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        output_name = 'wm_' + file.filename
        output_path = os.path.join(RESULT_FOLDER, output_name)
        
        # 1. Embed Watermark
        embed_watermark(filepath, watermark_text, secret_key, output_path)
        
        # 2. Hitung PSNR Asli
        psnr_val = calculate_psnr(filepath, output_path)
        
        # 3. Ekstraksi Original untuk bit referensi
        orig_bin = ''.join(format(ord(i), '08b') for i in watermark_text)
        
        # 4. Simulasi Serangan & Pengujian
        attacks_result = []
        
        # Serangan JPEG 90, 70, 50
        for q in [90, 70, 50]:
            atk_path = os.path.join(RESULT_FOLDER, f"jpeg_{q}_{file.filename}")
            attack_jpeg(output_path, atk_path, q)
            ext_text, ext_bin = extract_watermark(atk_path, secret_key, len(watermark_text))
            attacks_result.append({
                'Serangan': f'JPEG Quality {q}',
                'PSNR': calculate_psnr(filepath, atk_path),
                'NC': calculate_nc(orig_bin, ext_bin),
                'BER': calculate_ber(orig_bin, ext_bin)
            })
            
        # Serangan Gaussian Noise
        noise_path = os.path.join(RESULT_FOLDER, f"noise_{file.filename}")
        attack_gaussian_noise(output_path, noise_path)
        ext_text, ext_bin = extract_watermark(noise_path, secret_key, len(watermark_text))
        attacks_result.append({
            'Serangan': 'Gaussian Noise',
            'PSNR': calculate_psnr(filepath, noise_path),
            'NC': calculate_nc(orig_bin, ext_bin),
            'BER': calculate_ber(orig_bin, ext_bin)
        })

        # Simpan ke Excel XLSX menggunakan openpyxl (Tanpa Pandas)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Hasil Pengujian"
        ws.append(['Jenis Serangan', 'PSNR (dB)', 'Normalized Correlation (NC)', 'Bit Error Rate (BER)'])
        for row in attacks_result:
            ws.append([row['Serangan'], row['PSNR'], row['NC'], row['BER']])
        
        excel_path = os.path.join(RESULT_FOLDER, 'hasil_pengujian.xlsx')
        wb.save(excel_path)
        
        return render_template('result.html', psnr=psnr_val, image=output_name, table=attacks_result)
        
    return render_template('index.html')

@app.route('/download-excel')
def download_excel():
    return send_file(os.path.join(RESULT_FOLDER, 'hasil_pengujian.xlsx'), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)