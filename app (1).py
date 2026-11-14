"""
Dashboard Analisis Hoaks vs Berita Valid (TurnBackHoax + media nasional)
=======================================================================
Jalankan:  streamlit run app.py
Dataset :  Data_Final_Hoaks.csv.gz  (nama bebas selama berakhiran .csv / .csv.gz / .gz; taruh di folder yang sama dengan app.py,
           atau upload lewat sidebar)

Kolom yang diharapkan:
    url, judul, narasi, label (1 = hoaks, 0 = valid), clean_text, tanggal, berita_bersih
"""

from __future__ import annotations

import io
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import streamlit as st

# ----------------------------------------------------------------------------
# Konfigurasi
# ----------------------------------------------------------------------------
_BASE = Path(__file__).parent


def find_dataset() -> Path | None:
    """Cari dataset FINAL di folder app (termasuk subfolder).

    - Menerima .csv, .csv.gz, atau .gz (mis. 'Data_Final_Hoaks_csv.gz').
    - File yang namanya mengandung 'final' diprioritaskan.
    - File dataset lama ('Data_Clean...') SENGAJA diabaikan supaya dashboard
      tidak diam-diam memakai data lama yang angkanya berbeda dari paper.
    """
    files = [
        p for pattern in ("*.csv.gz", "*.csv", "*.gz")
        for p in _BASE.rglob(pattern)
        if "data_clean" not in p.name.lower().replace("-", "_").replace(" ", "_")
    ]
    files = list(dict.fromkeys(files))  # buang duplikat, urutan tetap
    files.sort(key=lambda p: ("final" not in p.name.lower(), -p.stat().st_size))
    return files[0] if files else None


