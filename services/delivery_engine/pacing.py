from .types import LineItem


def even_pacing_allows(line_item: LineItem, now: float) -> bool:
  if not line_item.start or not line_item.end or not line_item.booked_imps:
    return True
  if line_item.delivered_imps is None:
    return True
  total_seconds = max(1, line_item.end - line_item.start)
  elapsed = max(0, now - line_item.start)
  expected = line_item.booked_imps * (elapsed / total_seconds)
  shortfall = expected - line_item.delivered_imps
  return shortfall >= 0


def pacing_allows(line_item: LineItem, now: float) -> bool:
  if line_item.pacing == 'asap':
    return True
  return even_pacing_allows(line_item, now)
