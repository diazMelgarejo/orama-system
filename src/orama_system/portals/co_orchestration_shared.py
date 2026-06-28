"""Shared co-orchestration inbox logic and HTML shell."""
from __future__ import annotations

import datetime
import html
from typing import Any, Mapping

CO_ORCHESTRATION_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{page_title}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#475569;color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:14px;padding:1.25rem}}
  h1{{font-size:1.15rem;color:{accent};margin-bottom:.5rem}}
  .platform-banner{{background:#1e293b;border:1px solid #334155;border-left:3px solid {accent};border-radius:4px;padding:.55rem .75rem;margin-bottom:1rem;font-size:.75rem;color:#cbd5e1;line-height:1.45}}
  .platform-banner strong{{color:{accent}}}
  .navbar{{display:flex;justify-content:space-between;align-items:center;background:#1e293b;border-radius:4px;padding:.6rem 1rem;margin-bottom:1rem}}
  .nav-brand{{font-size:.95rem;font-weight:700;color:{accent}}}
  .nav-links{{display:flex;gap:.75rem;align-items:center;flex-wrap:wrap}}
  .nav-link{{color:#94a3b8;font-size:.8rem;text-decoration:none}}
  .nav-link:hover,.nav-link.active{{color:#f8fafc}}
  .stats{{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1rem}}
  .stat{{background:#1e293b;border:1px solid #334155;border-radius:4px;padding:.45rem .75rem;font-size:.75rem}}
  .stat strong{{color:{accent}}}
  .stat.err{{border-color:#f87171;color:#fecaca}}
  .cols{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
  @media(max-width:960px){{.cols{{grid-template-columns:1fr}}}}
  .panel{{background:#1e293b;border:1px solid #334155;border-radius:4px;overflow:hidden}}
  .panel-h{{padding:.55rem .75rem;border-bottom:1px solid #334155;font-size:.8rem;font-weight:600;color:#94a3b8;letter-spacing:.04em;text-transform:uppercase}}
  table{{width:100%;border-collapse:collapse;font-size:.72rem}}
  th{{text-align:left;color:#64748b;padding:.35rem .6rem;border-bottom:1px solid #334155}}
  td{{padding:.35rem .6rem;border-bottom:1px solid #1f2937;vertical-align:top;cursor:pointer}}
  tr:hover td{{background:#0f172a}}
  tr.sel td{{background:#0c2034}}
  .badge{{display:inline-block;border-radius:3px;font-size:.62rem;padding:.1rem .35rem;margin-right:.25rem}}
  .b-in{{background:#14532d;color:#86efac}}
  .b-out{{background:#1e3a5f;color:#93c5fd}}
  .b-local{{background:#3b0764;color:#d8b4fe}}
  .b-peer{{background:#422006;color:#fcd34d}}
  .preview{{margin-top:1rem;background:#1e293b;border:1px solid #334155;border-radius:4px;padding:1rem;min-height:8rem}}
  .preview-h{{font-size:.75rem;color:#64748b;margin-bottom:.5rem}}
  .md{{line-height:1.55;font-size:.85rem}}
  .md h1,.md h2,.md h3{{color:{accent};margin:.75rem 0 .35rem}}
  .md pre{{background:#0f172a;border:1px solid #334155;border-radius:3px;padding:.6rem;overflow-x:auto;font-size:.75rem}}
  .md code{{font-family:ui-monospace,monospace;font-size:.8em}}
  .md table{{margin:.5rem 0}}
  .footer{{margin-top:1rem;font-size:.7rem;color:#64748b}}
  .empty{{color:#64748b;padding:1rem;font-size:.75rem}}
  .filter{{margin-bottom:.75rem;display:flex;gap:.5rem;align-items:center;font-size:.75rem}}
  .filter select{{background:#1e293b;border:1px solid #475569;border-radius:3px;color:#f8fafc;padding:.25rem .5rem}}
</style>
</head>
<body>
<nav class="navbar">
  <span class="nav-brand">{nav_brand}</span>
  <div class="nav-links">
    <a class="nav-link" href="/">Portal home</a>
    <a class="nav-link active" href="{active_path}">Inbox queue</a>
    <a class="nav-link" href="/co-orchestration">Auto ({platform_label})</a>
    <a class="nav-link" href="/dashboard">Routing dashboard</a>
  </div>
</nav>
<h1>{heading}</h1>
<div class="platform-banner">{platform_banner}</div>
<div id="stats" class="stats"></div>
<div class="filter">
  <label for="fanout-filter">Fan-out:</label>
  <select id="fanout-filter"><option value="">All batches</option></select>
</div>
<div class="cols">
  <div class="panel">
    <div class="panel-h">Local inbox — received on this host ({local_role})</div>
    <div id="local-table"></div>
  </div>
  <div class="panel">
    <div class="panel-h">Peer inbox — on <span id="peer-label">peer</span> (<span id="peer-role">peer</span>)</div>
    <div id="peer-table"></div>
  </div>
</div>
<div class="preview">
  <div class="preview-h" id="preview-title">Select a file to preview rendered markdown</div>
  <div id="preview-body" class="md"></div>
</div>
<div class="footer">Platform skin: {platform_label} · Auto-refresh 10s · <span id="last-refresh">—</span></div>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
{cp_fetch_bootstrap}
let _summary = null;
let _sel = null;

function esc(s) {{
  const d = document.createElement('div');
  d.textContent = s == null ? '' : String(s);
  return d.innerHTML;
}}

function fmtTs(ts) {{
  if (!ts) return '—';
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}}

function dirBadge(item) {{
  const d = item.direction || '';
  if (d === 'inbound') return '<span class="badge b-in">inbound</span>';
  if (d === 'outbound') return '<span class="badge b-out">outbound</span>';
  if (d === 'peer_local') return '<span class="badge b-peer">peer local</span>';
  return '<span class="badge b-local">local</span>';
}}

function rowHtml(item, side, idx) {{
  const sel = _sel && _sel.side === side && _sel.idx === idx ? ' class="sel"' : '';
  return '<tr data-side="' + side + '" data-idx="' + idx + '"' + sel + '>' +
    '<td>' + dirBadge(item) + esc(item.filename) + '</td>' +
    '<td>' + esc(item.topic || '—') + '</td>' +
    '<td>' + esc(item.source || '—') + ' → ' + esc(item.assignee || '—') + '</td>' +
    '<td>' + fmtTs(item.received_at) + '</td></tr>';
}}

function renderTable(el, files, side) {{
  if (!files || !files.length) {{
    el.innerHTML = '<div class="empty">No files</div>';
    return;
  }}
  let rows = files.map((f, i) => rowHtml(f, side, i)).join('');
  el.innerHTML = '<table><thead><tr><th>File</th><th>Topic</th><th>Route</th><th>Received</th></tr></thead><tbody>' + rows + '</tbody></table>';
  el.querySelectorAll('tbody tr').forEach(tr => {{
    tr.addEventListener('click', () => selectFile(tr.dataset.side, parseInt(tr.dataset.idx, 10)));
  }});
}}

function fanoutFilter() {{
  const v = document.getElementById('fanout-filter').value;
  if (!_summary) return {{ local: [], peer: [] }};
  const loc = (_summary.local_inbox || []).filter(f => !v || f.fanout_id === v);
  const peer = (_summary.peer_inbox || []).filter(f => !v || f.fanout_id === v);
  return {{ local: loc, peer: peer }};
}}

function renderAll() {{
  if (!_summary) return;
  const {{ local, peer }} = fanoutFilter();
  document.getElementById('peer-label').textContent = _summary.peer_ip || 'peer';
  const pr = document.getElementById('peer-role');
  if (pr) pr.textContent = _summary.peer_role || 'peer';
  renderTable(document.getElementById('local-table'), local, 'local');
  renderTable(document.getElementById('peer-table'), peer, 'peer');
  const st = _summary.stats || {{}};
  let statsHtml = '<div class="stat"><strong>' + (st.local_count||0) + '</strong> local files</div>' +
    '<div class="stat"><strong>' + (st.peer_count||0) + '</strong> peer files</div>' +
    '<div class="stat"><strong>' + (st.inbound_from_peer||0) + '</strong> inbound from peer</div>' +
    '<div class="stat"><strong>' + (st.outbound_on_peer||0) + '</strong> our drops on peer</div>';
  if (_summary.peer_error) {{
    statsHtml += '<div class="stat err">Peer inbox: ' + esc(_summary.peer_error) + '</div>';
  }}
  if (_summary.platform_skin) {{
    statsHtml += '<div class="stat">skin <strong>' + esc(_summary.platform_skin) + '</strong></div>';
  }}
  document.getElementById('stats').innerHTML = statsHtml;
  document.getElementById('last-refresh').textContent = new Date().toLocaleString();
}}

async function selectFile(side, idx) {{
  const {{ local, peer }} = fanoutFilter();
  const list = side === 'local' ? local : peer;
  const item = list[idx];
  if (!item) return;
  _sel = {{ side, idx }};
  renderAll();
  const scope = side === 'local' ? 'local' : 'peer';
  document.getElementById('preview-title').textContent = item.filename + ' · ' + (item.topic || '');
  document.getElementById('preview-body').innerHTML = '<em>Loading…</em>';
  try {{
    const r = await cpFetch('/api/co-orchestration/file/' + encodeURIComponent(item.filename) + '?scope=' + scope);
    const d = await r.json();
    document.getElementById('preview-body').innerHTML = marked.parse(d.body || '');
  }} catch (e) {{
    document.getElementById('preview-body').textContent = 'Failed to load: ' + e;
  }}
}}

function fillFanoutFilter(summary) {{
  const sel = document.getElementById('fanout-filter');
  const prev = sel.value;
  const ids = new Set();
  (summary.local_inbox || []).forEach(f => {{ if (f.fanout_id) ids.add(f.fanout_id); }});
  (summary.peer_inbox || []).forEach(f => {{ if (f.fanout_id) ids.add(f.fanout_id); }});
  sel.innerHTML = '<option value="">All batches</option>' + Array.from(ids).sort().reverse().map(id =>
    '<option value="' + esc(id) + '">' + esc(id) + '</option>').join('');
  if (prev && ids.has(prev)) sel.value = prev;
}}

async function refresh() {{
  try {{
    const r = await cpFetch('/api/co-orchestration');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    _summary = await r.json();
    fillFanoutFilter(_summary);
    renderAll();
  }} catch (e) {{
    document.getElementById('stats').innerHTML = '<div class="stat err">Refresh failed: ' + esc(String(e)) + '</div>';
  }}
}}

document.getElementById('fanout-filter').addEventListener('change', renderAll);
refresh();
setInterval(refresh, 10000);
</script>
</body>
</html>
"""


def _annotate_inbox(
    files: list[dict[str, Any]],
    *,
    local_role: str,
    peer_role: str,
    side: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in sorted(files, key=lambda x: x.get("received_at", 0), reverse=True):
        row = dict(item)
        source = (row.get("source") or "").strip().lower()
        if side == "local":
            row["direction"] = "inbound" if source == peer_role else "local"
        else:
            if source == local_role:
                row["direction"] = "outbound"
            else:
                row["direction"] = "peer_local"
        out.append(row)
    return out


def _summary_stats(
    local_inbox: list[dict[str, Any]],
    peer_inbox: list[dict[str, Any]],
    *,
    peer_role: str,
) -> dict[str, Any]:
    local_role = "win" if peer_role == "mac" else "mac"
    inbound = sum(1 for f in local_inbox if (f.get("source") or "").lower() == peer_role)
    outbound = sum(1 for f in peer_inbox if (f.get("source") or "").lower() == local_role)
    fanouts: dict[str, dict[str, int]] = {}
    for side_name, items in ("local", local_inbox), ("peer", peer_inbox):
        for item in items:
            fid = (item.get("fanout_id") or "").strip()
            if not fid:
                continue
            fanouts.setdefault(fid, {"local": 0, "peer": 0})
            fanouts[fid][side_name] += 1
    return {
        "local_count": len(local_inbox),
        "peer_count": len(peer_inbox),
        "inbound_from_peer": inbound,
        "outbound_on_peer": outbound,
        "fanouts": fanouts,
    }


def build_co_orchestration_summary(
    *,
    local_role: str,
    peer_ip: str,
    local_inbox: list[dict[str, Any]],
    peer_inbox: list[dict[str, Any]],
    peer_error: str = "",
    platform_skin: str = "",
) -> dict[str, Any]:
    peer_role = "win" if local_role == "mac" else "mac"
    local_ann = _annotate_inbox(local_inbox, local_role=local_role, peer_role=peer_role, side="local")
    peer_ann = _annotate_inbox(peer_inbox, local_role=local_role, peer_role=peer_role, side="peer")
    return {
        "local_role": local_role,
        "peer_role": peer_role,
        "peer_ip": peer_ip,
        "peer_reachable": not peer_error and bool(peer_ip),
        "peer_error": peer_error,
        "platform_skin": platform_skin,
        "local_inbox": local_ann,
        "peer_inbox": peer_ann,
        "stats": _summary_stats(local_ann, peer_ann, peer_role=peer_role),
        "probed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def render_co_orchestration_html(
    skin: Mapping[str, str],
    *,
    version: str,
    cp_fetch_bootstrap: str,
) -> str:
    return CO_ORCHESTRATION_HTML.format(
        page_title=skin["page_title"],
        accent=skin["accent"],
        nav_brand=skin["nav_brand"],
        active_path=skin["active_path"],
        platform_label=skin["platform_label"],
        heading=skin["heading"],
        platform_banner=skin["platform_banner"],
        local_role=skin["local_role"],
        version=html.escape(version),
        cp_fetch_bootstrap=cp_fetch_bootstrap,
    )
