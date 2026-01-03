# GAM-360 Simulator

**An educational, production-grade simulator of Google Ad Manager 360 behavior.**

Learn how real ad servers work by building and running complete auction logic, targeting algorithms, pacing strategies, and floor pricing—all in Python.

## 🎯 What You'll Learn

- **Ad Auction Logic**: How ads are selected based on priority, price, and pacing
- **Real-World Algorithms**: Even pacing, floor pricing, targeting matching
- **Systems Architecture**: API design, database modeling, event streaming
- **Programmatic Advertising**: OpenRTB concepts, line items, creatives, impressions

**Not a GAM clone.** This is original, realistic, and fully implemented—perfect for interviews, portfolios, and understanding ad tech at scale.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
python -m pip install -r services/api/requirements.txt
```

### 2. Start the API
```bash
cd c:/Users/Santo/Desktop/AI\ project/Digital-SSP
python -m uvicorn services.api.app:app --host 0.0.0.0 --port 8001
```

### 3. Try an Ad Request
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

### 4. View API Docs
Open: **http://localhost:8001/docs** (Interactive Swagger UI)

## 📚 Documentation

| Document | Content |
|----------|---------|
| [GETTING_STARTED.md](docs/GETTING_STARTED.md) | **Start here** - tutorial, examples, learning path |
| [auction.md](docs/auction.md) | Deep dive into priority buckets, pacing, floors |
| [inventory.md](docs/inventory.md) | Data model, schema design |

## 🏗️ Architecture

### Core Components

```
┌─────────────────┐
│  API Gateway    │ (FastAPI endpoint)
│  /ad request    │
└────────┬────────┘
         │
┌────────▼──────────────────────────┐
│  Decision Engine (services/...)    │
│  ├─ Targeting Filter              │
│  ├─ Auction (priority buckets)     │
│  ├─ Pacing (even/asap)            │
│  ├─ Floor Pricing                 │
│  └─ Winner Selection              │
└────────┬──────────────────────────┘
         │
