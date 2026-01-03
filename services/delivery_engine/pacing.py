"""
Pacing algorithms to control delivery rate of line items.

Two main strategies:
1. EVEN: Delivers impressions evenly over flight dates
   - Calculates expected impressions based on time elapsed
   - Allows delivery if we're ahead of pace or on-pace
   
2. ASAP: Delivers as quickly as possible until booked_imps reached
   - No pacing constraints
"""
from .types import LineItem
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def even_pacing_allows(line_item: LineItem, now: float) -> bool:
    """
    Check if line item can serve with EVEN pacing.
    
    Calculates shortfall: expected_imps - delivered_imps
    - Positive shortfall: we're behind, can serve
    - Negative shortfall: we're ahead, skip serving
    - Zero: on pace
    
    Example:
        - Campaign: 100k impressions over 10 days (Jan 1-10)
        - On Jan 5 (halfway through): expected = 50k
        - If delivered = 48k: shortfall = 2k, allow serving
        - If delivered = 52k: shortfall = -2k, skip serving
    """
    if not line_item.start or not line_item.end or not line_item.booked_imps:
        return True
    if line_item.delivered_imps is None:
        return True
    
    now_ts = now if isinstance(now, (int, float)) else now.timestamp()
    start_ts = line_item.start if isinstance(line_item.start, (int, float)) else line_item.start.timestamp()
    end_ts = line_item.end if isinstance(line_item.end, (int, float)) else line_item.end.timestamp()
    
    total_seconds = max(1, end_ts - start_ts)
    elapsed = max(0, now_ts - start_ts)
    
    # Calculate expected impressions at current time
    expected = line_item.booked_imps * (elapsed / total_seconds)
    
    # Calculate shortfall (positive = behind pace, can serve)
    shortfall = expected - line_item.delivered_imps
    
    can_serve = shortfall >= 0
    logger.debug(f"Pacing check: LI={line_item.id}, expected={expected:.0f}, delivered={line_item.delivered_imps}, shortfall={shortfall:.0f}, allow={can_serve}")
    return can_serve


def asap_pacing_allows(line_item: LineItem, now: float) -> bool:
    """
    Check if line item can serve with ASAP (as-soon-as-possible) pacing.
    
    Only constraint: haven't reached booked_imps
    """
    if not line_item.booked_imps:
        return True
    if line_item.delivered_imps is None:
        return True
    return line_item.delivered_imps < line_item.booked_imps


def pacing_allows(line_item: LineItem, now: float) -> bool:
    """
    Main entry point: check if pacing allows serving for this line item.
    
    Args:
        line_item: The line item to check
        now: Current timestamp (float or datetime)
        
    Returns:
        True if pacing strategy allows serving, False otherwise
    """
    if line_item.pacing == 'asap':
        return asap_pacing_allows(line_item, now)
    else:  # 'even'
        return even_pacing_allows(line_item, now)
