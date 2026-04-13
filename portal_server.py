#!/usr/bin/env python3
"""portal_server.py — Slate-grey LAN portal on port 8002.

Shows live status of PT, ultrathink, LM Studio Win/Mac, and Ollama Win/Mac.
All probes run concurrently via asyncio.gather.

Routes:
  GET  /           HTML dashboard (meta-refresh every 10s)
  GET  /api/status JSON status of all services
  POST /api/user-input  proxy to PT /user-input (portal textbox handler)
  GET  /health     {"status": "ok", "version": "0.9.9.7"}
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env so IPs are correct whether portal is run from start.sh or directly.
try:
    from dotenv import load_dotenv as _load_dotenv
    _here = Path(__file__).parent
    _load_dotenv(_here / ".env",       override=False)
    _load_dotenv(_here / ".env.local", override=True)
except ImportError:
    pass

log = logging.getLogger("ultrathink.portal")
logging.basicConfig(level=logging.INFO)

VERSION = "0.9.9.7"

# ── Config ─────────────────────────────────────────────────────────────────────

PORTAL_HOST = os.getenv("PORTAL_HOST", "0.0.0.0")
PORTAL_PORT = int(os.getenv("PORTAL_PORT", "8002"))

PT_URL = os.getenv("ORCHESTRATOR_ENDPOINT", "http://localhost:8000")
US_URL = os.getenv("ULTRATHINK_ENDPOINT", "http://localhost:8001")

LMS_WIN_ENDPOINTS: List[str] = [
    ep.strip()
    for ep in os.getenv("LM_STUDIO_WIN_ENDPOINTS", "http://192.168.254.108:1234").split(",")
    if ep.strip()
]
LMS_MAC_ENDPOINT = os.getenv("LM_STUDIO_MAC_ENDPOINT", "http://192.168.254.110:1234")
LMS_API_TOKEN = os.getenv("LM_STUDIO_API_TOKEN", "")

OLLAMA_WIN = os.getenv("OLLAMA_WINDOWS_ENDPOINT", "http://192.168.254.108:11434")
OLLAMA_MAC = os.getenv("OLLAMA_MAC_ENDPOINT", "http://127.0.0.1:11434")

PROBE_TIMEOUT = 3.0

app = FastAPI(title="UltraThink LAN Portal", version=VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── HTML template ──────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="10">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UltraThink LAN Portal</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:#475569;color:#f8fafc;font-family:monospace;font-size:14px;padding:1.5rem}}
  h1{{font-size:1.25rem;letter-spacing:.05em;margin-bottom:1rem;color:#38bdf8}}
  .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem}}
  .card{{background:#334155;border:1px solid #64748b;border-radius:4px;padding:1rem}}
  .card-title{{font-size:.75rem;letter-spacing:.1em;text-transform:uppercase;color:#94a3b8;margin-bottom:.5rem}}
  .badge{{display:inline-block;padding:.15rem .5rem;border-radius:2px;font-size:.75rem;margin-bottom:.5rem}}
  .ok{{color:#4ade80}}
  .err{{color:#f87171}}
  .warn{{color:#fbbf24}}
  .url{{color:#38bdf8;font-size:.75rem}}
  .role{{color:#94a3b8;font-size:.75rem}}
  .models{{margin-top:.5rem}}
  .model{{color:#cbd5e1;font-size:.75rem;padding:.1rem 0}}
  .footer{{margin-top:1.5rem;font-size:.7rem;color:#64748b}}
  .version{{color:#64748b;font-size:.7rem}}
  .section{{margin-top:1.5rem}}
  .section-title{{font-size:.8rem;letter-spacing:.1em;text-transform:uppercase;color:#38bdf8;margin-bottom:.75rem;border-bottom:1px solid #38bdf840;padding-bottom:.25rem}}
  .feed{{background:#334155;border:1px solid #64748b;border-radius:4px;overflow:hidden}}
  .ev{{display:flex;gap:.5rem;padding:.4rem .75rem;border-bottom:1px solid #3f536640;align-items:baseline}}
  .ev:last-child{{border-bottom:none}}
  .ev-ts{{color:#64748b;font-size:.65rem;white-space:nowrap;min-width:5rem}}
  .ev-who{{color:#38bdf8;font-size:.7rem;white-space:nowrap;min-width:9rem}}
  .ev-tag{{font-size:.65rem;border-radius:2px;padding:.05rem .3rem;white-space:nowrap}}
  .tag-reply{{background:#4ade8020;color:#4ade80}}
  .tag-query{{background:#38bdf820;color:#7dd3fc}}
  .tag-error{{background:#f8717120;color:#f87171}}
  .tag-waiting{{background:#fbbf2420;color:#fbbf24}}
  .tag-user{{background:#a78bfa20;color:#a78bfa}}
  .tag-other{{background:#64748b40;color:#94a3b8}}
  .ev-msg{{color:#cbd5e1;font-size:.75rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}}
  .none{{color:#64748b;font-size:.75rem;padding:.75rem}}
  /* routing state card */
  .rt-row{{display:flex;gap:.5rem;margin:.2rem 0;font-size:.75rem}}
  .rt-key{{color:#94a3b8;min-width:7rem}}
  .rt-val{{color:#cbd5e1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}}
  /* input section */
  .input-section{{margin-top:1.5rem}}
  .input-box{{background:#334155;border:1px solid #64748b;border-radius:4px;padding:1rem}}
  .input-label{{font-size:.75rem;letter-spacing:.1em;text-transform:uppercase;color:#38bdf8;margin-bottom:.75rem;display:block}}
  .input-row{{display:flex;gap:.5rem}}
  .input-field{{flex:1;background:#1e293b;border:1px solid #475569;border-radius:3px;color:#f8fafc;font-family:monospace;font-size:.85rem;padding:.45rem .75rem;outline:none}}
  .input-field:focus{{border-color:#38bdf8}}
  .input-btn{{background:#0369a1;border:none;border-radius:3px;color:#f0f9ff;cursor:pointer;font-family:monospace;font-size:.8rem;padding:.45rem 1rem;white-space:nowrap}}
  .input-btn:hover{{background:#0284c7}}
  .input-status{{font-size:.7rem;color:#64748b;margin-top:.4rem;min-height:1rem}}
  .queue-depth{{font-size:.7rem;color:#fbbf24;margin-top:.3rem}}
  /* agent state pills */
  .agent-states{{margin-top:1rem}}
  .state-pill{{display:inline-flex;align-items:center;gap:.3rem;background:#1e293b;border:1px solid #475569;border-radius:12px;padding:.2rem .6rem;font-size:.7rem;margin:.2rem .2rem 0 0}}
  .s-running{{color:#4ade80}}
  .s-idle{{color:#94a3b8}}
  .s-waiting{{color:#fbbf24}}
  .s-error{{color:#f87171}}
  .s-stopped{{color:#475569}}
</style>
</head>
<body>
<h1>UltraThink LAN Portal <span class="version">v{version}</span></h1>
<div class="grid">
{cards}
</div>
{routing_section}
{agent_state_section}
{activity_section}
{input_section}
<div class="footer">Auto-refresh every 10s &bull; {timestamp}</div>
<script>
async function sendTask() {{
  const field = document.getElementById('task-input');
  const status = document.getElementById('input-status');
  const msg = field.value.trim();
  if (!msg) {{ status.textContent = 'Enter a task first.'; return; }}
  status.textContent = 'Sending…';
  try {{
    const r = await fetch('/api/user-input', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{message: msg}})
    }});
    const d = await r.json();
    if (d.status === 'queued') {{
      status.textContent = '✓ Queued (depth: ' + d.queue_depth + ')';
      field.value = '';
    }} else {{
      status.textContent = 'Error: ' + JSON.stringify(d);
    }}
  }} catch(e) {{
    status.textContent = 'Request failed: ' + e;
  }}
}}
document.addEventListener('DOMContentLoaded', function() {{
  document.getElementById('task-input').addEventListener('keydown', function(e) {{
    if (e.key === 'Enter') sendTask();
  }});
}});
</script>
</body>
</html>"""


