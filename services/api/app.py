"""
FastAPI application for the Digital-SSP platform.
Provides JSON APIs and lightweight HTML console pages.
"""

from typing import Dict, List, Optional
from uuid import uuid4
import logging
import time
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from services.delivery_engine.types import AdRequest, LineItem, Size
from services.delivery_engine.decision import evaluate_request
from services.api.examples import ALL_LINE_ITEMS, FLOOR_RULES, EXAMPLE_REQUESTS
from services.api.mysql_queries import get_line_items_for_engine


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _esc(val: str) -> str:
    """Minimal HTML escaping for inline strings."""
    if val is None:
        return ""
    return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _page(title: str, content: str, active_nav: str = "") -> str:
    """Fallback page wrapper for console pages (CSS moved to static files)."""
    nav_items = [
        ("Home", "/", "🏠"),
        ("Delivery", "/delivery", "📦"),
        ("Inventory", "/inventory", "📊"),
        ("Reporting", "/reporting", "📈"),
        ("Optimization", "/optimization", "⚡"),
        ("Programmatic", "/programmatic", "💰"),
        ("Admin", "/admin", "⚙️"),
        ("Privacy", "/privacy", "🔒"),
        ("Tools", "/tools", "🛠️"),
    ]
    
    sidebar_html = ""
    for label, url, icon in nav_items:
        is_active = "active" if active_nav.lower() == label.lower() else ""
        sidebar_html += f'<a href="{url}" class="sidebar-item {is_active}"><span class="icon">{icon}</span>{label}</a>'
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_esc(title)} - Digital-SSP</title>
    <link rel="stylesheet" href="/static/css/console.css">
</head>
<body>
    <div class="top-header">
        <div class="logo-container">
            <svg class="logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
            <span class="logo-text">Digital-<strong>SSP</strong></span>
        </div>
        <div class="search-container">
            <input type="text" placeholder="Search orders, line items, ad units..." class="search-input">
        </div>
        <div class="header-actions">
            <span class="network-badge">DEMO NETWORK</span>
            <div class="user-menu">👤</div>
        </div>
    </div>
    
    <div class="layout-container">
        <div class="sidebar">
            <div class="sidebar-section">
                <div class="sidebar-section-title">Main</div>
                {sidebar_html}
            </div>
            <div class="sidebar-section">
                <div class="sidebar-section-title">Help</div>
                <a href="/docs" class="sidebar-item"><span class="icon">📘</span>API Docs</a>
                <a href="/examples" class="sidebar-item"><span class="icon">💡</span>Examples</a>
            </div>
        </div>
        
        <div class="main-content">
            {content}
        </div>
    </div>
