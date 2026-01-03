from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

PriorityBucket = Literal[4, 6, 8, 10, 12, 16]


@dataclass
class Size:
  w: int
  h: int


@dataclass
class AdRequest:
  req_id: str
  ad_unit: str
  sizes: List[Size]
  kv: Dict[str, str]
  geo: str
  device: str
  user_id: Optional[str] = None
  viewport_w: Optional[int] = None
  pod: Optional[Dict[str, int]] = None


@dataclass
class Creative:
  id: str
  size: Size
  duration_sec: Optional[int] = None
  type: Literal['display', 'video'] = 'display'
  adm: Optional[str] = None


@dataclass
class LineItem:
  id: str
  priority: PriorityBucket
  cpm: float
  targeting: Dict
  pacing: Literal['even', 'asap']
  booked_imps: Optional[int] = None
  delivered_imps: Optional[int] = None
  start: Optional[int] = None
  end: Optional[int] = None
  freq_cap: Optional[Dict[str, int]] = None
  competitive: Optional[Dict[str, str]] = None
  creatives: List[Creative] = field(default_factory=list)


@dataclass
class Bid:
  source: Literal['internal', 'dsp']
  price: float
  seat: Optional[str] = None
  adm: Optional[str] = None
  line_item_id: Optional[str] = None
  creative_id: Optional[str] = None
  info: Optional[Dict] = None


@dataclass
class DecisionTrace:
  req_id: str
  steps: List[Dict] = field(default_factory=list)
  winner: Optional[Bid] = None
  no_fill_reason: Optional[str] = None