def _status_badge(ok: bool) -> str:
    if ok:
        return '<span class="ok">&#9679; ONLINE</span>'
    return '<span class="err">&#9679; OFFLINE</span>'


def _render_card(title: str, ok: bool, url: str, role: str = "", models: List[str] = None, extra: str = "") -> str:
    models_html = ""
    if models:
        items = "".join(f'<div class="model">&rsaquo; {m}</div>' for m in models[:5])
        if len(models) > 5:
            items += f'<div class="model">...+{len(models)-5} more</div>'
        models_html = f'<div class="models">{items}</div>'
    role_html = f'<div class="role">{role}</div>' if role else ""
    return (
        f'<div class="card">'
        f'<div class="card-title">{title}</div>'
        f'{_status_badge(ok)}'
        f'{role_html}'
        f'<div class="url">{url}</div>'
        f'{models_html}'
        f'{extra}'
        f'</div>'
    )


def _render_routing_section(routing: Dict[str, Any] | None) -> str:
    if not routing:
        return (
            '<div class="section">'
            '<div class="section-title">Routing State</div>'
            '<div class="feed"><div class="none">Routing state unavailable — PT may still be probing backends</div></div>'
            '</div>'
        )
    distributed = routing.get("distributed", False)
    mode_color = "ok" if distributed else "warn"
    mode_text = "DISTRIBUTED" if distributed else "SINGLE"
    rows = [
        f'<div class="rt-row"><span class="rt-key">mode</span><span class="rt-val {mode_color}">{mode_text}</span></div>',
        f'<div class="rt-row"><span class="rt-key">manager</span><span class="rt-val">{routing.get("manager_endpoint","—")}</span></div>',
        f'<div class="rt-row"><span class="rt-key">manager model</span><span class="rt-val">{routing.get("manager_model","—")}</span></div>',
        f'<div class="rt-row"><span class="rt-key">coder</span><span class="rt-val">{routing.get("coder_endpoint","—")}</span></div>',
        f'<div class="rt-row"><span class="rt-key">coder model</span><span class="rt-val">{routing.get("coder_model","—")}</span></div>',
        f'<div class="rt-row"><span class="rt-key">mac reachable</span><span class="rt-val">{"✓" if routing.get("mac_reachable") else "✗"}</span></div>',
        f'<div class="rt-row"><span class="rt-key">win reachable</span><span class="rt-val">{"✓" if routing.get("lmstudio_detected") else "✗"}</span></div>',
    ]
    synced_at = routing.get("synced_at", "")
    if synced_at:
        rows.append(f'<div class="rt-row"><span class="rt-key">synced at</span><span class="rt-val">{synced_at}</span></div>')
    return (
        '<div class="section">'
        '<div class="section-title">Routing State</div>'
        '<div class="card">' + "".join(rows) + '</div>'
        '</div>'
    )


