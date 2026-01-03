from typing import List, Optional
from .types import Bid


def select_winner(candidates: List[Bid], floor: float) -> Optional[Bid]:
  valid = [b for b in candidates if b.price >= floor]
  if not valid:
    return None
  valid.sort(key=lambda b: b.price, reverse=True)
  return valid[0]
