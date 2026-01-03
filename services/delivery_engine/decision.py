import time
from typing import Dict, List
from .types import AdRequest, Bid, DecisionTrace, LineItem
from .pacing import pacing_allows
from .floors import compute_floor
from .auction import select_winner


def matches_inventory(req: AdRequest, li: LineItem) -> bool:
  return req.ad_unit in li.targeting.get('adUnits', [])


def matches_kv(req_kv: Dict[str, str], target_kv: Dict) -> bool:
  if not target_kv:
    return True
  for k, v in target_kv.items():
    if k not in req_kv:
      return False
    if isinstance(v, list):
      if req_kv[k] not in v:
        return False
    else:
      if req_kv[k] != v:
        return False
  return True


def matches_geo(req_geo: str, geo_list: List[str]) -> bool:
  if not geo_list:
    return True
  return req_geo in geo_list


def size_compatible(req_sizes: List, creatives: List) -> bool:
  return any(
    c.size.w == s.w and c.size.h == s.h
    for c in creatives
    for s in req_sizes
  )


def is_frequency_capped() -> bool:
  # Placeholder; connect to Redis counters in real impl.
  return False


def evaluate_request(req: AdRequest, line_items: List[LineItem], opts: Dict) -> DecisionTrace:
  trace = DecisionTrace(req_id=req.req_id)
  now = time.time()
  eligible: List[LineItem] = []

  for li in line_items:
    if not matches_inventory(req, li):
      trace.steps.append({"step": "filter", "detail": "inventory", "data": li.id})
      continue
    if not matches_kv(req.kv, li.targeting.get('kv')):
      trace.steps.append({"step": "filter", "detail": "kv", "data": li.id})
      continue
    if not matches_geo(req.geo, li.targeting.get('geo', [])):
      trace.steps.append({"step": "filter", "detail": "geo", "data": li.id})
      continue
    if not size_compatible(req.sizes, li.creatives):
      trace.steps.append({"step": "filter", "detail": "size", "data": li.id})
      continue
    if is_frequency_capped():
      trace.steps.append({"step": "filter", "detail": "fc", "data": li.id})
      continue
    if not pacing_allows(li, now):
      trace.steps.append({"step": "filter", "detail": "pacing", "data": li.id})
      continue
    eligible.append(li)

  if not eligible:
    trace.no_fill_reason = 'targeting'
    return trace

  eligible.sort(key=lambda li: (li.priority, -li.cpm))
  internal = eligible[0]

  floor = compute_floor(req, opts.get('floor_rules', []), opts.get('deal'))
  bids: List[Bid] = [
    Bid(
      source='internal',
      price=internal.cpm,
      line_item_id=internal.id,
      creative_id=internal.creatives[0].id if internal.creatives else None,
    )
  ]

  winner = select_winner(bids, floor)
  trace.winner = winner
  if not winner:
    trace.no_fill_reason = 'floor'
  return trace
