# 🧺 Sistem Manajemen Laundry

Aplikasi web pencatatan pelanggan, transaksi laundry, dan status pengerjaan.
Dibuat dengan **Python Flask** + **SQLite** (HTML/CSS/JS murni tanpa framework frontend).

---

## 📋 Fitur

- **Dashboard** — Statistik jumlah pelanggan dan transaksi per status
- **Pelanggan** — Tambah, ubah, hapus, dan cari pelanggan
- **Transaksi** — Input transaksi baru dengan kalkulasi harga otomatis
- **Status pengerjaan** — Diterima → Diproses → Selesai → Diambil (berurutan)
- **Status pembayaran** — Belum Lunas / Lunas
- **Filter transaksi** — Berdasarkan status, status bayar, atau nama/ID transaksi
- **Validasi lengkap** — Semua aturan bisnis ditegakkan di backend

---

## 🚀 Cara Instalasi & Menjalankan

### 1. Prasyarat
- Python 3.9 atau lebih baru
- pip (sudah bawaan Python)

### 2. Clone / Unduh Proyek
```bash
# Jika menggunakan Git:
git clone <url-repo>
cd Sistem_laundry

# Atau ekstrak ZIP ke folder Sistem_laundry, lalu masuk ke folder tersebut.
```

### 3. Buat Virtual Environment (disarankan)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependensi
```bash
pip install -r requirements.txt
```

### 5. Jalankan Aplikasi
```bash
python app.py
```

Buka browser dan akses: **http://localhost:5000**

---

## 🌱 Data Contoh (Seed)

Saat pertama dijalankan, aplikasi otomatis membuat:
- 4 jenis layanan (master data)
- **5 pelanggan contoh**
- **8 transaksi contoh** dengan berbagai status

### Menonaktifkan Seed
Edit file `app.py`, komentari baris berikut:
```python
# seed_contoh()   # ← tambahkan # di awal baris ini
```

---

## 📁 Struktur Proyek

```
Sistem_laundry/
├── app.py              ← Entry point, semua route Flask
├── database.py         ← Inisialisasi DB & seed data
├── requirements.txt    ← Dependensi Python
├── laundry.db          ← File database SQLite (dibuat otomatis)
├── README.md
│
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── pelanggan/
│   │   ├── index.html
│   │   ├── tambah.html
│   │   └── edit.html
│   └── transaksi/
│       ├── index.html
│       ├── tambah.html
│       └── detail.html
│
└── static/
    ├── css/style.css
    └── js/main.js
```

---

## 🏷️ Layanan & Tarif

| Layanan | Tarif per kg |
|---------|-------------|
| Cuci Kering Lipat | Rp 6.000 |
| Cuci + Setrika | Rp 8.000 |
| Setrika Saja | Rp 5.000 |
| Dry Cleaning | Rp 15.000 |

---

## ⚙️ Aturan Bisnis Utama

| Aturan | Keterangan |
|--------|-----------|
| Nomor HP unik | Satu HP hanya untuk satu pelanggan |
| Berat cucian | Minimal 0,5 kg, maksimal 50 kg |
| Alur status | Diterima → Diproses → Selesai → Diambil (tidak bisa mundur/lompat) |
| Syarat diambil | Status = Selesai **DAN** pembayaran = Lunas |
| Hapus transaksi | Hanya jika status masih "Diterima" |
| Harga otomatis | Total = tarif per kg × berat (tidak bisa diubah manual) |

---

## 🔧 Dependensi

```
flask>=3.0.0
```

SQLite sudah built-in di Python, tidak perlu instalasi tambahan.

---

*UTS Testing dan Implementasi Sistem — Vibe Coding Approach*

