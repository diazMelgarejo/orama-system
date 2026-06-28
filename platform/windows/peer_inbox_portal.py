"""Windows lane: /peer-inbox portal — bidirectional queue + server-side markdown."""
from __future__ import annotations

from typing import Any, Callable, Mapping
from urllib.parse import quote

import httpx

PEER_INBOX_ROUTE = "/peer-inbox"


def render_peer_inbox_page(
    *,
    role: str,
    peer_ip: str,
    cp_fetch_bootstrap: str,
) -> str:
    peer = peer_ip or "—"
    cp_js = cp_fetch_bootstrap
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Peer Inbox — orama portal</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#475569;color:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:14px;padding:1.5rem}}
  .navbar{{display:flex;justify-content:space-between;align-items:center;background:#1e293b;border-radius:4px;padding:.6rem 1rem;margin-bottom:1rem}}
  .nav-brand{{font-size:.95rem;font-weight:700;color:#38bdf8}}
  .nav-links{{display:flex;gap:.75rem;align-items:center}}
  .nav-link{{color:#94a3b8;font-size:.8rem;text-decoration:none}}
  .nav-link:hover{{color:#f8fafc}}
  h1{{font-size:1.1rem;color:#38bdf8;margin-bottom:.5rem}}
  .meta{{color:#94a3b8;font-size:.75rem;margin-bottom:1rem}}
  .layout{{display:grid;grid-template-columns:1fr 1fr;gap:1rem}}
  @media(max-width:900px){{.layout{{grid-template-columns:1fr}}}}
  .panel{{background:#334155;border:1px solid #64748b;border-radius:4px;overflow:hidden}}
  .panel-h{{padding:.6rem .75rem;border-bottom:1px solid #64748b;font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:#38bdf8}}
  .tbl{{width:100%;border-collapse:collapse;font-size:.72rem}}
  .tbl th,.tbl td{{padding:.35rem .5rem;border-bottom:1px solid #475569;text-align:left}}
  .tbl th{{color:#94a3b8;font-weight:600}}
  .tbl tr{{cursor:pointer}}
  .tbl tr:hover{{background:#1e293b}}
  .tbl tr.sel{{background:#0f172a}}
  .preview{{padding:1rem;min-height:280px;max-height:60vh;overflow:auto}}
  .preview h1,.preview h2,.preview h3{{margin:.6rem 0 .3rem;color:#e2e8f0}}
  .preview pre{{background:#1e293b;padding:.75rem;border-radius:4px;overflow:auto;font-size:.75rem}}
  .preview code{{font-family:monospace;color:#7dd3fc}}
  .tag{{display:inline-block;padding:.05rem .35rem;border-radius:2px;background:#0f172a;color:#94a3b8;font-size:.65rem}}
  .err{{color:#f87171;font-size:.75rem;padding:.75rem}}
  .footer{{margin-top:1rem;font-size:.7rem;color:#64748b}}
</style>
</head>
<body>
<nav class="navbar">
  <span class="nav-brand">orama portal (Windows lane)</span>
  <div class="nav-links">
    <a class="nav-link" href="/">← Control plane</a>
    <a class="nav-link" href="/co-orchestration">Co-orchestration (Mac lane)</a>
    <a class="nav-link" href="/dashboard">Routing Dashboard</a>
  </div>
</nav>
<h1>LAN peer inbox <span style="font-weight:400;color:#94a3b8">({role} ↔ {peer})</span></h1>
<p class="meta">Co-orchestrator file handoff queue — click a row to preview rendered markdown. Auto-refresh 15s.</p>
<div class="layout">
  <div class="panel">
    <div class="panel-h">Local inbox ({role})</div>
    <div id="local-wrap" style="max-height:42vh;overflow:auto"><p class="meta" style="padding:.75rem">Loading…</p></div>
  </div>
  <div class="panel">
    <div class="panel-h">Peer inbox ({peer})</div>
    <div id="remote-wrap" style="max-height:42vh;overflow:auto"><p class="meta" style="padding:.75rem">Loading…</p></div>
  </div>
</div>
<div class="panel" style="margin-top:1rem">
  <div class="panel-h" id="preview-title">Preview</div>
  <div class="preview" id="preview-body"><p class="meta">Select a file from either inbox.</p></div>
</div>
<div class="footer">CLI: <code>lan_peer_assign.py list</code> · <code>list --peer</code> · <code>drop --peer</code></div>
<script>
{cp_js}
let selected = null;
function fmtTs(ts) {{
  if (!ts) return '—';
  const d = new Date(ts * 1000);
  return d.toLocaleString();
}}
function esc(s) {{
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}
function renderTable(files, scope) {{
  if (!files || !files.length) {{
    return '<p class="meta" style="padding:.75rem">(empty)</p>';
  }}
  const rows = files.map(f => {{
    const fn = esc(f.filename);
    const topic = esc(f.topic || '—');
    const assignee = esc(f.assignee || '—');
    const source = esc(f.source || '—');
    return `<tr data-scope="${{scope}}" data-name="${{fn}}">`
      + `<td>${{fn}}</td><td>${{assignee}}</td><td>${{topic}}</td>`
      + `<td>${{source}}</td><td>${{fmtTs(f.received_at)}}</td></tr>`;
  }}).join('');
  return '<table class="tbl"><thead><tr><th>File</th><th>Assignee</th><th>Topic</th><th>Source</th><th>Received</th></tr></thead>'
    + '<tbody>' + rows + '</tbody></table>';
}}
function bindRows(root) {{
  root.querySelectorAll('tr[data-name]').forEach(tr => {{
    tr.addEventListener('click', () => selectFile(tr.dataset.scope, tr.dataset.name, tr));
  }});
}}
async function selectFile(scope, name, tr) {{
  document.querySelectorAll('tr.sel').forEach(r => r.classList.remove('sel'));
  if (tr) tr.classList.add('sel');
  selected = {{scope, name}};
  document.getElementById('preview-title').textContent = (scope === 'remote' ? 'Peer: ' : 'Local: ') + name;
  const body = document.getElementById('preview-body');
  body.innerHTML = '<p class="meta">Loading…</p>';
  const url = scope === 'remote'
    ? '/api/peer-inbox/remote/' + encodeURIComponent(name) + '/html'
    : '/api/peer-inbox/' + encodeURIComponent(name) + '/html';
  try {{
    const r = await cpFetch(url);
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || r.statusText);
    const html = d.html || '<pre>' + esc(d.body || '') + '</pre>';
    const meta = d.meta || {{}};
    body.innerHTML = '<p class="meta">'
      + '<span class="tag">' + esc(meta.assignee || '—') + '</span> '
      + '<span class="tag">' + esc(meta.topic || '—') + '</span> '
      + '<span class="tag">fanout: ' + esc(meta.fanout_id || '—') + '</span>'
      + '</p>' + html;
  }} catch (e) {{
    body.innerHTML = '<p class="err">' + esc(e.message) + '</p>';
  }}
}}
async function refresh() {{
  try {{
    const [lr, rr] = await Promise.all([
      cpFetch('/api/peer-inbox'),
      cpFetch('/api/peer-inbox/remote'),
    ]);
    const local = await lr.json();
    const remote = await rr.json();
    const lw = document.getElementById('local-wrap');
    const rw = document.getElementById('remote-wrap');
    if (!remote.ok) {{
      rw.innerHTML = '<p class="err">' + esc(remote.error || 'peer unreachable') + '</p>';
    }} else {{
      rw.innerHTML = renderTable(remote.files, 'remote');
      bindRows(rw);
    }}
    lw.innerHTML = renderTable(local.files, 'local');
    bindRows(lw);
    if (selected) {{
      const sel = document.querySelector(`tr[data-scope="${{selected.scope}}"][data-name="${{selected.name}}"]`);
      if (sel) selectFile(selected.scope, selected.name, sel);
    }}
  }} catch (e) {{
    console.error(e);
  }}
}}
refresh();
setInterval(refresh, 15000);
</script>
</body>
</html>"""


async def fetch_remote_peer_api(
    path: str,
    *,
    peer_ip: str,
    portal_port: int,
    auth_headers: Mapping[str, str] | Callable[[], Mapping[str, str]],
) -> dict[str, Any]:
    """HTTP GET to peer portal for inbox mirror (Win lane API)."""
    if not peer_ip:
        return {
            "ok": False,
            "peer_ip": None,
            "error": "no peer IP in last_discovery.json",
            "files": [],
        }
    headers = auth_headers() if callable(auth_headers) else dict(auth_headers)
    url = f"http://{peer_ip}:{portal_port}{path}"
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.get(url, headers=headers)
        if response.status_code != 200:
            return {
                "ok": False,
                "peer_ip": peer_ip,
                "error": f"HTTP {response.status_code}",
                "files": [],
            }
        data = response.json()
        data["ok"] = True
        data["peer_ip"] = peer_ip
        data["scope"] = "remote"
        return data
    except httpx.HTTPError as exc:
        return {
            "ok": False,
            "peer_ip": peer_ip,
            "error": str(exc),
            "files": [],
        }


def remote_file_html_path(filename: str) -> str:
    return f"/api/peer-inbox/{quote(filename)}/html"


def remote_file_path(filename: str) -> str:
    return f"/api/peer-inbox/{quote(filename)}"
