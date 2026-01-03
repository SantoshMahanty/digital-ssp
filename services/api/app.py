"""
FastAPI application for GAM-360 Simulator.

Main endpoints:
- POST /ad - Submit ad request and get winning creative
- GET /ad/{req_id}/debug - Debug trace for a request
- POST /line-items - Create/manage line items
- GET /line-items - List line items
- GET /docs - Interactive API docs (Swagger)
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import uuid4
import logging
import time

from services.delivery_engine.types import AdRequest, LineItem, Size, Creative
from services.delivery_engine.decision import evaluate_request
from services.api.examples import ALL_LINE_ITEMS, FLOOR_RULES, EXAMPLE_REQUESTS

# Configure logging
logging.basicConfig(
    level='INFO',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="GAM-360 Simulator API",
    version="1.0.0",
    description="Educational simulator for Google Ad Manager 360 behavior"
)

# === PYDANTIC MODELS ===

class SizeModel(BaseModel):
    w: int = Field(..., description="Width in pixels")
    h: int = Field(..., description="Height in pixels")


class AdRequestModel(BaseModel):
    """Ad request payload matching OpenRTB concepts"""
    adUnit: str = Field(..., description="Ad unit path (e.g., 'tech/home/hero')")
    sizes: List[SizeModel] = Field(..., description="Requested ad sizes")
    kv: Dict[str, str] = Field(default_factory=dict, description="Key-value targeting")
    geo: str = Field(..., description="Geographic location (ISO-2 code)")
    device: str = Field(..., description="Device type: desktop, mobile, tablet, app")
    userId: Optional[str] = Field(None, description="User identifier")
    viewportW: Optional[int] = Field(None, description="Viewport width")

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


class CreativeModel(BaseModel):
    id: str
    width: int
    height: int
    type: str = "display"
    adm: Optional[str] = None


class LineItemModel(BaseModel):
    """Response model for line items"""
    id: str
    name: Optional[str] = None
    priority: int
    cpm: float
    targeting: Dict
    pacing: str
    booked_imps: Optional[int] = None
    delivered_imps: Optional[int] = None


class BidModel(BaseModel):
    """Winning bid response"""
    source: str
    price: float
    line_item_id: str
    creative_id: Optional[str] = None
    adm: Optional[str] = None


class DecisionTraceModel(BaseModel):
    """Debug trace for a request"""
    req_id: str
    steps: List[Dict]
    winner: Optional[BidModel] = None
    no_fill_reason: Optional[str] = None


# In-memory storage (replace with database in production)
LINE_ITEMS = ALL_LINE_ITEMS
FLOOR_RULES = FLOOR_RULES
REQUEST_TRACES: Dict[str, Dict] = {}


# === ENDPOINTS ===

@app.get("/")
async def root():
    """Root endpoint with usage info"""
    return HTMLResponse("""
    <html>
        <head><title>GAM-360 Simulator</title></head>
        <body style="font-family: sans-serif; margin: 40px;">
            <h1>GAM-360 Simulator API</h1>
            <p>Educational simulator for Google Ad Manager 360 behavior.</p>
            
            <h2>Key Features</h2>
            <ul>
                <li>Real auction logic with priority buckets</li>
                <li>Pacing algorithms (even / asap)</li>
                <li>Floor pricing with rule-based evaluation</li>
                <li>Detailed decision tracing</li>
                <li>Realistic line item setup</li>
            </ul>
            
            <h2>Quick Start</h2>
            <ol>
                <li>Check <a href="/docs">/docs</a> for interactive API documentation</li>
                <li>Submit an ad request: <code>POST /ad</code></li>
                <li>View decision trace: <code>GET /ad/{req_id}/debug</code></li>
                <li>Browse examples: <code>GET /examples</code></li>
            </ol>
            
            <h2>Useful Endpoints</h2>
            <ul>
                <li><a href="/docs"><strong>📖 API Documentation (Swagger)</strong></a></li>
                <li><a href="/examples"><strong>📋 Example Requests</strong></a></li>
                <li><a href="/line-items"><strong>📊 View All Line Items</strong></a></li>
                <li><strong>POST /ad</strong> - Submit ad request</li>
            </ul>
        </body>
    </html>
    """)


@app.post("/ad", response_model=BidModel)
async def get_ad(req: AdRequestModel):
    """
    Submit an ad request and receive winning creative.
    
    Returns 204 No Content if no eligible line items.
    
    Example request:
    ```json
    {
        "adUnit": "tech/home/hero",
        "sizes": [{"w": 728, "h": 90}],
        "kv": {"section": "technology"},
        "geo": "US",
        "device": "desktop"
    }
    ```
    """
    domain_req = req.to_domain()
    now = time.time()
    
    trace = evaluate_request(
        domain_req,
        LINE_ITEMS,
        {"floor_rules": FLOOR_RULES},
        now=now
    )
    
    # Store trace for debugging
    REQUEST_TRACES[trace.req_id] = {
        "trace": trace,
        "timestamp": now
    }
    
    if not trace.winner:
        logger.warning(f"No fill for request {domain_req.req_id}: {trace.no_fill_reason}")
        raise HTTPException(
            status_code=204,
            detail=trace.no_fill_reason or "no-fill"
        )
    
    logger.info(f"Request {domain_req.req_id} won by {trace.winner.line_item_id} at ${trace.winner.price}")
    return trace.winner


@app.get("/ad/{req_id}/debug", response_model=DecisionTraceModel)
async def debug_request(req_id: str):
    """
    Get detailed decision trace for a specific request.
    
    Shows all filtering steps, eligible line items, floor computation,
    and final winner selection.
    """
    if req_id not in REQUEST_TRACES:
        raise HTTPException(status_code=404, detail="Request not found")
    
    trace_data = REQUEST_TRACES[req_id]
    trace = trace_data["trace"]
    
    return {
        "req_id": trace.req_id,
        "steps": trace.steps,
        "winner": trace.winner,
        "no_fill_reason": trace.no_fill_reason
    }


@app.get("/line-items", response_model=List[LineItemModel])
async def list_line_items():
    """
    List all active line items.
    
    Returns line items with current delivery status.
    """
    return [
        {
            "id": li.id,
            "priority": li.priority,
            "cpm": li.cpm,
            "targeting": li.targeting,
            "pacing": li.pacing,
            "booked_imps": li.booked_imps,
            "delivered_imps": li.delivered_imps
        }
        for li in LINE_ITEMS
    ]


@app.get("/examples")
async def get_examples():
    """
    Get example ad requests to test with.
    
    Use these with POST /ad to see different scenarios.
    """
    return {
        "description": "Example ad requests for testing",
        "examples": EXAMPLE_REQUESTS,
        "how_to_use": "Copy an example and POST it to /ad",
        "note": "Each POST to /ad creates a request_id you can use with /ad/{req_id}/debug"
    }


@app.get("/floor-rules")
async def get_floor_rules():
    """
    Get all active floor rules.
    
    Shows how floor prices are computed based on request context.
    """
    return {
        "description": "Floor pricing rules",
        "rules": FLOOR_RULES,
        "note": "Rules are evaluated in order; highest matching floor wins"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "line_items_count": len(LINE_ITEMS)
    }


@app.get("/stats")
async def get_stats():
    """
    Get simulator statistics.
    
    Shows delivery pacing and fill rates.
    """
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
        "line_items_count": len(LINE_ITEMS)
    }


# === STARTUP/SHUTDOWN ===

@app.on_event("startup")
async def startup_event():
    logger.info("GAM-360 Simulator API starting...")
    logger.info(f"Loaded {len(LINE_ITEMS)} line items")
    logger.info(f"Configured {len(FLOOR_RULES)} floor rules")
    logger.info(f"API running on http://0.0.0.0:8001")
    logger.info(f"Interactive docs: http://localhost:8001/docs")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("GAM-360 Simulator API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "services.api.app:app",
        host="0.0.0.0",
        port=8001,
        reload=False
    )