┌────────▼──────────────────────────┐
│  Response                          │
│  {winning_bid, creative_markup}    │
└────────────────────────────────────┘
```

### Services

- **`services/api/app.py`** - FastAPI application
- **`services/api/database.py`** - SQLAlchemy ORM models
- **`services/api/examples.py`** - Example line items, creatives, floors
- **`services/delivery_engine/`** - Core auction logic
  - `decision.py` - Request evaluation & filtering
  - `auction.py` - Priority-based auction
  - `pacing.py` - Delivery rate control (even/asap)
  - `floors.py` - Floor price computation
  - `types.py` - Data classes

## 📊 Example Line Items

The simulator includes realistic test data:

| Priority | Name | CPM | Use Case |
|----------|------|-----|----------|
| 16 | Sponsorship | $15 | Brand partnerships |
| 12 | Premium Partner | $10 | Premium deals |
| 10 | Price Priority | $6.50 | Regular campaigns |
| 8 | Standard | $4 | Guaranteed inventory |
| 6 | Remnant | $1.50 | Unsold inventory |
| 4 | House | $0 | House ads |

Each line item has:
- ✅ Targeting rules (inventory, geo, device, key-values)
- ✅ Pacing strategy (even or asap)
- ✅ Booked & delivered impressions
- ✅ Flight dates (start/end)
- ✅ Creatives (ads at multiple sizes)

## 🧪 Testing & Learning

### Run Tests
```bash
python -m pytest services/tests.py -v
```

### Try Example Scenarios

**Get examples:**
```bash
curl http://localhost:8001/examples
```

**Debug a request:**
```bash
# Submit request
RESPONSE=$(curl -s -X POST http://localhost:8001/ad -H "Content-Type: application/json" -d '...')
REQ_ID=$(echo $RESPONSE | jq -r '.request_id')

# View decision trace
curl http://localhost:8001/ad/$REQ_ID/debug
```

Shows:
- Which line items were filtered and why
- Which line items were eligible
- How floor was computed
- Who won and why

### View Statistics
```bash
curl http://localhost:8001/stats
```

## 🎓 Learning Path

### Level 1: Basics (30 min)
1. Read [GETTING_STARTED.md](docs/GETTING_STARTED.md)
2. Submit test requests to POST /ad
3. View debug traces to understand outcomes

### Level 2: Understand Auctions (1 hour)
1. Read [auction.md](docs/auction.md)
2. Try requests with different priorities
3. See how priority 16 always beats priority 8
4. Understand pacing impact

### Level 3: Targeting & Pricing (1 hour)
1. Try requests with different geos/devices
2. See how floor rules prevent low CPM wins
3. Modify `services/api/examples.py` to change line items
4. Restart API and test changes

### Level 4: Algorithms (2 hours)
1. Read the implementation:
   - `services/delivery_engine/decision.py`
   - `services/delivery_engine/auction.py`
   - `services/delivery_engine/pacing.py`
2. Trace through code for a request
3. Implement a feature (e.g., frequency capping)

### Level 5: Database & Scale (2+ hours)
1. Enable database (PostgreSQL) instead of in-memory
2. Read `services/api/database.py` ORM models
3. Add migrations with Alembic
4. Handle concurrency and transactions

## 🔌 API Reference

### Submit Ad Request
```
POST /ad
Content-Type: application/json

{
    "adUnit": "tech/home/hero",
    "sizes": [{"w": 728, "h": 90}],
    "kv": {"section": "technology"},
    "geo": "US",
    "device": "desktop"
}

Response:
{
    "source": "internal",
    "price": 15.0,
    "line_item_id": "li-sponsor-001",
    "creative_id": "cr-lb-728x90",
    "adm": "<html>...</html>"
}
```

### Debug Request
```
GET /ad/{req_id}/debug

Response:
{
    "req_id": "abc-123",
    "steps": [
        {"step": "eligible", "line_item_id": "li-sponsor", "priority": 16, "cpm": 15.0},
        {"step": "floor_computed", "floor": 5.0},
        {"step": "winner_selected", "line_item_id": "li-sponsor", "price": 15.0}
    ],
    "winner": {...},
    "no_fill_reason": null
}
```

### Other Endpoints
- `GET /` - Welcome page
- `GET /docs` - Interactive Swagger UI
- `GET /examples` - Example requests
- `GET /line-items` - All active line items
- `GET /floor-rules` - Floor pricing rules
- `GET /health` - Health check
- `GET /stats` - Simulator statistics

## 💾 Database Setup (Optional)

The simulator runs in-memory by default. To use PostgreSQL:

1. **Start PostgreSQL**:
   ```bash
   docker run -d -e POSTGRES_PASSWORD=gam360 -e POSTGRES_USER=gam360 -e POSTGRES_DB=gam360 -p 5432:5432 postgres:15
   ```

2. **Initialize schema**:
   ```python
   from services.api.database import init_db
   init_db("postgresql://gam360:gam360@localhost:5432/gam360")
   ```

3. **Update .env**:
   ```
   DATABASE_URL=postgresql://gam360:gam360@localhost:5432/gam360
   ```

## 📋 Tech Stack

| Component | Technology |
|-----------|-----------|
| **Language** | Python 3.10+ |
| **API Framework** | FastAPI + Uvicorn |
| **ORM** | SQLAlchemy 2.0 |
| **Database** | PostgreSQL (optional) |
| **Cache** | Redis (optional) |
| **Testing** | pytest |
| **Data Validation** | Pydantic v2 |

## 🎓 Curriculum Ideas

### For Students
- Build the system from scratch, understanding each piece
- Add features: frequency capping, roadblocks, competitive separation
- Extend targeting: day-of-week, hour-of-day, user segments
- Implement: deal pricing, private auctions, first-look

### For Interviews
- Explain auction algorithm in depth
- Discuss pacing strategy trade-offs
- Design a floor pricing system
- Optimize for different metrics (revenue, fill rate, user experience)

### For Portfolio
- Deploy as API service (Heroku, AWS Lambda, etc.)
- Add web dashboard (React/Vue)
- Implement real-time analytics
- Add Kafka event streaming
- Scale to millions of QPS

## 🚀 Next Steps to Extend

- [ ] **Database persistence** - Replace in-memory with PostgreSQL
- [ ] **Frequency capping** - Limit impressions per user
- [ ] **Real-time bidding** - Add external DSP integration
- [ ] **Reporting** - Analytics dashboard
- [ ] **Deals** - Private marketplace pricing
- [ ] **Performance** - Caching, async tasks
- [ ] **Testing** - Integration and load tests
- [ ] **Deployment** - Containerization, CI/CD

## ❓ FAQ

**Q: How is this different from real GAM?**
A: Simplified, in-memory, single-threaded. Real GAM handles billions of impressions, has PG auctions, complex reporting, and video-specific logic. This teaches core concepts.

**Q: Can I deploy this to production?**
A: Not as-is. Add database persistence, Redis caching, message queues, monitoring, and stress testing first. Great as a foundation though.

**Q: Why Python, not Go/Rust?**
A: Readability for learning. Go/Rust are faster but harder to understand. Python's clarity makes concepts stick.

**Q: How accurate is the auction logic?**
A: ~90% of GAM's core rules. Simplified for learning; omits some edge cases and optimizations.

## 📄 License

Educational project. Feel free to learn, modify, and extend.

## 💬 Questions?

Check the docs:
1. [GETTING_STARTED.md](docs/GETTING_STARTED.md) - tutorials & examples
2. [auction.md](docs/auction.md) - detailed algorithm explanations
3. Code comments - heavily commented for clarity
  "siteAppId": "111-aaa",
  "parentId": null,
  "code": "news/home/hero",
  "sizes": [{"w": 970, "h": 250}, {"w": 1, "h": 1}],
  "keyValues": {"category": "news", "logged_in": "true"},
  "sizeMapping": [
    {"viewportMinW": 1024, "sizes": [{"w": 970, "h": 250}]},
    {"viewportMinW": 0, "sizes": [{"w": 1, "h": 1}]}
  ]
}
```

## 2) Orders, Line Items, Creatives

### Line item priorities (GAM-style)
- Sponsorship (4), Standard (6), Network (8), Price Priority (10), Bulk (12), House (16). Lower number = higher priority.

### Targeting evaluation
- Ad request → resolve ad unit + ancestors + placement membership.
- Match line item if: inventory match AND k/v match AND geo/device match AND size compatible AND competitive separation passes.

### Frequency capping
- Redis keys: `fc:{user}:{lineItem}` with TTL window; increment atomically if below cap.

### Pacing (even vs ASAP)
- Even: smooth impressions over flight using a moving target $target = \frac{booked - delivered}{remaining\_time}$.
- ASAP: deliver whenever eligible without smoothing (subject to caps and budget exhaustion).

### Creative association
- `line_item_creative` table maps creatives with size, type (display, video, VAST), backup image.

### Competitive exclusion
- Line items can declare competitive keys (e.g., `brand=auto`). If request carries same key from another winning line item in pod or page, exclude.

### Line-item decision pseudo-code
```ts
function evaluateLineItem(req, lineItem, pacingState) {
  if (!matchesInventory(req, lineItem)) return fail('inventory');
  if (!matchesKeyValues(req.kv, lineItem.targeting.kv)) return fail('kv');
  if (!matchesGeo(req.geo, lineItem.geo)) return fail('geo');
  if (!sizeCompatible(req.sizes, lineItem.creatives)) return fail('size');
  if (isCompetitive(req.context, lineItem)) return fail('competitive');
  if (isFrequencyCapped(req.user, lineItem)) return fail('fc');
  if (!pacingAllows(lineItem, pacingState)) return fail('pacing');
  return ok(score(lineItem)); // Score is priority bucket + price for tie-break.
}
```

### Example decision input/output
Input request:
```json
{
  "adUnit": "news/home/hero",
  "sizes": [{"w":970,"h":250}],
  "kv": {"category":"news","logged_in":"true"},
  "geo": "US",
  "device": "desktop",
  "userId": "u1"
}
```
Matching line items (simplified):
- LI-A: Sponsorship (4), CPM $= 8$, targets `category=news`, even pacing OK
- LI-B: Price Priority (10), CPM $= 5$, broad targeting
Output decision: LI-A wins (higher priority bucket). Pacing + fc logs recorded.

## 3) Yield Management & Unified Pricing

### Floor evaluation logic
1) Determine floor context: geo/device/placement.
2) Check deal overrides (PMP, PG) first.
3) Apply unified floor for inventory if higher than contextual.
4) For video/CTV, apply per-duration floors.
5) Reject bids below floor; otherwise pass to auction.

