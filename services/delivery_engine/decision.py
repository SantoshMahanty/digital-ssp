"""
Decision engine: evaluates ad requests against line items.

Flow:
1. Filter line items by:
   - Inventory targeting (ad unit codes)
   - Key-value (context) targeting
   - Geographic targeting
   - Device targeting
   - Creative size compatibility
   - Frequency caps (if implemented)
   - Pacing constraints
   
2. Run auction on eligible line items

3. Validate winner against floor price

Returns a DecisionTrace with detailed logging of each step.
"""
import time
from typing import Dict, List, Optional
from .types import AdRequest, Bid, DecisionTrace, LineItem
from .pacing import pacing_allows
from .floors import compute_floor
from .auction import run_auction
import logging

logger = logging.getLogger(__name__)


def matches_inventory(req: AdRequest, li: LineItem) -> bool:
    """Check if request's ad unit matches line item's inventory targeting"""
    ad_units = li.targeting.get('adUnits', [])
    if not ad_units:
        return True
    return req.ad_unit in ad_units


def matches_kv(req_kv: Dict[str, str], target_kv: Dict) -> bool:
    """
    Check if request key-values match line item's targeting.
    
    Line item targeting can specify exact values or lists of acceptable values.
    Request must have matching values for all keys in line item targeting.
    """
    if not target_kv:
        return True
    
    for k, v in target_kv.items():
        if k not in req_kv:
            return False
        
        # Target value is list of acceptable values
        if isinstance(v, list):
            if req_kv[k] not in v:
                return False
        else:
            # Target value is exact match
            if req_kv[k] != v:
                return False
    
    return True


def matches_geo(req_geo: str, geo_list: List[str]) -> bool:
    """Check if request geography matches line item's geo targeting"""
    if not geo_list:
        return True
    return req_geo in geo_list


def matches_device(req_device: str, device_list: List[str]) -> bool:
    """Check if request device matches line item's device targeting"""
    if not device_list:
        return True
    return req_device in device_list


def size_compatible(req_sizes: List, creatives: List) -> bool:
    """
    Check if any creative size matches any requested size.
    """
    if not creatives:
        return False
    
    return any(
        c.size.w == s.w and c.size.h == s.h
        for c in creatives
        for s in req_sizes
    )


def evaluate_request(
    req: AdRequest,
    line_items: List[LineItem],
    opts: Dict,
    now: Optional[float] = None
) -> DecisionTrace:
    """
    Evaluate ad request and return winning line item.
    
    Args:
        req: The ad request
        line_items: Candidate line items
        opts: Options dict with 'floor_rules' and 'deal'
        now: Current timestamp (defaults to time.time())
        
    Returns:
        DecisionTrace with winner, no-fill reason, and detailed steps
    """
    if now is None:
        now = time.time()
    
    trace = DecisionTrace(req_id=req.req_id)
    eligible: List[LineItem] = []
    
    logger.info(f"Evaluating request {req.req_id} for ad_unit={req.ad_unit}, sizes={req.sizes}, geo={req.geo}")
    
    # Filtering pass
    for li in line_items:
        # Check inventory targeting
        if not matches_inventory(req, li):
            trace.steps.append({
                "step": "filter",
                "reason": "inventory_mismatch",
                "line_item_id": li.id
            })
            continue
        
        # Check key-value targeting
        if not matches_kv(req.kv, li.targeting.get('kv')):
            trace.steps.append({
                "step": "filter",
                "reason": "kv_mismatch",
                "line_item_id": li.id
            })
            continue
        
        # Check geographic targeting
        if not matches_geo(req.geo, li.targeting.get('geo', [])):
            trace.steps.append({
                "step": "filter",
                "reason": "geo_mismatch",
                "line_item_id": li.id
            })
            continue
        
        # Check device targeting
        if not matches_device(req.device, li.targeting.get('devices', [])):
            trace.steps.append({
                "step": "filter",
                "reason": "device_mismatch",
                "line_item_id": li.id
            })
            continue
        
        # Check creative size compatibility
        if not size_compatible(req.sizes, li.creatives):
            trace.steps.append({
                "step": "filter",
                "reason": "no_compatible_creative",
                "line_item_id": li.id
            })
            continue
        
        # Check pacing
        if not pacing_allows(li, now):
            trace.steps.append({
                "step": "filter",
                "reason": "pacing_constraint",
                "line_item_id": li.id
            })
            continue
        
        eligible.append(li)
        trace.steps.append({
            "step": "eligible",
            "line_item_id": li.id,
            "priority": li.priority,
            "cpm": li.cpm
        })
    
    logger.info(f"Eligible line items: {len(eligible)} out of {len(line_items)}")
    
    # No eligible line items
    if not eligible:
        trace.no_fill_reason = 'targeting'
        logger.info(f"No eligible line items for request {req.req_id}")
        return trace
    
    # Run auction
    floor = compute_floor(req, opts.get('floor_rules', []), opts.get('deal'))
    trace.steps.append({
        "step": "floor_computed",
        "floor": floor
    })
    
    winner_bid = run_auction(eligible, floor)
    
    if not winner_bid:
        trace.no_fill_reason = 'floor'
        logger.info(f"No bid above floor ${floor} for request {req.req_id}")
        return trace
    
    trace.winner = winner_bid
    trace.steps.append({
        "step": "winner_selected",
        "line_item_id": winner_bid.line_item_id,
        "price": winner_bid.price,
        "creative_id": winner_bid.creative_id
    })
    
    logger.info(f"Request {req.req_id} won by {winner_bid.line_item_id} at ${winner_bid.price}")
    return trace
