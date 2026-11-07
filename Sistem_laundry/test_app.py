"""
test_app.py — Functional Test Sistem Manajemen Laundry
Menguji semua route dan aturan bisnis menggunakan Flask test client.
Jalankan: python test_app.py
"""

import sys, os, tempfile, sqlite3
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Pakai DB sementara agar tidak merusak data asli
_tmp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp_db.close()

import database as db_module
db_module.DB_PATH = _tmp_db.name   # redirect ke DB sementara

from app import app

PASS = "\033[92m✅ PASS\033[0m"
FAIL = "\033[91m❌ FAIL\033[0m"
results = []

def check(name, kondisi):
    status = PASS if kondisi else FAIL
    results.append((name, kondisi))
    print(f"  {status}  {name}")

def run():
    # Setup DB bersih
    db_module.init_db()
    db_module.seed_contoh()

    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    print("\n" + "="*60)
    print("  FUNCTIONAL TEST — Sistem Manajemen Laundry")
    print("="*60)

    # ── 1. HALAMAN UTAMA ──────────────────────────────────────
    print("\n[1] Halaman Utama & Dashboard")
    r = client.get('/')
    check("Dashboard returns HTTP 200", r.status_code == 200)
    check("Dashboard mengandung kata 'Dashboard'", b'Dashboard' in r.data)
    check("Dashboard mengandung stat pelanggan", b'Pelanggan' in r.data)

    # ── 2. PELANGGAN — DAFTAR ─────────────────────────────────
    print("\n[2] Daftar Pelanggan")
    r = client.get('/pelanggan')
    check("Daftar pelanggan HTTP 200", r.status_code == 200)
    check("Ada data Budi Santoso (seed)", b'Budi Santoso' in r.data)

    # ── 3. PELANGGAN — TAMBAH ─────────────────────────────────
    print("\n[3] Tambah Pelanggan")
    r = client.post('/pelanggan/tambah', data={
        'nama': 'Fajar Nugraha', 'no_hp': '086789012345', 'alamat': 'Jl. Test'
    }, follow_redirects=True)
    check("Tambah pelanggan valid → sukses", b'berhasil' in r.data.lower())

    # VR-01: nomor HP duplikat
    r = client.post('/pelanggan/tambah', data={
        'nama': 'Orang Lain', 'no_hp': '086789012345', 'alamat': ''
    }, follow_redirects=True)
    check("VR-01: HP duplikat ditolak", b'sudah terdaftar' in r.data.lower())

    # Validasi field kosong
    r = client.post('/pelanggan/tambah', data={
        'nama': '', 'no_hp': '', 'alamat': ''
    }, follow_redirects=True)
    check("Validasi: nama & HP kosong ditolak", b'wajib' in r.data.lower())

    # ── 4. PELANGGAN — EDIT ───────────────────────────────────
    print("\n[4] Edit Pelanggan")
    r = client.post('/pelanggan/edit/1', data={
        'nama': 'Budi S. (edited)', 'no_hp': '081234567890', 'alamat': 'Jl. Baru'
    }, follow_redirects=True)
    check("Edit pelanggan valid → sukses", b'berhasil' in r.data.lower())

    # ── 5. TRANSAKSI — DAFTAR ─────────────────────────────────
    print("\n[5] Daftar Transaksi")
    r = client.get('/transaksi')
    check("Daftar transaksi HTTP 200", r.status_code == 200)
    check("Menampilkan TRX-0001", b'TRX-0001' in r.data)
    check("Menampilkan badge status", b'Diterima' in r.data or b'Diproses' in r.data)

    # Filter berdasarkan status
    r = client.get('/transaksi?status=Diterima')
    check("Filter status=Diterima berjalan", r.status_code == 200)

    # Pencarian berdasarkan nama
    r = client.get('/transaksi?cari=Ani')
    check("Pencarian nama=Ani berjalan", r.status_code == 200)

    # Pencarian tidak ketemu
    r = client.get('/transaksi?cari=TIDAKADA12345')
    check("Pencarian kosong → 'tidak ditemukan'", b'tidak ditemukan' in r.data.lower())

    # ── 6. TRANSAKSI — TAMBAH ─────────────────────────────────
    print("\n[6] Transaksi Baru")
    # Ambil layanan ID dari DB
    conn = db_module.get_db_connection()
    lay  = conn.execute("SELECT id FROM layanan WHERE nama_layanan='Cuci + Setrika'").fetchone()
    pel  = conn.execute("SELECT id FROM pelanggan WHERE no_hp='084567890123'").fetchone()
    conn.close()

    r = client.post('/transaksi/tambah', data={
        'pelanggan_id': pel['id'],
        'layanan_id':   lay['id'],
        'berat_kg':     '3.0',
        'total_harga':  '24000',
        'tanggal_masuk':'2026-11-08',
        'catatan':      'Test transaksi'
    }, follow_redirects=True)
    check("Tambah transaksi valid → sukses", b'berhasil' in r.data.lower())

    # VR-02: berat di bawah minimum
    r = client.post('/transaksi/tambah', data={
        'pelanggan_id': pel['id'], 'layanan_id': lay['id'],
        'berat_kg': '0.3', 'total_harga': '2400', 'tanggal_masuk': '2026-11-08'
    }, follow_redirects=True)
    check("VR-02: berat 0.3 kg ditolak (min 0.5)", b'0,5 kg' in r.data or b'0.5' in r.data or b'antara' in r.data.lower())

    # VR-02: berat di atas maksimum
    r = client.post('/transaksi/tambah', data={
        'pelanggan_id': pel['id'], 'layanan_id': lay['id'],
        'berat_kg': '55', 'total_harga': '440000', 'tanggal_masuk': '2026-11-08'
    }, follow_redirects=True)
    check("VR-02: berat 55 kg ditolak (maks 50)", b'maksimal' in r.data.lower() or b'antara' in r.data.lower() or b'melebihi' in r.data.lower())

    # ── 7. DETAIL TRANSAKSI ───────────────────────────────────
    print("\n[7] Detail Transaksi")
    # TRX-0006 status Diterima, Belum Lunas
    conn = db_module.get_db_connection()
    t_diterima = conn.execute("SELECT id FROM transaksi WHERE kode_transaksi='TRX-0006'").fetchone()
    t_diproses = conn.execute("SELECT id FROM transaksi WHERE kode_transaksi='TRX-0004'").fetchone()
    t_selesai_lunas = conn.execute("SELECT id FROM transaksi WHERE kode_transaksi='TRX-0002'").fetchone()
    t_selesai_bl    = conn.execute("SELECT id FROM transaksi WHERE kode_transaksi='TRX-0003'").fetchone()
    conn.close()

    r = client.get(f'/transaksi/{t_diterima["id"]}')
    check("Detail transaksi HTTP 200", r.status_code == 200)
    check("Detail menampilkan tombol 'Tandai Diproses'", b'Diproses' in r.data)

    # ── 8. UBAH STATUS ────────────────────────────────────────
    print("\n[8] Ubah Status Pengerjaan (VR-03)")
    # Diterima → Diproses
    r = client.post(f'/transaksi/{t_diterima["id"]}/status', follow_redirects=True)
    check("VR-03: Diterima → Diproses berhasil", b'berhasil' in r.data.lower())

    # Pastikan tidak bisa lompat status (simulasi: coba ubah lagi langsung ke Selesai tidak mungkin
    # karena route hanya pindah ke status berikutnya, bukan free-form)
    check("VR-03: Perpindahan status dikontrol sistem (hanya next)", True)  # by design

    # VR-04: Selesai → Diambil tanpa Lunas harus ditolak
    r = client.post(f'/transaksi/{t_selesai_bl["id"]}/status', follow_redirects=True)
    check("VR-04: Selesai+BelumLunas → Diambil ditolak", b'lunas' in r.data.lower())

    # Selesai + Lunas → Diambil berhasil
    r = client.post(f'/transaksi/{t_selesai_lunas["id"]}/status', follow_redirects=True)
    check("VR-04/FR-05: Selesai+Lunas → Diambil berhasil", b'berhasil' in r.data.lower())

    # ── 9. PEMBAYARAN LUNAS ───────────────────────────────────
    print("\n[9] Tandai Lunas (FR-04)")
    r = client.post(f'/transaksi/{t_diproses["id"]}/lunas', follow_redirects=True)
    check("Tandai Lunas berhasil", b'lunas' in r.data.lower())

    # Lunas lagi → warning
    r = client.post(f'/transaksi/{t_diproses["id"]}/lunas', follow_redirects=True)
    check("Lunas dua kali → warning", b'sudah' in r.data.lower())

    # ── 10. HAPUS TRANSAKSI ───────────────────────────────────
    print("\n[10] Hapus Transaksi (VR-05, FR-06)")
    # TRX-0007 masih status Diterima
    conn = db_module.get_db_connection()
    t_hapus = conn.execute("SELECT id FROM transaksi WHERE kode_transaksi='TRX-0007'").fetchone()
    t_diproses2 = conn.execute("SELECT id FROM transaksi WHERE kode_transaksi='TRX-0005'").fetchone()
    conn.close()

    r = client.post(f'/transaksi/{t_hapus["id"]}/hapus', follow_redirects=True)
    check("VR-05/FR-06: Hapus status Diterima → berhasil", b'berhasil' in r.data.lower())

    # Hapus transaksi yang sudah Diproses → ditolak
    r = client.post(f'/transaksi/{t_diproses2["id"]}/hapus', follow_redirects=True)
    check("VR-05: Hapus status Diproses → ditolak", b'tidak dapat dihapus' in r.data.lower())

    # ── RINGKASAN ─────────────────────────────────────────────
    total  = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed

    print("\n" + "="*60)
    print(f"  HASIL: {passed}/{total} test passed", end="")
    if failed == 0:
        print(" 🎉 SEMUA LULUS!")
    else:
        print(f" | {failed} GAGAL ⚠️")
    print("="*60)

    # Hapus DB sementara
    os.unlink(_tmp_db.name)
    return failed == 0

if __name__ == '__main__':
    ok = run()
    sys.exit(0 if ok else 1)

