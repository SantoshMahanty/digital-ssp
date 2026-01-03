# Getting Started with GAM-360 Simulator

## What is GAM-360?

GAM-360 (Google Ad Manager 360 Simulator) is an **educational project** that models how real ad serving systems work. It's not a clone, but rather a complete, working implementation of core concepts:

- **Inventory management** (ad units, placements, sites)
- **Line items** (ad campaigns with targeting)
- **Auction logic** (priority buckets, pricing, pacing)
- **Delivery decisioning** (which ad wins for each request)

Perfect for learning:
- How ad auctions work under the hood
- Real-world ad server architecture
- Programmatic advertising concepts
- Business logic behind ad technology

## Quick Start

### 1. Start the Servers

The servers are already running:
- **API**: `http://localhost:8001` (FastAPI backend)
- **UI**: `http://localhost:8000` (Flask web interface)

### 2. Explore the API

#### Interactive Documentation
Visit: **http://localhost:8001/docs**

This gives you an interactive Swagger interface to:
- See all available endpoints
- Read request/response models
- Try endpoints directly in the browser

#### Get Example Requests
```
GET http://localhost:8001/examples
```

Returns realistic example ad requests you can test with.

#### Submit an Ad Request
```json
POST http://localhost:8001/ad
Content-Type: application/json

{
    "adUnit": "tech/home/hero",
    "sizes": [{"w": 728, "h": 90}],
    "kv": {"section": "technology"},
    "geo": "US",
    "device": "desktop"
}
```

**Response:**
```json
{
    "source": "internal",
    "price": 15.0,
    "line_item_id": "li-sponsor-001",
    "creative_id": "cr-lb-728x90",
    "adm": "<div>...</div>"
}
```

#### Debug a Request

Every response includes a `request_id`. Use it to see the full decision trace:

```
GET http://localhost:8001/ad/{request_id}/debug
```

Shows:
- Which line items were filtered and why
- Which line items were eligible
- How the floor was computed
- Which line item won and why

### 3. Understanding the System

#### Key Concepts

**Line Item**: An ad campaign
- Has a priority level (4-16)
- Has a CPM (cost per thousand impressions)
- Has targeting rules (inventory, geo, device, KV)
- Has pacing strategy (even or asap)
- Has creatives (ad content at specific sizes)

**Auction**: Selection process for each request
1. Filter line items by targeting
2. Group eligible line items by priority
3. Pick highest-priority eligible line item
4. Validate against floor price
5. Return winning creative or no-fill

**Pacing**: Delivery rate control
- **Even**: Spread impressions evenly over campaign duration
- **ASAP**: Deliver as fast as possible

**Floor**: Minimum CPM to win auction
- Protects publisher yield
- Computed from rules matching request context
- Can be overridden by private deals

## Example Scenarios

### Scenario 1: Basic Request

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

**What happens:**
1. Requests ad for tech homepage hero position
2. 728x90 leaderboard size
3. In US, desktop
4. Sponsorship line item matches best (priority 16, $15 CPM)
5. Floor for US desktop is $5.0
6. Sponsorship wins: $15 > $5 ✅

### Scenario 2: Mobile Request

```bash
curl -X POST http://localhost:8001/ad \
  -H "Content-Type: application/json" \
  -d '{
    "adUnit": "tech/articles",
    "sizes": [{"w": 300, "h": 250}],
    "kv": {"section": "news"},
    "geo": "US",
    "device": "mobile"
  }'
```

**What happens:**
1. Requests ad for article position, mobile device
2. Standard line item eligible (priority 8, $4 CPM)
3. Floor for US mobile is $2.5
4. Standard line item wins: $4 > $2.5 ✅

### Scenario 3: No Fill (Floor)

```bash
curl -X POST http://localhost:8001/ad \
  -H "Content-Type: application/json" \
  -d '{
    "adUnit": "tech/home/hero",
    "sizes": [{"w": 728, "h": 90}],
    "geo": "MX",
    "device": "mobile"
  }'
```

