"""
database.py — Inisialisasi database dan helper koneksi SQLite
Sistem Manajemen Laundry
"""

import sqlite3
import os

# Lokasi file database SQLite — disimpan di folder proyek
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH   = os.path.join(_BASE_DIR, 'laundry.db')


def get_db_connection():
    """Buka koneksi ke database dan return objek Row agar hasil bisa diakses seperti dict."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # aktifkan foreign key constraint
    return conn


def init_db():
    """
    Buat tabel jika belum ada, lalu isi data awal (seed).
    Dipanggil sekali saat aplikasi pertama dijalankan.
    """
    conn = get_db_connection()
    cur  = conn.cursor()

    # --- Tabel pelanggan ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pelanggan (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            nama       TEXT    NOT NULL,
            no_hp      TEXT    NOT NULL UNIQUE,
            alamat     TEXT,
            created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # --- Tabel layanan (master data 4 jenis) ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS layanan (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_layanan  TEXT    NOT NULL UNIQUE,
            tarif_per_kg  INTEGER NOT NULL CHECK(tarif_per_kg > 0)
        )
    ''')

    # --- Tabel transaksi ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS transaksi (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            kode_transaksi     TEXT    NOT NULL UNIQUE,
            pelanggan_id       INTEGER NOT NULL,
            layanan_id         INTEGER NOT NULL,
            berat_kg           REAL    NOT NULL CHECK(berat_kg >= 0.5 AND berat_kg <= 50),
            total_harga        INTEGER NOT NULL,
            status_pengerjaan  TEXT    NOT NULL DEFAULT 'Diterima'
                               CHECK(status_pengerjaan IN ('Diterima','Diproses','Selesai','Diambil')),
            status_pembayaran  TEXT    NOT NULL DEFAULT 'Belum Lunas'
                               CHECK(status_pembayaran IN ('Belum Lunas','Lunas')),
            tanggal_masuk      TEXT    NOT NULL,
            catatan            TEXT,
            created_at         TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pelanggan_id) REFERENCES pelanggan(id) ON DELETE RESTRICT,
            FOREIGN KEY (layanan_id)   REFERENCES layanan(id)   ON DELETE RESTRICT
        )
    ''')

    # --- Seed: 4 Layanan ---
    layanan_seed = [
        ('Cuci Kering Lipat', 6000),
        ('Cuci + Setrika',    8000),
        ('Setrika Saja',      5000),
        ('Dry Cleaning',     15000),
    ]
    for nama, tarif in layanan_seed:
        cur.execute(
            'INSERT OR IGNORE INTO layanan (nama_layanan, tarif_per_kg) VALUES (?, ?)',
            (nama, tarif)
        )

    conn.commit()
    conn.close()


def seed_contoh():
    """
    Tambahkan 5 pelanggan contoh dan 8 transaksi contoh untuk kemudahan pengujian.
    Fungsi ini AMAN dipanggil berulang kali — hanya menambah jika belum ada.
    
    Untuk menonaktifkan seed, komentari baris seed_contoh() di app.py.
    """
    conn = get_db_connection()
    cur  = conn.cursor()

    # Cek apakah sudah ada data
    if cur.execute('SELECT COUNT(*) FROM pelanggan').fetchone()[0] > 0:
        conn.close()
        return  # sudah ada data, lewati

    # --- 5 Pelanggan Contoh ---
    pelanggan_data = [
        ('Budi Santoso',   '081234567890', 'Jl. Merdeka No. 10, Jakarta'),
        ('Ani Rahayu',     '082345678901', 'Jl. Sudirman No. 5, Bandung'),
        ('Chandra Wijaya', '083456789012', 'Jl. Gatot Subroto No. 3, Surabaya'),
        ('Dewi Lestari',   '084567890123', 'Jl. Diponegoro No. 7, Yogyakarta'),
        ('Eko Prasetyo',   '085678901234', 'Jl. Ahmad Yani No. 15, Semarang'),
    ]
    cur.executemany(
        'INSERT OR IGNORE INTO pelanggan (nama, no_hp, alamat) VALUES (?, ?, ?)',
        pelanggan_data
    )

    # Ambil ID pelanggan yang baru dibuat
    p = {row['nama']: row['id']
         for row in cur.execute('SELECT id, nama FROM pelanggan').fetchall()}

    # Ambil ID layanan
    l = {row['nama_layanan']: row['id']
         for row in cur.execute('SELECT id, nama_layanan FROM layanan').fetchall()}

    # --- 8 Transaksi Contoh dengan berbagai status ---
    # Format: (kode, pelanggan_id, layanan_id, berat, total, status_pengerjaan, status_pembayaran, tgl_masuk, catatan)
    transaksi_data = [
        ('TRX-0001', p['Budi Santoso'],   l['Cuci + Setrika'],    3.5, 3.5 * 8000,  'Diambil',  'Lunas',       '2026-11-01', 'Pakaian kantor'),
        ('TRX-0002', p['Ani Rahayu'],     l['Dry Cleaning'],      2.0, 2.0 * 15000, 'Selesai',  'Lunas',       '2026-11-02', 'Jas dan blazer'),
        ('TRX-0003', p['Chandra Wijaya'], l['Cuci Kering Lipat'], 5.0, 5.0 * 6000,  'Selesai',  'Belum Lunas', '2026-11-03', None),
        ('TRX-0004', p['Dewi Lestari'],   l['Setrika Saja'],      1.5, 1.5 * 5000,  'Diproses', 'Belum Lunas', '2026-11-04', 'Tolong rapi'),
        ('TRX-0005', p['Eko Prasetyo'],   l['Cuci + Setrika'],    4.0, 4.0 * 8000,  'Diproses', 'Lunas',       '2026-11-05', None),
        ('TRX-0006', p['Budi Santoso'],   l['Cuci Kering Lipat'], 2.5, 2.5 * 6000,  'Diterima', 'Belum Lunas', '2026-11-06', 'Pakaian casual'),
        ('TRX-0007', p['Ani Rahayu'],     l['Setrika Saja'],      3.0, 3.0 * 5000,  'Diterima', 'Belum Lunas', '2026-11-07', None),
        ('TRX-0008', p['Chandra Wijaya'], l['Dry Cleaning'],      1.0, 1.0 * 15000, 'Diterima', 'Belum Lunas', '2026-11-08', 'Jas pengantin'),
    ]
    cur.executemany('''
        INSERT OR IGNORE INTO transaksi
            (kode_transaksi, pelanggan_id, layanan_id, berat_kg, total_harga,
             status_pengerjaan, status_pembayaran, tanggal_masuk, catatan)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', transaksi_data)

    conn.commit()
    conn.close()
    print("[Seed] Data contoh berhasil ditambahkan.")