DEFAULT_CSV = find_dataset()
LABEL_MAP = {1: "Hoaks", 0: "Berita Valid"}
COLORS = {"Hoaks": "#E4572E", "Berita Valid": "#2E86AB"}
NO_DATE_TEXT = "tidak tersedia"
# Periode tren hoaks (sesuai tanggal terbit TurnBackHoax yang berhasil diambil ulang)
TREN_MULAI, TREN_SELESAI = pd.Timestamp("2024-02-01"), pd.Timestamp("2026-04-30")
BULAN_ID = {1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni", 7: "Juli",
            8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"}
SAMPLE_LIMIT = 6000  # batas dokumen per kelompok untuk word cloud / n-gram (supaya cepat)

# Stopword tambahan (data sudah dibersihkan, ini hanya pelengkap)
EXTRA_STOPWORDS = {
    "yang", "dan", "di", "ke", "dari", "ini", "itu", "untuk", "dengan", "pada", "adalah",
    "dalam", "akan", "atau", "juga", "tidak", "bisa", "ada", "oleh", "saya", "kami",
    "kita", "mereka", "anda", "sudah", "telah", "karena", "agar", "serta", "bahwa",
    "yg", "dg", "nya", "kan", "pun", "lebih", "para", "sebagai", "hingga", "sampai",
    "antara", "saat", "setelah", "sebelum", "kata", "ujar", "jakarta", "antara",
    "https", "http", "www", "com", "co", "id",
    # sisa boilerplate/iklan hasil scraping (mis. detik.com) yang bukan isi berita
    "scroll", "continue", "with", "content", "inline", "passback", "pengindeksan",
    "crawling", "advertisement", "iklan", "baca", "juga", "simak",
}


# ----------------------------------------------------------------------------
# Pemuatan & penyiapan data
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Memuat dataset...")
def load_data(source: bytes | str) -> pd.DataFrame:
    """Baca CSV (path atau bytes upload) lalu tambahkan kolom turunan."""
    if isinstance(source, (bytes, bytearray)):
        comp = "gzip" if bytes(source[:2]) == b"\x1f\x8b" else None  # deteksi file .gz hasil upload
        df = pd.read_csv(io.BytesIO(source), compression=comp)
    else:
        df = pd.read_csv(source)

    required = {"url", "judul", "label", "tanggal", "berita_bersih"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Kolom wajib tidak ditemukan: {sorted(missing)}")

    df = df.copy()
    df["judul"] = df["judul"].fillna("(tanpa judul)").astype(str)
    df["berita_bersih"] = df["berita_bersih"].fillna("").astype(str)
    if "narasi" not in df.columns:
        df["narasi"] = ""
    df["narasi"] = df["narasi"].fillna("").astype(str)

    df["label"] = pd.to_numeric(df["label"], errors="coerce").fillna(-1).astype(int)
    df = df[df["label"].isin(LABEL_MAP)].copy()
    df["label_name"] = df["label"].map(LABEL_MAP)

    # Tanggal: 'tidak tersedia' / format salah -> NaT
    df["tanggal_dt"] = pd.to_datetime(df["tanggal"], format="%Y-%m-%d", errors="coerce")

    # Sumber dari domain URL
    df["sumber"] = (
        df["url"].astype(str).str.extract(r"https?://(?:www\.)?([^/]+)")[0].fillna("tidak diketahui")
    )

    # Jumlah kata teks bersih
    df["jumlah_kata"] = df["berita_bersih"].str.split().str.len().fillna(0).astype(int)

    # Jenis hoaks dari label pemeriksa fakta di judul TurnBackHoax (sama dengan mini paper)
    df["kategori"] = "Berita Valid"
    is_hoax = df["label"] == 1
    df.loc[is_hoax, "kategori"] = df.loc[is_hoax, "judul"].map(jenis_hoaks)
    # Artikel berlabel [BENAR] / [SEBAGIAN BENAR] bukan hoaks, jadi dikeluarkan
    df = df[~df["kategori"].isin(["Benar", "Sebagian Benar"])]

    return df.reset_index(drop=True)


def jenis_hoaks(judul: str) -> str:
    j = str(judul).lower()
    if "sebagian benar" in j:
        return "Sebagian Benar"
    if re.match(r"^\s*\[?\s*benar\s*[\]:,]", j):
        return "Benar"
    if "penipuan" in j:
        return "Penipuan"
    if "menyesatkan" in j:
        return "Menyesatkan"
    if "keliru" in j:
        return "Keliru"
    if "klarifikasi" in j:
        return "Klarifikasi"
    if re.search(r"satir|parodi", j):
        return "Satire/Parodi"
    if re.search(r"belum terbukti|belum ada bukti", j):
        return "Belum Terbukti"
    if re.search(r"hoaks|hoax|salah|tidak benar|manipulasi|disinformasi", j):
        return "Salah/Hoaks"
    return "Lainnya"


# ----------------------------------------------------------------------------
# Fungsi analisis teks
# ----------------------------------------------------------------------------
def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z]{3,}", text.lower()) if t not in EXTRA_STOPWORDS]


@st.cache_data(show_spinner=False)
def word_frequencies(texts: pd.Series, top_n: int = 300) -> dict[str, int]:
    counter: Counter = Counter()
    for t in texts:
        counter.update(_tokens(t))
    return dict(counter.most_common(top_n))


@st.cache_data(show_spinner=False)
def bigram_frequencies(texts: pd.Series, top_n: int = 20) -> pd.DataFrame:
    counter: Counter = Counter()
    for t in texts:
        tok = _tokens(t)
        counter.update(zip(tok, tok[1:]))
    rows = [(" ".join(k), v) for k, v in counter.most_common(top_n)]
    return pd.DataFrame(rows, columns=["frasa", "frekuensi"])


@st.cache_data(show_spinner="Menghitung kata pembeda...")
def distinctive_words(texts_hoax: pd.Series, texts_valid: pd.Series, top_n: int = 15, min_count: int = 30):
    """Kata yang paling khas di tiap kelas (log-odds ratio dengan smoothing)."""
    import math

    ch, cv = Counter(), Counter()
    for t in texts_hoax:
        ch.update(_tokens(t))
    for t in texts_valid:
        cv.update(_tokens(t))
    nh, nv = sum(ch.values()) or 1, sum(cv.values()) or 1
    rows = []
    for w in set(ch) | set(cv):
        a, b = ch.get(w, 0), cv.get(w, 0)
        if a + b < min_count:
            continue
        score = math.log((a + 1) / (nh + 1)) - math.log((b + 1) / (nv + 1))
        rows.append((w, a, b, score))
    d = pd.DataFrame(rows, columns=["kata", "freq_hoaks", "freq_valid", "skor"])
    return (
        d.sort_values("skor", ascending=False).head(top_n).reset_index(drop=True),
        d.sort_values("skor").head(top_n).reset_index(drop=True),
    )


def sample_texts(df: pd.DataFrame, label: int | None = None) -> pd.Series:
    sub = df if label is None else df[df["label"] == label]
    texts = sub["berita_bersih"]
    texts = texts[texts.str.len() > 0]
    if len(texts) > SAMPLE_LIMIT:
        texts = texts.sample(SAMPLE_LIMIT, random_state=42)
    return texts


def make_wordcloud_figure(freqs: dict[str, int], colormap: str, max_words: int):
    import matplotlib.pyplot as plt
    from wordcloud import WordCloud

    wc = WordCloud(
        width=900, height=500, background_color="white", colormap=colormap,
        max_words=max_words, prefer_horizontal=0.9, random_state=42,
    ).generate_from_frequencies(freqs)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    fig.tight_layout(pad=0)
    return fig


# ----------------------------------------------------------------------------
# Filter sidebar
# ----------------------------------------------------------------------------
def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("🎛️ Filter Data")

    labels = st.sidebar.multiselect(
        "Label", list(LABEL_MAP.values()), default=list(LABEL_MAP.values())
    )
    sumber_all = sorted(df["sumber"].unique())
    sumber = st.sidebar.multiselect("Sumber", sumber_all, default=sumber_all)

    out = df[df["label_name"].isin(labels) & df["sumber"].isin(sumber)]

    # Tanggal
    dated = out["tanggal_dt"].dropna()
    if not dated.empty:
        dmin, dmax = dated.min().date(), dated.max().date()
        rng = st.sidebar.date_input("Rentang tanggal", value=(dmin, dmax), min_value=dmin, max_value=dmax)
        include_nodate = st.sidebar.checkbox(
            "Sertakan data tanpa tanggal", value=True,
            help="Sekitar 70% berita valid dan 1,7% hoaks tidak punya tanggal. Matikan untuk hanya data bertanggal.",
        )
        if isinstance(rng, (tuple, list)) and len(rng) == 2:
            start, end = pd.Timestamp(rng[0]), pd.Timestamp(rng[1])
            in_range = out["tanggal_dt"].between(start, end)
            out = out[in_range | (out["tanggal_dt"].isna() & include_nodate)]
        elif not include_nodate:
            out = out[out["tanggal_dt"].notna()]

    # Panjang teks
    if not out.empty:
        lo, hi = int(out["jumlah_kata"].min()), int(out["jumlah_kata"].max())
        if lo < hi:
            wmin, wmax = st.sidebar.slider("Jumlah kata (teks bersih)", lo, hi, (lo, hi))
            out = out[out["jumlah_kata"].between(wmin, wmax)]

    # Pencarian kata kunci
    q = st.sidebar.text_input("🔎 Cari kata di judul / teks", "").strip().lower()
    if q:
        mask = out["judul"].str.lower().str.contains(q, regex=False) | out["berita_bersih"].str.contains(
            q, regex=False
        )
        out = out[mask]

    st.sidebar.caption(f"Menampilkan **{len(out):,}** dari **{len(df):,}** artikel")
    return out


# ----------------------------------------------------------------------------
# Tab-tab dashboard
# ----------------------------------------------------------------------------
def tab_ringkasan(df: pd.DataFrame):
    import plotly.express as px

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Proporsi label")
        cnt = df["label_name"].value_counts().reset_index()
        cnt.columns = ["label", "jumlah"]
        fig = px.pie(cnt, names="label", values="jumlah", hole=0.45,
                     color="label", color_discrete_map=COLORS)
        fig.update_traces(textinfo="percent+value")
        st.plotly_chart(fig)
    with c2:
        st.subheader("Sebaran jumlah kata")
        fig = px.histogram(df, x="jumlah_kata", color="label_name", nbins=50, barmode="overlay",
                           opacity=0.65, color_discrete_map=COLORS,
                           labels={"jumlah_kata": "Jumlah kata", "label_name": "Label"})
        st.plotly_chart(fig)

    c3, c4 = st.columns(2)
    with c3:
        st.subheader("Sumber artikel")
        s = df.groupby(["sumber", "label_name"]).size().reset_index(name="jumlah")
        order = s.groupby("sumber")["jumlah"].sum().sort_values().index
        fig = px.bar(s, x="jumlah", y="sumber", color="label_name", orientation="h",
                     color_discrete_map=COLORS, category_orders={"sumber": list(order)},
                     labels={"jumlah": "Jumlah artikel", "sumber": "", "label_name": "Label"})
        st.plotly_chart(fig)
    with c4:
        st.subheader("Jenis hoaks")
        hx = df[df["label"] == 1]
        if hx.empty:
            st.info("Tidak ada artikel hoaks pada filter saat ini.")
        else:
            k = hx["kategori"].value_counts().reset_index()
            k.columns = ["kategori", "jumlah"]
            k["persen"] = (k["jumlah"] / k["jumlah"].sum() * 100).round(1)
            k["label_teks"] = k["persen"].astype(str) + "%"
            fig = px.bar(k.sort_values("jumlah"), x="jumlah", y="kategori", orientation="h",
                         text="label_teks", color_discrete_sequence=[COLORS["Hoaks"]],
                         labels={"jumlah": "Jumlah artikel hoaks", "kategori": ""})
            fig.update_traces(textposition="outside", cliponaxis=False)
            st.plotly_chart(fig)
    st.caption("Jenis hoaks dikelompokkan dari kata/label pemeriksa fakta di judul TurnBackHoax "
               "(salah/hoaks, penipuan, keliru, dll.), sama dengan aturan di Mini Paper. "
               "Persentase dihitung dari artikel hoaks pada filter saat ini. "
               "'Lainnya' = judul tanpa kata kunci jenis hoaks.")


def tab_tren(df: pd.DataFrame):
    import plotly.express as px

    total = len(df)
    dated = df[df["tanggal_dt"].notna()].copy()
    cov = df.groupby("label_name")["tanggal_dt"].apply(lambda s: s.notna().mean() * 100).round(1)

    st.subheader("Tren artikel dari waktu ke waktu")
    cols = st.columns(max(len(cov), 1))
    for col, (name, pct) in zip(cols, cov.items()):
        col.metric(f"Kelengkapan tanggal – {name}", f"{pct}%")

    if dated.empty:
        st.warning("Tidak ada artikel bertanggal pada filter saat ini, sehingga grafik tren tidak dapat dibuat.")
        return

    if "Hoaks" in cov.index and cov["Hoaks"] < 50:
        st.warning(
            f"⚠️ Hanya {cov['Hoaks']}% artikel hoaks pada filter ini yang punya tanggal, "
            "jadi tren hoaks bisa tidak lengkap."
        )

    only_valid = (df["label"] == 0).all()
    c1, c2 = st.columns([1, 1])
    gran = c1.radio("Granularitas", ["Harian", "Mingguan", "Bulanan"], horizontal=True, index=2)
    show_valid = c2.checkbox(
        "Tampilkan berita valid", value=only_valid,
        help="Hanya sekitar 30% berita valid yang punya tanggal (kebanyakan Maret–April 2026), "
             "jadi garisnya tidak bisa dibandingkan langsung dengan hoaks.",
    )
    dated = dated[dated["tanggal_dt"].between(TREN_MULAI, TREN_SELESAI)]
    if not show_valid:
        dated = dated[dated["label"] == 1]
    st.caption("Periode: Februari 2024 – April 2026. Tanggal hoaks = tanggal terbit artikel di TurnBackHoax.")
    if dated.empty:
        st.info("Tidak ada artikel bertanggal pada periode dan filter ini.")
        return

    if gran == "Harian":
        dated["periode"] = dated["tanggal_dt"].dt.floor("D")
    elif gran == "Mingguan":
        dated["periode"] = dated["tanggal_dt"].dt.to_period("W").dt.start_time
    else:
        dated["periode"] = dated["tanggal_dt"].dt.to_period("M").dt.to_timestamp()

    ts = dated.groupby(["periode", "label_name"]).size().reset_index(name="jumlah")
    fig = px.line(ts, x="periode", y="jumlah", color="label_name", markers=True,
                  color_discrete_map=COLORS,
                  labels={"periode": "Tanggal", "jumlah": "Jumlah artikel", "label_name": "Label"})
    fig.update_layout(hovermode="x unified")
    st.plotly_chart(fig)
    hx_m = dated[dated["label"] == 1].groupby(dated["tanggal_dt"].dt.to_period("M")).size()
    if not hx_m.empty:
        puncak = hx_m.idxmax()
        st.caption(
            f"Puncak artikel hoaks (per bulan): {BULAN_ID[puncak.month]} {puncak.year} dengan {int(hx_m.max()):,} artikel."
        )
    st.caption(f"Dasar data: {len(dated):,} dari {total:,} artikel (yang memiliki tanggal valid).")


def tab_wordcloud(df: pd.DataFrame):
    st.subheader("Word Cloud")
    try:
        import wordcloud  # noqa: F401
    except ImportError:
        st.error("Library `wordcloud` belum terpasang. Jalankan: `pip install wordcloud`")
        return

    c1, c2 = st.columns(2)
    max_words = c1.slider("Jumlah kata maksimum", 30, 300, 120, step=10)
    extra = c2.text_input("Tambah stopword (pisahkan koma)", "", help="Contoh: katanya, via, share")
    extra_set = {w.strip().lower() for w in extra.split(",") if w.strip()}

    present = [l for l in (1, 0) if (df["label"] == l).any()]
    cmaps = {1: "Reds", 0: "Blues"}
    cols = st.columns(len(present)) if present else []
    for col, lab in zip(cols, present):
        with col:
            st.markdown(f"**{LABEL_MAP[lab]}**")
            freqs = word_frequencies(sample_texts(df, lab))
            freqs = {w: c for w, c in freqs.items() if w not in extra_set}
            if not freqs:
                st.info("Tidak ada kata untuk ditampilkan.")
                continue
            import matplotlib.pyplot as plt

            fig = make_wordcloud_figure(freqs, cmaps[lab], max_words)
            st.pyplot(fig)
            plt.close(fig)
    if len(df) > 0:
        st.caption(f"Untuk kecepatan, tiap kelompok disampel maksimal {SAMPLE_LIMIT:,} artikel.")


def tab_kata(df: pd.DataFrame, full: pd.DataFrame):
    import plotly.express as px

    st.subheader("Kata & frasa teratas")
    present = [l for l in (1, 0) if (df["label"] == l).any()]
    n = st.slider("Jumlah item", 5, 30, 15)

    cols = st.columns(len(present)) if present else []
    for col, lab in zip(cols, present):
        with col:
            name = LABEL_MAP[lab]
            texts = sample_texts(df, lab)
            uni = pd.DataFrame(word_frequencies(texts, n).items(), columns=["kata", "frekuensi"])
            fig = px.bar(uni.sort_values("frekuensi"), x="frekuensi", y="kata", orientation="h",
                         title=f"Kata teratas – {name}", color_discrete_sequence=[COLORS[name]])
            st.plotly_chart(fig)
            bi = bigram_frequencies(texts, n)
            fig = px.bar(bi.sort_values("frekuensi"), x="frekuensi", y="frasa", orientation="h",
                         title=f"Frasa dua kata – {name}", color_discrete_sequence=[COLORS[name]])
            st.plotly_chart(fig)

    st.divider()
    st.subheader("Kata paling khas tiap kelas")
    st.caption("Dihitung dari seluruh dataset (tidak terpengaruh filter) memakai log-odds ratio. "
               "Skor positif = lebih khas hoaks, negatif = lebih khas berita valid.")
    th, tv = sample_texts(full, 1), sample_texts(full, 0)
    if len(th) == 0 or len(tv) == 0:
        st.info("Butuh data hoaks dan valid sekaligus untuk analisis ini.")
        return
    hoax_w, valid_w = distinctive_words(th, tv, top_n=15)
    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(hoax_w.sort_values("skor"), x="skor", y="kata", orientation="h",
                     title="Paling khas HOAKS", color_discrete_sequence=[COLORS["Hoaks"]],
                     hover_data=["freq_hoaks", "freq_valid"])
        st.plotly_chart(fig)
    with c2:
        fig = px.bar(valid_w.sort_values("skor", ascending=False), x="skor", y="kata", orientation="h",
                     title="Paling khas BERITA VALID", color_discrete_sequence=[COLORS["Berita Valid"]],
                     hover_data=["freq_hoaks", "freq_valid"])
        st.plotly_chart(fig)


def tab_explorer(df: pd.DataFrame):
    st.subheader("Penjelajah data")
    view = df[["judul", "label_name", "kategori", "sumber", "tanggal", "jumlah_kata", "url"]].rename(
        columns={"label_name": "label"}
    )
    st.dataframe(
        view.head(5000),
        hide_index=True,
        column_config={"url": st.column_config.LinkColumn("url", display_text="buka")},
    )
    if len(view) > 5000:
        st.caption("Tabel dibatasi 5.000 baris pertama; gunakan tombol unduh untuk data lengkap hasil filter.")
    st.download_button(
        "⬇️ Unduh hasil filter (CSV)",
        data=view.to_csv(index=False).encode("utf-8"),
        file_name="data_terfilter.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("Baca satu artikel")
    options = df.head(300)
    if options.empty:
        return
    pick = st.selectbox(
        "Pilih artikel (300 pertama hasil filter)",
        options.index,
        format_func=lambda i: f"[{options.at[i, 'label_name']}] {options.at[i, 'judul'][:90]}",
    )
    row = df.loc[pick]
    st.markdown(f"**{row['judul']}**  \n{row['label_name']} · {row['sumber']} · tanggal: {row['tanggal']}")
    st.write(row["narasi"][:3000] + ("…" if len(row["narasi"]) > 3000 else ""))
    st.markdown(f"[Buka sumber asli]({row['url']})")


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="Dashboard Hoaks vs Berita Valid", page_icon="🕵️", layout="wide")
    st.title("🕵️ Dashboard Analisis Hoaks vs Berita Valid")
    st.caption("Sumber data: TurnBackHoax (hoaks) dan media nasional (berita valid) · Data teks berbahasa Indonesia")

    uploaded = st.sidebar.file_uploader("Upload dataset lain (opsional)", type=["csv", "gz"])
    try:
        if uploaded is not None:
            full = load_data(uploaded.getvalue())
            st.sidebar.caption(f"Dataset: `{uploaded.name}` (upload)")
        elif DEFAULT_CSV is not None:
            full = load_data(str(DEFAULT_CSV))
            st.sidebar.caption(f"Dataset: `{DEFAULT_CSV.name}`")
        else:
            isi = sorted(p.name for p in _BASE.iterdir())
            st.info(
                "File dataset final (.csv / .csv.gz / .gz) tidak ditemukan di folder aplikasi "
                "(file 'Data_Clean...' yang lama sengaja diabaikan). "
                "Upload dataset final ke repo GitHub atau pakai uploader di sidebar."
            )
            st.caption("File yang terbaca di folder aplikasi: " + ", ".join(f"`{n}`" for n in isi))
            st.stop()
    except Exception as e:  # tampilkan pesan ramah, bukan traceback
        st.error(f"Gagal memuat data: {e}")
        st.stop()

    df = apply_filters(full)
    if df.empty:
        st.warning("Tidak ada data yang cocok dengan filter. Longgarkan filter di sidebar.")
        st.stop()

    # KPI
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total artikel", f"{len(df):,}")
    hoax_n = int((df["label"] == 1).sum())
    k2.metric("Hoaks", f"{hoax_n:,}")
    k2.caption(f"{hoax_n / len(df) * 100:.1f}% dari total")
    k3.metric("Berita valid", f"{len(df) - hoax_n:,}")
    k4.metric("Rata-rata kata / artikel", f"{df['jumlah_kata'].mean():.0f}")

    t1, t2, t3, t4, t5 = st.tabs(
        ["📊 Ringkasan", "📈 Tren Waktu", "☁️ Word Cloud", "🔤 Analisis Kata", "🗂️ Data Explorer"]
    )
    with t1:
        tab_ringkasan(df)
    with t2:
        tab_tren(df)
    with t3:
        tab_wordcloud(df)
    with t4:
        tab_kata(df, full)
    with t5:
        tab_explorer(df)


if __name__ == "__main__":
    main()
