# Quick Reference Guide

## API Endpoints

### Core Endpoints
| Method | Endpoint | Returns |
|--------|----------|---------|
| POST | `/ad` | Winning bid (or 204 no-fill) |
| GET | `/ad/{req_id}/debug` | Decision trace |
| GET | `/line-items` | All active line items |
| GET | `/floor-rules` | Floor pricing rules |

### Utility Endpoints
| Method | Endpoint | Returns |
|--------|----------|---------|
| GET | `/` | Welcome page |
| GET | `/docs` | Interactive Swagger UI |
| GET | `/examples` | Example ad requests |
| GET | `/health` | Health check |
| GET | `/stats` | Simulator statistics |

## Sample Request/Response

### POST /ad (Request)
```json
{
    "adUnit": "tech/home/hero",
    "sizes": [{"w": 728, "h": 90}],
    "kv": {"section": "technology"},
    "geo": "US",
    "device": "desktop",
    "userId": "user-123"
}
```

### POST /ad (Response - Success)
```json
{
    "source": "internal",
    "price": 15.0,
    "line_item_id": "li-sponsor-001",
    "creative_id": "cr-lb-728x90",
    "adm": "<div>...</div>"
}
```

### POST /ad (Response - No Fill)
```
HTTP/1.1 204 No Content
```

## Priority Buckets

Higher = higher priority. Always evaluated first.

```
16  House/Sponsorship   ($15 CPM)  ← Brand partnerships
12  Premium             ($10 CPM)  ← Premium deals
10  Price Priority      ($6.50)   ← Regular campaigns
 8  Standard            ($4 CPM)  ← Guaranteed inventory
 6  Remnant             ($1.50)   ← Unsold inventory
 4  House Ads           ($0 CPM)  ← House promotions
```

**Key Rule**: Priority 8 at $1 beats Priority 6 at $100

## Targeting Matching

All must match for line item to be eligible:

| Dimension | Description | Example |
|-----------|-------------|---------|
| **Inventory** | Ad unit code | "tech/home/hero" must be in line item's adUnits list |
| **KV** | Context variables | Request must have all KVs line item specifies, with matching values |
| **Geo** | Country code | "US" must be in line item's geo list |
| **Device** | Device type | "desktop" must be in line item's devices list |
| **Size** | Creative dimensions | Request must include a size that matches a creative |

## Pacing Algorithms

### Even Pacing
Spreads impressions evenly over campaign duration.

```
shortfall = expected_imps - delivered_imps
if shortfall >= 0: allow_serving()
else: skip_serving()
```

Example:
- Campaign: 100k imps over 10 days
- Day 5 (50% elapsed): expected = 50k
- If delivered = 48k: shortfall = 2k → serve
- If delivered = 52k: shortfall = -2k → skip

### ASAP Pacing
Deliver as quickly as possible until goal reached.

```
if delivered_imps < booked_imps: allow_serving()
else: skip_serving()
```

## Floor Pricing

Minimum CPM to win. Computed from rules matching request context.

```
rules = [
    {"floor": 5.0, "geo": "US", "device": "desktop"},
    {"floor": 3.0, "geo": "US", "device": "mobile"},
    {"floor": 0.0},  // catch-all
]

// For request (US, mobile):
// 1. Check rule 1: geo matches, device doesn't → skip
// 2. Check rule 2: geo matches, device matches → floor = $3.0
// 3. Stop evaluating (highest match wins)
```

## Decision Trace Structure

Every request returns a trace showing decision steps:

```json
{
    "req_id": "abc-123",
    "steps": [
        {"step": "filter", "reason": "geo_mismatch", "line_item_id": "li-1"},
        {"step": "filter", "reason": "size_mismatch", "line_item_id": "li-2"},
        {"step": "eligible", "line_item_id": "li-3", "priority": 16, "cpm": 15.0},
        {"step": "floor_computed", "floor": 5.0},
        {"step": "winner_selected", "line_item_id": "li-3", "price": 15.0, "creative_id": "cr-123"}
    ],
    "winner": {
        "source": "internal",
        "price": 15.0,
        "line_item_id": "li-3",
        "creative_id": "cr-123"
    },
    "no_fill_reason": null
}
```

