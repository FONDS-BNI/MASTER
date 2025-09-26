import streamlit as st
from datetime import date

st.set_page_config(
    page_title="Fonds BNI-HEC",
    page_icon="📊",
    layout="wide"
)

# ------------- STYLE -------------
CUSTOM_CSS = """
<style>
    .main > div { padding-top: 1.5rem; }
    .hero {
        padding: 2.2rem 2.4rem;
        border-radius: 14px;
        position: relative;
        overflow: hidden;
    }
    .hero h1 { font-size: 2.2rem; margin: 0 0 .6rem 0; }
    .hero p { font-size: 1.05rem; opacity: .92; }
    .watermark {
        position:absolute; right:-40px; bottom:-40px;
        font-size:140px; font-weight:700; color:rgba(255,255,255,0.05);
        pointer-events:none;
    }
    .section-title {
        font-weight:600; font-size:1.05rem; letter-spacing:.5px;
        text-transform:uppercase; color:#555; margin:1.5rem 0 .4rem;
    }
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e8edf2;
        padding: 1.1rem 1rem .9rem 1rem;
        border-radius: 12px;
        height: 100%;
    }
    .kpi-label {
        font-size:.75rem; font-weight:600; text-transform:uppercase; color:#5b6b7d; letter-spacing:.5px;
    }
    .kpi-value {
        font-size:1.55rem; font-weight:600; margin:.15rem 0 .2rem;
    }
    .kpi-delta.up { color:#179c55; font-weight:600; font-size:.85rem; }
    .kpi-delta.down { color:#c43f3f; font-weight:600; font-size:.85rem; }
    footer { visibility: hidden; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ------------- HERO -------------
with st.container():
    st.markdown(
        f"""
        <div class="hero">
            <div class="watermark">BNI</div>
            <h1>Fonds BNI‑HEC Performance & Analytics</h1>
            <p>
                Central hub for monitoring portfolio performance, risk diagnostics,
                factor exposures, and operational dashboards. Use the sidebar to explore
                analytics modules and drill down into positions, returns, attribution
                and scenario views.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

# ------------- QUICK KPI PLACEHOLDERS (Replace with real pipeline) -------------
# In production, source these from your data layer (e.g., Snowflake, SQL, Parquet)
mock_data = {
    "AUM_M": 128.4,
    "MTD_RET": 0.0042,
    "YTD_RET": 0.0725,
    "ANN_VOL": 0.091,
    "SHARPE_12M": 1.42,
    "DRAWDOWN": -0.038
}

def fmt_pct(x, decimals=2):
    return f"{x*100:.{decimals}f}%"

kpi_definitions = [
    {"label": "Assets (MM)", "value": f'{mock_data["AUM_M"]:.1f}', "delta": "Updated", "delta_class": "up"},
    {"label": "MTD Return", "value": fmt_pct(mock_data["MTD_RET"]), "delta": "▲ vs prior day" if mock_data["MTD_RET"] >= 0 else "▼ vs prior day", "delta_class": "up" if mock_data["MTD_RET"] >= 0 else "down"},
    {"label": "YTD Return", "value": fmt_pct(mock_data["YTD_RET"]), "delta": "▲ cumulative" if mock_data["YTD_RET"] >= 0 else "▼ cumulative", "delta_class": "up" if mock_data["YTD_RET"] >= 0 else "down"},
    {"label": "Annualized Vol", "value": fmt_pct(mock_data["ANN_VOL"]), "delta": "Rolling 1Y", "delta_class": "up"},
    {"label": "Sharpe (12M)", "value": f'{mock_data["SHARPE_12M"]:.2f}', "delta": "Excess vs RF", "delta_class": "up"},
    {"label": "Max Drawdown (12M)", "value": fmt_pct(mock_data["DRAWDOWN"]), "delta": "Peak to trough", "delta_class": "down"},
]

kpi_cols = st.columns(len(kpi_definitions))
for i, kpi in enumerate(kpi_definitions):
    with kpi_cols[i]:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{kpi["label"]}</div>'
            f'<div class="kpi-value">{kpi["value"]}</div>'
            f'<div class="kpi-delta {kpi["delta_class"]}">{kpi["delta"]}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

# ------------- NAVIGATION HELP -------------
st.markdown('<div class="section-title">Navigation</div>', unsafe_allow_html=True)
nav_cols = st.columns(3)
with nav_cols[0]:
    st.markdown("**Performance**\n\nDaily / monthly returns, cumulative curves, rolling stats.")
with nav_cols[1]:
    st.markdown("**Risk & Factors**\n\nVol, drawdown, factor loadings, stress tests.")
with nav_cols[2]:
    st.markdown("**Attribution**\n\nBrinson / factor contributions, sector & strategy splits.")

st.markdown('<div class="section-title">Quick Start</div>', unsafe_allow_html=True)
with st.expander("1. Load / refresh data"):
    st.write("Integrate a data loader (database, API, or file). Provide a cached function that returns standardized DataFrames (prices, positions, benchmarks).")
with st.expander("2. Configure benchmarks & factors"):
    st.write("Maintain a config object (YAML / JSON) for benchmark tickers, factor model specification, risk-free rate.")
with st.expander("3. Extend modules"):
    st.write("Add pages in a pages/ directory (Streamlit multipage) for deeper analytics (liquidity, exposures, ESG overlays).")

# ------------- OPTIONAL DATA UPLOAD (placeholder) -------------
st.markdown('<div class="section-title">Ad hoc file preview</div>', unsafe_allow_html=True)
uploaded = st.file_uploader("Upload a CSV (e.g., positions or returns)", type=["csv"])
if uploaded:
    import pandas as pd
    df = pd.read_csv(uploaded)
    st.dataframe(df.head(50))
    st.success("Loaded preview. Integrate ETL pipeline for production use.")

# ------------- FOOTER / DISCLAIMER -------------
st.markdown(
    f"""
    ---
    Data as of {date.today().isoformat()} (illustrative). This interface is for internal analytics only
    and not an offer or solicitation. Verify figures against official books & records before distribution.
    """.strip()
)