def _render_agent_state_section(agents: List[Dict[str, Any]]) -> str:
    if not agents:
        return (
            '<div class="section">'
            '<div class="section-title">Active Agents</div>'
            '<div class="feed"><div class="none">No agents registered yet</div></div>'
            '</div>'
        )
    pills = []
    for a in agents:
        status = a.get("status", "unknown")
        role = a.get("role", a.get("agent_id", "?"))
        model = a.get("model", "")
        css = {"running": "s-running", "idle": "s-idle", "error": "s-error",
               "stopped": "s-stopped", "waiting_for_input": "s-waiting"}.get(status, "s-idle")
        icon = {"running": "▶", "idle": "◉", "error": "✗",
                "stopped": "◻", "waiting_for_input": "✋"}.get(status, "·")
        label = f"{icon} {role}"
        if model:
            label += f"  <span style='color:#64748b'>{model[:30]}</span>"
        pills.append(f'<span class="state-pill"><span class="{css}">{label}</span></span>')
    return (
        '<div class="section">'
        '<div class="section-title">Active Agents</div>'
        '<div class="agent-states">' + "".join(pills) + '</div>'
        '</div>'
    )


def _render_activity_section(events: List[Dict[str, Any]]) -> str:
    import datetime

    def _fmt_ts(ts: float) -> str:
        try:
            return datetime.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
        except Exception:
            return "—"

    def _tag(event: str) -> str:
        if event in ("reply", "reply_received"):
            return '<span class="ev-tag tag-reply">reply</span>'
        if event in ("query_sent", "started"):
            return '<span class="ev-tag tag-query">{}</span>'.format(event)
        if event == "error":
            return '<span class="ev-tag tag-error">error</span>'
        if event in ("waiting_for_input",):
            return '<span class="ev-tag tag-waiting">waiting</span>'
        if event in ("user_task_received",):
            return '<span class="ev-tag tag-user">user task</span>'
        return '<span class="ev-tag tag-other">{}</span>'.format(event)

    if not events:
        return (
            '<div class="section">'
            '<div class="section-title">Autoresearchers</div>'
            '<div class="feed"><div class="none">No activity yet — run scripts/launch_researchers.py</div></div>'
            '</div>'
        )

    rows = []
    for ev in events[:15]:
        msg = ev.get("msg", "")[:120].replace("<", "&lt;").replace(">", "&gt;")
        rows.append(
            '<div class="ev">'
            f'<span class="ev-ts">{_fmt_ts(ev.get("ts", 0))}</span>'
            f'<span class="ev-who">{ev.get("agent","?")}</span>'
            f'{_tag(ev.get("event","?"))}'
            f'<span class="ev-msg">{msg}</span>'
            '</div>'
        )
    return (
        '<div class="section">'
        '<div class="section-title">Autoresearchers</div>'
        '<div class="feed">'
        + "".join(rows)
        + '</div></div>'
    )


