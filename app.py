"""Content Strategy Mind Map — Streamlit app.

Reads the "Internal Links" tab of the SEO Google Sheet (live) and renders an
XMind-style interactive mind map: Themes -> clusters (sx) -> keywords.
"""
import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components

import mindmap

st.set_page_config(page_title="Content Strategy Mind Map",
                   page_icon="🧠", layout="wide")

# --- Source config (not secret; the credentials are the only secret) ---------
SHEET_ID = "1M7WrRKoFbOHdozAT5JU-ge-rQgH566yZ7FgDcWy2oGY"
WORKSHEET = "Internal Links"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
CACHE_TTL = 60  # seconds — how "live" the sync is


@st.cache_resource(show_spinner=False)
def _gspread_client():
    info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_data(ttl=CACHE_TTL, show_spinner="Syncing with Google Sheets…")
def load_dataframe():
    gc = _gspread_client()
    ws = gc.open_by_key(SHEET_ID).worksheet(WORKSHEET)
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame()
    return pd.DataFrame(values[1:], columns=values[0])


def _has_credentials():
    try:
        return "gcp_service_account" in st.secrets
    except Exception:
        return False


CLAUDE_CSS = """
<style>
:root {
  --c-bg:#F5F4EF; --c-surface:#FFFFFF; --c-accent:#D97757;
  --c-accent-hover:#C15F3C; --c-accent-soft:#FBEFE9;
  --c-text:#262625; --c-muted:#73726C; --c-border:#E7E4DA;
}
.stApp { background: var(--c-bg); }
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 1.2rem; max-width: 100%; }

h1, h2, h3, h4, .cs-title {
  font-family: 'Tiempos', Georgia, 'Times New Roman', serif !important;
  color: var(--c-text); letter-spacing: -0.01em;
}

/* ---- App header ---- */
.cs-header { margin: 0 0 6px 0; }
.cs-title { font-size: 30px; font-weight: 600; line-height: 1.15; }
.cs-title .cs-dot { color: var(--c-accent); }
.cs-sub { color: var(--c-muted); font-size: 14px; margin-top: 3px; }

/* ---- Buttons (target by testid; help= wraps them in a tooltip span) ---- */
.stButton button, button[data-testid^="stBaseButton"] {
  background: var(--c-surface); color: var(--c-text);
  border: 1px solid var(--c-border); border-radius: 10px;
  font-weight: 500; transition: all .15s ease;
}
.stButton button:hover, button[data-testid^="stBaseButton"]:hover {
  border-color: var(--c-accent); color: var(--c-accent);
  background: var(--c-accent-soft);
}
button[data-testid="stBaseButton-primary"] {
  background: var(--c-accent); color: #fff; border: none;
}
button[data-testid="stBaseButton-primary"]:hover { background: var(--c-accent-hover); color: #fff; }

/* ---- Metric card ---- */
[data-testid="stMetric"] {
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: 12px; padding: 8px 16px;
}
[data-testid="stMetricValue"] { color: var(--c-accent); font-weight: 700; }
[data-testid="stMetricLabel"] { color: var(--c-muted); }

[data-testid="stCaptionContainer"] p { color: var(--c-muted) !important; }

/* alerts a touch warmer */
[data-testid="stAlert"] { border-radius: 12px; }

/* ---- Stat chips ---- */
.cs-stats { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cs-chip {
  display: flex; align-items: baseline; gap: 6px;
  background: var(--c-surface); border: 1px solid var(--c-border);
  border-radius: 11px; padding: 7px 13px;
}
.cs-chip .cs-n {
  font-family: 'Tiempos', Georgia, serif; font-size: 18px; font-weight: 600;
  color: var(--c-accent); line-height: 1;
}
.cs-chip .cs-l {
  font-size: 11px; letter-spacing: .04em; text-transform: uppercase;
  color: var(--c-muted);
}
.cs-chip.cs-gap .cs-n { color: #C4720E; }
.cs-live {
  display: flex; align-items: center; gap: 7px; margin-left: 4px;
  color: var(--c-muted); font-size: 12.5px;
}
.cs-live .cs-dot {
  width: 8px; height: 8px; border-radius: 50%; background: #3E9B6B;
  animation: cs-pulse 2.2s infinite;
}
@keyframes cs-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(62,155,107,.5); }
  70%  { box-shadow: 0 0 0 7px rgba(62,155,107,0); }
  100% { box-shadow: 0 0 0 0 rgba(62,155,107,0); }
}
</style>
"""


def _stats_bar(stats):
    chips = [("Themes", stats["themes"], ""),
             ("Clusters", stats["clusters"], ""),
             ("Keywords", stats["leaves"], "")]
    gap = stats.get("gap", 0)
    if gap:
        chips.append(("Gap ideas", gap, "cs-gap"))
    chip_html = "".join(
        f'<div class="cs-chip {cls}"><span class="cs-n">{v}</span>'
        f'<span class="cs-l">{label}</span></div>'
        for label, v, cls in chips
    )
    return (
        '<div class="cs-stats">' + chip_html +
        f'<div class="cs-live"><span class="cs-dot"></span>'
        f'Live · {WORKSHEET} · refreshes every {CACHE_TTL}s</div></div>'
    )


def _render_header():
    st.markdown(CLAUDE_CSS, unsafe_allow_html=True)
    st.markdown(
        '<div class="cs-header">'
        '<div class="cs-title">Content Strategy <span class="cs-dot">Mind Map</span></div>'
        '<div class="cs-sub">Live from Google Sheets · Themes → Clusters → Keywords</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def main():
    _render_header()

    if not _has_credentials():
        st.error(
            "**Missing credentials.** Add your service-account JSON under "
            "`[gcp_service_account]` in the app's **Secrets** "
            "(Manage app → Settings → Secrets). See `README.md`."
        )
        st.stop()

    try:
        df = load_dataframe()
    except Exception as e:
        st.error(f"Could not read the sheet: `{e}`")
        st.info(
            "Make sure the Google Sheet is **shared as Viewer** with the "
            "service-account email in your credentials, and that the tab "
            f"named **{WORKSHEET}** exists."
        )
        st.stop()

    if df.empty:
        st.warning("The sheet returned no rows.")
        st.stop()

    mind, meta, stats = mindmap.build_mind(df)

    row = st.columns([1.15, 8.85], vertical_alignment="center")
    with row[0]:
        if st.button("🔄 Refresh", use_container_width=True,
                     help="Re-sync from Google Sheets now"):
            load_dataframe.clear()
            st.rerun()
    with row[1]:
        st.markdown(_stats_bar(stats), unsafe_allow_html=True)

    components.html(mindmap.build_html(mind, meta, height=780),
                    height=800, scrolling=False)


if __name__ == "__main__":
    main()
