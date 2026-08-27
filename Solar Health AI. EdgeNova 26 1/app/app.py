"""
app.py - Streamlit Dashboard for SolarPanel Health AI
Team Optisuns - SolarPanel Health AI

---------------------------------
To Run the application
---------------------------------
# On Mac/Linux
./run.sh

# On Windows
python app/data_generator.py
streamlit run app/app.py
---------------------------------

Design note: this dashboard is styled as a "fleet control room" for a solar
farm operator — dark instrument-panel surfaces, an amber energy accent, and
monospace numerals for anything that reads like a live readout. The theme
tokens live in .streamlit/config.toml (native widgets) and in the CSS block
below (layout/typography). Change TOKENS below to re-theme everything.
"""

import base64
import os
import sys
from datetime import datetime
from io import BytesIO

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import qrcode
import streamlit as st
from streamlit_folium import st_folium

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from degradation_engine import calculate_metrics, calculate_financial_loss, get_panel_summary

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="SolarPanel Health AI",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

REQUIRED_COLUMNS = [
    "panel_id", "manufacturer", "original_wattage", "current_wattage",
    "years_operating", "efficiency", "temperature", "dust_level",
    "installation_date",
]

DEMO_PATH = "data/solar_farm_data.csv"

# ---------- DESIGN TOKENS ----------
TOKENS = {
    "void": "#10141B",       # page background
    "surface": "#1A2029",    # card / panel background
    "surface_hi": "#212836", # elevated surface (hover, active)
    "line": "#2A3140",       # hairline borders
    "text": "#EDF0F5",       # primary text
    "muted": "#8992A6",      # secondary text
    "ember": "#FFB640",      # brand / energy accent
    "keep": "#34D399",       # healthy / keep
    "repurpose": "#FFB640",  # degrading / repurpose (shares ember)
    "recycle": "#F87171",    # end-of-life / recycle
}
COLOR_MAP = {"KEEP": TOKENS["keep"], "REPURPOSE": TOKENS["repurpose"], "RECYCLE": TOKENS["recycle"]}
EMOJI_MAP = {"KEEP": "●", "REPURPOSE": "●", "RECYCLE": "●"}

PLOTLY_LAYOUT = dict(
    paper_bgcolor=TOKENS["surface"],
    plot_bgcolor=TOKENS["surface"],
    font=dict(color=TOKENS["muted"], family="Inter, sans-serif", size=12),
    title_font=dict(color=TOKENS["text"], family="Space Grotesk, sans-serif", size=16),
    margin=dict(t=50, b=30, l=10, r=10),
)

