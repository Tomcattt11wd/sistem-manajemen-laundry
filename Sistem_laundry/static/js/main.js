/* ============================================================
   Sistem Manajemen Laundry — JavaScript Minimal
   Fungsi: kalkulasi harga otomatis, filter tabel, konfirmasi hapus
   ============================================================ */

// --- 1. KALKULASI HARGA OTOMATIS (Form Transaksi) ---
(function () {
    const selectLayanan = document.getElementById('layanan_id');
    const inputBerat    = document.getElementById('berat_kg');
    const displayHarga  = document.getElementById('total_harga_display');
    const inputHarga    = document.getElementById('total_harga');
    const tarifInfo     = document.getElementById('tarif_info');

    // Map tarif: value = tarif_per_kg (di-embed dari template via data attribute)
    function getTarif() {
        if (!selectLayanan) return 0;
        const opt = selectLayanan.options[selectLayanan.selectedIndex];
        return parseInt(opt.getAttribute('data-tarif') || '0', 10);
    }

    function formatRupiah(angka) {
        return 'Rp ' + angka.toLocaleString('id-ID');
    }

    function hitungHarga() {
        if (!selectLayanan || !inputBerat || !displayHarga) return;

        const tarif = getTarif();
        // Terima koma MAUPUN titik sebagai pemisah desimal (VR-05)
        const beratRaw = inputBerat.value.replace(',', '.');
        const berat    = parseFloat(beratRaw) || 0;
        const total    = tarif * berat;

        // Update display harga
        displayHarga.textContent = total > 0 ? formatRupiah(total) : 'Rp —';

        // Update hidden input
        if (inputHarga) {
            inputHarga.value = total > 0 ? Math.round(total) : '';
        }

        // Update info tarif
        if (tarifInfo && selectLayanan.selectedIndex > 0) {
            tarifInfo.textContent = 'Tarif: ' + formatRupiah(tarif) + ' / kg';
            tarifInfo.style.display = 'block';
        } else if (tarifInfo) {
            tarifInfo.style.display = 'none';
        }
    }

    if (selectLayanan) selectLayanan.addEventListener('change', hitungHarga);
    if (inputBerat)    inputBerat.addEventListener('input', hitungHarga);

    // Jalankan sekali saat halaman dimuat (untuk mode edit/reload)
    hitungHarga();
})();


// --- 2. FILTER / PENCARIAN TABEL PELANGGAN (client-side) ---
(function () {
    const searchInput = document.getElementById('cari_pelanggan');
    const tableBody   = document.getElementById('tabel_pelanggan_body');

    if (!searchInput || !tableBody) return;

    searchInput.addEventListener('input', function () {
        const keyword = this.value.toLowerCase().trim();
        const rows    = tableBody.querySelectorAll('tr[data-searchable]');
        let visible   = 0;

        rows.forEach(function (row) {
            const text = row.getAttribute('data-searchable').toLowerCase();
            if (text.includes(keyword)) {
                row.style.display = '';
                visible++;
            } else {
                row.style.display = 'none';
            }
        });

        // Tampilkan pesan kosong
        const emptyRow = document.getElementById('row_kosong_pelanggan');
        if (emptyRow) {
            emptyRow.style.display = visible === 0 ? '' : 'none';
        }
    });
})();


// --- 3. KONFIRMASI HAPUS ---
function konfirmasiHapus(pesan) {
    return confirm(pesan || 'Apakah Anda yakin ingin menghapus data ini?');
}


// --- 4. AUTO-DISMISS FLASH MESSAGES ---
(function () {
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(function (el) {
        setTimeout(function () {
            el.style.transition = 'opacity 0.5s';
            el.style.opacity = '0';
            setTimeout(function () { el.style.display = 'none'; }, 500);
        }, 4000); // hilang setelah 4 detik
    });
})();

