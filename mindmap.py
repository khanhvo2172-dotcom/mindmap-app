"""Pure logic: turn the Internal Links dataframe into a jsMind tree + HTML.

No Streamlit / network imports here so it can be unit-tested standalone.
"""
import html
import json
from urllib.parse import urlparse

ROOT_LABEL = "Content Strategy"

# Column names in the "Internal Links" tab
COL_THEME = "Themes"
COL_SX = "sx"
COL_KEYWORD = "Keyword"
COL_URL = "URLs"
COL_VOLUME = "Volume"
COL_TITLE = "Page Title"
COL_TYPE = "Content Type"
COL_NOTES = "Notes"

UNGROUPED = "(Ungrouped)"

# Keywords whose Notes cell equals this get bucketed under a collapsed node.
GAP_NOTE = "suggested keyword gap"
GAP_LABEL = "Suggested Keyword Gap"
GAP_BG = "#ffedd5"       # amber-100
GAP_FG = "#c2410c"       # amber-700
GAP_LEAF_BG = "#fff7ed"  # amber-50

# Distinct-ish colors for the 12 (or more) themes — XMind vibe.
THEME_PALETTE = [
    "#2563eb", "#0d9488", "#db2777", "#d97706", "#7c3aed", "#dc2626",
    "#0891b2", "#65a30d", "#c026d3", "#ea580c", "#4f46e5", "#059669",
    "#e11d48", "#0284c7", "#9333ea", "#16a34a",
]
ROOT_COLOR = "#262625"


def _lighten(hexc, f):
    """Mix a hex color toward white by factor f (0..1)."""
    hexc = hexc.lstrip("#")
    r, g, b = int(hexc[0:2], 16), int(hexc[2:4], 16), int(hexc[4:6], 16)
    r = int(r + (255 - r) * f)
    g = int(g + (255 - g) * f)
    b = int(b + (255 - b) * f)
    return f"#{r:02x}{g:02x}{b:02x}"


def _cell(row, name):
    v = row.get(name, "")
    return ("" if v is None else str(v)).strip()


def _slug_label(url):
    try:
        path = urlparse(url).path.rstrip("/")
        seg = path.split("/")[-1] if path else ""
        seg = seg.replace("-", " ").strip()
        return seg.title() if seg else ""
    except Exception:
        return ""


def build_mind(df):
    """Return (mind_dict, meta_dict, stats_dict).

    mind_dict  -> jsMind node_tree data
    meta_dict  -> {node_id: {url, tip, bg, fg}} applied client-side
    """
    meta = {}
    root_id = "root"
    root = {"id": root_id, "topic": ROOT_LABEL, "children": []}
    meta[root_id] = {"bg": ROOT_COLOR, "fg": "#ffffff"}

    theme_nodes = {}   # theme -> node dict
    cluster_nodes = {}  # (theme, sx) -> node dict
    gap_nodes = {}     # cluster id -> "Suggested Keyword Gap" bucket node
    ti = 0
    ci = 0
    ki = 0
    n_leaves = 0

    records = df.to_dict("records") if hasattr(df, "to_dict") else df

    for row in records:
        theme = _cell(row, COL_THEME) or UNGROUPED
        sx = _cell(row, COL_SX) or UNGROUPED
        kw = _cell(row, COL_KEYWORD)
        title = _cell(row, COL_TITLE)
        url = _cell(row, COL_URL)
        vol = _cell(row, COL_VOLUME)
        ctype = _cell(row, COL_TYPE)
        is_gap = _cell(row, COL_NOTES).lower() == GAP_NOTE

        # Skip fully empty rows.
        if not any([_cell(row, COL_THEME), _cell(row, COL_SX), kw, title, url]):
            continue

        # ---- Level 1: Theme ----
        if theme not in theme_nodes:
            tid = f"t{ti}"
            color = THEME_PALETTE[ti % len(THEME_PALETTE)]
            node = {"id": tid, "topic": theme, "expanded": True, "children": []}
            theme_nodes[theme] = node
            root["children"].append(node)
            meta[tid] = {"bg": color, "fg": "#ffffff"}
            ti += 1
        tnode = theme_nodes[theme]
        tcolor = meta[tnode["id"]]["bg"]

        # ---- Level 2: cluster (sx) ----
        ckey = (theme, sx)
        if ckey not in cluster_nodes:
            cid = f"{tnode['id']}_c{ci}"
            # keep keyword leaves collapsed until clicked
            node = {"id": cid, "topic": sx, "expanded": False, "children": []}
            cluster_nodes[ckey] = node
            tnode["children"].append(node)
            meta[cid] = {"bg": _lighten(tcolor, 0.80), "fg": tcolor}
            ci += 1
        cnode = cluster_nodes[ckey]

        # ---- Optional: "Suggested Keyword Gap" bucket inside the cluster ----
        if is_gap:
            gkey = cnode["id"]
            if gkey not in gap_nodes:
                gid = f"{cnode['id']}_gap"
                gbucket = {"id": gid, "topic": GAP_LABEL,
                           "expanded": False, "children": []}
                gap_nodes[gkey] = gbucket
                cnode["children"].append(gbucket)
                meta[gid] = {"bg": GAP_BG, "fg": GAP_FG}
            leaf_parent = gap_nodes[gkey]["children"]
            leaf_bg = GAP_LEAF_BG
        else:
            leaf_parent = cnode["children"]
            leaf_bg = _lighten(tcolor, 0.90)

        # ---- Level 3: keyword leaf ----
        label = kw or title or _slug_label(url) or "(Untitled)"
        lid = f"k{ki}"
        ki += 1
        leaf_parent.append({"id": lid, "topic": label, "children": []})
        n_leaves += 1

        tip_parts = []
        if kw:
            tip_parts.append(f"Keyword: {kw}")
        if vol:
            tip_parts.append(f"Volume: {vol}")
        if ctype:
            tip_parts.append(f"Type: {ctype}")
        if title:
            tip_parts.append(f"Title: {title}")
        if url:
            tip_parts.append(f"URL: {url}")
            tip_parts.append("(double-click to open)")
        m = {"bg": leaf_bg, "fg": "#1e293b"}
        if tip_parts:
            m["tip"] = "\n".join(tip_parts)
        if url:
            m["url"] = url
        meta[lid] = m

    # Label each gap bucket with its count and push it to the end of the cluster.
    n_gap_leaves = 0
    for cid, gbucket in gap_nodes.items():
        gbucket["topic"] = f"{GAP_LABEL} ({len(gbucket['children'])})"
        n_gap_leaves += len(gbucket["children"])
        cnode = next(c for c in cluster_nodes.values() if c["id"] == cid)
        cnode["children"].remove(gbucket)
        cnode["children"].append(gbucket)

    # Balance the tree: alternate top-level themes left/right.
    n_themes = len(root["children"])
    for i, node in enumerate(root["children"]):
        node["direction"] = "right" if i < (n_themes + 1) // 2 else "left"

    stats = {"themes": n_themes, "clusters": ci, "leaves": n_leaves,
             "gap": n_gap_leaves}
    return root, meta, stats


