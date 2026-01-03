"""
Floor price calculation.

Floors are minimum CPM prices set by publisher to maintain yield.
Can be specified at multiple levels with context matching.

Rules are evaluated in order and the highest matching floor wins.
"""
from typing import Dict, List, Optional
from .types import AdRequest
import logging

logger = logging.getLogger(__name__)

FloorRule = Dict[str, object]


def rule_matches(rule: FloorRule, req: AdRequest) -> bool:
    """
    Check if floor rule matches the request.
    
    A rule matches if all specified conditions match.
    Missing conditions in the rule means "match any value".
    """
    # Check geo
    if 'geo' in rule and rule['geo'] and rule['geo'] != req.geo:
        return False
    
    # Check device
    if 'device' in rule and rule['device'] and rule['device'] != req.device:
        return False
    
    # Check ad_unit
    if 'ad_unit' in rule and rule['ad_unit'] and rule['ad_unit'] != req.ad_unit:
        return False
    
    # Check size
    if 'size' in rule and rule['size']:
        size = rule['size']
        has_match = any(
            s.w == size.get('w') and s.h == size.get('h')
            for s in req.sizes
        )
        if not has_match:
            return False
    
    return True


def compute_floor(
    req: AdRequest,
    rules: List[FloorRule],
    deal: Optional[Dict] = None
) -> float:
    """
    Compute floor price for this request.
    
    Args:
        req: The ad request
        rules: List of floor rules to evaluate (evaluated in order, highest match wins)
        deal: Optional private deal with custom floor
        
    Returns:
        Floor price in CPM
        
    Example rules:
        [
            {"floor": 5.0, "geo": "US", "device": "desktop"},
            {"floor": 3.0, "geo": "US", "device": "mobile"},
            {"floor": 2.0},  # Catch-all
        ]
    """
    # Private deals override all rules
    if deal:
        deal_floor = float(deal.get('floor', 0))
        logger.debug(f"Using deal floor: ${deal_floor}")
        return deal_floor
    
    floor = 0.0
    matched_rule = None
    
    # Evaluate rules in order, keeping highest matching floor
    for rule in rules:
        if rule_matches(rule, req):
            rule_floor = float(rule.get('floor', 0))
            if rule_floor > floor:
                floor = rule_floor
                matched_rule = rule
    
    logger.debug(f"Computed floor: ${floor} (matched rule: {matched_rule})")
    return floor
