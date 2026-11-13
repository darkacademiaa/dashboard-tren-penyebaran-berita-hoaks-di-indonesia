# 🕵️ Dashboard Tren Penyebaran Berita Hoaks di Indonesia

Dashboard interaktif untuk mengeksplorasi dan membandingkan **berita hoaks** dengan **berita valid** berbahasa Indonesia, dibangun menggunakan Python dan Streamlit.

🔗 **Demo langsung:** [LINK_APP_STREAMLIT]
📄 **Mini Paper:** [LINK_PDF]

---

## 📌 Latar Belakang

Penyebaran hoaks di media sosial dan platform digital terus menjadi masalah di Indonesia. Proyek ini mengumpulkan artikel hoaks yang sudah diverifikasi dan berita dari media nasional, lalu menyajikannya dalam dashboard agar pola bahasa, sumber, dan kategori klaim dapat dibandingkan secara visual.

## 📊 Dataset

| Keterangan | Nilai |
|---|---|
| Total artikel | 23.747 |
| Hoaks (label `1`) | 11.608 |
| Berita valid (label `0`) | 12.139 |
| Sumber hoaks | turnbackhoax.id |
| Sumber berita valid | antaranews.com, kompas.com, detik.com |

**Kolom data:** `url`, `judul`, `narasi`, `label`, `clean_text`, `tanggal`, `berita_bersih`

Teks pada kolom `berita_bersih` telah melalui tahap pembersihan (huruf kecil, penghapusan tanda baca dan stopword).

## ✨ Fitur Dashboard

| Tab | Fungsi |
|---|---|
| 📊 **Ringkasan** | Proporsi label, sebaran jumlah kata, sumber artikel, dan kategori klaim (tag `[SALAH]`, `[HOAKS]`, `[PENIPUAN]`, dll.) |
| 📈 **Tren Waktu** | Jumlah artikel per hari, minggu, atau bulan, disertai indikator kelengkapan tanggal |
| ☁️ **Word Cloud** | Perbandingan kata dominan hoaks vs berita valid |
| 🔤 **Analisis Kata** | Kata dan frasa dua kata teratas, serta kata yang paling khas tiap kelas (log-odds ratio) |
| 🗂️ **Data Explorer** | Tabel data, unduh hasil filter (CSV), dan pembaca artikel |

**Filter di sidebar:** label, sumber, rentang tanggal, jumlah kata, dan pencarian kata kunci.

## 🛠️ Teknologi

- Python 3
- [Streamlit](https://streamlit.io/): kerangka dashboard
- Pandas: pengolahan data
- Plotly: grafik interaktif
- WordCloud dan Matplotlib: visualisasi word cloud

## 🚀 Menjalankan Secara Lokal

```bash
# 1. Clone repositori
git clone https://github.com/darkacademiaa/dashboard-tren-penyebaran-berita-hoaks-di-indonesia.git
cd dashboard-tren-penyebaran-berita-hoaks-di-indonesia

# 2. Pasang dependensi
pip install -r requirements.txt

# 3. Jalankan dashboard
streamlit run app.py
```

Pastikan file `Data_Clean_-_data_clean.csv` berada di folder yang sama dengan `app.py`. Dataset lain dengan kolom yang sama juga bisa diunggah lewat sidebar.

## 📁 Struktur Repositori

```
├── app.py                        # Kode utama dashboard
├── requirements.txt              # Daftar dependensi
├── Data_Clean_-_data_clean.csv   # Dataset
└── README.md
```

## ⚠️ Keterbatasan

- **Tanggal artikel hoaks tidak tersedia.** Seluruh data hoaks dari TurnBackHoax tidak memiliki tanggal pada dataset ini. Hanya sekitar 30% artikel berita valid yang bertanggal, sebagian besar pada Maret–April 2026. Karena itu grafik tren waktu **tidak dapat dibaca sebagai perbandingan tren hoaks vs berita valid**. Dashboard menampilkan peringatan untuk hal ini.
- **Sumber berkorelasi dengan label.** Semua hoaks berasal dari satu situs dan semua berita valid dari situs lain, sehingga perbedaan gaya bahasa bisa sebagian mencerminkan perbedaan sumber, bukan hanya perbedaan hoaks dan valid.
- **Kategori klaim** diambil dari tag di awal judul TurnBackHoax; sebagian artikel tidak memiliki tag (ditampilkan sebagai `TANPA TAG`).
- Untuk kecepatan, word cloud dan analisis kata menggunakan sampel maksimal 6.000 artikel per kelompok.

## 👥 Tim

**Kelompok 28 · Fortran 2026**

| Peran | Nama |
|---|---|
| Data Collector | Naufal |
| Data Cleaner | Nabila, Tiara |
| Dashboard Developer | Nadya |
| Insight & Data Analyst | Caca, Fadhil |
| Penulis Mini Paper | Fatih, Rayyan, Ezzar, Cattleya |
| Website Developer | Wili |
| Dokumentasi & Bukti Pendukung | Tegar |

## 📚 Sumber Data

- [TurnBackHoax](https://turnbackhoax.id): arsip klarifikasi hoaks oleh MAFINDO
- Antara News, Kompas.com, dan Detik.com: berita valid