### Example scenarios
- Geo floor: US desktop display floor $=1.20$ CPM; EU mobile floor $=0.80$ CPM.
- Deal override: A PMP deal with min $=2.50$ CPM bypasses lower unified floor.
- Video duration tiers: 6s: $1.00$, 15s: $4.00$, 30s: $6.00$.

## 4) Open Auction (GAM ↔ SSP Bridge)

### Internal competition
- Step 1: Evaluate all guaranteed/non-guaranteed line items (Sponsorship → House).
- Step 2: If open auction enabled and no higher-priority winner blocks, issue OpenRTB 2.5 request to DSPs.
- Step 3: Run first-price auction across internal candidate (with its bid price) + external bids above floor.

### Sample OpenRTB 2.5 bid request
```json
{
  "id": "req-123",
  "imp": [{
    "id": "1",
    "banner": {"format": [{"w": 300, "h": 250}]},
    "tagid": "news/home/hero",
    "bidfloor": 1.2,
    "ext": {"kv": {"category": "news"}}
  }],
  "site": {"domain": "news.example"},
  "device": {"ua": "Mozilla", "geo": {"country": "USA"}},
  "user": {"id": "u1"}
}
```

### Mock DSP bidders (local stubs)
- `dsp-a` responds with bid $=2.1$ CPM; `dsp-b` with $=1.5$ CPM or no-bid.

