import re
import pandas as pd
import streamlit as st
import plotly.express as px

# =========================
# CONFIG PAGE
# =========================
st.set_page_config(
    page_title="Dashboard CR mySIKAP",
    page_icon="📊",
    layout="wide"
)

# =========================
# STYLE CUSTOM
# =========================
st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
.main-title {font-size: 34px; font-weight: 800; margin-bottom: 0px;}
.sub-title {font-size: 15px; color: #666; margin-bottom: 22px;}
.metric-card {
    background: white;
    border: 1px solid #E9EEF5;
    border-radius: 18px;
    padding: 18px 20px;
    box-shadow: 0 3px 12px rgba(18, 38, 63, 0.06);
}
.metric-label {font-size: 13px; color: #667085; font-weight: 600;}
.metric-value {font-size: 32px; font-weight: 800; margin-top: 4px;}
.section-card {
    background: white;
    border: 1px solid #E9EEF5;
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 3px 12px rgba(18, 38, 63, 0.05);
    margin-bottom: 16px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# HELPER FUNCTION
# =========================
def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    return df


def parse_request_date(series: pd.Series) -> pd.Series:
    # Format dalam file: 5-Jun-24, 11-Jul-24 etc.
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def extract_date_from_note(text):
    """Extract date like 31/7/2024 daripada column Nota."""
    if pd.isna(text):
        return pd.NaT
    text = str(text)
    match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", text)
    if not match:
        return pd.NaT
    return pd.to_datetime(match.group(1), errors="coerce", dayfirst=True)


def aging_bucket(days):
    if pd.isna(days):
        return "Tiada tarikh"
    if days <= 30:
        return "0-30 hari"
    if days <= 60:
        return "31-60 hari"
    if days <= 90:
        return "61-90 hari"
    if days <= 180:
        return "91-180 hari"
    if days <= 365:
        return "181-365 hari"
    return ">365 hari"


def status_group(status):
    status = str(status).strip().upper()
    if status == "SELESAI":
        return "Selesai"
    if status == "GUGUR":
        return "Gugur"
    return "Belum Selesai"


@st.cache_data
def load_data(uploaded_file=None):
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        # Letak nama CSV yang sama dalam folder GitHub bersama app.py
        df = pd.read_csv("Senarai CR Update Dashboard test 2.csv")

    df = clean_columns(df)

    # Pastikan column wajib wujud
    required_cols = ["Bil", "Bahagian", "Tarikh Permohonan", "CCB", "No. CCB", "Tajuk CR", "Status", "Nota"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"Column tiada dalam file: {missing}")
        st.stop()

    df["Tarikh Mula"] = parse_request_date(df["Tarikh Permohonan"])
    df["Tarikh Dari Nota"] = df["Nota"].apply(extract_date_from_note)
    df["Status Clean"] = df["Status"].astype(str).str.strip().str.upper()
    df["Kumpulan Status"] = df["Status Clean"].apply(status_group)

    today = pd.Timestamp.today().normalize()

    # Untuk timeline:
    # - Kalau selesai dan nota ada tarikh selesai, guna tarikh nota sebagai tamat
    # - Kalau belum selesai, guna hari ini sebagai tamat supaya nampak tempoh berjalan
    df["Tarikh Tamat Timeline"] = df["Tarikh Dari Nota"]
    df.loc[df["Kumpulan Status"].eq("Belum Selesai"), "Tarikh Tamat Timeline"] = today
    df.loc[df["Tarikh Tamat Timeline"].isna(), "Tarikh Tamat Timeline"] = today

    df["Hari Berlalu"] = (today - df["Tarikh Mula"]).dt.days
    df["Aging Bucket"] = df["Hari Berlalu"].apply(aging_bucket)

    df["Tempoh Timeline"] = (df["Tarikh Tamat Timeline"] - df["Tarikh Mula"]).dt.days
    df.loc[df["Tempoh Timeline"] < 0, "Tempoh Timeline"] = None

    df["Label CR"] = df["No. CCB"].fillna(df["Bil"].astype(str)) + " | " + df["Tajuk CR"].astype(str).str.slice(0, 70)

    return df


# =========================
# HEADER
# =========================
st.markdown('<div class="main-title">Dashboard Change Request (CR)</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Ringkasan jumlah CR, status siap/belum siap, aging, dan timeline setiap CR.</div>', unsafe_allow_html=True)

# =========================
# SIDEBAR UPLOAD + FILTER
# =========================
st.sidebar.header("📁 Data")
uploaded_file = st.sidebar.file_uploader("Upload CSV terkini", type=["csv"])
df = load_data(uploaded_file)

st.sidebar.header("🔎 Filter")

bahagian_list = sorted(df["Bahagian"].dropna().unique())
selected_bahagian = st.sidebar.multiselect("Bahagian", bahagian_list, default=bahagian_list)

status_list = sorted(df["Status Clean"].dropna().unique())
selected_status = st.sidebar.multiselect("Status", status_list, default=status_list)

ccb_list = sorted(df["CCB"].dropna().unique())
selected_ccb = st.sidebar.multiselect("CCB", ccb_list, default=ccb_list)

search_text = st.sidebar.text_input("Cari Tajuk CR / No. CCB")

filtered = df[
    df["Bahagian"].isin(selected_bahagian)
    & df["Status Clean"].isin(selected_status)
    & df["CCB"].isin(selected_ccb)
].copy()

if search_text:
    search_text_lower = search_text.lower()
    filtered = filtered[
        filtered["Tajuk CR"].astype(str).str.lower().str.contains(search_text_lower, na=False)
        | filtered["No. CCB"].astype(str).str.lower().str.contains(search_text_lower, na=False)
    ]

# =========================
# KPI METRICS
# =========================
total_cr = len(filtered)
selesai = (filtered["Kumpulan Status"] == "Selesai").sum()
belum = (filtered["Kumpulan Status"] == "Belum Selesai").sum()
gugur = (filtered["Kumpulan Status"] == "Gugur").sum()
completion_rate = (selesai / total_cr * 100) if total_cr else 0

c1, c2, c3, c4, c5 = st.columns(5)
metrics = [
    ("Jumlah CR", total_cr),
    ("Selesai", selesai),
    ("Belum Selesai", belum),
    ("Gugur", gugur),
    ("Completion Rate", f"{completion_rate:.1f}%"),
]

for col, (label, value) in zip([c1, c2, c3, c4, c5], metrics):
    with col:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")

# =========================
# CHARTS ROW 1
# =========================
left, right = st.columns([1, 1])

with left:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Status Siap vs Belum Siap")
    pie_data = filtered[filtered["Kumpulan Status"].isin(["Selesai", "Belum Selesai"])]
    pie_summary = pie_data["Kumpulan Status"].value_counts().reset_index()
    pie_summary.columns = ["Kumpulan Status", "Jumlah"]
    fig_pie = px.pie(
        pie_summary,
        names="Kumpulan Status",
        values="Jumlah",
        hole=0.45,
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label+value")
    fig_pie.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Pecahan Mengikut Status")
    status_summary = filtered["Status Clean"].value_counts().reset_index()
    status_summary.columns = ["Status", "Jumlah"]
    fig_status = px.bar(status_summary, x="Jumlah", y="Status", orientation="h", text="Jumlah")
    fig_status.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_status, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# CHARTS ROW 2: BAHAGIAN + AGING
# =========================
left2, right2 = st.columns([1, 1])

with left2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Jumlah CR Mengikut Bahagian")
    bahagian_summary = filtered["Bahagian"].value_counts().reset_index()
    bahagian_summary.columns = ["Bahagian", "Jumlah"]
    fig_bahagian = px.bar(bahagian_summary, x="Jumlah", y="Bahagian", orientation="h", text="Jumlah")
    fig_bahagian.update_layout(height=430, margin=dict(l=10, r=10, t=30, b=10), yaxis={"categoryorder": "total ascending"})
    st.plotly_chart(fig_bahagian, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with right2:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Aging Bucket - Belum Selesai")
    
    aging_df = filtered[
    (filtered["Kumpulan Status"] == "Belum Selesai")
    & (filtered["Status"].astype(str).str.upper().str.strip() != "DITANGGUHKAN")
].copy()
    
    bucket_order = ["0-30 hari", "31-60 hari", "61-90 hari", "91-180 hari", "181-365 hari", ">365 hari", "Tiada tarikh"]
    aging_summary = aging_df["Aging Bucket"].value_counts().reindex(bucket_order).dropna().reset_index()
    aging_summary.columns = ["Aging Bucket", "Jumlah"]
    fig_aging = px.bar(aging_summary, x="Aging Bucket", y="Jumlah", text="Jumlah")
    fig_aging.update_layout(height=430, margin=dict(l=10, r=10, t=30, b=10), xaxis_title="", yaxis_title="Jumlah CR")
    st.plotly_chart(fig_aging, use_container_width=True)

    selected_bucket = st.selectbox("Klik/pilih bucket untuk lihat senarai CR", ["Semua"] + bucket_order)
    aging_table = aging_df.copy()
    if selected_bucket != "Semua":
        aging_table = aging_table[aging_table["Aging Bucket"] == selected_bucket]

    st.dataframe(
        aging_table[["No. CCB", "Bahagian", "Tajuk CR", "Status", "Tarikh Mula", "Hari Berlalu", "Aging Bucket", "Nota"]],
        use_container_width=True,
        hide_index=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

# =========================
# TIMELINE SETIAP CR
# =========================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("Timeline Setiap CR")
st.caption("Untuk CR belum selesai, tarikh tamat timeline dikira sehingga hari ini. Untuk CR selesai, sistem cuba ambil tarikh selesai daripada column Nota.")

timeline_df = filtered.dropna(subset=["Tarikh Mula", "Tarikh Tamat Timeline"]).copy()

# Elak timeline terlalu padat: user boleh pilih jumlah row
max_rows = st.slider("Jumlah CR dipaparkan dalam timeline", min_value=10, max_value=min(168, max(10, len(timeline_df))), value=min(60, max(10, len(timeline_df))), step=10)

timeline_df = timeline_df.sort_values(["Tarikh Mula", "No. CCB"]).head(max_rows)

fig_timeline = px.timeline(
    timeline_df,
    x_start="Tarikh Mula",
    x_end="Tarikh Tamat Timeline",
    y="Label CR",
    color="Kumpulan Status",
    hover_data={
        "No. CCB": True,
        "Bahagian": True,
        "Status Clean": True,
        "Tarikh Mula": True,
        "Tarikh Tamat Timeline": True,
        "Tempoh Timeline": True,
        "Nota": True,
        "Label CR": False,
    },
)
fig_timeline.update_yaxes(autorange="reversed")
fig_timeline.update_layout(
    height=max(520, max_rows * 22),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="Tarikh",
    yaxis_title="CR",
)
st.plotly_chart(fig_timeline, use_container_width=True)
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# DETAIL TABLE
# =========================
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("Senarai Detail CR")
st.dataframe(
    filtered[[
        "Bil", "Bahagian", "Tarikh Permohonan", "CCB", "No. CCB", "Tajuk CR",
        "Status", "Kumpulan Status", "Hari Berlalu", "Aging Bucket", "Nota", "On-Site", "Off-Site"
    ]],
    use_container_width=True,
    hide_index=True,
)

csv_export = filtered.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "⬇️ Download data selepas filter",
    data=csv_export,
    file_name="cr_dashboard_filtered.csv",
    mime="text/csv",
)
st.markdown('</div>', unsafe_allow_html=True)