# ============================================================
# STYLING
# ============================================================
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    .stApp {{
        background: radial-gradient(circle at 15% 0%, #171d27 0%, {TOKENS['void']} 45%);
    }}

    h1, h2, h3, h4 {{
        font-family: 'Space Grotesk', sans-serif !important;
        letter-spacing: -0.01em;
        color: {TOKENS['text']};
    }}

    /* ---------- HERO ---------- */
    .op-eyebrow {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72em;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: {TOKENS['ember']};
        margin-bottom: 2px;
    }}
    .op-title {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.1em;
        font-weight: 700;
        color: {TOKENS['text']};
        margin: 0;
        line-height: 1.1;
    }}
    .op-subtitle {{
        color: {TOKENS['muted']};
        font-size: 0.95em;
        margin-top: 4px;
    }}
    .op-status {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78em;
        color: {TOKENS['muted']};
        text-align: right;
        line-height: 1.6;
    }}
    .op-status b {{ color: {TOKENS['text']}; }}

    /* ---------- SIGNATURE: FLEET HEALTH HORIZON ---------- */
    .op-horizon-wrap {{
        margin: 18px 0 6px 0;
    }}
    .op-horizon-label {{
        display: flex;
        justify-content: space-between;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72em;
        color: {TOKENS['muted']};
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }}
    .op-horizon {{
        display: flex;
        width: 100%;
        height: 10px;
        border-radius: 6px;
        overflow: hidden;
        border: 1px solid {TOKENS['line']};
        box-shadow: 0 0 24px -6px rgba(255,182,64,0.35);
    }}
    .op-horizon-seg {{ height: 100%; }}

    /* ---------- CARDS / METRICS ---------- */
    div[data-testid="stMetric"] {{
        background: {TOKENS['surface']};
        border: 1px solid {TOKENS['line']};
        border-top: 2px solid {TOKENS['ember']};
        border-radius: 8px;
        padding: 14px 16px 10px 16px;
    }}
    div[data-testid="stMetricLabel"] {{
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.72em !important;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: {TOKENS['muted']} !important;
    }}
    div[data-testid="stMetricValue"] {{
        font-family: 'JetBrains Mono', monospace;
        color: {TOKENS['text']} !important;
        font-size: clamp(0.95rem, 1.6vw, 1.55rem) !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: clip !important;
        word-break: break-word;
        line-height: 1.25 !important;
    }}
    div[data-testid="stMetricValue"] * {{
        overflow: visible !important;
        text-overflow: clip !important;
        white-space: normal !important;
    }}
    div[data-testid="stMetric"] {{
        min-width: 0;
    }}

    /* ---------- TABS ---------- */
    button[data-baseweb="tab"] {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.92em;
        color: {TOKENS['muted']};
    }}
    button[data-baseweb="tab"][aria-selected="true"] {{
        color: {TOKENS['ember']} !important;
    }}
    div[data-baseweb="tab-highlight"] {{
        background-color: {TOKENS['ember']} !important;
    }}
    div[data-baseweb="tab-border"] {{
        background-color: {TOKENS['line']} !important;
    }}

    /* ---------- SIDEBAR ---------- */
    section[data-testid="stSidebar"] {{
        background: {TOKENS['surface']};
        border-right: 1px solid {TOKENS['line']};
    }}
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {{
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.9em !important;
        letter-spacing: 0.03em;
    }}

    /* ---------- EXPANDER / CONTAINERS ---------- */
    div[data-testid="stExpander"] {{
        background: {TOKENS['surface']};
        border: 1px solid {TOKENS['line']};
        border-radius: 8px;
    }}

    /* ---------- RADIO AS SEGMENTED BUTTONS (Sort list by) ---------- */
    div[data-testid="stRadio"] > div[role="radiogroup"] {{
        gap: 6px;
        flex-wrap: wrap;
    }}
    div[data-testid="stRadio"] label {{
        background: {TOKENS['surface_hi']};
        border: 1px solid {TOKENS['line']};
        border-radius: 20px;
        padding: 4px 14px;
        margin: 0 !important;
        cursor: pointer;
    }}

    /* ---------- BUTTONS ---------- */
    .stButton > button, .stDownloadButton > button {{
        font-family: 'Space Grotesk', sans-serif;
        border: 1px solid {TOKENS['line']};
        background: {TOKENS['surface_hi']};
        color: {TOKENS['text']};
        border-radius: 6px;
        transition: border-color 0.15s ease;
    }}
    .stButton > button:hover, .stDownloadButton > button:hover {{
        border-color: {TOKENS['ember']};
        color: {TOKENS['ember']};
    }}

    /* ---------- BADGES ---------- */
    .op-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 10px;
        border-radius: 20px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75em;
        font-weight: 600;
        border: 1px solid currentColor;
    }}

    /* ---------- MONO UTILITY ---------- */
    .op-mono {{ font-family: 'JetBrains Mono', monospace; }}

    hr {{ border-color: {TOKENS['line']} !important; }}

    .op-footer {{
        text-align: center;
        color: {TOKENS['muted']};
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75em;
        letter-spacing: 0.04em;
        padding: 10px 0 4px 0;
    }}
    .op-footer b {{ color: {TOKENS['ember']}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


def style_fig(fig, height=380):
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    fig.update_xaxes(gridcolor=TOKENS["line"], zerolinecolor=TOKENS["line"])
    fig.update_yaxes(gridcolor=TOKENS["line"], zerolinecolor=TOKENS["line"])
    return fig


def rec_badge(rec: str) -> str:
    color = COLOR_MAP.get(rec, TOKENS["muted"])
    return f'<span class="op-badge" style="color:{color}">● {rec}</span>'


# ============================================================
# HELPERS
# ============================================================
@st.cache_data(show_spinner=False)
def load_csv(path_or_buffer):
    return pd.read_csv(path_or_buffer)


@st.cache_data(show_spinner=False)
def load_csv_from_path(path: str, _mtime: float):
    """Cached CSV load keyed on file path + last-modified time.

    Using cache_data on a plain path string caches by the string value only,
    so regenerating data/solar_farm_data.csv (e.g. via data_generator.py)
    keeps serving the stale, previously-cached DataFrame. Passing the file's
    mtime as part of the cache key busts the cache whenever the file
    actually changes on disk.
    """
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def run_engine(df: pd.DataFrame):
    results = calculate_metrics(df)

    # Defensive: some versions of calculate_metrics() only return the
    # columns it computes on, silently dropping extra input columns like
    # 'farm' / 'block' / 'latitude' / 'longitude'. Re-attach anything that got lost,
    # keyed on panel_id, so features like the Fleet Map keep working
    # regardless of how the engine is implemented.
    if "panel_id" in df.columns and "panel_id" in results.columns:
        dropped_cols = [c for c in df.columns if c not in results.columns and c != "panel_id"]
        if dropped_cols:
            results = results.merge(df[["panel_id"] + dropped_cols], on="panel_id", how="left")

    financial = calculate_financial_loss(results)
    summary = get_panel_summary(results)
    return results, financial, summary


def validate_columns(df: pd.DataFrame):
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]


def build_fleet_map(df: pd.DataFrame) -> folium.Map:
    """Build a dark-themed folium map with one colored dot per panel (no clustering).

    Deliberately NOT cached: folium.Map is a stateful object with an internal
    map id baked in at creation time. Reusing the same cached instance across
    Streamlit reruns (e.g. the rerun triggered by clicking a marker) confuses
    Leaflet's re-initialization and the map disappears after the first click.
    Rebuilding per-render is cheap enough at ~1000 markers, especially with
    prefer_canvas for faster vector rendering.
    """
    center_lat = df["latitude"].mean()
    center_lon = df["longitude"].mean()

    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    # None of these require an API key or signup (unlike CartoDB's raster
    # basemaps, which now do). Satellite is the default. `show=False` on the
    # other two keeps them dormant until picked from the LayerControl —
    # without it, all three render stacked on top of each other and
    # whichever was added last visually wins regardless of any selection.
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
        name="Satellite",
        control=True,
        overlay=False,
        show=True,
    ).add_to(fmap)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Esri, USGS, NOAA",
        name="Terrain",
        control=True,
        overlay=False,
        show=False,
    ).add_to(fmap)
    folium.TileLayer(
        tiles="https://services.arcgisonline.com/arcgis/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ",
        name="Dark (clean)",
        control=True,
        overlay=False,
        show=False,
    ).add_to(fmap)
    folium.LayerControl(collapsed=True).add_to(fmap)

    for _, panel in df.iterrows():
        if pd.isna(panel.get("latitude")) or pd.isna(panel.get("longitude")):
            continue
        color = COLOR_MAP.get(panel["recommendation"], TOKENS["muted"])
        block = panel.get("block", "")
        popup_html = f"""
        <div style="font-family:'Inter',sans-serif; background:{TOKENS['surface']};
                    color:{TOKENS['text']}; padding:10px 12px; border-radius:6px; min-width:200px;">
            <div style="font-family:'JetBrains Mono',monospace; font-weight:600; color:{TOKENS['ember']};
                        font-size:0.85em; margin-bottom:4px;">{panel['panel_id']}</div>
            {f'<div style="color:{TOKENS["muted"]}; font-size:0.78em; margin-bottom:6px;">{block}</div>' if block else ''}
            <div style="font-size:0.82em; line-height:1.6;">
                <b>Manufacturer:</b> {panel['manufacturer']}<br>
                <b>Efficiency:</b> {panel['efficiency']:.1f}%<br>
                <b>Health Score:</b> {panel['health_score']:.1f}/100<br>
                <b>Remaining Life:</b> {panel['remaining_life']:.1f} yrs<br>
                <b>Recommendation:</b> <span style="color:{color}; font-weight:600;">{panel['recommendation']}</span>
            </div>
        </div>
        """
        folium.CircleMarker(
            location=[panel["latitude"], panel["longitude"]],
            radius=5,
            color="#FFFFFF",
            fill=True,
            fill_color=color,
            fill_opacity=0.95,
            weight=1.5,
            opacity=0.9,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=f"{panel['panel_id']} — {panel['recommendation']}",
        ).add_to(fmap)

    return fmap