def build_html(mind_data, meta, height=760):
    data_json = json.dumps(mind_data, ensure_ascii=False)
    meta_json = json.dumps(meta, ensure_ascii=False)

    return f"""
<div id="mm-toolbar">
  <button class="mm-btn" onclick="mmExpandAll()">＋ Expand all</button>
  <button class="mm-btn" onclick="mmCollapseAll()">－ Collapse all</button>
  <span class="mm-sep"></span>
  <button class="mm-btn" onclick="mmZoom(1)">🔍 +</button>
  <button class="mm-btn" onclick="mmZoom(-1)">🔍 −</button>
  <button class="mm-btn" onclick="mmReset()">⟲ Reset</button>
  <input id="mm-search" class="mm-search" type="text"
         placeholder="Search node, press Enter…"
         onkeydown="if(event.key==='Enter'){{event.preventDefault();mmSearch(this.value);}}"/>
  <span class="mm-hint">Click branch = expand · drag a node to rearrange (resets on refresh) · drag empty space = pan · scroll = zoom · dbl-click keyword = open · right-click = copy</span>
</div>
<div id="jsmind_container"></div>
<div id="mm-ctx"></div>
<div id="mm-toast"></div>

<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/jsmind@0.8.6/style/jsmind.css"/>
<script src="https://cdn.jsdelivr.net/npm/jsmind@0.8.6/es6/jsmind.js"></script>
<script src="https://cdn.jsdelivr.net/npm/jsmind@0.8.6/es6/jsmind.draggable-node.js"></script>

<style>
  html, body {{ margin:0; padding:0; }}
  #mm-toolbar {{
    display:flex; align-items:center; gap:6px; flex-wrap:wrap;
    padding:8px 4px; font-family:'Segoe UI',Roboto,sans-serif;
  }}
  .mm-btn {{
    border:1px solid #E7E4DA; background:#fff; color:#262625;
    border-radius:9px; padding:6px 11px; font-size:13px; cursor:pointer;
    transition:all .14s ease;
  }}
  .mm-btn:hover {{ background:#FBEFE9; border-color:#D97757; color:#C15F3C; }}
  .mm-sep {{ width:1px; height:20px; background:#E7E4DA; margin:0 4px; }}
  .mm-search {{
    border:1px solid #E7E4DA; border-radius:9px; padding:6px 11px;
    font-size:13px; width:190px; outline:none; color:#262625; background:#fff;
  }}
  .mm-search:focus {{ border-color:#D97757; box-shadow:0 0 0 3px rgba(217,119,87,.15); }}
  .mm-search::placeholder {{ color:#A8A69E; }}
  .mm-hint {{ color:#908E85; font-size:11.5px; margin-left:auto; }}
  #jsmind_container {{
    width:100%; height:{height - 60}px;
    border:1px solid #E7E4DA; border-radius:14px;
    background:
      radial-gradient(circle, #E7E3D7 1px, transparent 1px) 0 0/22px 22px,
      #FAF9F4;
  }}
  jmnode {{
    border-radius:9px !important;
    font-family:'Segoe UI',Roboto,sans-serif !important;
    box-shadow:0 1px 2px rgba(38,38,37,.10);
    padding:6px 12px !important;
  }}
  jmnode.selected {{ box-shadow:0 0 0 3px rgba(217,119,87,.40) !important; }}
  jmnode.mm-match {{ box-shadow:0 0 0 3px #E8A838 !important; }}
  jmexpander {{ font-weight:700; }}
  #mm-ctx {{
    position:fixed; z-index:9999; display:none; background:#fff;
    border:1px solid #E7E4DA; border-radius:10px; padding:4px; min-width:158px;
    box-shadow:0 10px 30px rgba(38,38,37,.16);
    font-family:'Segoe UI',Roboto,sans-serif;
  }}
  #mm-ctx .mm-ctx-item {{
    padding:7px 12px; font-size:13px; color:#262625; border-radius:7px;
    cursor:pointer; white-space:nowrap; user-select:none;
  }}
  #mm-ctx .mm-ctx-item:hover {{ background:#FBEFE9; color:#C15F3C; }}
  #mm-toast {{
    position:fixed; z-index:10000; bottom:16px; left:50%;
    transform:translateX(-50%); background:#262625; color:#fff;
    padding:8px 15px; border-radius:10px; font-size:13px; opacity:0;
    transition:opacity .18s; pointer-events:none;
    font-family:'Segoe UI',Roboto,sans-serif;
  }}
  #mm-toast.show {{ opacity:.96; }}
</style>

<script>
  var MIND = {{ meta:{{name:"content-strategy", author:"", version:"1.0"}},
               format:"node_tree", data:{data_json} }};
  var META = {meta_json};
  var jm = null;

  function applyMeta() {{
    document.querySelectorAll('jmnode').forEach(function(el) {{
      var m = META[el.getAttribute('nodeid')];
      if (!m) return;
      if (m.tip && el.getAttribute('title') !== m.tip) el.setAttribute('title', m.tip);
      if (m.bg) {{ el.style.backgroundColor = m.bg; }}
      if (m.fg) {{ el.style.color = m.fg; }}
      if (m.url) {{ el.style.cursor = 'pointer'; }}
    }});
  }}

  function init() {{
    var options = {{
      container: 'jsmind_container',
      theme: 'greensea',
      editable: true,               // required for node dragging (rearrange)
      mode: 'full',
      shortcut: {{ enable: false }},  // no keyboard delete/edit
      view: {{ engine:'canvas', hmargin:80, vmargin:40, line_width:2,
               line_color:'#CFC9BA', draggable:true,
               zoom:{{ min:0.3, max:2.2, step:0.08 }} }},
      layout: {{ hspace:28, vspace:14, pspace:13 }}
    }};
    jm = new jsMind(options);
    jm.show(MIND);
    // Editable is on only to allow drag-to-rearrange; block inline text editing.
    jm.begin_edit = function() {{ return false; }};

    // Recolor / tooltips, and re-apply whenever nodes are (re)rendered.
    applyMeta();
    var container = document.getElementById('jsmind_container');
    new MutationObserver(function() {{ applyMeta(); }})
        .observe(container, {{ childList:true, subtree:true }});

    // Single-click a branch node (theme/cluster/gap) -> toggle expand/collapse.
    container.addEventListener('click', function(e) {{
      if (e.target.closest && e.target.closest('jmexpander')) return; // let +/- work
      hideCtx();
      var n = e.target.closest ? e.target.closest('jmnode') : null;
      if (!n) return;
      var id = n.getAttribute('nodeid');
      var node = jm.get_node(id);
      if (node && node.children && node.children.length) jm.toggle_node(id);
    }});

    // Double-click a node with a URL -> open it.
    container.addEventListener('dblclick', function(e) {{
      var n = e.target.closest ? e.target.closest('jmnode') : null;
      if (!n) return;
      var m = META[n.getAttribute('nodeid')];
      if (m && m.url) window.open(m.url, '_blank');
    }});

    // Right-click a keyword leaf -> context menu.
    var ctx = document.getElementById('mm-ctx');
    container.addEventListener('contextmenu', function(e) {{
      var n = e.target.closest ? e.target.closest('jmnode') : null;
      if (!n) {{ hideCtx(); return; }}
      var id = n.getAttribute('nodeid');
      var node = jm.get_node(id);
      var isLeaf = node && (!node.children || node.children.length === 0) && id !== 'root';
      if (!isLeaf) {{ hideCtx(); return; }}  // branches keep the native menu
      e.preventDefault();
      var m = META[id] || {{}};
      CTX_URL = m.url || null;
      CTX_TEXT = node.topic || '';
      var items = '<div class="mm-ctx-item" data-act="copytext">📝 Copy keyword text</div>';
      if (CTX_URL) {{
        items += '<div class="mm-ctx-item" data-act="copy">📋 Copy link</div>' +
                 '<div class="mm-ctx-item" data-act="open">↗ Open link</div>';
      }}
      ctx.innerHTML = items;
      ctx.style.left = Math.min(e.clientX, window.innerWidth - 180) + 'px';
      ctx.style.top = e.clientY + 'px';
      ctx.style.display = 'block';
    }});
    ctx.addEventListener('click', function(e) {{
      var act = e.target.getAttribute('data-act');
      if (act === 'copytext' && CTX_TEXT) {{ copyText(CTX_TEXT); toast('Keyword copied'); }}
      else if (act === 'copy' && CTX_URL) {{ copyText(CTX_URL); toast('Link copied'); }}
      else if (act === 'open' && CTX_URL) {{ window.open(CTX_URL, '_blank'); }}
      hideCtx();
    }});
    document.addEventListener('click', function(e) {{
      if (!e.target.closest || !e.target.closest('#mm-ctx')) hideCtx();
    }});
    document.addEventListener('scroll', hideCtx, true);
    document.addEventListener('keydown', function(e) {{ if (e.key === 'Escape') hideCtx(); }});

    // Wheel to zoom.
    container.addEventListener('wheel', function(e) {{
      e.preventDefault();
      hideCtx();
      mmZoom(e.deltaY < 0 ? 1 : -1);
    }}, {{ passive:false }});
  }}

  var CTX_URL = null;
  var CTX_TEXT = null;
  function hideCtx() {{
    var c = document.getElementById('mm-ctx');
    if (c) c.style.display = 'none';
  }}

  function copyText(text) {{
    try {{
      if (navigator.clipboard && navigator.clipboard.writeText) {{
        navigator.clipboard.writeText(text).catch(function() {{ fallbackCopy(text); }});
        return;
      }}
    }} catch (e) {{}}
    fallbackCopy(text);
  }}
  function fallbackCopy(text) {{
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.top = '-1000px';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    try {{ document.execCommand('copy'); }} catch (e) {{}}
    document.body.removeChild(ta);
  }}
  var TOAST_TIMER = null;
  function toast(msg) {{
    var t = document.getElementById('mm-toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    clearTimeout(TOAST_TIMER);
    TOAST_TIMER = setTimeout(function() {{ t.classList.remove('show'); }}, 1400);
  }}

  function mmZoom(dir) {{
    if (!jm || !jm.view) return;
    try {{ dir > 0 ? jm.view.zoomIn() : jm.view.zoomOut(); }} catch (e) {{}}
  }}
  function mmReset() {{ if (jm && jm.view && jm.view.set_zoom) jm.view.set_zoom(1); }}
  function mmExpandAll() {{ if (jm) jm.expand_all(); }}
  function mmCollapseAll() {{ if (jm) {{ jm.collapse_all(); jm.expand_node('root'); }} }}

  function mmSearch(q) {{
    q = (q || '').trim().toLowerCase();
    document.querySelectorAll('jmnode').forEach(function(el) {{
      el.classList.remove('mm-match');
    }});
    if (!q) return;
    var first = null;
    var nodes = jm ? jm.mind.nodes : {{}};
    for (var id in nodes) {{
      var topic = (nodes[id].topic || '').toLowerCase();
      if (topic.indexOf(q) !== -1) {{
        // reveal ancestors
        var p = nodes[id].parent;
        while (p) {{ jm.expand_node(p.id); p = p.parent; }}
        if (!first) first = id;
      }}
    }}
    setTimeout(function() {{
      document.querySelectorAll('jmnode').forEach(function(el) {{
        var t = (el.textContent || '').toLowerCase();
        if (t.indexOf(q) !== -1) el.classList.add('mm-match');
      }});
      if (first) jm.select_node(first);
    }}, 60);
  }}

  if (document.readyState === 'complete' || document.readyState === 'interactive') {{
    setTimeout(init, 50);
  }} else {{
    window.addEventListener('DOMContentLoaded', init);
  }}
</script>
"""
