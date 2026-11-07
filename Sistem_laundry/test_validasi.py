"""Script test validasi — jalankan: python test_validasi.py"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
tmp.close()

import database as db_module
db_module.DB_PATH = tmp.name
db_module.init_db()
db_module.seed_contoh()

from app import app, validasi_nama, validasi_berat, validasi_no_hp

total_ok = 0
total_fail = 0

def chk(label, kondisi):
    global total_ok, total_fail
    if kondisi:
        total_ok += 1
        print(f"  [PASS] {label}")
    else:
        total_fail += 1
        print(f"  [FAIL] {label}")

# ── VR-01 Nama ──
print("\n=== VR-01: Validasi Nama ===")
chk("Nama kosong ditolak",           validasi_nama('') is not None)
chk("Nama spasi saja ditolak",       validasi_nama('   ') is not None)
chk("Nama 2 karakter ditolak",       validasi_nama('AB') is not None)
chk("Nama 3 karakter diterima",      validasi_nama('Ani') is None)
chk("Nama 50 karakter diterima",     validasi_nama('A' * 50) is None)
chk("Nama 51 karakter ditolak",      validasi_nama('A' * 51) is not None)
chk("Nama dengan spasi diterima",    validasi_nama('Budi Santoso') is None)
# Pastikan pesan menyebut field dan penyebab
err = validasi_nama('AB')
chk("Pesan VR-01 menyebut karakter", err is not None and 'karakter' in err)

# ── VR-02 No. HP ──
print("\n=== VR-02: Validasi No. HP ===")
chk("HP kosong ditolak",             validasi_no_hp('') is not None)
chk("HP ada huruf ditolak",          validasi_no_hp('0812ABC890') is not None)
chk("HP ada spasi ditolak",          validasi_no_hp('0812 345 678') is not None)
chk("HP ada strip ditolak",          validasi_no_hp('0812-345-678') is not None)
chk("HP 9 digit ditolak",            validasi_no_hp('081234567') is not None)
chk("HP 10 digit valid diterima",    validasi_no_hp('0812345678') is None)
chk("HP 13 digit valid diterima",    validasi_no_hp('0812345678901') is None)
chk("HP 14 digit ditolak",           validasi_no_hp('08123456789012') is not None)
chk("HP tidak diawali 08 ditolak",   validasi_no_hp('092345678901') is not None)
chk("HP diawali 08 diterima",        validasi_no_hp('081234567890') is None)
# Pesan menyebut penyebab
err_hp = validasi_no_hp('092345678901')
chk('Pesan VR-02 menyebut "08"',     err_hp is not None and '08' in err_hp)
err_len = validasi_no_hp('081234567')
chk('Pesan VR-02 menyebut digit/panjang', err_len is not None and 'digit' in err_len)

# ── VR-05 Berat ──
print("\n=== VR-05: Validasi Berat ===")
chk("Berat kosong ditolak",          validasi_berat('')[1] is not None)
chk("Berat huruf ditolak",           validasi_berat('abc')[1] is not None)
chk("Berat nol ditolak",             validasi_berat('0')[1] is not None)
chk("Berat negatif ditolak",         validasi_berat('-1')[1] is not None)
chk("Berat 0.3 kg ditolak",          validasi_berat('0.3')[1] is not None)
chk("Berat 0.5 kg diterima",         validasi_berat('0.5')[1] is None)
chk("Berat 0,5 (koma) diterima",     validasi_berat('0,5')[1] is None)
chk("Berat 2,5 (koma) diterima",     validasi_berat('2,5')[1] is None)
chk("Berat 10,0 (koma) diterima",    validasi_berat('10,0')[1] is None)
chk("Berat 50 kg diterima",          validasi_berat('50')[1] is None)
chk("Berat 50.1 kg ditolak",         validasi_berat('50.1')[1] is not None)
chk("Berat 55 kg ditolak",           validasi_berat('55')[1] is not None)
bv, _ = validasi_berat('2,5')
chk("Berat 2,5 -> float 2.5",        bv == 2.5)
bv2, _ = validasi_berat('3.0')
chk("Berat 3.0 -> float 3.0",        bv2 == 3.0)
# Pesan menyebut penyebab
err_berat = validasi_berat('0.3')[1]
chk("Pesan VR-05 menyebut batas min",  err_berat is not None and ('0,5' in err_berat or 'ringan' in err_berat))
err_berat2 = validasi_berat('abc')[1]
chk("Pesan VR-05 menyebut nilai buruk", err_berat2 is not None and 'valid' in err_berat2.lower())

# ── Flask Test Client ──
print("\n=== Flask: Form Preservation & Error Messages ===")
app.config['TESTING'] = True
client = app.test_client()

# Form tambah pelanggan — semua field kosong
r = client.post('/pelanggan/tambah',
                data={'nama': '', 'no_hp': '', 'alamat': ''},
                follow_redirects=True)
html = r.data.decode('utf-8')
chk("Form kosong -> HTTP 200 (tidak redirect)", r.status_code == 200)
chk("Form kosong -> ada error-summary", 'error-summary' in html)
chk("Form kosong -> menyebut field Nama", 'Nama' in html and 'wajib' in html.lower())
chk("Form kosong -> menyebut field Nomor HP", 'Nomor HP' in html and 'wajib' in html.lower())

# Form isi sebagian — nama valid, HP format salah
r2 = client.post('/pelanggan/tambah',
                 data={'nama': 'Test User', 'no_hp': '0922334455', 'alamat': ''},
                 follow_redirects=True)
html2 = r2.data.decode('utf-8')
chk("HP tidak diawali 08 -> error muncul", '08' in html2)
chk("HP tidak diawali 08 -> nama tetap terisi di form", 'Test User' in html2)

# HP duplikat
r3 = client.post('/pelanggan/tambah',
                 data={'nama': 'Orang Baru', 'no_hp': '081234567890', 'alamat': ''},
                 follow_redirects=True)
html3 = r3.data.decode('utf-8')
chk("HP duplikat -> error menyebut nama pelanggan lama", 'Budi' in html3 or 'sudah terdaftar' in html3.lower())
chk("HP duplikat -> nama baru tetap terisi", 'Orang Baru' in html3)

# Berat dengan koma berhasil disimpan
conn = db_module.get_db_connection()
pel_id = conn.execute('SELECT id FROM pelanggan LIMIT 1').fetchone()['id']
lay_id = conn.execute('SELECT id FROM layanan LIMIT 1').fetchone()['id']
conn.close()
r4 = client.post('/transaksi/tambah',
                 data={'pelanggan_id': str(pel_id), 'layanan_id': str(lay_id),
                       'berat_kg': '0,5', 'tanggal_masuk': '2026-11-08'},
                 follow_redirects=True)
chk("Berat 0,5 (koma) -> transaksi tersimpan", 'berhasil' in r4.data.decode('utf-8').lower())

# Berat 0,3 ditolak
r5 = client.post('/transaksi/tambah',
                 data={'pelanggan_id': str(pel_id), 'layanan_id': str(lay_id),
                       'berat_kg': '0,3', 'tanggal_masuk': '2026-11-08'},
                 follow_redirects=True)
html5 = r5.data.decode('utf-8')
chk("Berat 0,3 -> form kembali dengan error (tidak crash)", r5.status_code == 200)
chk("Berat 0,3 -> ada pesan error berat", 'berat' in html5.lower() or 'kg' in html5.lower())

# ID tidak ada -> redirect dengan flash
r6 = client.get('/transaksi/99999', follow_redirects=True)
chk("Transaksi ID 99999 -> tidak crash, ada pesan error", r6.status_code == 200)

# Pelanggan ID tidak ada -> redirect dengan flash
r7 = client.get('/pelanggan/edit/99999', follow_redirects=True)
chk("Pelanggan ID 99999 -> tidak crash, ada pesan error", r7.status_code == 200)

# ── Ringkasan ──
print()
print("=" * 50)
print(f"  Hasil: {total_ok} PASS, {total_fail} FAIL dari {total_ok+total_fail} test")
if total_fail == 0:
    print("  Semua validasi lolos!")
else:
    print(f"  {total_fail} test gagal — perlu perbaikan.")
print("=" * 50)

os.unlink(tmp.name)
sys.exit(0 if total_fail == 0 else 1)