@st.cache_data(show_spinner=False)
def make_qr_code(data: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=4, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(data)
    qr.make()
    img = qr.make_image(fill_color=TOKENS["text"], back_color=TOKENS["surface"])
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


# ============================================================
# SIDEBAR
# ============================================================
st.sidebar.markdown(
    f"""
    <div style="text-align: center; padding: 14px 0 6px 0;">
        <div style="font-size: 2em;">☀️</div>
        <div style="font-family:'Space Grotesk',sans-serif; font-size:1.3em; font-weight:700; color:{TOKENS['ember']};">Optisuns</div>
        <div class="op-mono" style="font-size:0.72em; color:{TOKENS['muted']}; letter-spacing:0.08em;">FLEET CONTROL</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

st.sidebar.markdown("**📊 Data Source**")
uploaded_file = st.sidebar.file_uploader("Upload CSV", type=["csv"])

col_a, col_b = st.sidebar.columns(2)
with col_a:
    load_demo = st.button("📊 Demo Data", width='stretch')
with col_b:
    clear_data = st.button("🗑️ Clear", width='stretch')

if clear_data:
    st.session_state.pop("df", None)
    st.rerun()

if load_demo:
    if os.path.exists(DEMO_PATH):
        try:
            st.session_state["df"] = load_csv_from_path(DEMO_PATH, os.path.getmtime(DEMO_PATH))
            st.session_state["source_label"] = "demo data"
            st.sidebar.success("✅ Demo data loaded!")
        except Exception as e:
            st.sidebar.error(f"❌ Failed to load demo data: {e}")
    else:
        st.sidebar.error("❌ Demo data not found. Run data_generator.py first.")

st.sidebar.markdown("---")
st.sidebar.markdown(
    f'<span class="op-mono" style="font-size:0.72em; color:{TOKENS["muted"]};">'
    f'TEAM OPTISUNS<br>CIRCULAR SOLAR ECONOMY</span>',
    unsafe_allow_html=True,
)

# ============================================================
# LOAD DATA
# ============================================================
df, load_error = None, None

if uploaded_file is not None:
    try:
        df = load_csv(uploaded_file)
        st.session_state["df"] = df
        st.session_state["source_label"] = f"upload: {uploaded_file.name}"
    except Exception as e:
        load_error = f"Could not read that CSV: {e}"
elif "df" in st.session_state:
    df = st.session_state["df"]

if df is not None:
    missing_cols = validate_columns(df)
    if missing_cols:
        load_error = f"Uploaded file is missing required column(s): {', '.join(missing_cols)}. See the expected format below."
        df = None
        st.session_state.pop("df", None)

# ============================================================
# HERO
# ============================================================
title_col, status_col = st.columns([3, 1])
with title_col:
    st.markdown('<div class="op-eyebrow">SOLAR ASSET INTELLIGENCE</div>', unsafe_allow_html=True)
    st.markdown('<div class="op-title">☀️ SolarPanel Health AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="op-subtitle">Data-driven lifecycle management for solar fleets</div>', unsafe_allow_html=True)
with status_col:
    if df is not None:
        st.markdown(
            f"""<div class="op-status">SOURCE<br><b>{st.session_state.get('source_label', 'data')}</b><br>
            {len(df):,} PANELS</div>""",
            unsafe_allow_html=True,
        )

if load_error:
    st.error(f"⚠️ {load_error}")

# ============================================================
# MAIN
# ============================================================
if df is not None:
    with st.spinner("Analyzing panel health..."):
        results, financial, summary = run_engine(df)

    # ---------- FILTERS ----------
    with st.expander("🔎 Filters", expanded=False):
        f1, f2, f3 = st.columns(3)
        with f1:
            manufacturers = sorted(results["manufacturer"].dropna().unique().tolist())
            selected_mfrs = st.multiselect("Manufacturer", manufacturers, default=manufacturers)
        with f2:
            recs = sorted(results["recommendation"].dropna().unique().tolist())
            selected_recs = st.multiselect("Recommendation", recs, default=recs)
        with f3:
            eff_min, eff_max = float(results["efficiency"].min()), float(results["efficiency"].max())
            eff_range = st.slider(
                "Efficiency range (%)",
                min_value=float(min(0, eff_min)), max_value=float(max(100, eff_max)),
                value=(eff_min, eff_max),
            )

    filtered = results[
        results["manufacturer"].isin(selected_mfrs)
        & results["recommendation"].isin(selected_recs)
        & results["efficiency"].between(eff_range[0], eff_range[1])
    ]

    if filtered.empty:
        st.warning("No panels match the current filters. Adjust filters above to see data.")
        st.stop()

    filt_financial = calculate_financial_loss(filtered)
    filt_summary = get_panel_summary(filtered)

    # Derive KEEP/REPURPOSE/RECYCLE counts directly from the recommendation
    # column rather than from get_panel_summary()'s separately-computed
    # threshold buckets. The two can disagree (e.g. a panel efficiency-
    # bucketed as "end of life" but not actually flagged RECYCLE), which is
    # why "Panels to Replace" could show a different number than the actual
    # count of RECYCLE panels. Counting from `recommendation` everywhere
    # keeps every number on the page consistent with the badges/charts.
    n_keep = int((filtered["recommendation"] == "KEEP").sum())
    n_repurpose = int((filtered["recommendation"] == "REPURPOSE").sum())
    n_recycle = int((filtered["recommendation"] == "RECYCLE").sum())

    # ---------- SIGNATURE: FLEET HEALTH HORIZON ----------
    total = len(filtered)
    keep_pct = n_keep / total * 100
    repurpose_pct = n_repurpose / total * 100
    recycle_pct = n_recycle / total * 100

    st.markdown(
        f"""
        <div class="op-horizon-wrap">
            <div class="op-horizon-label">
                <span>FLEET HEALTH HORIZON</span>
                <span>{keep_pct:.0f}% KEEP · {repurpose_pct:.0f}% REPURPOSE · {recycle_pct:.0f}% RECYCLE</span>
            </div>
            <div class="op-horizon">
                <div class="op-horizon-seg" style="width:{keep_pct}%; background:{TOKENS['keep']};"></div>
                <div class="op-horizon-seg" style="width:{repurpose_pct}%; background:{TOKENS['repurpose']};"></div>
                <div class="op-horizon-seg" style="width:{recycle_pct}%; background:{TOKENS['recycle']};"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------- METRICS ROW ----------
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Panels", f"{total:,}")
    m2.metric("Healthy (KEEP)", f"{n_keep:,}")
    m3.metric("Degrading (REPURPOSE)", f"{n_repurpose:,}")
    m4.metric("End-of-Life (RECYCLE)", f"{n_recycle:,}")
    m5.metric("Annual Loss", filt_financial["total_loss_formatted"])

    st.markdown("---")

    tab_overview, tab_map, tab_explorer, tab_financial, tab_export = st.tabs(
        ["Overview", "Fleet Map", "Panel Explorer", "Financial Impact", "Export"]
    )

    # ===== OVERVIEW TAB =====
    with tab_overview:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Efficiency Distribution")
            fig = px.histogram(
                filtered, x="efficiency", nbins=30, color="recommendation",
                color_discrete_map=COLOR_MAP,
                labels={"efficiency": "Efficiency (%)", "count": "Panels"},
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01), bargap=0.05)
            st.plotly_chart(style_fig(fig), width='stretch')

        with c2:
            st.markdown("##### Recommendation Breakdown")
            rec_counts = filtered["recommendation"].value_counts().reset_index()
            rec_counts.columns = ["Recommendation", "Count"]
            fig = px.pie(
                rec_counts, values="Count", names="Recommendation", color="Recommendation",
                color_discrete_map=COLOR_MAP, hole=0.55,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label", textfont_color=TOKENS["void"])
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig), width='stretch')

        c3, c4 = st.columns(2)
        with c3:
            st.markdown("##### Degradation vs. Age")
            fig = px.scatter(
                filtered, x="years_operating", y="degradation_rate", color="recommendation",
                color_discrete_map=COLOR_MAP, opacity=0.7,
                labels={"years_operating": "Years Operating", "degradation_rate": "Degradation Rate (%/yr)"},
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(style_fig(fig, height=340), width='stretch')

        with c4:
            st.markdown("##### Panel Count by Manufacturer")
            mfr_counts = filtered["manufacturer"].value_counts().reset_index()
            mfr_counts.columns = ["Manufacturer", "Count"]
            fig = px.bar(
                mfr_counts.sort_values("Count"), x="Count", y="Manufacturer", orientation="h",
                color_discrete_sequence=[TOKENS["ember"]],
            )
            st.plotly_chart(style_fig(fig, height=340), width='stretch')

        st.markdown("##### Recommendations Summary")
        rec_summary = filtered.groupby("recommendation").agg(
            Count=("panel_id", "count"),
            **{
                "Avg Efficiency (%)": ("efficiency", "mean"),
                "Avg Remaining Life (years)": ("remaining_life", "mean"),
                "Avg Original (W)": ("original_wattage", "mean"),
                "Avg Current (W)": ("current_wattage", "mean"),
            },
        ).reset_index().rename(columns={"recommendation": "Recommendation"})
        rec_summary["Avg Efficiency (%)"] = rec_summary["Avg Efficiency (%)"].round(1)
        rec_summary["Avg Remaining Life (years)"] = rec_summary["Avg Remaining Life (years)"].round(1)
        rec_summary["Avg Original (W)"] = rec_summary["Avg Original (W)"].round(0).astype(int)
        rec_summary["Avg Current (W)"] = rec_summary["Avg Current (W)"].round(0).astype(int)
        st.dataframe(rec_summary, width='stretch', hide_index=True)

    # ===== MAP TAB =====
    with tab_map:
        st.markdown("##### Fleet Map")

        has_location = "latitude" in filtered.columns and "longitude" in filtered.columns
        if has_location:
            has_location = filtered["latitude"].notna().any() and filtered["longitude"].notna().any()

        if not has_location:
            st.warning("This dataset has no `latitude` / `longitude` columns, so panels can't be placed on a map.")
            st.caption(f"Columns currently in the filtered data: {', '.join(filtered.columns.tolist())}")
            st.caption(
                "Add `latitude` and `longitude` columns to your CSV (or regenerate demo data with "
                "the updated `data_generator.py`) to enable this view."
            )
        else:
            geo = filtered.dropna(subset=["latitude", "longitude"])
            farm_name = geo["farm"].iloc[0] if "farm" in geo.columns and len(geo) else None
            caption = f"{len(geo):,} of {len(filtered):,} filtered panels have location data."
            if farm_name:
                caption = f"**{farm_name}** — " + caption
            st.caption(caption + " Click a marker for details.")

            g1, g2, g3 = st.columns(3)
            g1.metric("On Map", f"{len(geo):,}")
            g2.metric("Blocks", f"{geo['block'].nunique():,}" if "block" in geo.columns else "—")
            g3.markdown(
                f"""<div style="display:flex; gap:16px; padding-top:22px;" class="op-mono">
                <span style="color:{TOKENS['keep']}">● KEEP</span>
                <span style="color:{TOKENS['repurpose']}">● REPURPOSE</span>
                <span style="color:{TOKENS['recycle']}">● RECYCLE</span>
                </div>""",
                unsafe_allow_html=True,
            )

            try:
                fmap = build_fleet_map(geo)
                map_state = st_folium(
                    fmap, width=None, height=520, returned_objects=["last_object_clicked_tooltip"],
                    key="fleet_map",
                )
            except Exception as e:
                st.error(f"Map failed to render: {e}")
                map_state = None

            clicked = map_state.get("last_object_clicked_tooltip") if map_state else None
            if clicked:
                clicked_id = clicked.split(" — ")[0].strip()
                match = geo[geo["panel_id"] == clicked_id]
                if not match.empty:
                    panel = match.iloc[0]
                    st.markdown("---")
                    st.markdown(f"**Selected: `{panel['panel_id']}`** {rec_badge(panel['recommendation'])}", unsafe_allow_html=True)
                    st.markdown(
                        f"""<div class="op-mono" style="font-size:0.85em; line-height:1.9;">
                        <b>MANUFACTURER</b> &nbsp; {panel['manufacturer']} &nbsp;&nbsp;
                        <b>EFFICIENCY</b> &nbsp; {panel['efficiency']:.1f}% &nbsp;&nbsp;
                        <b>HEALTH SCORE</b> &nbsp; {panel['health_score']:.1f}/100 &nbsp;&nbsp;
                        <b>REMAINING LIFE</b> &nbsp; {panel['remaining_life']:.1f} yrs
                        </div>""",
                        unsafe_allow_html=True,
                    )

    # ===== PANEL EXPLORER TAB =====
    with tab_explorer:
        st.markdown("##### Panel Detail Viewer")
        search_col, sort_col = st.columns([2, 1])
        with search_col:
            search_term = st.text_input("Search by Panel ID", placeholder="e.g. PANEL-00001")
        with sort_col:
            sort_labels = {
                "panel_id": "Panel ID", "efficiency": "Efficiency",
                "health_score": "Health Score", "remaining_life": "Remaining Life",
            }
            sort_by = st.radio(
                "Sort list by", list(sort_labels.keys()),
                format_func=lambda k: sort_labels[k], horizontal=True,
            )

        panel_pool = filtered.sort_values(sort_by)
        if search_term:
            panel_pool = panel_pool[panel_pool["panel_id"].astype(str).str.contains(search_term, case=False)]

        if panel_pool.empty:
            st.info("No panels match that search.")
        else:
            selected_panel = st.selectbox("Select Panel ID", panel_pool["panel_id"].unique())
            panel = filtered[filtered["panel_id"] == selected_panel].iloc[0]

            d1, d2, d3 = st.columns([2, 1, 1])
            with d1:
                st.markdown(
                    f"""
                    <div class="op-mono" style="line-height:2;">
                    <b>PANEL ID</b> &nbsp; {panel['panel_id']}<br>
                    <b>MANUFACTURER</b> &nbsp; {panel['manufacturer']}<br>
                    <b>INSTALLED</b> &nbsp; {panel['installation_date']}<br>
                    <b>YEARS OPERATING</b> &nbsp; {panel['years_operating']}<br>
                    <b>ORIGINAL WATTAGE</b> &nbsp; {panel['original_wattage']}W<br>
                    <b>CURRENT WATTAGE</b> &nbsp; {panel['current_wattage']:.1f}W<br>
                    <b>DEGRADATION RATE</b> &nbsp; {panel['degradation_rate']:.2f}%/yr<br>
                    <b>REMAINING LIFE</b> &nbsp; {panel['remaining_life']:.1f} yrs<br>
                    <b>TEMPERATURE</b> &nbsp; {panel['temperature']:.1f}°C<br>
                    <b>DUST LEVEL</b> &nbsp; {panel['dust_level']:.1f}%<br>
                    </div>
                    <div style="margin-top:10px;">{rec_badge(panel['recommendation'])}</div>
                    """,
                    unsafe_allow_html=True,
                )

            with d2:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=panel["health_score"],
                    number={"font": {"color": TOKENS["text"], "family": "JetBrains Mono"}},
                    title={"text": "Health Score", "font": {"color": TOKENS["muted"], "size": 13}},
                    domain={"x": [0, 1], "y": [0, 1]},
                    gauge={
                        "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": TOKENS["muted"]},
                        "bar": {"color": TOKENS["ember"]},
                        "bgcolor": TOKENS["surface"],
                        "borderwidth": 1,
                        "bordercolor": TOKENS["line"],
                        "steps": [
                            {"range": [0, 70], "color": "#3a2528"},
                            {"range": [70, 85], "color": "#3a3323"},
                            {"range": [85, 100], "color": "#1f3a30"},
                        ],
                        "threshold": {"line": {"color": TOKENS["ember"], "width": 3}, "thickness": 0.8, "value": panel["health_score"]},
                    },
                ))
                fig.update_layout(paper_bgcolor=TOKENS["surface"], height=250, margin=dict(t=40, b=10))
                st.plotly_chart(fig, width='stretch')

            with d3:
                qr_data = (
                    f"Panel: {panel['panel_id']}|Manufacturer: {panel['manufacturer']}|"
                    f"Efficiency: {panel['efficiency']}%|Recommendation: {panel['recommendation']}"
                )
                img_str = make_qr_code(qr_data)
                st.markdown(
                    f"""<div style="background:{TOKENS['surface']}; border:1px solid {TOKENS['line']};
                    border-radius:8px; padding:10px; text-align:center;">
                    <img src="data:image/png;base64,{img_str}" width="180"/>
                    <div class="op-mono" style="font-size:0.7em; color:{TOKENS['muted']}; margin-top:6px;">
                    SCAN → {panel['panel_id']}</div></div>""",
                    unsafe_allow_html=True,
                )

            st.markdown("---")
            with st.expander("↔️ Compare with another panel"):
                other_options = [p for p in panel_pool["panel_id"].unique() if p != selected_panel]
                if other_options:
                    other_id = st.selectbox("Compare against", other_options, key="compare_panel")
                    other = filtered[filtered["panel_id"] == other_id].iloc[0]
                    compare_df = pd.DataFrame({
                        "Metric": ["Efficiency (%)", "Health Score", "Remaining Life (yrs)", "Degradation Rate (%/yr)"],
                        panel["panel_id"]: [panel["efficiency"], panel["health_score"], panel["remaining_life"], panel["degradation_rate"]],
                        other["panel_id"]: [other["efficiency"], other["health_score"], other["remaining_life"], other["degradation_rate"]],
                    })
                    st.dataframe(compare_df, width='stretch', hide_index=True)
                else:
                    st.caption("No other panels in the current filter to compare against.")

    # ===== FINANCIAL TAB =====
    with tab_financial:
        st.markdown("##### Financial Impact Analysis")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Annual Loss", filt_financial["total_loss_formatted"])
        f2.metric("Panels to Replace", f"{n_recycle:,}")
        f3.metric("Repurpose Potential", f"{n_repurpose:,}")
        saved = n_repurpose * 10000
        f4.metric("Potential Savings", f"₹{saved:,.0f}")
        st.caption("Potential savings estimated at ₹10,000 per repurposed panel.")

        st.markdown("---")
        st.markdown("##### Loss Contribution by Manufacturer")
        loss_by_mfr = (
            filtered.assign(wattage_loss=filtered["original_wattage"] - filtered["current_wattage"])
            .groupby("manufacturer")["wattage_loss"].sum().reset_index()
            .sort_values("wattage_loss", ascending=False)
        )
        fig = px.bar(
            loss_by_mfr, x="manufacturer", y="wattage_loss",
            labels={"manufacturer": "Manufacturer", "wattage_loss": "Total Wattage Lost (W)"},
            color_discrete_sequence=[TOKENS["recycle"]],
        )
        st.plotly_chart(style_fig(fig), width='stretch')

    # ===== EXPORT TAB =====
    with tab_export:
        st.markdown("##### Export Results")
        st.caption(f"Exports reflect the current filters ({len(filtered):,} of {len(results):,} panels).")
        e1, e2 = st.columns(2)
        with e1:
            csv_full = filtered.to_csv(index=False)
            st.download_button(
                "📥 Download Full Report (CSV)", data=csv_full,
                file_name=f"panel_health_report_{datetime.now():%Y%m%d}.csv",
                mime="text/csv", width='stretch',
            )
        with e2:
            csv_summary = rec_summary.to_csv(index=False)
            st.download_button(
                "📥 Download Summary (CSV)", data=csv_summary,
                file_name=f"panel_health_summary_{datetime.now():%Y%m%d}.csv",
                mime="text/csv", width='stretch',
            )

