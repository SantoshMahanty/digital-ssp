from typing import Dict, List, Optional
from .types import AdRequest

FloorRule = Dict[str, object]


def compute_floor(req: AdRequest, rules: List[FloorRule], deal: Optional[Dict] = None) -> float:
  if deal:
    return float(deal.get('floor', 0))
  floor = 0.0
  for r in rules:
    geo = r.get('geo')
    device = r.get('device')
    ad_unit = r.get('ad_unit')
    matches = (
      (geo is None or geo == req.geo) and
      (device is None or device == req.device) and
      (ad_unit is None or ad_unit == req.ad_unit)
    )
    if matches:
      floor = max(floor, float(r.get('floor', 0)))
  return floor
