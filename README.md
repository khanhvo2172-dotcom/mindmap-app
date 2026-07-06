# Content Strategy Mind Map

An interactive, XMind-style mind map that renders live from the SEO Google
Sheet. Built with Streamlit + [jsMind](https://github.com/hizzgdev/jsmind).

**Hierarchy** (from the `Internal Links` tab):

```
Content Strategy (root)
 └─ Themes            → Level 1   (column "Themes")
     └─ sx            → Level 2   (column "sx")
         └─ Keyword   → Level 3   (column "Keyword")
```

Each keyword leaf carries its `Volume`, `Content Type`, `Page Title` and `URL`
(shown on hover; **double-click a leaf to open its URL**).

## Features
- Live sync from Google Sheets (auto-refresh ≤ 60s + manual **Refresh** button).
- Expand / collapse all, wheel-zoom, drag empty space to pan.
- Search box highlights matching nodes and reveals their branch.
- Branch colours grouped by theme.

## Run locally
```bash
pip install -r requirements.txt
# put your service-account JSON values into .streamlit/secrets.toml
#   (copy .streamlit/secrets.toml.example)
streamlit run app.py
```

## Deploy on Streamlit Cloud
1. Go to https://share.streamlit.io → **New app**.
2. Repository: `khanhvo2172-dotcom/mindmap-app` · Branch: `main` · Main file: `app.py`.
3. **Advanced settings → Secrets**: paste the `[gcp_service_account]` block
   (see `.streamlit/secrets.toml.example`) filled with your real key.
4. Deploy. It auto-redeploys on every push to `main`.

## Data access
The Google Sheet must be **shared as Viewer** with the service-account email:
`google-drive-files-editor@focused-outlook-465107-u9.iam.gserviceaccount.com`

## Configuration
- `SHEET_ID` / `WORKSHEET` — in `app.py`.
- Column names, root label, colours — in `mindmap.py`.
