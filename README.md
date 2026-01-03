# GAM-360 Simulator (Educational)

This dummy project models how Google Ad Manager 360 behaves at a systems level while remaining fully original. It focuses on correct concepts, decisioning logic, and data flows rather than UI cloning or proprietary behavior.

## Tech Stack (Python-Only)
- **Backend**: Python 3.10+ with FastAPI + Pydantic for API/delivery
- **Async Processing**: asyncio for fan-out; Celery/RQ for background pacing jobs
- **Database**: PostgreSQL (config + delivery logs), Redis (caps + pacing counters), ClickHouse (reporting/analytics)
- **Messaging**: Kafka event bus for streaming analytics
- **API Layer**: FastAPI with OpenAPI/Swagger docs
- **UI**: Flask with Jinja2 templates
- **Infrastructure**: Docker Compose for local development

## Repository Structure
```
/README.md                   # This document
/docs                        # Deep-dive docs per domain
  /inventory.md
  /auction.md
  /ctv_ssai.md
/examples                    # Request/response fixtures
  /openrtb-bid-request.json
  /vast-pod-response.xml
/services
  /api                       # FastAPI API for trafficking + ad decisioning
  /delivery_engine           # Core: line items, auction, pacing, floors
  /reporting_pipeline        # Kafka consumer → ClickHouse ETL
  /ui                        # Flask web UI with Jinja2 templates
/docker-compose.yml          # Local infrastructure stack
```

## 1) Inventory (matches GAM concepts)

### Hierarchy
- Network → Site/App → Ad Units (tree) → Placements (collections of ad units).
- Ad Units define size buckets and key-values; Placements group units for trafficking convenience.

### Schema (Postgres)
```sql
CREATE TABLE network (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE site_app (
  id UUID PRIMARY KEY,
  network_id UUID REFERENCES network(id),
  type TEXT CHECK (type IN ('web','app','ctv')),
  domain TEXT,
  bundle_id TEXT
);

CREATE TABLE ad_unit (
  id UUID PRIMARY KEY,
  parent_id UUID REFERENCES ad_unit(id),
  site_app_id UUID REFERENCES site_app(id),
  code TEXT NOT NULL,
  description TEXT,
  sizes JSONB NOT NULL,              -- e.g. [{"w":300,"h":250},{"w":1,"h":1}]
  key_values JSONB DEFAULT '{}',     -- defaults for requests
  is_archived BOOLEAN DEFAULT FALSE
);

CREATE TABLE placement (
  id UUID PRIMARY KEY,
  network_id UUID REFERENCES network(id),
  name TEXT NOT NULL
);

CREATE TABLE placement_ad_unit (
  placement_id UUID REFERENCES placement(id),
  ad_unit_id UUID REFERENCES ad_unit(id),
  PRIMARY KEY (placement_id, ad_unit_id)
);

CREATE TABLE size_mapping (
  id UUID PRIMARY KEY,
  ad_unit_id UUID REFERENCES ad_unit(id),
  viewport_min_w INT,
  viewport_min_h INT,
  sizes JSONB NOT NULL               -- eligible sizes for that breakpoint
);

CREATE TABLE custom_key_definition (
  id UUID PRIMARY KEY,
  network_id UUID REFERENCES network(id),
  name TEXT NOT NULL,
  allowed_values TEXT[]
);
```

### Sample API endpoints
- `POST /ad-units` create ad unit (payload: site/app, parent, sizes, defaults, k/vs).
- `POST /placements` create placement with ad unit IDs.
- `GET /inventory/tree?siteId=` return network tree with sizes and placements.
- `POST /size-mapping` attach responsive size rules to an ad unit.

### Example ad unit setup (payload)
```json
{
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