### First-price winner selection logic
```python
def select_winner(internal_candidate, external_bids, floor):
    valid = [b for b in external_bids if b.price >= floor]
    pool = [internal_candidate] if internal_candidate else []
    pool.extend([
        Bid(source='dsp', price=b.price, seat=b.seat, adm=b.adm)
        for b in valid
    ])
    return max(pool, key=lambda x: x.price, default=None)
```

### Auction flow diagram (text)
```
Request → Inventory match → Line item scoring → Is higher-priority guaranteed? yes → serve
                                                           no
                                                   OpenRTB fan-out
                                                bids filtered by floors
                              internal (price-priority) + dsp bids → first-price sort → winner
```

## 5) CTV & SSAI

### Ad pod decisioning
- Inputs: pod duration (e.g., 120s), max ads, competitive separation rules, per-slot min/max.
- Fit creatives by duration using bin-packing with competitive keys per slot.

### Pod duration split (example)
- For a 120s pod: [60s, 30s, 15s, 15s]; enforce per-slot floors.

### Competitive separation
- No two ads with same `brand_category` in the same pod; enforce at slot placement time.

### Sample ad pod request
```json
{
  "podId": "pod-42",
  "totalDuration": 120,
  "maxAds": 4,
  "adUnit": "ctv/show1/pod1",
  "kv": {"genre": "sports"},
  "geo": "US",
  "device": "ctv",
  "ssai": true
}
```

### Sample VAST 4.x SSAI response (snippet)
```xml
<VAST version="4.2">
  <Ad id="win-1">
    <InLine>
      <AdSystem>GAM-360-Sim</AdSystem>
      <AdTitle>Sports Sponsor</AdTitle>
      <Creatives>
        <Creative sequence="1" AdID="cr-123">
          <Linear>
            <Duration>00:00:60</Duration>
            <MediaFiles>
              <MediaFile delivery="progressive" type="video/mp4" width="1920" height="1080">https://cdn.example/sponsor.mp4</MediaFile>
            </MediaFiles>
          </Linear>
        </Creative>
      </Creatives>
    </InLine>
  </Ad>
</VAST>
```

## 6) Delivery, Pacing, Forecasting

### Even delivery algorithm (simplified)
```python
def even_pacing_target(line_item, now):
    total_seconds = line_item.end - line_item.start
    elapsed = now - line_item.start
    expected = line_item.booked_imps * (elapsed / total_seconds)
    shortfall = expected - line_item.delivered_imps
    return shortfall > 0  # allow serve if behind schedule
```

