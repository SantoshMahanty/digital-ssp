"""
Auction logic for selecting winning bids
Implements GAM-style auction with priority buckets and price negotiation
"""
from typing import List, Optional, Dict
from .types import Bid, LineItem
import logging

logger = logging.getLogger(__name__)


def select_winner(candidates: List[Bid], floor: float) -> Optional[Bid]:
    """
    Select winning bid based on price and floor.
    All bids above floor are eligible; highest price wins.
    
    Args:
        candidates: List of bids to evaluate
        floor: Minimum CPM required to win
        
    Returns:
        Winning bid or None if no bid meets floor
    """
    valid = [b for b in candidates if b.price >= floor]
    if not valid:
        logger.info(f"No bids above floor ${floor}")
        return None
    valid.sort(key=lambda b: b.price, reverse=True)
    winner = valid[0]
    logger.info(f"Winner selected: {winner.line_item_id} at ${winner.price}")
    return winner


def run_auction(
    eligible_line_items: List[LineItem],
    floor: float,
    external_bids: Optional[List[Bid]] = None
) -> Optional[Bid]:
    """
    Run complete auction with priority buckets.
    
    Priority buckets (GAM standard):
    - 16: House/sponsorship (highest)
    - 12: Premium (partner/premium inventory)
    - 10: Price priority (cost-based)
    - 8: Standard (regular campaigns)
    - 6: Non-guaranteed (remnant)
    - 4: Lowest (house ads)
    
    Within each bucket, sort by CPM descending.
    If multiple buckets tie, higher bucket wins.
    
    Args:
        eligible_line_items: Line items that match targeting
        floor: Minimum CPM
        external_bids: Optional list of DSP bids to compare
        
    Returns:
        Winning bid
    """
    external_bids = external_bids or []
    
    # Group line items by priority bucket
    by_priority: Dict[int, List[LineItem]] = {}
    for li in eligible_line_items:
        if li.priority not in by_priority:
            by_priority[li.priority] = []
        by_priority[li.priority].append(li)
    
    # Sort each bucket by CPM descending
    for priority in by_priority:
        by_priority[priority].sort(key=lambda li: li.cpm, reverse=True)
    
    # Find winner in highest priority bucket with eligible items
    for priority in sorted(by_priority.keys(), reverse=True):
        bucket_items = by_priority[priority]
        if bucket_items:
            winner_li = bucket_items[0]
            internal_bid = Bid(
                source='internal',
                price=winner_li.cpm,
                line_item_id=winner_li.id,
                creative_id=winner_li.creatives[0].id if winner_li.creatives else None,
            )
            
            # Compare with external bids at same priority level
            high_external = [b for b in external_bids if b.price >= internal_bid.price]
            if high_external:
                high_external.sort(key=lambda b: b.price, reverse=True)
                external_winner = high_external[0]
                if external_winner.price > internal_bid.price:
                    return external_winner if external_winner.price >= floor else None
            
            return internal_bid if internal_bid.price >= floor else None
    
    # No internal line items; evaluate external bids
    external_valid = [b for b in external_bids if b.price >= floor]
    if external_valid:
        external_valid.sort(key=lambda b: b.price, reverse=True)
        return external_valid[0]
    
    return None
