import re
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# =========================
# DASHBOARD COLORS
# =========================
COLOR_SELESAI = "#16A34A"
COLOR_BELUM = "#2563EB"
COLOR_TANGGUH = "#F59E0B"
COLOR_GUGUR = "#DC2626"
COLOR_GREY = "#64748B"

STATUS_COLOR_MAP = {
    "SELESAI": COLOR_SELESAI,
    "BELUM SELESAI": COLOR_BELUM,
    "DITANGGUHKAN": COLOR_TANGGUH,
    "GUGUR": COLOR_GUGUR,
    "BAHARU": "#0EA5E9",
    "SRS": "#8B5CF6",
    "SDD": "#6366F1",
    "TPA": "#EC4899",
    "PEMBANGUNAN": "#14B8A6",
    "SIT": "#F97316",
    "UAT": "#84CC16",
    "TIADA STATUS": COLOR_GREY,
}

# =========================
# CONFIG PAGE
# =========================
st.set_page_config(
    page_title="Dashboard Pemantauan Status Change Request (CR) Sistem mySIKAP",
    page_icon="📊",
    layout="wide"
)

# =========================
# STYLE CUSTOM
# =========================
st.markdown("""
<style>

.stApp {
    background: linear-gradient(180deg, #F8FAFC 0%, #EEF2F7 100%);
}

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    
.main-title {
    font-size: 34px;
    font-weight: 800;
    margin-bottom: 0px;
    color: #1F2937;
}

.sub-title {
    font-size: 15px;
    color: #667085;
    margin-bottom: 22px;
}

.metric-card {
    background: #FFFFFF;
    border: 1px solid #E9EEF5;
    border-radius: 18px;
    padding: 18px 20px;
    box-shadow: 0 4px 14px rgba(18, 38, 63, 0.08);
    border-top: 6px solid var(--accent-color);
}

.metric-card.total { --accent-color: #334155; }
.metric-card.selesai { --accent-color: #16A34A; }
.metric-card.belum { --accent-color: #2563EB; }
.metric-card.tangguh { --accent-color: #F59E0B; }
.metric-card.gugur { --accent-color: #DC2626; }
.metric-card.rate { --accent-color: #7C3AED; }
.metric-label {font-size: 13px; color: #667085; font-weight: 600;}
.metric-value {font-size: 32px; font-weight: 800; margin-top: 4px;}

.section-card {
    background: #FFFFFF;
    border: 1px solid #E9EEF5;
    border-radius: 18px;
    padding: 18px;
    box-shadow: 0 4px 14px rgba(18, 38, 63, 0.07);
    margin-bottom: 16px;
}

/* Hide Streamlit toolbar/header for presentation */
[data-testid="stToolbar"] {
    display: none;
}

[data-testid="stDecoration"] {
    display: none;
}

[data-testid="stStatusWidget"] {
    display: none;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header {
    visibility: hidden;
}

/* Make selectbox look clearer */
div[data-baseweb="select"] > div {
    background-color: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 12px;
    min-height: 48px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.06);
}

div[data-baseweb="select"] > div:hover {
    border-color: #2563EB;
    box-shadow: 0 3px 10px rgba(37, 99, 235, 0.12);
}

.section-divider {
    border: none;
    border-top: 1px solid rgba(148, 163, 184, 0.35);
    margin: 28px 0 22px 0;
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
    if days <= 14:
        return "0-14 hari"
    if days <= 30:
        return "15-30 hari"
    if days <= 60:
        return "31-60 hari"
    if days <= 90:
        return "61-90 hari"
    if days <= 120:
        return "91-120 hari"
    if days <= 180:
        return "121-180 hari"
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
st.markdown('<div class="main-title">Dashboard Pemantauan Status Change Request (CR) Sistem mySIKAP</div>', unsafe_allow_html=True)
#st.markdown('<div class="sub-title">Ringkasan jumlah CR, status siap/belum siap, aging, dan timeline setiap CR.</div>', unsafe_allow_html=True)#

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
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
total_cr = len(filtered)

selesai = (filtered["Status Clean"] == "SELESAI").sum()
tangguh = (filtered["Status Clean"] == "DITANGGUHKAN").sum()
gugur = (filtered["Status Clean"] == "GUGUR").sum()

belum = (
     ~filtered["Status Clean"].isin(["SELESAI", "GUGUR"])
).sum()

completion_rate = (selesai / total_cr * 100) if total_cr else 0

c1, c2, c3, c4, c5 = st.columns(5)
metrics = [
    ("Jumlah CR", total_cr),
    ("Selesai", selesai),
    ("Belum Selesai", belum),
    ("Ditangguhkan", tangguh),
    ("Gugur", gugur),
    ("Peratus Selesai", f"{completion_rate:.1f}%"),
]

metrics_row1 = [
    ("Jumlah CR", total_cr, "total"),
    ("Selesai", selesai, "selesai"),
    ("Belum Selesai", belum, "belum"),
]

metrics_row2 = [
    ("Ditangguhkan", tangguh, "tangguh"),
    ("Gugur", gugur, "gugur"),
    ("Peratus Selesai", f"{completion_rate:.1f}%", "rate"),
]

cols1 = st.columns(3)
for col, (label, value, card_class) in zip(cols1, metrics_row1):
    with col:
        st.markdown(
            f"""
            <div class="metric-card {card_class}">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

cols2 = st.columns(3)
for col, (label, value, card_class) in zip(cols2, metrics_row2):
    with col:
        st.markdown(
            f"""
            <div class="metric-card {card_class}">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================
# CR MENGIKUT BAHAGIAN
# =========================
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.subheader("CR Mengikut Bahagian")

bahagian_status = filtered.copy()

# Group status kepada Selesai / Belum Selesai / Ditangguhkan / Gugur
def ringkasan_status_bahagian(status):
    if status == "SELESAI":
        return "Selesai"
    elif status == "DITANGGUHKAN":
        return "Ditangguhkan"
    elif status == "GUGUR":
        return "Gugur"
    else:
        return "Belum Selesai"

bahagian_status["Ringkasan Status"] = bahagian_status["Status Clean"].apply(
    ringkasan_status_bahagian
)

bahagian_summary = (
    bahagian_status
    .groupby(["Bahagian", "Ringkasan Status"])
    .size()
    .reset_index(name="Jumlah")
)

bahagian_pivot = (
    bahagian_summary
    .pivot(index="Bahagian", columns="Ringkasan Status", values="Jumlah")
    .fillna(0)
    .reset_index()
)

for col in ["Belum Selesai", "Selesai", "Ditangguhkan", "Gugur"]:
    if col not in bahagian_pivot.columns:
        bahagian_pivot[col] = 0

bahagian_pivot["Total"] = (
    bahagian_pivot["Belum Selesai"]
    + bahagian_pivot["Selesai"]
    + bahagian_pivot["Ditangguhkan"]
    + bahagian_pivot["Gugur"]
)

bahagian_pivot = bahagian_pivot.sort_values("Total", ascending=True)

fig_bahagian_status = go.Figure()

fig_bahagian_status.add_trace(
    go.Bar(
        y=bahagian_pivot["Bahagian"],
        x=bahagian_pivot["Belum Selesai"],
        name="Belum Selesai",
        orientation="h",
        marker=dict(color=COLOR_BELUM),
        text=bahagian_pivot["Belum Selesai"],
        textposition="auto",
    )
)

fig_bahagian_status.add_trace(
    go.Bar(
        y=bahagian_pivot["Bahagian"],
        x=bahagian_pivot["Selesai"],
        name="Selesai",
        orientation="h",
        marker=dict(color=COLOR_SELESAI),
        text=bahagian_pivot["Selesai"],
        textposition="auto",
    )
)

fig_bahagian_status.add_trace(
    go.Bar(
        y=bahagian_pivot["Bahagian"],
        x=bahagian_pivot["Ditangguhkan"],
        name="Ditangguhkan",
        orientation="h",
        marker=dict(color=COLOR_TANGGUH),
        text=bahagian_pivot["Ditangguhkan"],
        textposition="auto",
    )
)

fig_bahagian_status.add_trace(
    go.Bar(
        y=bahagian_pivot["Bahagian"],
        x=bahagian_pivot["Gugur"],
        name="Gugur",
        orientation="h",
        marker=dict(color=COLOR_GUGUR),
        text=bahagian_pivot["Gugur"],
        textposition="auto",
    )
)

fig_bahagian_status.update_layout(
    barmode="stack",
    height=560,
    margin=dict(l=10, r=120, t=30, b=80),
    xaxis_title="Jumlah CR",
    yaxis_title="Bahagian",
    legend_title_text="Status",
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.18,
        xanchor="center",
        x=0.5
    ),
    xaxis=dict(
        range=[0, bahagian_pivot["Total"].max() + 10]
    )
)

# Tambah total CR di hujung setiap bar
total_label_x = bahagian_pivot["Total"].max() + 2

fig_bahagian_status.add_trace(
    go.Scatter(
        y=bahagian_pivot["Bahagian"],
        x=[total_label_x] * len(bahagian_pivot),
        mode="text",
        text=["<b>" + str(int(x)) + "</b>" for x in bahagian_pivot["Total"]],
        textposition="middle right",
        textfont=dict(
            size=14,
            color="#111827",
        ),
        showlegend=False,
        hoverinfo="skip",
    )
)

st.plotly_chart(
    fig_bahagian_status,
    use_container_width=True,
    key="chart_bahagian_status_full_row",
    config={"displayModeBar": False}
)


st.markdown('</div>', unsafe_allow_html=True)


# =========================
# STATUS BREAKDOWN
# =========================
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.subheader("Pecahan Mengikut Status")

status_summary = (
    filtered["Status"]
    .fillna("Tiada Status")
    .astype(str)
    .str.upper()
    .str.strip()
    .value_counts()
    .reset_index()
)

status_summary.columns = ["Status", "Jumlah"]

pastel_colors = [
    "#A7C7E7",  # pastel blue
    "#B5EAD7",  # pastel mint
    "#FFDAC1",  # pastel peach
    "#E2F0CB",  # pastel green
    "#C7CEEA",  # pastel lavender
    "#FFB7B2",  # pastel pink
    "#F3D1F4",  # pastel purple
    "#FFF1A8",  # pastel yellow
    "#D5AAFF",  # soft violet
    "#BDE0FE",  # baby blue
]

fig_status = px.pie(
    status_summary,
    names="Status",
    values="Jumlah",
    hole=0.45,
    color="Status",
    color_discrete_map=STATUS_COLOR_MAP,
)

fig_status.update_traces(
    textposition="auto",
    textinfo="label+value",
    pull=[0.02] * len(status_summary),
)

fig_status.update_layout(
    height=480,
    margin=dict(l=10, r=10, t=30, b=10),
    legend_title_text="Status",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.15,
        xanchor="center",
        x=0.5
    )
)

st.plotly_chart(fig_status, use_container_width=True)
selected_status = st.selectbox(
    "Pilih status untuk lihat senarai CR",
    ["Pilih status..."] + status_summary["Status"].tolist(),
    key="selected_status_detail"
)

if selected_status != "Pilih status...":
    status_detail = filtered[
        filtered["Status Clean"] == selected_status
    ].copy()

    st.dataframe(
        status_detail[
            ["Bil", "Bahagian", "Tarikh Permohonan", "CCB", "No. CCB", "Status", "Tajuk CR", "Nota"]
        ],
        use_container_width=True,
        hide_index=True
    )

st.markdown('</div>', unsafe_allow_html=True)

# =========================
# PRIORITY KPI
# =========================
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.subheader("Tempoh CR Aktif")

active_status = ["BAHARU", "SRS", "SDD", "TPA", "PEMBANGUNAN", "SIT", "UAT"]
active_df = filtered[filtered["Status Clean"].isin(active_status)].copy()

aktif_180 = (active_df["Hari Berlalu"] > 180).sum()
aktif_365 = (active_df["Hari Berlalu"] > 365).sum()
tiada_tarikh = active_df["Tarikh Mula"].isna().sum()

left_spacer, p1, p2, right_spacer = st.columns([1, 2, 2, 1])

priority_metrics = [
    ("CR Aktif >180 Hari", aktif_180),
    ("CR Aktif >365 Hari", aktif_365),
]

for col, (label, value) in zip([p1, p2], priority_metrics):
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


# =========================
# AGING BUCKET - CR AKTIF
# =========================

aging_df = filtered[
    (filtered["Kumpulan Status"] == "Belum Selesai")
    & (filtered["Status"].astype(str).str.upper().str.strip() != "DITANGGUHKAN")
].copy()

bucket_order = [
    "0-14 hari",
    "15-30 hari",
    "31-60 hari",
    "61-90 hari",
    "91-120 hari",
    "121-180 hari",
    "181-365 hari",
    ">365 hari",
    "Tiada tarikh",
]

aging_summary = (
    aging_df["Aging Bucket"]
    .value_counts()
    .reindex(bucket_order)
    .fillna(0)
    .reset_index()
)

aging_summary.columns = ["Tempoh CR Aktif", "Jumlah"]

tempoh_colors = [
    "#16A34A",  # 0-14 hari
    "#22C55E",  # 15-30 hari
    "#84CC16",  # 31-60 hari
    "#EAB308",  # 61-90 hari
    "#F59E0B",  # 91-120 hari
    "#F97316",  # 121-180 hari
    "#EF4444",  # 181-365 hari
    "#B91C1C",  # >365 hari
    "#64748B",  # Tiada tarikh
]

fig_aging = px.bar(
    aging_summary,
    x="Tempoh CR Aktif",
    y="Jumlah",
    text="Jumlah",
    color="Tempoh CR Aktif",
    color_discrete_sequence=tempoh_colors,
)

fig_aging.update_layout(
    height=430,
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="Tempoh CR Aktif",
    yaxis_title="Jumlah CR",
    showlegend=False,
)

st.plotly_chart(
    fig_aging,
    use_container_width=True,
    key="chart_aging_bucket_full_row"
)

selected_bucket = st.selectbox(
    "Pilih tempoh untuk lihat senarai CR",
    ["Pilih tempoh..."] + bucket_order,
    key="selected_aging_bucket",
)

if selected_bucket != "Pilih tempoh...":
    aging_table = aging_df[
        aging_df["Aging Bucket"] == selected_bucket
    ].copy()

    aging_table = aging_table.sort_values("Hari Berlalu", ascending=False)

    display_cols = [
        col for col in [
            "Bil", "No. CCB", "Bahagian", "Status",
            "Tarikh Permohonan", "Hari Berlalu", "Aging Bucket"
        ]
        if col in aging_table.columns
    ]

    with st.expander(f"Senarai CR Mengikut Tempoh Aktif: {selected_bucket}", expanded=True):
        st.caption(f"Jumlah CR dalam bucket ini: {len(aging_table)}")

        st.dataframe(
            aging_table[display_cols],
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Detail CR")

        for _, row in aging_table.iterrows():
            no_ccb = row.get("No. CCB", "-")
            status = row.get("Status", "-")
            bahagian = row.get("Bahagian", "-")
            ccb = row.get("CCB", "-")
            tarikh = row.get("Tarikh Permohonan", "-")
            hari = row.get("Hari Berlalu", "-")
            tajuk = row.get("Tajuk CR", "-")
            nota = row.get("Nota", "-")

            with st.expander(f"{no_ccb} | {status} | {bahagian}", expanded=False):
                st.markdown(f"**Tajuk CR:** {tajuk}")
                st.markdown(f"**CCB:** {ccb}")
                st.markdown(f"**Tarikh Permohonan:** {tarikh}")
                st.markdown(f"**Hari Berlalu:** {hari}")
                st.markdown(f"**Nota:** {nota}")
            
st.markdown('</div>', unsafe_allow_html=True)

# =========================
# SENARAI CR KESELURUHAN
# =========================
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
st.subheader("Senarai CR Keseluruhan")

bahagian_options = ["Pilih Bahagian...", "Semua Bahagian"] + sorted(
    filtered["Bahagian"].dropna().unique().tolist()
)

selected_detail_bahagian = st.selectbox(
    "Pilih Bahagian untuk paparan senarai CR",
    bahagian_options,
    key="selected_detail_bahagian"
)

if selected_detail_bahagian != "Pilih Bahagian...":
    detail_df = filtered.copy()

    if selected_detail_bahagian != "Semua Bahagian":
        detail_df = detail_df[
            detail_df["Bahagian"] == selected_detail_bahagian
        ].copy()

    st.caption(f"Jumlah CR dipaparkan: {len(detail_df)}")

    display_cols = [
        col for col in [
            "Bil", "Bahagian", "Tarikh Permohonan", "CCB", "No. CCB", "Tajuk CR",
            "Status", "Kumpulan Status", "Hari Berlalu", "Aging Bucket", "Nota",
            "On-Site", "Off-Site"
        ]
        if col in detail_df.columns
    ]

    st.dataframe(
        detail_df[display_cols],
        use_container_width=True,
        hide_index=True,
    )

    csv_export = detail_df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "⬇️ Download senarai CR dipaparkan",
        data=csv_export,
        file_name="senarai_cr_keseluruhan.csv",
        mime="text/csv",
    )

st.markdown('</div>', unsafe_allow_html=True)