def _render_input_section(queue_depth: int) -> str:
    depth_html = ""
    if queue_depth > 0:
        depth_html = f'<div class="queue-depth">&#9679; {queue_depth} task(s) pending in queue</div>'
    return (
        '<div class="input-section">'
        '<div class="input-box">'
        '<label class="input-label" for="task-input">Send Task to Agents</label>'
        '<div class="input-row">'
        '<input id="task-input" class="input-field" type="text" '
        'placeholder="Describe the task for the researchers…" autocomplete="off">'
        '<button class="input-btn" onclick="sendTask()">Send &#9654;</button>'
        '</div>'
        f'<div class="input-status" id="input-status">{depth_html}</div>'
        '<div style="font-size:.65rem;color:#475569;margin-top:.4rem">'
        f'CLI: curl -sX POST {PT_URL}/user-input -H \'Content-Type: application/json\' '
        '-d \'{"message":"your task"}\''
        '</div>'
        '</div>'
        '</div>'
    )


def _render_html(status: Dict[str, Any]) -> str:
    import datetime

    cards = []
    svc = status.get("services", {})

    # PT
    pt = svc.get("perplexity_tools", {})
    cards.append(_render_card(
        "Perplexity-Tools", pt.get("ok", False), pt.get("url", ""),
        role="orchestrator / cloud router",
        extra=f'<div class="version">{pt.get("version","")}</div>',
    ))

    # US
    us = svc.get("ultrathink", {})
    cards.append(_render_card(
        "UltraThink API", us.get("ok", False), us.get("url", ""),
        role="5-stage reasoning bridge",
        extra=f'<div class="version">{us.get("version","")}</div>',
    ))

    # LM Studio Mac
    lm_mac = svc.get("lmstudio_mac", {})
    cards.append(_render_card(
        "LM Studio — Mac", lm_mac.get("ok", False), lm_mac.get("url", ""),
        role="orchestrator + validator + presenter",
        models=lm_mac.get("models", []),
    ))

    # LM Studio Win(s)
    for key, entry in svc.items():
        if key.startswith("lmstudio_win"):
            label = "LM Studio — Win" if key == "lmstudio_win" else f"LM Studio — {key}"
            cards.append(_render_card(
                label, entry.get("ok", False), entry.get("url", ""),
                role="UltraThink agent (coder/checker/refiner/executor/verifier)",
                models=entry.get("models", []),
            ))

    # Ollama Win
    ol_win = svc.get("ollama_win", {})
    cards.append(_render_card(
        "Ollama — Win (fallback)", ol_win.get("ok", False), ol_win.get("url", ""),
        models=ol_win.get("models", []),
    ))

    # Ollama Mac
    ol_mac = svc.get("ollama_mac", {})
    cards.append(_render_card(
        "Ollama — Mac (manager)", ol_mac.get("ok", False), ol_mac.get("url", ""),
        role="manager: qwen3.5-local",
        models=ol_mac.get("models", []),
    ))

    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    activity_events = status.get("activity", [])
    routing = status.get("routing")
    agents = status.get("agents", [])
    queue_depth = status.get("queue_depth", 0)
    return HTML_TEMPLATE.format(
        version=VERSION,
        cards="\n".join(cards),
        routing_section=_render_routing_section(routing),
        agent_state_section=_render_agent_state_section(agents),
        activity_section=_render_activity_section(activity_events),
        input_section=_render_input_section(queue_depth),
        timestamp=ts,
    )


# ── Probes ─────────────────────────────────────────────────────────────────────

async def _probe_http(client: httpx.AsyncClient, url: str) -> tuple[bool, str]:
    try:
        r = await client.get(url, timeout=PROBE_TIMEOUT)
        version = ""
        try:
            data = r.json()
            version = data.get("version", "")
        except Exception:
            pass
        return r.status_code < 500, version
    except Exception:
        return False, ""


async def _probe_lms_models(client: httpx.AsyncClient, endpoint: str, token: str) -> tuple[bool, List[str]]:
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = await client.get(f"{endpoint}/v1/models", headers=headers, timeout=PROBE_TIMEOUT)
        r.raise_for_status()
        models = [m["id"] for m in r.json().get("data", [])]
        return True, models
    except Exception:
        return False, []