</body>
</html>
"""

# Setup templates and static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


# Logging
logging.basicConfig(level="INFO", format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# FastAPI app
app = FastAPI(title="Digital-SSP API", version="1.0.0", description="Digital Supply-Side Platform for programmatic advertising")

# Mount static files
static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# -----------------------------------------------------------------------------
# Models
# -----------------------------------------------------------------------------
class SizeModel(BaseModel):
    w: int = Field(..., description="Width in pixels")
    h: int = Field(..., description="Height in pixels")


class AdRequestModel(BaseModel):
    adUnit: str = Field(..., description="Ad unit path")
    sizes: List[SizeModel]
    kv: Dict[str, str] = Field(default_factory=dict)
    geo: str
    device: str
    userId: Optional[str] = None
    viewportW: Optional[int] = None

    def to_domain(self) -> AdRequest:
        return AdRequest(
            req_id=str(uuid4()),
            ad_unit=self.adUnit,
            sizes=[Size(w=s.w, h=s.h) for s in self.sizes],
            kv=self.kv,
            geo=self.geo,
            device=self.device,
            user_id=self.userId,
            viewport_w=self.viewportW,
        )


class LineItemModel(BaseModel):
    id: str
    name: Optional[str] = None
    priority: int
    cpm: float
    targeting: Dict
    pacing: str
    booked_imps: Optional[int] = None
    delivered_imps: Optional[int] = None


class BidModel(BaseModel):
    source: str
    price: float
    line_item_id: str
    creative_id: Optional[str] = None
    adm: Optional[str] = None
    request_id: Optional[str] = None


class DecisionTraceModel(BaseModel):
    req_id: str
    steps: List[Dict]
    winner: Optional[BidModel] = None
    no_fill_reason: Optional[str] = None


# -----------------------------------------------------------------------------
# Data
# -----------------------------------------------------------------------------
try:
    LINE_ITEMS: List[LineItem] = get_line_items_for_engine()
    if not LINE_ITEMS:
        LINE_ITEMS = ALL_LINE_ITEMS
        logger.warning("Using in-memory sample line items; DB returned none.")
except Exception as e:
    logger.error(f"Error loading line items from DB: {e}")
    LINE_ITEMS = ALL_LINE_ITEMS
FLOOR_RULES_DATA = FLOOR_RULES
REQUEST_TRACES: Dict[str, Dict] = {}


# -----------------------------------------------------------------------------
# API endpoints
# -----------------------------------------------------------------------------
async def _render_console(request: Request):
    """Shared renderer for the console dashboard."""
    try:
        from services.api.mysql_queries import get_dashboard_data
        dashboard_data = get_dashboard_data()
    except Exception as e:
        logger.error(f"Error fetching dashboard data: {e}")
        dashboard_data = {}

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "active_nav": "Home", "data": dashboard_data},
    )


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    # Render console directly at root for a consistent entry point.
    return await _render_console(request)


@app.post("/ad", response_model=BidModel)
async def get_ad(req: AdRequestModel):
    domain_req = req.to_domain()
    now = time.time()

    trace = evaluate_request(domain_req, LINE_ITEMS, {"floor_rules": FLOOR_RULES_DATA}, now=now)

    REQUEST_TRACES[trace.req_id] = {"trace": trace, "timestamp": now}

    if not trace.winner:
        raise HTTPException(status_code=204, detail=trace.no_fill_reason or "no-fill")

    return trace.winner


@app.get("/ad/{req_id}/debug", response_model=DecisionTraceModel)
async def debug_request(req_id: str):
    if req_id not in REQUEST_TRACES:
        raise HTTPException(status_code=404, detail="Request not found")
    trace = REQUEST_TRACES[req_id]["trace"]
    return {
        "req_id": trace.req_id,
        "steps": trace.steps,
        "winner": trace.winner,
        "no_fill_reason": trace.no_fill_reason,
    }


@app.get("/line-items", response_model=List[LineItemModel])
async def list_line_items():
    return [
        {
            "id": li.id,
            "priority": li.priority,
            "cpm": li.cpm,
            "targeting": li.targeting,
            "pacing": li.pacing,
            "booked_imps": li.booked_imps,
            "delivered_imps": li.delivered_imps,
        }
        for li in LINE_ITEMS
    ]


@app.get("/examples")
async def get_examples():
    return {
        "description": "Example ad requests for testing",
        "examples": EXAMPLE_REQUESTS,
        "how_to_use": "Copy an example and POST it to /ad",
        "note": "Each POST to /ad creates a request_id you can use with /ad/{req_id}/debug",
    }


@app.get("/floor-rules")
async def get_floor_rules():
    return {"rules": FLOOR_RULES_DATA, "note": "Rules are evaluated in order"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time(), "line_items_count": len(LINE_ITEMS)}


@app.get("/stats")
async def get_stats():
    total_requests = len(REQUEST_TRACES)
    filled = sum(1 for t in REQUEST_TRACES.values() if t["trace"].winner)
    total_booked = sum(li.booked_imps or 0 for li in LINE_ITEMS if li.booked_imps)
    total_delivered = sum(li.delivered_imps or 0 for li in LINE_ITEMS)
    return {
        "total_requests": total_requests,
        "filled_requests": filled,
        "fill_rate": filled / max(total_requests, 1),
        "total_booked_impressions": total_booked,
        "total_delivered_impressions": total_delivered,
        "line_items_count": len(LINE_ITEMS),
    }


# -----------------------------------------------------------------------------
# Console pages
# -----------------------------------------------------------------------------
@app.get("/console", response_class=RedirectResponse, status_code=307)
async def console_redirect():
    # Backward compatibility: old /console links now land on root.
    return RedirectResponse(url="/", status_code=307)


@app.get("/delivery", response_class=HTMLResponse)
async def console_delivery(request: Request):
    """Delivery management page."""
    return templates.TemplateResponse("delivery.html", {"request": request, "active_nav": "Delivery"})


@app.get("/orders", response_class=HTMLResponse)
async def console_orders(request: Request):
    """Orders management page using Jinja2 template with live MySQL data."""
    try:
        from services.api.mysql_queries import get_orders_list
        orders = get_orders_list()
    except Exception as e:
        logger.error(f"Error fetching orders data: {e}")
        orders = []
    return templates.TemplateResponse("orders.html", {"request": request, "active_nav": "Orders", "orders": orders})


@app.get("/inventory", response_class=HTMLResponse)
async def console_inventory():
    ad_units = set()
    placements = set()
    kvs = {}
    sizes = set()

    for li in LINE_ITEMS:
        for unit in li.targeting.get("adUnits", []) or []:
            ad_units.add(unit)
        for placement in li.targeting.get("placements", []) or []:
            placements.add(placement)
        for k, v in (li.targeting.get("kv", {}) or {}).items():
            vals = v if isinstance(v, list) else [v]
            kvs.setdefault(k, set()).update(vals)
        for c in li.creatives:
            sizes.add(f"{c.size.w}x{c.size.h}")

    ad_rows = "".join(f"<span class='pill'>{_esc(u)}</span>" for u in sorted(ad_units)) or "<span class='muted'>No ad units configured</span>"
    placement_rows = "".join(f"<span class='pill'>{_esc(p)}</span>" for p in sorted(placements)) or "<span class='muted'>No placements</span>"
    kv_rows = "".join(
        f"""
        <tr>
            <td>{_esc(k)}</td>
            <td>{', '.join(_esc(v) for v in sorted(vals))}</td>
        </tr>
        """
        for k, vals in sorted(kvs.items())
    ) or "<tr><td colspan='2' class='muted'>No key-values defined</td></tr>"

    size_rows = "".join(f"<span class='pill'>{_esc(s)}</span>" for s in sorted(sizes)) or "<span class='muted'>No creative sizes yet</span>"

    body = f"""
        <div class=\"card\" style=\"margin-bottom:20px;\">
            <h2>Inventory</h2>
            <div class=\"muted\">Ad units, placements, labels, key-values</div>
            <div style=\"display:grid; grid-template-columns: repeat(auto-fit, minmax(240px,1fr)); gap:14px; margin-top:12px;\">
                <div class=\"card\"><h4>Ad Units</h4>{ad_rows}</div>
                <div class=\"card\"><h4>Placements</h4>{placement_rows}</div>
                <div class=\"card\"><h4>Sizes in use</h4>{size_rows}</div>
            </div>
        </div>
        <div class=\"card\">
            <h3>Key-Values</h3>
            <div class=\"muted\">Custom targeting keys and allowed values from loaded line items.</div>
            <table style=\"margin-top:10px;\">
                <thead><tr><th>Key</th><th>Values</th></tr></thead>
                <tbody>{kv_rows}</tbody>
            </table>
        </div>
    """
    return HTMLResponse(_page("Inventory", body, "Inventory"))


@app.get("/reporting", response_class=HTMLResponse)
async def console_reporting():
    total_requests = len(REQUEST_TRACES)
    filled = sum(1 for t in REQUEST_TRACES.values() if t["trace"].winner)
    fill_rate = filled / max(total_requests, 1)
    templates = [
        ("Network delivery", "Dimensions: date, ad unit; Metrics: imps, revenue, eCPM"),
        ("Line item pacing", "Dimensions: line item; Metrics: booked, delivered, pacing"),
        ("Creative quality", "Dimensions: creative; Metrics: errors, size"),
    ]

    template_rows = "".join(
        f"<tr><td>{_esc(name)}</td><td>{_esc(desc)}</td><td><a href='/stats'>Run sample</a></td></tr>" for name, desc in templates
    )

    body = f"""
        <div class=\"card\" style=\"margin-bottom:20px;\">
            <h2>Reporting</h2>
            <div class=\"muted\">Quick stats derived from current simulator state.</div>
            <div style=\"display:flex; gap:14px; flex-wrap:wrap; margin-top:12px;\">
                <div class=\"card\" style=\"flex:1; min-width:220px;\"><div class=\"muted\">Requests</div><div style=\"font-size:24px; font-weight:700;\">{total_requests}</div></div>
                <div class=\"card\" style=\"flex:1; min-width:220px;\"><div class=\"muted\">Filled</div><div style=\"font-size:24px; font-weight:700;\">{filled}</div></div>
                <div class=\"card\" style=\"flex:1; min-width:220px;\"><div class=\"muted\">Fill Rate</div><div style=\"font-size:24px; font-weight:700;\">{fill_rate:.2%}</div></div>
            </div>
        </div>
        <div class=\"card\">
            <h3>Templates</h3>
            <table style=\"margin-top:10px;\"><thead><tr><th>Name</th><th>Definition</th><th>Action</th></tr></thead><tbody>{template_rows}</tbody></table>
            <p class=\"muted\" style=\"margin-top:10px;\">Use the API for full reporting: /stats, /line-items, /floor-rules, /ad/&lt;req&gt;/debug.</p>
        </div>
    """
    return HTMLResponse(_page("Reporting", body, "Reporting"))


@app.get("/optimization", response_class=HTMLResponse)
async def console_optimization():
    rows = []
    for rule in FLOOR_RULES_DATA:
        rows.append(
            f"<tr><td>${rule.get('floor',0):.2f}</td><td>{_esc(rule.get('ad_unit','Any'))}</td><td>{_esc(rule.get('geo','Any'))}</td><td>{_esc(rule.get('device','Any'))}</td></tr>"
        )

    tips = [
        "Run availability check before increasing goals.",
        "Tighten floor rules by geo/device where IVT is high.",
        "Use pacing insights: shift from ASAP to Even when ahead.",
    ]
    tip_list = "".join(f"<li>{_esc(t)}</li>" for t in tips)

    body = f"""
        <div class=\"card\" style=\"margin-bottom:20px;\">
            <h2>Optimization</h2>
            <div class=\"muted\">Floors and quick win suggestions.</div>
            <table style=\"margin-top:10px;\"><thead><tr><th>Floor</th><th>Ad Unit</th><th>Geo</th><th>Device</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
        </div>
        <div class=\"card\"><h3>Suggestions</h3><ul>{tip_list}</ul></div>
    """
    return HTMLResponse(_page("Optimization", body, "Optimization"))


@app.get("/programmatic", response_class=HTMLResponse)
async def console_programmatic_page():
    body = f"""
        <div class=\"card\" style=\"margin-bottom:20px;\">
            <h2>Programmatic & Deals</h2>
            <div class=\"muted\">Unified auction placeholder: floors, buyers, deals.</div>
            <p>Use floor rules as yield groups; map buyers and deals in a future iteration.</p>
            <ul>
                <li><a href="/floors">Floor rules</a></li>
                <li><a href=\"/line-items\">Line items JSON</a> for price priority vs. sponsorship mix</li>
            </ul>
        </div>
        <div class=\"card\">
            <h3>What to add next</h3>
            <ul>
                <li>Deal creation form (PMP/PG) with fixed or floor price</li>
                <li>Buyer/seat picker and targeting summary chips</li>
                <li>Auction simulator showing applied floor and winner</li>
            </ul>
        </div>
    """
    return HTMLResponse(_page("Programmatic", body, "Programmatic"))


@app.get("/admin", response_class=HTMLResponse)
async def console_admin():
    body = f"""
        <div class=\"card\" style=\"margin-bottom:20px;\">
            <h2>Admin</h2>
            <div class=\"muted\">RBAC, settings, and integrations (static for now).</div>
            <ul>
                <li>Users & Roles: add role presets (Viewer, Trafficker, Admin)</li>
                <li>Network settings: currency, timezone, default priorities</li>
                <li>API keys & webhooks: rotate keys, view audit log</li>
            </ul>
        </div>
        <div class=\"card\">
            <h3>Current simulator stats</h3>
            <p>Line items loaded: {len(LINE_ITEMS)}</p>
            <p>Floor rules loaded: {len(FLOOR_RULES_DATA)}</p>
            <p>Requests logged: {len(REQUEST_TRACES)}</p>
        </div>
    """
    return HTMLResponse(_page("Admin", body, "Admin"))


@app.get("/privacy", response_class=HTMLResponse)
async def console_privacy():
    body = """
        <div class=\"card\" style=\"margin-bottom:20px;\">
            <h2>Privacy & Messaging</h2>
            <div class=\"muted\">Consent and restricted ads (conceptual)</div>
            <ul>
                <li>CMP config: TCF/CCPA toggles, default consent</li>
                <li>Region/device rules: enforce Limited Ads mode</li>
                <li>Message templates: A/B variants and preview</li>
                <li>Logs: consent strings, enforcement outcomes</li>
            </ul>
        </div>
        <div class=\"card\">
            <h3>Next</h3>
            <p>Wire CMP signals into request evaluation and expose them in /ad/&lt;req_id&gt;/debug.</p>
        </div>
    """
    return HTMLResponse(_page("Privacy", body, "Privacy"))


@app.get("/tools", response_class=HTMLResponse)
async def console_tools():
    recent = sorted(REQUEST_TRACES.items(), key=lambda x: x[1]["timestamp"], reverse=True)[:15]
    trace_rows = []
    for req_id, data in recent:
        trace = data["trace"]
        winner = trace.winner.line_item_id if trace.winner else "—"
        trace_rows.append(f"<tr><td>{_esc(req_id)}</td><td>{_esc(winner)}</td><td><a href='/ad/{_esc(req_id)}/debug'>Debug</a></td></tr>")

    body = f"""
        <div class=\"card\" style=\"margin-bottom:20px;\">
            <h2>Tools</h2>
            <ul>
                <li><a href=\"/docs\">Swagger</a> to POST /ad and view schemas</li>
                <li><a href=\"/examples\">Example requests</a> for quick testing</li>
                <li><a href=\"/stats\">Stats</a> for health</li>
                <li><a href="/floors">Floor rules</a> viewer</li>
            </ul>
        </div>
        <div class=\"card\">
            <h3>Recent Debug Traces</h3>
            <table style=\"margin-top:10px;\"><thead><tr><th>Request</th><th>Winner</th><th>Debug</th></tr></thead><tbody>{''.join(trace_rows) if trace_rows else '<tr><td colspan="3" class="muted">No requests yet</td></tr>'}</tbody></table>
        </div>
    """
    return HTMLResponse(_page("Tools", body, "Tools"))


@app.get("/line-items", response_class=HTMLResponse)
async def console_line_items(request: Request):
    """Line items management page using Jinja2 template with live MySQL data."""
    try:
        from services.api.mysql_queries import get_line_items_list
        line_items = get_line_items_list()
    except Exception as e:
        logger.error(f"Error fetching line items data: {e}")
        line_items = []
    return templates.TemplateResponse("line_items.html", {"request": request, "active_nav": "Line Items", "line_items": line_items})


@app.get("/creatives", response_class=HTMLResponse)
async def console_creatives(request: Request):
    """Creatives management page using Jinja2 template with live MySQL data."""
    try:
        from services.api.mysql_queries import get_creatives_list
        creatives = get_creatives_list()
    except Exception as e:
        logger.error(f"Error fetching creatives data: {e}")
        creatives = []
    return templates.TemplateResponse("creatives.html", {"request": request, "active_nav": "Creatives", "creatives": creatives})


@app.get("/study-hub", response_class=HTMLResponse)
async def console_study_hub(request: Request):
    """Study Hub page for organizing learning resources."""
    return templates.TemplateResponse("study_hub.html", {"request": request, "active_nav": "Study Hub"})

@app.get("/pacing", response_class=HTMLResponse)
async def console_pacing(request: Request):
    """Pacing & delivery controls page using Jinja2 template."""
    return templates.TemplateResponse("pacing.html", {"request": request, "active_nav": "Pacing"})

@app.get("/api/dashboard-data")
async def api_dashboard_data(period: str = 'today'):
    """API endpoint to fetch dashboard data as JSON for auto-refresh.
    
    Args:
        period: 'today', 'last24h', or 'last7d'
    """
    try:
        from services.api.mysql_queries import get_dashboard_data
        dashboard_data = get_dashboard_data(period=period)
        return dashboard_data
    except Exception as e:
        logger.error(f"Error fetching dashboard data API: {e}")
        return {"error": str(e)}

@app.get("/creative-health-check", response_class=HTMLResponse)
async def console_creative_health_check(request: Request):
    """Creative health check and QA page using Jinja2 template."""
    return templates.TemplateResponse("creative-health-check.html", {"request": request, "active_nav": "Creative Health"})

@app.get("/audiences", response_class=HTMLResponse)
async def console_audiences(request: Request):
    """Audience management and segmentation page using Jinja2 template."""
    return templates.TemplateResponse("audiences.html", {"request": request, "active_nav": "Audiences"})

@app.get("/floors", response_class=HTMLResponse)
async def console_floors():
    rows = []
    for rule in FLOOR_RULES_DATA:
        rows.append(
            f"""
            <tr>
                <td>${rule.get('floor', 0):.2f}</td>
                <td>{_esc(rule.get('ad_unit', 'Any'))}</td>
                <td>{_esc(rule.get('geo', 'Any'))}</td>
                <td>{_esc(rule.get('device', 'Any'))}</td>
            </tr>
        """
        )

    body = f"""
        <div class=\"card\">
            <h2>Floor Rules</h2>
            <div class=\"muted\" style=\"margin-bottom:12px;\">Highest matching floor wins</div>
            <table>
                <thead>
                    <tr><th>Floor</th><th>Ad Unit</th><th>Geo</th><th>Device</th></tr>
                </thead>
                <tbody>{''.join(rows)}</tbody>
            </table>
        </div>
    """
    return HTMLResponse(_page("Floor Rules", body, "Optimization"))


# -----------------------------------------------------------------------------
# Lifecycle
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("Digital-SSP API starting...")
    logger.info(f"Loaded {len(LINE_ITEMS)} line items")
    logger.info(f"Configured {len(FLOOR_RULES_DATA)} floor rules")
    logger.info("API running on http://0.0.0.0:8001")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Digital-SSP API shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("services.api.app:app", host="0.0.0.0", port=8001, reload=False)
