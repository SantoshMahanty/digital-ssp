from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from uuid import uuid4

from ..delivery_engine.types import AdRequest, LineItem, Size, Creative
from ..delivery_engine.decision import evaluate_request

app = FastAPI(title="GAM-360 Simulator API", version="0.1.0")


class SizeModel(BaseModel):
  w: int
  h: int


class AdRequestModel(BaseModel):
  adUnit: str = Field(..., alias="adUnit")
  sizes: List[SizeModel]
  kv: Dict[str, str] = {}
  geo: str
  device: str
  userId: Optional[str] = Field(None, alias="userId")
  viewportW: Optional[int] = Field(None, alias="viewportW")

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


# In-memory mocks; replace with persistence layer.
LINE_ITEMS: List[LineItem] = [
  LineItem(
    id="li-sponsor",
    priority=4,
    cpm=8.0,
    targeting={"adUnits": ["news/home/hero"], "kv": {"category": "news"}, "geo": ["US"], "devices": ["desktop"]},
    pacing="even",
    booked_imps=100000,
    delivered_imps=42000,
    start=1704067200,  # 2024-01-01
    end=1735689600,    # 2024-12-31
    creatives=[Creative(id="cr-970x250", size=Size(w=970, h=250), adm="<div>Sponsor</div>")],
  ),
  LineItem(
    id="li-price-priority",
    priority=10,
    cpm=5.0,
    targeting={"adUnits": ["news/home/hero"], "kv": {}, "geo": ["US"], "devices": ["desktop"]},
    pacing="asap",
    creatives=[Creative(id="cr-pp-970x250", size=Size(w=970, h=250), adm="<div>Price Priority</div>")],
  ),
]

FLOOR_RULES: List[Dict] = [{"floor": 1.2, "geo": "US", "device": "desktop"}]
TRACES: Dict[str, Dict] = {}


@app.post("/ad")
async def get_ad(req: AdRequestModel):
  domain_req = req.to_domain()
  trace = evaluate_request(domain_req, LINE_ITEMS, {"floor_rules": FLOOR_RULES})
  TRACES[trace.req_id] = trace
  if not trace.winner:
    raise HTTPException(status_code=204, detail=trace.no_fill_reason or "no-fill")
  return trace.winner


@app.get("/debug/{req_id}")
async def debug(req_id: str):
  trace = TRACES.get(req_id)
  if not trace:
    raise HTTPException(status_code=404, detail="not found")
  return trace