**What happens:**
1. Mexico mobile request
2. Only remnant line item eligible ($1.5 CPM)
3. Floor for MX mobile is high ($2.0)
4. $1.5 < $2.0 → No fill ❌

## Available Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | Root page with info |
| GET | `/docs` | Swagger interactive docs |
| POST | `/ad` | Submit ad request |
| GET | `/ad/{req_id}/debug` | Debug trace for request |
| GET | `/line-items` | List all line items |
| GET | `/examples` | Example requests |
| GET | `/floor-rules` | Floor pricing rules |
| GET | `/health` | Health check |
| GET | `/stats` | Simulator statistics |

## Key Files to Understand

| File | Purpose |
|------|---------|
| `services/delivery_engine/types.py` | Data models (LineItem, Creative, Bid, etc.) |
| `services/delivery_engine/decision.py` | Main auction logic |
| `services/delivery_engine/auction.py` | Priority bucket evaluation |
| `services/delivery_engine/pacing.py` | Pacing algorithms |
| `services/delivery_engine/floors.py` | Floor computation |
| `services/api/app.py` | FastAPI endpoints |
| `services/api/examples.py` | Example line items and requests |
| `services/api/database.py` | Database models (SQLAlchemy) |
| `services/api/config.py` | Configuration management |

## Learning Path

### Level 1: Basics
1. Submit a request and get a response
2. Check the decision trace
3. Understand why a specific line item won
4. Read [auction.md](auction.md) - understand priority buckets

### Level 2: Targeting
1. Try requests with different geos/devices
2. Try requests with different key-values
3. Modify example line items in `services/api/examples.py`
4. See how targeting rules affect outcomes

### Level 3: Pacing
1. Create a line item with even pacing
2. Submit multiple requests at different times
3. See how pacing prevents delivery when ahead of pace
4. Try ASAP pacing - notice difference

### Level 4: Floors
1. Review `services/api/examples.py` FLOOR_RULES
2. Try requests from different geos
3. See how floors prevent low CPM line items from winning
4. Understand yield optimization

### Level 5: Architecture
1. Read database models in `database.py`
2. Understand the decision engine flow in `decision.py`
3. Explore the API structure in `app.py`
4. Consider: How would you add frequency capping?

## Common Questions

**Q: Why doesn't the highest CPM always win?**
A: Because priority matters more than price. A priority 16 line item at $1 CPM beats a priority 10 line item at $50 CPM.

**Q: What's pacing?**
A: It's delivery rate control. If a campaign books 100k impressions over 10 days, pacing ensures ~10k per day (even) instead of 100k on day 1.

**Q: Why does a request get no-filled?**
A: Usually one of three reasons:
- No line items match the targeting
- No eligible line item has compatible size/creative
- Winning line item CPM is below floor price

**Q: Can I modify line items?**
A: Yes! Edit `services/api/examples.py` to change line items, creatives, or floor rules. Restart the server to see changes.

**Q: How is this different from real GAM?**
A: This is simplified for learning. Real GAM has:
- Database persistence (this uses in-memory)
- Real-time bidding with external DSPs
- Frequency capping, roadblocks, competitive separation
- Complex reporting and analytics
- Video/CTV-specific features

But the core auction and pacing logic is authentic.

## Next Steps

1. **Understand the auction**: Read [docs/auction.md](auction.md)
2. **Experiment**: Try different requests, see outcomes
3. **Modify**: Change line items in `examples.py`, restart server
4. **Extend**: Add features like frequency capping or deals
5. **Deploy**: Use database instead of in-memory storage

## Troubleshooting

**Servers not responding?**
- Check if they're running: `http://localhost:8001/health`
- If not, restart them from terminal

**Getting 204 No Content?**
- That's a no-fill response
- Check the debug trace to see why: GET `/ad/{req_id}/debug`

**Want to see database queries?**
- Enable logging by setting `LOG_LEVEL=DEBUG` in `.env`

**Want to restart with fresh data?**
- Restart the server
- In-memory storage is cleared on restart