### Over-delivery protection
- Cap daily impressions to `ceil(booked / flight_days * 1.05)`.
- Use Redis counters per day; deny once exceeded unless makegood flag is set.

### Forecasting (basic)
- Use historical requests per ad unit and fill rate to project future availability: $forecast\_imps = req\_rate \times predicted\_fill$.
- Monte Carlo optional: sample variability in request volume and bid rates.

## 7) Reporting

### Tracked metrics
- Requests, matched line items, impressions, clicks (if needed), revenue (gross/net), bids, wins.
- Derived: fill rate $= \frac{impressions}{requests}$, win rate $= \frac{wins}{bids}$, eCPM $= \frac{revenue}{impressions} \times 1000$.

### Event pipeline
1) Delivery engine emits events (`request`, `match`, `auction`, `impression`, `win`).
2) Kafka topic per event type; compacted for user-level caps if needed.
3) Stream processor (Flink/Spark) aggregates into hour buckets; sink to ClickHouse.

### Aggregation queries (ClickHouse)
```sql
-- Hourly revenue by placement
SELECT placement_id, toStartOfHour(ts) AS hour, sum(revenue) AS rev
FROM events
WHERE event_type = 'impression'
GROUP BY placement_id, hour;

-- Fill rate by ad unit
SELECT ad_unit_id,
  sum(event_type = 'impression') AS imps,
  sum(event_type = 'request') AS req,
  imps / NULLIF(req,0) AS fill_rate
FROM events
GROUP BY ad_unit_id;
```

## 8) Ad Inspector / Diagnostics

### Request-ID based debugging
- Each request gets `reqId`; all decisions log with that ID.
- Inspector endpoint `GET /debug/{reqId}` returns trace: inventory match, line item passes/fails, floor applied, bids, pacing state.

### Debug decision tree (text)
```
Request arrives
  ├─ Inventory found?
  │   └─ no → no-fill: inventory
  ├─ Eligible line items?
  │   └─ none → no-fill: targeting
  ├─ Pacing/Frequency allow?
  │   └─ no → no-fill: pacing or fc
  ├─ Auction bids above floor?
  │   └─ no → no-fill: floor
  └─ Winner rendered
```

## 9) UI (functional, not a visual clone)
- Inventory: tree editor, size mapping per breakpoint, placement grouping.
- Orders & Line Items: create/edit flights, pacing charts, targeting builder, creative upload.
- Yield: unified floor ruleset editor; deal overrides table; preview effective floor per geo/device.
- Reports: explore hourly rollups, export CSV; visualize fill and eCPM.
- Ad Inspector: search by `reqId` or time window; show decision trace timeline.

## 10) Project bootstrap
- Run `docker compose up` to start PostgreSQL, Redis, Kafka, ClickHouse.
- Seed scripts insert sample inventory, line items, creatives, and DSP stubs.
- **Python Services**:
  - **API** (`services/api`): FastAPI endpoints for trafficking, ad decisioning, and inspector
  - **Delivery Engine** (`services/delivery_engine`): Core decisioning, pacing, auction, floors
  - **Reporting Pipeline** (`services/reporting_pipeline`): Kafka consumer → ClickHouse ETL
  - **UI** (`services/ui`): Flask web interface with Jinja2 templates

### Getting Started
```bash
# Start infrastructure
docker compose up -d

# Install Python dependencies
cd services/api && pip install -r requirements.txt
cd ../delivery_engine && pip install -r requirements.txt
cd ../reporting_pipeline && pip install -r requirements.txt
cd ../ui && pip install -r requirements.txt

# Run API server
cd services/api && uvicorn app:app --reload --port 8000

# Run Flask UI
cd services/ui && python app.py
```

---

### How this mirrors real GAM 360 behavior
- Uses identical trafficking primitives (inventory hierarchy, line item priorities, unified pricing floors, OpenRTB bridge) and delivery constraints (pacing, frequency caps, competitive separation). Open auction and first-price logic reflect current industry practice; CTV/SSAI podding and VAST 4.x align with modern GAM video flows.

### What skills this proves
- AdTech systems design, line-item decisioning, auction theory implementation, pacing/frequency control, yield management, CTV/SSAI handling, reporting pipelines, and diagnostics tooling in a service-oriented stack.
