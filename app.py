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


def main():
    top = st.columns([1.1, 1, 1, 5])
    with top[0]:
        st.markdown("### 🧠 Content Strategy")

    if not _has_credentials():
        st.error(
            "**Missing credentials.** Add your service-account JSON under "
            "`[gcp_service_account]` in the app's **Secrets** "
            "(Manage app → Settings → Secrets). See `README.md`."
        )
        st.stop()

    with top[1]:
        if st.button("🔄 Refresh", use_container_width=True,
                     help="Re-sync from Google Sheets now"):
            load_dataframe.clear()
            st.rerun()

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

    with top[2]:
        st.metric("Keywords", stats["leaves"])
    with top[3]:
        gap = stats.get("gap", 0)
        gap_txt = f" (incl. **{gap}** keyword-gap suggestions)" if gap else ""
        st.caption(
            f"**{stats['themes']}** themes · **{stats['clusters']}** clusters · "
            f"**{stats['leaves']}** keywords{gap_txt} — live from *{WORKSHEET}* "
            f"(auto-refresh ≤ {CACHE_TTL}s)."
        )

    components.html(mindmap.build_html(mind, meta, height=780),
                    height=800, scrolling=False)


if __name__ == "__main__":
    main()