## Common Scenarios

### Scenario 1: Priority Beats Price
```
Request: tech/home/hero, US, desktop

Line Items:
- LI-A: Priority 16, $15 CPM ← WINS
- LI-B: Priority 10, $50 CPM

Result: LI-A wins at $15
Reason: Priority 16 evaluated before priority 10
```

### Scenario 2: Floor Prevents Low CPM
```
Request: tech/home/hero, MX, mobile

Line Items:
- LI-A: Priority 8, $1.5 CPM

Floor Rules:
- MX mobile: $2.0

Result: NO FILL
Reason: $1.5 < $2.0 floor
```

### Scenario 3: Pacing Blocks Delivery
```
Campaign (even pacing):
- Booked: 100k impressions over 10 days
- Day 7 (70% elapsed): expected = 70k
- Delivered: 75k (ahead of pace)

Result: REQUEST SKIPPED
Reason: shortfall = 70k - 75k = -5k (negative)
```

## File Structure

```
services/
├── api/
│   ├── app.py              # FastAPI endpoints
│   ├── database.py         # SQLAlchemy models
│   ├── config.py           # Configuration
│   ├── examples.py         # Sample data
│   └── requirements.txt
├── delivery_engine/
│   ├── decision.py         # Request evaluation
│   ├── auction.py          # Auction logic
│   ├── pacing.py           # Pacing algorithms
│   ├── floors.py           # Floor pricing
│   └── types.py            # Data classes
├── ui/                     # Flask web UI
└── tests.py                # Unit tests

docs/
├── GETTING_STARTED.md      # Tutorial
├── auction.md              # Auction deep dive
└── inventory.md            # Inventory structure

.env                        # Configuration
README.md                   # Main documentation
UPGRADE_SUMMARY.md          # What changed
```

## Testing

### Run All Tests
```bash
python -m pytest services/tests.py -v
```

### Run Specific Test
```bash
python -m pytest services/tests.py::TestPacing::test_even_pacing_behind -v
```

### Run with Coverage
```bash
python -m pytest services/tests.py --cov=services
```

## Debugging a Request

1. **Submit request**:
   ```bash
   curl -X POST http://localhost:8001/ad ... > response.json
   ```

2. **Extract request_id** from response headers or create a new one

3. **View decision trace**:
   ```bash
   curl http://localhost:8001/ad/{request_id}/debug | jq .
   ```

4. **Analyze steps**:
   - Look for filter reasons
   - Check which line items passed
   - Verify floor computation
   - Confirm winner selection

## Key Data Classes

### AdRequest
```python
AdRequest(
    req_id: str,
    ad_unit: str,
    sizes: List[Size],
    kv: Dict[str, str],
    geo: str,
    device: str,
    user_id: Optional[str] = None,
    viewport_w: Optional[int] = None
)
```

### LineItem
```python
LineItem(
    id: str,
    priority: int,              # 4-16
    cpm: float,
    targeting: Dict,
    pacing: Literal['even', 'asap'],
    booked_imps: Optional[int],
    delivered_imps: Optional[int],
    start: Optional[float],     # unix timestamp
    end: Optional[float],
    creatives: List[Creative]
)
```

### Bid
```python
Bid(
    source: str,                # 'internal' or 'dsp'
    price: float,
    line_item_id: Optional[str],
    creative_id: Optional[str],
    adm: Optional[str]          # ad markup
)
```

## Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Kafka (optional)
KAFKA_BOOTSTRAP_SERVERS=localhost:9093

# API
API_HOST=0.0.0.0
API_PORT=8001
API_DEBUG=False

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 204 No Content | No-fill | Check debug trace for reason |
| 404 Not Found | Invalid request ID | Make sure request was submitted first |
| Floor price error | CPM < floor | Lower the floor or increase CPM |
| Pacing skip | Ahead of pace | Wait or reduce delivery |

---

**For full details, see [GETTING_STARTED.md](docs/GETTING_STARTED.md) and [auction.md](docs/auction.md)**
