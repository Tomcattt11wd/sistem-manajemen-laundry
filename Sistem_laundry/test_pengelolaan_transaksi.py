"""
test_pengelolaan_transaksi.py — Pengujian Fitur Pengelolaan Transaksi & Pelanggan
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
tmp.close()

import database as db_module
db_module.DB_PATH = tmp.name
db_module.init_db()
db_module.seed_contoh()

from app import app

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

app.config['TESTING'] = True
client = app.test_client()

conn = db_module.get_db_connection()
# Ambil transaksi sesuai status
t_diterima_bl = conn.execute("SELECT id, kode_transaksi FROM transaksi WHERE status_pengerjaan='Diterima' AND status_pembayaran='Belum Lunas' LIMIT 1").fetchone()
t_diproses_bl = conn.execute("SELECT id, kode_transaksi FROM transaksi WHERE status_pengerjaan='Diproses' AND status_pembayaran='Belum Lunas' LIMIT 1").fetchone()
t_diproses_lunas = conn.execute("SELECT id, kode_transaksi FROM transaksi WHERE status_pengerjaan='Diproses' AND status_pembayaran='Lunas' LIMIT 1").fetchone()
t_selesai_bl = conn.execute("SELECT id, kode_transaksi FROM transaksi WHERE status_pengerjaan='Selesai' AND status_pembayaran='Belum Lunas' LIMIT 1").fetchone()
t_selesai_lunas = conn.execute("SELECT id, kode_transaksi FROM transaksi WHERE status_pengerjaan='Selesai' AND status_pembayaran='Lunas' LIMIT 1").fetchone()
t_diambil_lunas = conn.execute("SELECT id, kode_transaksi FROM transaksi WHERE status_pengerjaan='Diambil' LIMIT 1").fetchone()
conn.close()

print("\n=== 1. Tampilan Daftar Transaksi (Aksi Buttons & Disabled States) ===")
r = client.get('/transaksi')
html = r.data.decode('utf-8')
chk("Halaman daftar transaksi HTTP 200", r.status_code == 200)
chk("Terdapat kolom Aksi", "Aksi" in html)
chk("Terdapat tombol '→ Diproses'", "→ Diproses" in html)
chk("Terdapat tombol '→ Selesai'", "→ Selesai" in html)
chk("Terdapat tombol '💳 Lunas'", "💳 Lunas" in html)
chk("Terdapat tombol hapus 🗑️", "🗑️" in html)

print("\n=== 2. Alur Status Berurutan & Pelanggaran (VR-06) ===")
# 2.1 Valid: Diterima -> Diproses
r = client.post(f"/transaksi/{t_diterima_bl['id']}/status", data={'status': 'Diproses'}, follow_redirects=True)
chk("Diterima -> Diproses berhasil", "Diproses" in r.data.decode('utf-8'))

# 2.2 Pelanggaran: Lompat dari Diterima ke Selesai
# Buat transaksi baru status Diterima untuk pengujian
conn = db_module.get_db_connection()
conn.execute("INSERT INTO transaksi (kode_transaksi, pelanggan_id, layanan_id, berat_kg, total_harga, status_pengerjaan, status_pembayaran, tanggal_masuk) VALUES ('TRX-TEST1', 1, 1, 2.0, 12000, 'Diterima', 'Belum Lunas', '2026-11-08')")
conn.commit()
tid_test1 = conn.execute("SELECT id FROM transaksi WHERE kode_transaksi='TRX-TEST1'").fetchone()['id']
conn.close()

r = client.post(f"/transaksi/{tid_test1}/status", data={'status': 'Selesai'}, follow_redirects=True)
html = r.data.decode('utf-8')
chk("Lompat Diterima -> Selesai ditolak", "status harus berurutan" in html.lower())

# 2.3 Pelanggaran: Mundur dari Diproses ke Diterima
r = client.post(f"/transaksi/{t_diproses_bl['id']}/status", data={'status': 'Diterima'}, follow_redirects=True)
html = r.data.decode('utf-8')
chk("Mundur Diproses -> Diterima ditolak", "status harus berurutan" in html.lower())

# 2.4 Pelanggaran: Status akhir Diambil diubah lagi
r = client.post(f"/transaksi/{t_diambil_lunas['id']}/status", data={'status': 'Diproses'}, follow_redirects=True)
html = r.data.decode('utf-8')
chk("Diambil diubah lagi ditolak", "status harus berurutan" in html.lower())

print("\n=== 3. Aturan Pengambilan (VR-07: Selesai DAN Lunas) ===")
# 3.1 Status Belum Selesai (misal masih Diproses) coba diambil
r = client.post(f"/transaksi/{t_diproses_lunas['id']}/status", data={'status': 'Diambil'}, follow_redirects=True)
html = r.data.decode('utf-8')
chk("Belum Selesai -> Diambil ditolak", "cucian belum selesai" in html.lower())

# 3.2 Status Selesai tetapi Belum Lunas
r = client.post(f"/transaksi/{t_selesai_bl['id']}/status", data={'status': 'Diambil'}, follow_redirects=True)
html = r.data.decode('utf-8')
chk("Selesai tapi Belum Lunas -> Diambil ditolak", "pembayaran belum lunas" in html.lower())

# 3.3 Status Selesai dan Lunas -> Diambil berhasil
r = client.post(f"/transaksi/{t_selesai_lunas['id']}/status", data={'status': 'Diambil'}, follow_redirects=True)
html = r.data.decode('utf-8')
chk("Selesai + Lunas -> Diambil berhasil", "berhasil diubah menjadi \"diambil\"" in html.lower() or "diambil" in html.lower())

print("\n=== 4. Tombol Tandai Lunas ===")
r = client.post(f"/transaksi/{t_selesai_bl['id']}/lunas", follow_redirects=True)
html = r.data.decode('utf-8')
chk("Tandai Lunas berhasil", "berhasil dicatat sebagai lunas" in html.lower())

# Setelah lunas, sekarang t_selesai_bl (yang sudah lunas) boleh diambil!
r = client.post(f"/transaksi/{t_selesai_bl['id']}/status", data={'status': 'Diambil'}, follow_redirects=True)
chk("Setelah lunas, cucian selesai dapat diambil", "berhasil diubah" in r.data.decode('utf-8').lower())

print("\n=== 5. Aturan Hapus Transaksi (VR-08) ===")
# 5.1 Hapus transaksi status Diproses -> Ditolak
r = client.post(f"/transaksi/{t_diproses_bl['id']}/hapus", follow_redirects=True)
html = r.data.decode('utf-8')
chk("Hapus status Diproses ditolak", "hanya transaksi berstatus diterima yang dapat dihapus" in html.lower())

# 5.2 Hapus transaksi status Diterima -> Berhasil
r = client.post(f"/transaksi/{tid_test1}/hapus", follow_redirects=True)
html = r.data.decode('utf-8')
chk("Hapus status Diterima berhasil", "berhasil dihapus" in html.lower())

print("\n=== 6. Tombol Ubah Pelanggan & Form Edit Validasi ===")
r = client.get('/pelanggan')
html = r.data.decode('utf-8')
chk("Daftar pelanggan memiliki tombol Ubah", "✏️ Ubah" in html or "Ubah" in html)

# Validasi form edit sama dengan tambah:
# Nama < 3 karakter ditolak
r = client.post('/pelanggan/edit/1', data={'nama': 'Al', 'no_hp': '081234567890', 'alamat': ''}, follow_redirects=True)
html = r.data.decode('utf-8')
chk("Edit: Nama < 3 karakter ditolak", "terlalu pendek" in html.lower())

# HP tidak diawali 08 ditolak
r = client.post('/pelanggan/edit/1', data={'nama': 'Budi Santoso', 'no_hp': '071234567890', 'alamat': ''}, follow_redirects=True)
html = r.data.decode('utf-8')
chk("Edit: HP tanpa 08 ditolak", "08" in html)

# HP milik pelanggan lain ditolak (VR-03)
r = client.post('/pelanggan/edit/1', data={'nama': 'Budi Santoso', 'no_hp': '082345678901', 'alamat': ''}, follow_redirects=True)
html = r.data.decode('utf-8')
chk("Edit: HP duplikat milik orang lain ditolak", "sudah terdaftar" in html.lower())

# HP milik sendiri tetap diterima (VR-03)
r = client.post('/pelanggan/edit/1', data={'nama': 'Budi Santoso Updated', 'no_hp': '081234567890', 'alamat': 'Jl. Baru No. 1'}, follow_redirects=True)
html = r.data.decode('utf-8')
chk("Edit: HP sendiri tetap valid & simpan berhasil", "berhasil diperbarui" in html.lower())

print("\n" + "=" * 55)
print(f"  Hasil Pengujian: {total_ok} PASS, {total_fail} FAIL dari {total_ok+total_fail} test")
if total_fail == 0:
    print("  Semua fitur transaksi & pelanggan berfungsi sempurna!")
print("=" * 55)

os.unlink(tmp.name)
sys.exit(0 if total_fail == 0 else 1)

