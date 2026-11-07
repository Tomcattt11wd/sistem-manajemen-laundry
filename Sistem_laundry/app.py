"""
app.py — Entry point utama Flask
Sistem Manajemen Laundry
Jalankan: python app.py
"""

from flask import (Flask, render_template, request,
                   redirect, url_for, flash)
from database import get_db_connection, init_db, seed_contoh
from datetime import date
import sqlite3

app = Flask(__name__)
app.secret_key = 'laundry-secret-2026'   # ganti di production

# Urutan status pengerjaan (untuk validasi transisi alur)
STATUS_FLOW = ['Diterima', 'Diproses', 'Selesai', 'Diambil']


# ═══════════════════════════════════════════════════════════════
# HELPER & FILTER JINJA
# ═══════════════════════════════════════════════════════════════

def format_rupiah(angka):
    """Format angka ke string Rupiah (dipakai di Jinja filter)."""
    return f"Rp {int(angka):,}".replace(',', '.')

app.jinja_env.filters['rupiah'] = format_rupiah


def generate_kode(conn):
    """Buat kode transaksi otomatis: TRX-0001, TRX-0002, dst."""
    row = conn.execute(
        "SELECT kode_transaksi FROM transaksi ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return 'TRX-0001'
    last_num = int(row['kode_transaksi'].split('-')[1])
    return f'TRX-{last_num + 1:04d}'


# ═══════════════════════════════════════════════════════════════
# FUNGSI VALIDASI — semua pesan dalam Bahasa Indonesia
# ═══════════════════════════════════════════════════════════════

def validasi_nama(nama: str) -> str | None:
    """
    VR-01: Nama pelanggan wajib diisi, 3–50 karakter.
    Nama yang hanya berisi spasi dianggap kosong.
    Mengembalikan pesan error (str) atau None jika valid.
    """
    nama_bersih = (nama or '').strip()
    if not nama_bersih:
        return 'Nama pelanggan wajib diisi dan tidak boleh hanya berisi spasi.'
    if len(nama_bersih) < 3:
        return (f'Nama pelanggan terlalu pendek — '
                f'saat ini {len(nama_bersih)} karakter, minimal 3 karakter.')
    if len(nama_bersih) > 50:
        return (f'Nama pelanggan terlalu panjang — '
                f'saat ini {len(nama_bersih)} karakter, maksimal 50 karakter.')
    return None


def validasi_no_hp(no_hp: str) -> str | None:
    """
    VR-02: No. HP wajib diisi, hanya angka, 10–13 digit, diawali "08".
    Mengembalikan pesan error (str) atau None jika valid.
    """
    hp = (no_hp or '').strip()
    if not hp:
        return 'Nomor HP wajib diisi.'
    if not hp.isdigit():
        return ('Nomor HP hanya boleh berisi angka — '
                'hapus spasi, tanda hubung (-), atau karakter lain.')
    if len(hp) < 10:
        return (f'Nomor HP terlalu pendek — '
                f'saat ini {len(hp)} digit, minimal 10 digit.')
    if len(hp) > 13:
        return (f'Nomor HP terlalu panjang — '
                f'saat ini {len(hp)} digit, maksimal 13 digit.')
    if not hp.startswith('08'):
        return ('Nomor HP harus diawali dengan "08" '
                '(contoh: 081234567890).')
    return None


def validasi_berat(berat_str: str):
    """
    VR-05: Berat wajib angka antara 0,5–50 kg.
    Menerima koma maupun titik sebagai pemisah desimal.
    Mengembalikan (berat: float, error: str|None).
    """
    raw = (berat_str or '').strip().replace(',', '.')
    if not raw:
        return None, 'Berat cucian wajib diisi.'
    try:
        berat = float(raw)
    except ValueError:
        return None, (f'Berat cucian "{berat_str}" bukan angka yang valid — '
                      f'gunakan angka seperti 2.5 atau 2,5.')
    if berat <= 0:
        return None, 'Berat cucian harus lebih dari 0 kg (nilai nol atau negatif tidak diizinkan).'
    if berat < 0.5:
        return None, (f'Berat cucian {berat} kg terlalu ringan — '
                      f'minimal 0,5 kg per transaksi.')
    if berat > 50:
        return None, (f'Berat cucian {berat} kg melebihi batas — '
                      f'maksimal 50 kg per transaksi.')
    return berat, None


# ═══════════════════════════════════════════════════════════════
# ERROR HANDLERS — tangani 404, 500, dan exception tak terduga
# ═══════════════════════════════════════════════════════════════

@app.errorhandler(404)
def halaman_tidak_ditemukan(e):
    return render_template('error.html',
                           kode=404,
                           judul='Halaman Tidak Ditemukan',
                           pesan='Halaman yang Anda cari tidak ada atau sudah dipindahkan.'), 404


@app.errorhandler(500)
def kesalahan_server(e):
    return render_template('error.html',
                           kode=500,
                           judul='Kesalahan Server',
                           pesan='Terjadi kesalahan tak terduga pada server. Silakan coba lagi.'), 500


@app.errorhandler(Exception)
def tangani_exception(e):
    """Tangkap semua exception yang tidak ditangani agar tidak muncul halaman error mentah."""
    app.logger.error(f'Unhandled exception: {e}', exc_info=True)
    return render_template('error.html',
                           kode=500,
                           judul='Terjadi Kesalahan',
                           pesan=f'Terjadi kesalahan yang tidak terduga: {type(e).__name__}. '
                                 f'Silakan kembali dan coba lagi.'), 500


# ═══════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════

@app.route('/')
def dashboard():
    conn = get_db_connection()
    total_pelanggan = conn.execute('SELECT COUNT(*) FROM pelanggan').fetchone()[0]
    total_transaksi = conn.execute('SELECT COUNT(*) FROM transaksi').fetchone()[0]

    status_counts = {s: 0 for s in STATUS_FLOW}
    for r in conn.execute(
        'SELECT status_pengerjaan, COUNT(*) as jml FROM transaksi GROUP BY status_pengerjaan'
    ).fetchall():
        status_counts[r['status_pengerjaan']] = r['jml']

    transaksi_terbaru = conn.execute('''
        SELECT t.id, t.kode_transaksi, p.nama AS nama_pelanggan,
               l.nama_layanan, t.berat_kg, t.total_harga,
               t.status_pengerjaan, t.status_pembayaran, t.tanggal_masuk
        FROM transaksi t
        JOIN pelanggan p ON t.pelanggan_id = p.id
        JOIN layanan   l ON t.layanan_id   = l.id
        ORDER BY t.id DESC LIMIT 5
    ''').fetchall()
    conn.close()

    return render_template('dashboard.html',
                           total_pelanggan=total_pelanggan,
                           total_transaksi=total_transaksi,
                           status_counts=status_counts,
                           transaksi_terbaru=transaksi_terbaru)


# ═══════════════════════════════════════════════════════════════
# PELANGGAN
# ═══════════════════════════════════════════════════════════════

@app.route('/pelanggan')
def pelanggan_list():
    conn = get_db_connection()
    pelanggan = conn.execute('SELECT * FROM pelanggan ORDER BY nama ASC').fetchall()
    conn.close()
    return render_template('pelanggan/index.html', pelanggan=pelanggan)


@app.route('/pelanggan/tambah', methods=['GET', 'POST'])
def pelanggan_tambah():
    if request.method == 'POST':
        nama   = request.form.get('nama', '')
        no_hp  = request.form.get('no_hp', '')
        alamat = request.form.get('alamat', '').strip()

        errors = {}

        err_nama = validasi_nama(nama)
        if err_nama:
            errors['nama'] = err_nama

        err_hp = validasi_no_hp(no_hp)
        if err_hp:
            errors['no_hp'] = err_hp

        # VR-03: Cek duplikasi HP
        if 'no_hp' not in errors:
            try:
                conn = get_db_connection()
                existing = conn.execute(
                    'SELECT id, nama FROM pelanggan WHERE no_hp = ?', (no_hp.strip(),)
                ).fetchone()
                conn.close()
                if existing:
                    errors['no_hp'] = (f'Nomor HP {no_hp.strip()} sudah terdaftar '
                                       f'untuk pelanggan "{existing["nama"]}".')
            except sqlite3.Error as e:
                errors['_db'] = f'Gagal memeriksa data: {e}'

        if not errors:
            try:
                conn = get_db_connection()
                conn.execute(
                    'INSERT INTO pelanggan (nama, no_hp, alamat) VALUES (?, ?, ?)',
                    (nama.strip(), no_hp.strip(), alamat or None)
                )
                conn.commit()
                conn.close()
                flash(f'Pelanggan "{nama.strip()}" berhasil ditambahkan.', 'success')
                return redirect(url_for('pelanggan_list'))
            except sqlite3.IntegrityError:
                errors['no_hp'] = (f'Nomor HP {no_hp.strip()} sudah digunakan '
                                   f'oleh pelanggan lain.')
            except sqlite3.Error as e:
                errors['_db'] = f'Gagal menyimpan data: {e}'

        return render_template('pelanggan/tambah.html',
                               errors=errors,
                               form={'nama': nama, 'no_hp': no_hp, 'alamat': alamat})

    return render_template('pelanggan/tambah.html', errors={}, form={})


@app.route('/pelanggan/edit/<int:pid>', methods=['GET', 'POST'])
def pelanggan_edit(pid):
    conn = get_db_connection()
    pelanggan = conn.execute('SELECT * FROM pelanggan WHERE id = ?', (pid,)).fetchone()
    conn.close()

    if pelanggan is None:
        flash(f'Pelanggan dengan ID #{pid} tidak ditemukan.', 'error')
        return redirect(url_for('pelanggan_list'))

    if request.method == 'POST':
        nama   = request.form.get('nama', '')
        no_hp  = request.form.get('no_hp', '')
        alamat = request.form.get('alamat', '').strip()

        errors = {}

        err_nama = validasi_nama(nama)
        if err_nama:
            errors['nama'] = err_nama

        err_hp = validasi_no_hp(no_hp)
        if err_hp:
            errors['no_hp'] = err_hp

        # VR-03: Cek duplikat HP milik pelanggan LAIN (kecuali milik sendiri)
        if 'no_hp' not in errors:
            try:
                conn = get_db_connection()
                existing = conn.execute(
                    'SELECT id, nama FROM pelanggan WHERE no_hp = ? AND id != ?',
                    (no_hp.strip(), pid)
                ).fetchone()
                conn.close()
                if existing:
                    errors['no_hp'] = (f'Nomor HP {no_hp.strip()} sudah terdaftar '
                                       f'untuk pelanggan "{existing["nama"]}".')
            except sqlite3.Error as e:
                errors['_db'] = f'Gagal memeriksa data: {e}'

        if not errors:
            try:
                conn = get_db_connection()
                conn.execute(
                    'UPDATE pelanggan SET nama = ?, no_hp = ?, alamat = ? WHERE id = ?',
                    (nama.strip(), no_hp.strip(), alamat or None, pid)
                )
                conn.commit()
                conn.close()
                flash(f'Data pelanggan "{nama.strip()}" berhasil diperbarui.', 'success')
                return redirect(url_for('pelanggan_list'))
            except sqlite3.IntegrityError:
                errors['no_hp'] = (f'Nomor HP {no_hp.strip()} sudah digunakan '
                                   f'oleh pelanggan lain.')
            except sqlite3.Error as e:
                errors['_db'] = f'Gagal menyimpan data: {e}'

        return render_template('pelanggan/edit.html',
                               pelanggan=pelanggan,
                               errors=errors,
                               form={'nama': nama, 'no_hp': no_hp, 'alamat': alamat})

    return render_template('pelanggan/edit.html',
                           pelanggan=pelanggan,
                           errors={},
                           form=dict(pelanggan))


@app.route('/pelanggan/hapus/<int:pid>', methods=['POST'])
def pelanggan_hapus(pid):
    try:
        conn = get_db_connection()
        pelanggan = conn.execute('SELECT nama FROM pelanggan WHERE id = ?', (pid,)).fetchone()
        if pelanggan is None:
            conn.close()
            flash(f'Pelanggan dengan ID #{pid} tidak ditemukan.', 'error')
            return redirect(url_for('pelanggan_list'))

        trx_count = conn.execute(
            'SELECT COUNT(*) FROM transaksi WHERE pelanggan_id = ?', (pid,)
        ).fetchone()[0]

        if trx_count > 0:
            conn.close()
            flash((f'Pelanggan "{pelanggan["nama"]}" tidak dapat dihapus '
                   f'karena masih memiliki {trx_count} transaksi aktif.'), 'error')
            return redirect(url_for('pelanggan_list'))

        nama = pelanggan['nama']
        conn.execute('DELETE FROM pelanggan WHERE id = ?', (pid,))
        conn.commit()
        conn.close()
        flash(f'Pelanggan "{nama}" berhasil dihapus.', 'success')
    except sqlite3.Error as e:
        flash(f'Gagal menghapus pelanggan: {e}', 'error')

    return redirect(url_for('pelanggan_list'))


# ═══════════════════════════════════════════════════════════════
# TRANSAKSI
# ═══════════════════════════════════════════════════════════════

@app.route('/transaksi')
def transaksi_list():
    f_status = request.args.get('status', '')
    f_bayar  = request.args.get('bayar', '')
    f_cari   = request.args.get('cari', '').strip()

    try:
        conn  = get_db_connection()
        query = '''
            SELECT t.id, t.kode_transaksi, p.nama AS nama_pelanggan,
                   l.nama_layanan, t.berat_kg, t.total_harga,
                   t.status_pengerjaan, t.status_pembayaran, t.tanggal_masuk
            FROM transaksi t
            JOIN pelanggan p ON t.pelanggan_id = p.id
            JOIN layanan   l ON t.layanan_id   = l.id
            WHERE 1=1
        '''
        params = []
        if f_status:
            query += ' AND t.status_pengerjaan = ?'
            params.append(f_status)
        if f_bayar:
            query += ' AND t.status_pembayaran = ?'
            params.append(f_bayar)
        if f_cari:
            query += ' AND (p.nama LIKE ? OR t.kode_transaksi LIKE ?)'
            params.extend([f'%{f_cari}%', f'%{f_cari}%'])

        query += ' ORDER BY t.id DESC'
        transaksi = conn.execute(query, params).fetchall()

        total_lunas = conn.execute(
            "SELECT COALESCE(SUM(total_harga),0) FROM transaksi WHERE status_pembayaran='Lunas'"
        ).fetchone()[0]
        conn.close()
    except sqlite3.Error as e:
        flash(f'Gagal memuat daftar transaksi: {e}', 'error')
        transaksi, total_lunas = [], 0

    return render_template('transaksi/index.html',
                           transaksi=transaksi,
                           total_lunas=total_lunas,
                           f_status=f_status,
                           f_bayar=f_bayar,
                           f_cari=f_cari,
                           status_list=STATUS_FLOW)


@app.route('/transaksi/tambah', methods=['GET', 'POST'])
def transaksi_tambah():
    def _load_lists(conn):
        pel = conn.execute('SELECT id, nama, no_hp FROM pelanggan ORDER BY nama').fetchall()
        lay = conn.execute('SELECT * FROM layanan ORDER BY id').fetchall()
        return pel, lay

    conn = get_db_connection()

    if request.method == 'POST':
        pelanggan_id = request.form.get('pelanggan_id', '').strip()
        layanan_id   = request.form.get('layanan_id', '').strip()
        berat_str    = request.form.get('berat_kg', '').strip()
        catatan      = request.form.get('catatan', '').strip()
        tgl_masuk    = request.form.get('tanggal_masuk', '').strip() or str(date.today())

        errors = {}

        # VR-04: Pelanggan wajib dipilih
        if not pelanggan_id:
            errors['pelanggan_id'] = 'Pelanggan wajib dipilih — pilih nama pelanggan dari daftar.'

        # VR-04: Layanan wajib dipilih
        if not layanan_id:
            errors['layanan_id'] = 'Jenis layanan wajib dipilih — pilih salah satu dari daftar layanan.'

        # VR-05: Validasi berat
        berat, err_berat = validasi_berat(berat_str)
        if err_berat:
            errors['berat_kg'] = err_berat

        total = None
        if not errors:
            layanan = conn.execute(
                'SELECT tarif_per_kg, nama_layanan FROM layanan WHERE id = ?', (layanan_id,)
            ).fetchone()
            if layanan is None:
                errors['layanan_id'] = (f'Jenis layanan dengan ID #{layanan_id} tidak ditemukan. '
                                        f'Pilih ulang dari daftar.')
            else:
                total = round(layanan['tarif_per_kg'] * berat)

        if not errors:
            pel_row = conn.execute(
                'SELECT nama FROM pelanggan WHERE id = ?', (pelanggan_id,)
            ).fetchone()
            if pel_row is None:
                errors['pelanggan_id'] = (f'Pelanggan dengan ID #{pelanggan_id} tidak ditemukan. '
                                          f'Pilih ulang dari daftar.')

        if not errors:
            try:
                kode = generate_kode(conn)
                conn.execute('''
                    INSERT INTO transaksi
                        (kode_transaksi, pelanggan_id, layanan_id, berat_kg,
                         total_harga, tanggal_masuk, catatan)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (kode, pelanggan_id, layanan_id, berat,
                      total, tgl_masuk, catatan or None))
                conn.commit()
                trx_id = conn.execute(
                    'SELECT id FROM transaksi WHERE kode_transaksi = ?', (kode,)
                ).fetchone()['id']
                conn.close()
                flash(f'Transaksi {kode} berhasil dicatat.', 'success')
                return redirect(url_for('transaksi_detail', tid=trx_id))
            except sqlite3.Error as e:
                errors['_db'] = f'Gagal menyimpan transaksi: {e}'

        pelanggan_list, layanan_list = _load_lists(conn)
        conn.close()
        return render_template('transaksi/tambah.html',
                               pelanggan_list=pelanggan_list,
                               layanan_list=layanan_list,
                               errors=errors,
                               form=request.form,
                               today=str(date.today()))

    pelanggan_list, layanan_list = _load_lists(conn)
    conn.close()
    return render_template('transaksi/tambah.html',
                           pelanggan_list=pelanggan_list,
                           layanan_list=layanan_list,
                           errors={},
                           form={},
                           today=str(date.today()))


@app.route('/transaksi/<int:tid>')
def transaksi_detail(tid):
    try:
        conn = get_db_connection()
        trx  = conn.execute('''
            SELECT t.*, p.nama AS nama_pelanggan, p.no_hp,
                   l.nama_layanan, l.tarif_per_kg
            FROM transaksi t
            JOIN pelanggan p ON t.pelanggan_id = p.id
            JOIN layanan   l ON t.layanan_id   = l.id
            WHERE t.id = ?
        ''', (tid,)).fetchone()
        conn.close()
    except sqlite3.Error as e:
        flash(f'Gagal memuat detail transaksi: {e}', 'error')
        return redirect(url_for('transaksi_list'))

    if trx is None:
        flash(f'Transaksi dengan ID #{tid} tidak ditemukan.', 'error')
        return redirect(url_for('transaksi_list'))

    idx = STATUS_FLOW.index(trx['status_pengerjaan'])
    status_berikutnya = STATUS_FLOW[idx + 1] if idx < len(STATUS_FLOW) - 1 else None

    return render_template('transaksi/detail.html',
                           trx=trx,
                           status_flow=STATUS_FLOW,
                           status_berikutnya=status_berikutnya)


@app.route('/transaksi/<int:tid>/status', methods=['POST'])
def transaksi_ubah_status(tid):
    """
    Ubah status pengerjaan secara berurutan: Diterima -> Diproses -> Selesai -> Diambil.
    Aturan VR-06: Status harus berurutan, tidak boleh melompati langkah atau mundur.
    Aturan VR-07: Status "Diambil" hanya boleh jika status "Selesai" dan pembayaran "Lunas".
    """
    redirect_target = request.form.get('next') or request.referrer or url_for('transaksi_list')

    try:
        conn = get_db_connection()
        trx  = conn.execute(
            'SELECT kode_transaksi, status_pengerjaan, status_pembayaran FROM transaksi WHERE id = ?',
            (tid,)
        ).fetchone()

        if trx is None:
            conn.close()
            flash(f'Transaksi dengan ID #{tid} tidak ditemukan.', 'error')
            return redirect(url_for('transaksi_list'))

        status_saat_ini = trx['status_pengerjaan']
        if status_saat_ini not in STATUS_FLOW:
            conn.close()
            flash('Status saat ini tidak valid.', 'error')
            return redirect(redirect_target)

        idx_sekarang = STATUS_FLOW.index(status_saat_ini)
        status_tujuan = request.form.get('status', '').strip()

        # Jika form tidak menyertakan status_tujuan spesifik, lanjutkan ke langkah berikutnya
        if not status_tujuan:
            if idx_sekarang >= len(STATUS_FLOW) - 1:
                conn.close()
                flash('Status harus berurutan. Transaksi sudah pada status akhir (Diambil) dan tidak dapat diubah lagi.', 'warning')
                return redirect(redirect_target)
            status_tujuan = STATUS_FLOW[idx_sekarang + 1]

        # Validasi status_tujuan ada di alur resmi
        if status_tujuan not in STATUS_FLOW:
            conn.close()
            flash('Status tidak valid. Status harus berurutan: Diterima → Diproses → Selesai → Diambil.', 'error')
            return redirect(redirect_target)

        # VR-07: Aturan pengambilan cucian (status "Diambil")
        if status_tujuan == 'Diambil':
            if status_saat_ini != 'Selesai':
                conn.close()
                flash('Cucian belum selesai. Status harus berurutan dan cucian harus berstatus Selesai terlebih dahulu sebelum dapat diambil.', 'error')
                return redirect(redirect_target)
            if trx['status_pembayaran'] != 'Lunas':
                conn.close()
                flash('Pembayaran belum lunas. Selesaikan pembayaran terlebih dahulu sebelum cucian dapat diambil.', 'error')
                return redirect(redirect_target)
            status_baru = 'Diambil'
        else:
            # VR-06: Validasi urutan status harus tepat +1 langkah
            idx_tujuan = STATUS_FLOW.index(status_tujuan)
            if idx_tujuan != idx_sekarang + 1:
                conn.close()
                flash('Status harus berurutan (Diterima → Diproses → Selesai → Diambil). Tidak boleh melompati status atau mundur.', 'error')
                return redirect(redirect_target)
            status_baru = status_tujuan

        conn.execute(
            'UPDATE transaksi SET status_pengerjaan = ? WHERE id = ?', (status_baru, tid)
        )
        conn.commit()
        conn.close()
        flash(f'Status transaksi {trx["kode_transaksi"]} berhasil diubah menjadi "{status_baru}".', 'success')
    except sqlite3.Error as e:
        flash(f'Gagal mengubah status: {e}', 'error')

    return redirect(redirect_target)


@app.route('/transaksi/<int:tid>/lunas', methods=['POST'])
def transaksi_lunas(tid):
    """Tandai transaksi sebagai Lunas."""
    redirect_target = request.form.get('next') or request.referrer or url_for('transaksi_list')

    try:
        conn = get_db_connection()
        trx  = conn.execute(
            'SELECT kode_transaksi, status_pembayaran FROM transaksi WHERE id = ?', (tid,)
        ).fetchone()

        if trx is None:
            conn.close()
            flash(f'Transaksi dengan ID #{tid} tidak ditemukan.', 'error')
            return redirect(url_for('transaksi_list'))

        if trx['status_pembayaran'] == 'Lunas':
            conn.close()
            flash(f'Transaksi {trx["kode_transaksi"]} sudah berstatus Lunas — '
                  f'tidak perlu dikonfirmasi ulang.', 'warning')
            return redirect(redirect_target)

        conn.execute(
            "UPDATE transaksi SET status_pembayaran = 'Lunas' WHERE id = ?", (tid,)
        )
        conn.commit()
        conn.close()
        flash(f'Pembayaran transaksi {trx["kode_transaksi"]} '
              f'berhasil dicatat sebagai Lunas. ✅', 'success')
    except sqlite3.Error as e:
        flash(f'Gagal memperbarui pembayaran: {e}', 'error')

    return redirect(redirect_target)


@app.route('/transaksi/<int:tid>/hapus', methods=['POST'])
def transaksi_hapus(tid):
    """
    VR-08: Hapus transaksi hanya boleh jika statusnya masih "Diterima".
    Jika status lain, tolak dengan pesan error yang tegas.
    """
    try:
        conn = get_db_connection()
        trx  = conn.execute(
            'SELECT kode_transaksi, status_pengerjaan FROM transaksi WHERE id = ?', (tid,)
        ).fetchone()

        if trx is None:
            conn.close()
            flash(f'Transaksi dengan ID #{tid} tidak ditemukan.', 'error')
            return redirect(url_for('transaksi_list'))

        if trx['status_pengerjaan'] != 'Diterima':
            conn.close()
            flash((f'Transaksi {trx["kode_transaksi"]} tidak dapat dihapus. '
                   f'Hanya transaksi berstatus Diterima yang dapat dihapus.'), 'error')
            return redirect(request.referrer or url_for('transaksi_list'))

        kode = trx['kode_transaksi']
        conn.execute('DELETE FROM transaksi WHERE id = ?', (tid,))
        conn.commit()
        conn.close()
        flash(f'Transaksi {kode} berhasil dihapus.', 'success')
        return redirect(url_for('transaksi_list'))
    except sqlite3.Error as e:
        flash(f'Gagal menghapus transaksi: {e}', 'error')
        return redirect(url_for('transaksi_list'))


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════
if __name__ == '__main__':
    init_db()
    seed_contoh()      # komentari baris ini untuk menonaktifkan data contoh
    app.run(debug=True, port=5000)