else:
    st.info("👈 Upload a CSV file or click 'Demo Data' in the sidebar to get started")
    st.markdown("### 📋 Expected CSV Format")
    st.markdown(
        "Your CSV should contain the following columns:\n\n"
        "| Column | Description | Example |\n"
        "|--------|-------------|---------|\n"
        "| `panel_id` | Unique panel identifier | PANEL-00001 |\n"
        "| `manufacturer` | Panel manufacturer | SunPower |\n"
        "| `original_wattage` | Original power output (W) | 500 |\n"
        "| `current_wattage` | Current power output (W) | 480 |\n"
        "| `years_operating` | Years in operation | 5 |\n"
        "| `efficiency` | Current efficiency (%) | 96.0 |\n"
        "| `temperature` | Module temperature (°C) | 42.5 |\n"
        "| `dust_level` | Soiling level (%) | 5.2 |\n"
        "| `installation_date` | Installation date | 2020-01-01 |\n"
    )
    st.markdown("### 🚀 Quick Start\n1. Click **Demo Data** in the sidebar\n2. Or upload your own CSV file")

# ---------- FOOTER ----------
st.markdown("---")
st.markdown(
    '<div class="op-footer"><b>TEAM OPTISUNS</b> — BUILDING A CIRCULAR SOLAR ECONOMY · SOLARPANEL HEALTH AI v3.0</div>',
    unsafe_allow_html=True,
)