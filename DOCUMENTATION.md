# GAM-360 Simulator - Complete Documentation

**A production-grade, educational simulator of Google Ad Manager 360**

---

## Table of Contents

1. [Quick Start (5 Minutes)](#quick-start)
2. [Complete System Overview](#system-overview)
3. [API Reference](#api-reference)
4. [Auction Algorithm Deep Dive](#auction-algorithm)
5. [Pacing Algorithms](#pacing-algorithms)
6. [Floor Pricing System](#floor-pricing)
7. [Database Setup (MySQL)](#database-setup)
8. [Testing & Debugging](#testing)
9. [Architecture & Code](#architecture)
10. [Learning Path](#learning-path)

---

## Quick Start

### ✅ Your System Is Ready

The API server is running on `http://localhost:8001`

### Step 1: View Welcome Page
```bash
curl http://localhost:8001/
```

### Step 2: Try Interactive Docs
Visit: `http://localhost:8001/docs`

Swagger UI where you can:
- See all endpoints
- Read request/response models  
- Try endpoints directly in browser

### Step 3: Get Example Requests
```bash
curl http://localhost:8001/examples
```

Shows 4 realistic ad requests you can try.

### Step 4: Submit an Ad Request
```bash
curl -X POST http://localhost:8001/ad \
  -H "Content-Type: application/json" \
  -d '{
    "adUnit": "tech/home/hero",
    "sizes": [{"w": 728, "h": 90}],
    "kv": {"section": "technology"},
    "geo": "US",
    "device": "desktop"
  }'
```

Returns the winning ad with price and creative.

### Step 5: Debug the Decision
Extract `request_id` from response, then:

```bash
curl http://localhost:8001/ad/{request_id}/debug
```

Shows:
- All filtering steps
- Which line items passed
- How floor was computed
- Why winner was selected

---

## System Overview

### ✅ What You Have

**API Server** (FastAPI)
- 9+ endpoints with full documentation
- Real auction algorithm with priority buckets
- Pacing algorithms (even and asap)
- Floor pricing system
- Decision tracing for debugging
- Health checks and statistics

**Realistic Test Data**
- 6 line items across all priority buckets (4-16)
- 3 creatives at different sizes (728x90, 300x250, 300x600)
- 7 floor pricing rules (geo/device based)
- 4 example requests showing different scenarios

**Comprehensive Code**
- Production-grade architecture
- Full unit test suite (20+ tests)
- SQLAlchemy ORM models (ready for MySQL)
- Configuration management (.env)
- Extensive code comments

**Complete Documentation**
- This file covers everything
- API endpoints reference
- Algorithm explanations
- Examples and scenarios
- Debugging guide

### Line Items by Priority

```
Priority 16  House/Sponsorship      $15 CPM  ← Highest priority, brand partnerships
Priority 12  Premium                $10 CPM  ← Premium inventory deals
Priority 10  Price Priority         $6.50    ← Cost-based campaigns
Priority 8   Standard               $4 CPM   ← Guaranteed inventory
Priority 6   Remnant                $1.50    ← Non-guaranteed, fill remaining
Priority 4   House Ads              $0 CPM   ← Lowest priority, house promotions
```

Each line item has:
- ✅ Inventory targeting (ad unit codes)
- ✅ Key-value targeting (context variables)
- ✅ Geographic targeting (country codes)
- ✅ Device targeting (desktop/mobile)
- ✅ Multiple creatives at different sizes
- ✅ Pacing strategy (even or asap)
- ✅ Booked and delivered impressions
- ✅ Flight dates

---

## API Reference

### Core Endpoints

#### POST /ad
**Submit an ad request and get winning bid**

Request:
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

Response (Success - 200):
```json
{
    "source": "internal",
    "price": 15.0,
    "line_item_id": "li-sponsor-001",
    "creative_id": "cr-lb-728x90",
    "adm": "<div>...</div>",
    "request_id": "abc-123"
}
```

Response (No Fill - 204 No Content):
```
HTTP/1.1 204 No Content
```

#### GET /ad/{req_id}/debug
**View decision trace for a request**

Response:
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

### Data Endpoints

#### GET /line-items
Returns all active line items with full details (priority, CPM, targeting, creatives)

#### GET /floor-rules
Returns all floor pricing rules with conditions and minimum CPM values

#### GET /examples
Returns 4 example ad requests you can submit to `/ad`

### Utility Endpoints

#### GET /
Welcome page with quick links

#### GET /docs
Interactive Swagger UI documentation

#### GET /health
Health check (always returns 200)

#### GET /stats
Simulator statistics (total requests, fills, auctions, etc.)

---

## Auction Algorithm

### Overview

The auction system selects which line item wins the right to deliver an ad creative for a given request. It's based on Google Ad Manager's real auction logic.

### Auction Flow

```
1. Request arrives (inventory, sizes, geo, device, KV, etc.)
   ↓
2. Filter eligible line items:
   - Inventory targeting match
   - Key-value targeting match
   - Geo targeting match
   - Device targeting match
   - Creative size compatibility
   - Pacing constraints
   ↓
3. Group eligible line items by priority bucket
   ↓
4. Find winner in highest priority bucket
   ↓
5. Validate against floor price
   ↓
6. Return winning creative or no-fill
```

### Priority Buckets

GAM uses 6 standard priority levels. **Higher number = higher priority.**

| Priority | Name | Behavior | Use Case |
|----------|------|----------|----------|
| 16 | House/Sponsorship | Guarantees delivery, controls flow | Brand partnerships, sponsorships |
| 12 | Premium | High-priority guaranteed inventory | Premium partners |
| 10 | Price Priority | Cost-based; winners sorted by CPM | Regular advertiser campaigns |
| 8 | Standard | Guaranteed inventory | Standard line items |
| 6 | Non-Guaranteed | Delivers if unsold inventory exists | Remnant campaigns |
| 4 | House Ads | Lowest priority, fills remaining | House ads, promotions |

### Priority Bucket Rules

1. Line items are grouped by priority
2. Within each bucket, sort by CPM descending
3. Evaluate buckets from highest priority down
4. First bucket with eligible line items determines winner
5. In that bucket, highest CPM wins

**Critical Rule**: 
```
Priority 16 at $0.01 beats Priority 6 at $1000.00
```

This allows publishers to honor guaranteed deals first, then sell remaining inventory.

### Targeting Matching

**All dimensions must match for line item to be eligible:**

#### Inventory Targeting
Must match ad unit codes.
```python
targeting = {"adUnits": ["tech/home/hero", "tech/sidebar"]}

Request for "tech/home/hero"   → ✅ Match
Request for "tech/articles"    → ❌ No match
```

#### Key-Value (KV) Targeting
Line item specifies what KVs it targets. Request must have ALL specified KVs with matching values.
```python
targeting = {"kv": {"section": ["tech", "ai"], "author": "alice"}}

{"section": "tech", "author": "alice"}     → ✅ Match
{"section": "news", "author": "alice"}     → ❌ No match (section)
{"section": "tech", "author": "bob"}       → ❌ No match (author)
{"section": "tech"}                        → ❌ No match (missing author)
```

#### Geographic Targeting
Must match country code.
```python
targeting = {"geo": ["US", "CA", "MX"]}

Request from "US"   → ✅ Match
Request from "UK"   → ❌ No match
```

#### Device Targeting
Must match device type.
```python
targeting = {"devices": ["desktop", "mobile"]}

Request from desktop  → ✅ Match
Request from tablet   → ❌ No match
```

#### Size Compatibility
Request must include at least one size matching a creative.
```
Line item creatives: 728x90, 300x250
Request sizes:       728x90, 970x250

Result: ✅ Match (728x90 is compatible)
```

### Example Scenarios

#### Scenario 1: Priority Beats Price
```
Request: tech/home/hero, US, desktop

Line Items:
- LI-A: Priority 16, $15 CPM     ← WINS
- LI-B: Priority 10, $50 CPM

Decision:
1. Both pass targeting filters
2. Evaluate priority 16: LI-A eligible
3. Winner: LI-A at $15
4. Floor check: $15 > $5.0 → ✅ Serve

Result: LI-A wins at $15 (even though LI-B has higher CPM)
```

#### Scenario 2: All Targeting Must Match
```
Request: tech/articles, US, mobile

Line Items:
- LI-A: adUnits=[tech/home/hero], geo=[US], device=[desktop, mobile]

Decision:
1. Filter inventory: tech/articles not in [tech/home/hero] → ❌ EXCLUDED
2. Filter geo: US in [US] → ✅ Pass
3. Filter device: mobile in [desktop, mobile] → ✅ Pass

Result: NO FILL (failed inventory targeting)
```

#### Scenario 3: Floor Prevents Low CPM
```
Request: tech/home/hero, MX, mobile

Line Items:
- LI-A: Priority 8, $1.5 CPM

Floor Rules:
- MX mobile: $2.0 floor
- Catch-all: $0.0

Decision:
1. LI-A passes all targeting
2. Auction: LI-A selected
3. Floor computation: $2.0 (MX mobile rule matches)
4. Price validation: $1.5 < $2.0 → ❌ FAIL

Result: NO FILL (price below floor)
```

---

## Pacing Algorithms

Pacing controls the delivery rate of impressions throughout a campaign.

### Even Pacing

Spreads impressions evenly over the campaign period.

**Algorithm:**
```
elapsed = now - start_time
total_duration = end_time - start_time
expected_imps = booked_imps * (elapsed / total_duration)
shortfall = expected_imps - delivered_imps

if shortfall >= 0:
    allow serving
else:
    skip serving
```

**Example:**
- Campaign: 100k impressions over 10 days (Jan 1-10)

| Day | % Elapsed | Expected | Delivered | Shortfall | Decision |
|-----|-----------|----------|-----------|-----------|----------|
| 1 | 10% | 10k | 9.5k | +0.5k | ✅ Serve |
| 5 | 50% | 50k | 48k | +2k | ✅ Serve |
| 7 | 70% | 70k | 72k | -2k | ❌ Skip (ahead of pace) |
| 10 | 100% | 100k | 95k | +5k | ✅ Serve |

**Use Case**: Guaranteed campaigns with fixed rates. Publisher wants to deliver exactly 100k by day 10.

### ASAP Pacing

Delivers as quickly as possible until booked impressions reached.

**Algorithm:**
```
if delivered_imps < booked_imps:
    allow serving
else:
    skip serving
```

**Example:**
- Campaign: 100k impressions (no end date)

| Event | Delivered | Booked | Decision |
|-------|-----------|--------|----------|
| Start | 0 | 100k | ✅ Serve |
| 50k delivered | 50k | 100k | ✅ Serve |
| 100k delivered | 100k | 100k | ❌ Skip (goal reached) |

**Use Case**: Non-guaranteed campaigns. Advertiser wants 100k impressions ASAP.

---

## Floor Pricing

Floor is the minimum CPM required to win an auction. Computed from rules that match request context.

### Rule Matching

Rules are evaluated in order. A rule matches if ALL its conditions match.

```python
rules = [
    {"floor": 5.0, "geo": "US", "device": "desktop"},
    {"floor": 3.0, "geo": "US", "device": "mobile"},
    {"floor": 1.0, "geo": "UK"},
    {"floor": 0.0},  # Catch-all (always matches)
]
```

**How it works:**
1. For each rule, check if ALL conditions match the request
2. Use the highest-matching rule's floor
3. Stop evaluating (don't check later rules if one matched)

**Example 1: US Mobile**
```
Request: geo=US, device=mobile

Rule 1: geo=US, device=desktop  → ❌ device doesn't match
Rule 2: geo=US, device=mobile   → ✅ ALL match → FLOOR = $3.0
(Rules 3-4 not evaluated)
```

**Example 2: Mexico**
```
Request: geo=MX, device=mobile

Rule 1: geo=US, device=desktop  → ❌ geo doesn't match
Rule 2: geo=US, device=mobile   → ❌ geo doesn't match
Rule 3: geo=UK                  → ❌ doesn't match
Rule 4: (catch-all)             → ✅ always matches → FLOOR = $0.0
```

**Example 3: US Desktop**
```
Request: geo=US, device=desktop

Rule 1: geo=US, device=desktop  → ✅ ALL match → FLOOR = $5.0
(Rules 2-4 not evaluated)
```

### How Floor Affects Auctions

Once floor is computed, it becomes a gate:

```
if winning_bid >= floor:
    ✅ Serve the ad
else:
    ❌ No fill
```

**Example:**
```
Request: tech/home/hero, US, desktop

Line Items eligible:
- LI-A: $4 CPM

Auction result: LI-A wins at $4

Floor for US desktop: $5.0

Validation: $4 < $5.0 → ❌ NO FILL

(Even though LI-A would have won, floor prevents serving)
```

---

## Database Setup (MySQL)

### Current Status

✅ Database `gam360` is already created and ready.

### Connection Details

```env
DATABASE_URL=mysql+mysqlconnector://root:root@localhost:3306/gam360
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DATABASE=gam360
```

These are configured in `.env` file.

### MySQL Requirements

#### Windows
1. Download: https://dev.mysql.com/downloads/installer/
2. Install MySQL Server
3. Configure port 3306 and create Windows service
4. Start service

#### macOS
```bash
brew install mysql
brew services start mysql
```

#### Linux
```bash
sudo apt-get install mysql-server
sudo mysql_secure_installation
```

### Verify Connection

```bash
mysql -u root -p -h localhost
```

Enter password: `root`

### Database Schema

The database is ready for these tables:

```
gam360/
├── networks          # Publisher network
├── site_apps         # Website/app properties
├── ad_units          # Ad slots (728x90, etc.)
├── placements        # Ad placements on pages
├── line_items        # Campaign line items
├── orders            # Advertiser orders
├── creatives         # Ad creative assets
├── pacing_states     # Pacing delivery tracking
└── ad_requests       # Historical requests
```

To initialize tables (if needed):
```python
from services.api.database import init_db
init_db("mysql+mysqlconnector://root:root@localhost:3306/gam360")
```

Note: SQLAlchemy import has Python 3.13 compatibility issue. Currently using in-memory data storage. Tables can be initialized later with database layer upgrade.

---

## Testing & Debugging

### Run Tests

**All tests:**
```bash
python -m pytest services/tests.py -v
```

**Specific test:**
```bash
python -m pytest services/tests.py::TestAuction::test_priority_wins -v
```

**With coverage:**
```bash
python -m pytest services/tests.py --cov=services
```

### Debug a Request

1. **Submit request:**
   ```bash
   curl -X POST http://localhost:8001/ad \
     -H "Content-Type: application/json" \
     -d '{"adUnit": "tech/home/hero", "sizes": [{"w": 728, "h": 90}], "geo": "US", "device": "desktop"}' \
     > response.json
   ```

2. **Extract request_id** from response

3. **View decision trace:**
   ```bash
   curl http://localhost:8001/ad/{request_id}/debug | jq .
   ```

4. **Analyze the trace:**
   - Look for filtering steps (which line items were excluded)
   - Check eligible line items
   - Verify floor computation
   - Confirm winner selection

### Common Debugging Scenarios

#### "No fill but I expected a winner"
1. Check decision trace for filter reasons
2. Verify targeting dimensions:
   - Is adUnit in line item's inventory list?
   - Do all KVs match (if line item requires them)?
   - Is geo in line item's geo list?
   - Is device in line item's device list?
   - Does a creative match the requested size?

#### "Wrong line item won"
1. Check priority of winning line item
2. Verify no higher-priority items were eligible
3. If same priority, check CPM (highest should win)
4. Verify floor didn't block a higher-CPM item

#### "Pacing seems wrong"
1. Check campaign flight dates (start/end)
2. Calculate elapsed percentage
3. Verify expected vs delivered impressions
4. Check pacing algorithm (even vs asap)

---

## Architecture & Code

### Project Structure

```
services/
├── api/
│   ├── app.py              # FastAPI endpoints (9+ routes)
│   ├── database.py         # SQLAlchemy ORM models
│   ├── config.py           # Configuration management
│   ├── examples.py         # Sample data (6 line items)
│   └── requirements.txt
│
├── delivery_engine/
│   ├── decision.py         # Request evaluation & filtering
│   ├── auction.py          # Auction logic (priority buckets)
│   ├── pacing.py           # Pacing algorithms (even/asap)
│   ├── floors.py           # Floor pricing rules
│   ├── types.py            # Data classes
│   └── __init__.py
│
└── tests.py                # Unit tests (20+ tests)

docs/
└── (consolidated into DOCUMENTATION.md)

.env                        # Configuration (DATABASE_URL, etc.)
.gitignore
README.md                   # Quick reference
setup_mysql.py              # Database initialization script
requirements.txt            # Python dependencies
```

### Key Components

#### Decision Engine (`services/delivery_engine/decision.py`)
Filters line items based on targeting and pacing.

```python
def evaluate_request(request: AdRequest, line_items: List[LineItem], trace: DecisionTrace) -> List[LineItem]:
    """Filter line items that match targeting and pacing constraints"""
```

Steps:
1. Check inventory targeting (ad unit match)
2. Check KV targeting
3. Check geo targeting
4. Check device targeting
5. Check size compatibility
6. Check pacing constraints

#### Auction Engine (`services/delivery_engine/auction.py`)
Selects winner from eligible line items.

```python
def run_auction(eligible_items: List[LineItem], floor: float, trace: DecisionTrace) -> Optional[LineItem]:
    """Find winning line item among eligible candidates"""
```

Steps:
1. Group by priority bucket
2. Evaluate highest priority first
3. Within bucket: sort by CPM, pick highest
4. Validate against floor
5. Return winner or None

#### Pacing Engine (`services/delivery_engine/pacing.py`)
Determines if line item is eligible based on pacing constraints.

```python
def check_even_pacing(state: PacingState, now: float) -> bool:
    """Check if even pacing allows serving"""

def check_asap_pacing(state: PacingState) -> bool:
    """Check if ASAP pacing allows serving"""
```

#### Floor Engine (`services/delivery_engine/floors.py`)
Computes minimum CPM from matching rules.

```python
def compute_floor(request: AdRequest, floor_rules: List[FloorRule]) -> float:
    """Find highest-matching floor rule"""
```

### Data Models

#### AdRequest
```python
@dataclass
class AdRequest:
    req_id: str                          # Unique request ID
    ad_unit: str                         # Ad unit code (e.g., "tech/home/hero")
    sizes: List[Size]                    # Requested creative sizes
    kv: Dict[str, str]                   # Key-value targeting
    geo: str                             # Country code (e.g., "US")
    device: str                          # Device type ("desktop" or "mobile")
    user_id: Optional[str] = None        # Optional user ID
    viewport_w: Optional[int] = None     # Optional viewport width
```

#### LineItem
```python
@dataclass
class LineItem:
    id: str                              # Line item ID
    name: str                            # Display name
    priority: int                        # 4-16 (higher = higher priority)
    cpm: float                           # CPM price
    targeting: Dict[str, Any]            # Targeting rules
    pacing: Literal['even', 'asap']      # Pacing algorithm
    booked_imps: Optional[int]           # Total impressions to deliver
    delivered_imps: Optional[int]        # Impressions delivered so far
    start: Optional[float]               # Unix timestamp start date
    end: Optional[float]                 # Unix timestamp end date
    creatives: List[Creative]            # Creative assets
```

#### Bid
```python
@dataclass
class Bid:
    source: str                          # "internal" or "dsp"
    price: float                         # Winning price
    line_item_id: Optional[str]          # Winning line item
    creative_id: Optional[str]           # Winning creative
    adm: Optional[str]                   # Ad markup HTML
    request_id: Optional[str]            # Request ID for tracking
```

---

## Learning Path

### 📖 Read First (30 minutes)
1. This document - Overview section
2. [API Reference](#api-reference) section
3. Try 4 example requests via `/examples`

### 🧪 Experiment (30 minutes)
1. Submit requests to `/ad` endpoint
2. View decision traces with `/debug`
3. Try different ad units, geos, devices
4. Observe how floor pricing blocks bids
5. Notice how priority always wins over CPM

### 🧠 Understand (1 hour)
1. Read [Auction Algorithm](#auction-algorithm) section
2. Read [Pacing Algorithms](#pacing-algorithms) section
3. Read [Floor Pricing](#floor-pricing) section
4. Study `services/delivery_engine/auction.py`
5. Study `services/delivery_engine/decision.py`
6. Trace a request through all decision steps

### 📝 Modify (30 minutes)
1. Edit `services/api/examples.py`
2. Change CPM, priority, or targeting
3. Restart API server
4. Test how behavior changes
5. Observe decision trace differences

### ✍️ Build (2+ hours)
1. Add frequency capping to decision.py
2. Implement private deals override in auction.py
3. Add additional targeting dimension
4. Write unit tests for new feature
5. Debug with decision traces

### 🚀 Advanced
1. Connect to MySQL database
2. Add Redis caching layer
3. Implement real-time bidding
4. Add more realistic floor rules
5. Deploy as microservice

---

## Key Concepts Summary

### Priority Buckets
Organize line items by priority (4-16). Higher priority ALWAYS wins over lower priority, regardless of price. Allows publishers to honor guaranteed deals first.

### Targeting
All specified dimensions must match: inventory, KV, geo, device, size. If any dimension doesn't match, line item is excluded from auction.

### Pacing
Controls delivery rate:
- **Even**: Spread evenly over campaign period
- **ASAP**: Deliver as fast as possible

### Floor Pricing
Minimum CPM set by publisher. Winning bid must be >= floor or auction results in no-fill. Protects publisher revenue.

### Auction
Select highest-CPM line item within highest-priority bucket that:
1. Passes all targeting filters
2. Passes pacing constraints
3. Has a creative matching requested size
4. Has price >= floor

---

## Common Questions

**Q: Can I modify the line items?**
A: Yes! Edit `services/api/examples.py` and restart the server.

**Q: How do I add a new targeting dimension?**
A: Add to `LineItem.targeting` dict and update `decision.py` to filter on it.

**Q: How do I connect to a real database?**
A: Follow [Database Setup](#database-setup) section. Database schema is in `services/api/database.py`.

**Q: Why do some requests return no-fill?**
A: Use the `/ad/{req_id}/debug` endpoint to see the decision trace.

**Q: How do I run tests?**
A: `python -m pytest services/tests.py -v`

**Q: Can I add real-time bidding?**
A: Yes! The system is designed to support external DSPs. See `services/api/app.py` for integration points.

---

## Production Considerations

This system is:
- ✅ Educational (teaches real concepts)
- ✅ Production-grade (well-architected code)
- ⚠️ NOT production-ready (runs in-memory, single-threaded)

To production-harden:
1. Add MySQL persistence
2. Add Redis caching
3. Add request queuing (RabbitMQ/Kafka)
4. Add load balancing
5. Add monitoring/logging
6. Add rate limiting
7. Add authentication

---

**Happy learning! Your GAM-360 simulator is ready to teach you how ad servers work.** 🚀