async def _probe_ollama_models(client: httpx.AsyncClient, endpoint: str) -> tuple[bool, List[str]]:
    try:
        r = await client.get(f"{endpoint}/api/tags", timeout=PROBE_TIMEOUT)
        r.raise_for_status()
        models = [m.get("name", "") for m in r.json().get("models", [])]
        return True, models
    except Exception:
        return False, []


async def _probe_activity(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    try:
        r = await client.get(f"{PT_URL}/activity?limit=15", timeout=PROBE_TIMEOUT)
        r.raise_for_status()
        return r.json().get("events", [])
    except Exception:
        return []


async def _probe_agents(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch active agents from PT's /agents endpoint."""
    try:
        r = await client.get(f"{PT_URL}/agents", timeout=PROBE_TIMEOUT)
        r.raise_for_status()
        return r.json().get("agents", [])
    except Exception:
        return []


async def _probe_routing(client: httpx.AsyncClient) -> Dict[str, Any] | None:
    """Fetch current routing state from PT's /runtime endpoint."""
    try:
        r = await client.get(f"{PT_URL}/runtime", timeout=PROBE_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


async def _probe_queue_depth(client: httpx.AsyncClient) -> int:
    """Fetch pending user-input queue depth from PT."""
    try:
        r = await client.get(f"{PT_URL}/user-input/status", timeout=PROBE_TIMEOUT)
        r.raise_for_status()
        return r.json().get("queue_depth", 0)
    except Exception:
        return 0


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "version": VERSION}


class UserInputRequest(BaseModel):
    message: str
    source: str = "portal"


@app.post("/api/user-input")
async def api_user_input(req: UserInputRequest):
    """Proxy user task from portal textbox to PT's /user-input queue."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.post(
                f"{PT_URL}/user-input",
                json={"message": req.message, "source": "portal"},
            )
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            return {"status": "error", "message": str(exc)}


@app.get("/api/status")
async def api_status():
    async with httpx.AsyncClient() as client:
        (
            (pt_ok, pt_ver),
            (us_ok, us_ver),
            (lm_mac_ok, lm_mac_models),
            ol_win_result,
            ol_mac_result,
            activity_events,
            agents,
            routing,
            queue_depth,
            *lm_win_results,
        ) = await asyncio.gather(
            _probe_http(client, f"{PT_URL}/health"),
            _probe_http(client, f"{US_URL}/health"),
            _probe_lms_models(client, LMS_MAC_ENDPOINT, LMS_API_TOKEN),
            _probe_ollama_models(client, OLLAMA_WIN),
            _probe_ollama_models(client, OLLAMA_MAC),
            _probe_activity(client),
            _probe_agents(client),
            _probe_routing(client),
            _probe_queue_depth(client),
            *[_probe_lms_models(client, ep, LMS_API_TOKEN) for ep in LMS_WIN_ENDPOINTS],
        )

    services: Dict[str, Any] = {
        "perplexity_tools": {"ok": pt_ok, "version": pt_ver, "url": PT_URL},
        "ultrathink": {"ok": us_ok, "version": us_ver, "url": US_URL},
        "lmstudio_mac": {"ok": lm_mac_ok, "models": lm_mac_models, "url": LMS_MAC_ENDPOINT},
        "ollama_win": {"ok": ol_win_result[0], "models": ol_win_result[1], "url": OLLAMA_WIN},
        "ollama_mac": {"ok": ol_mac_result[0], "models": ol_mac_result[1], "url": OLLAMA_MAC},
    }

    if len(LMS_WIN_ENDPOINTS) == 1:
        ok, models = lm_win_results[0]
        services["lmstudio_win"] = {"ok": ok, "models": models, "url": LMS_WIN_ENDPOINTS[0]}
    else:
        for i, (ok, models) in enumerate(lm_win_results):
            services[f"lmstudio_win_{i}"] = {"ok": ok, "models": models, "url": LMS_WIN_ENDPOINTS[i]}

    return {
        "portal_version": VERSION,
        "services": services,
        "activity": activity_events,
        "agents": agents,
        "routing": routing,
        "queue_depth": queue_depth,
    }


@app.get("/", response_class=None)
async def index():
    from fastapi.responses import HTMLResponse
    status = await api_status()
    html = _render_html(status)
    return HTMLResponse(content=html)


if __name__ == "__main__":
    uvicorn.run(app, host=PORTAL_HOST, port=PORTAL_PORT)
