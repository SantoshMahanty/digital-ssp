# Auction System - Complete Guide

This document explains the GAM-360 auction algorithm in detail.

## Overview

The auction system selects which line item wins the right to deliver an ad creative for a given request. It's based on Google Ad Manager's real auction logic but simplified for educational purposes.

## Auction Flow

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

## Priority Buckets

GAM uses 6 standard priority levels. Higher number = higher priority.

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

**Example:**
```
Priority 16: [LI-A ($15 CPM)]
Priority 12: [LI-B ($12 CPM), LI-C ($10 CPM)]
Priority 10: [LI-D ($8 CPM), LI-E ($6 CPM)]

Request arrives → Evaluate priority 16 → LI-A is eligible → LI-A wins
```

## Targeting Matching

### Inventory Targeting

Must match ad unit codes.

```python
targeting = {"adUnits": ["tech/home/hero", "tech/sidebar"]}
```

Request for "tech/home/hero" → ✅ Match
Request for "tech/articles" → ❌ No match

### Key-Value (KV) Targeting

Matches context variables. Line item must specify what KVs it targets.

```python
targeting = {"kv": {"section": ["tech", "ai"], "author": "alice"}}
```

Request must have ALL specified KVs with matching values:
- `{"section": "tech", "author": "alice"}` → ✅ Match
- `{"section": "news", "author": "alice"}` → ❌ No match (section doesn't match)
- `{"section": "tech", "author": "bob"}` → ❌ No match (author doesn't match)
- `{"section": "tech"}` → ❌ No match (missing author KV)

### Geographic Targeting

Must match country code.

```python
targeting = {"geo": ["US", "CA", "MX"]}
```

### Device Targeting

Must match device type.

```python
targeting = {"devices": ["desktop", "mobile"]}
```

### Size Compatibility

Request must include at least one size that matches a creative in the line item.

Line item has creatives: 728x90, 300x250
Request for: 728x90, 970x250

Result: ✅ Match (728x90 is compatible)

## Pacing Algorithms

### Even Pacing

Delivers impressions evenly over the flight period.

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
- On Jan 5 (50% elapsed):
  - Expected = 100k × 0.5 = 50k
  - Delivered = 48k
  - Shortfall = 2k (positive → can serve)
  
- On Jan 7 (70% elapsed):
  - Expected = 100k × 0.7 = 70k
  - Delivered = 72k
  - Shortfall = -2k (negative → skip, we're ahead)

### ASAP Pacing

Delivers as quickly as possible until booked impressions reached.

**Algorithm:**
```
if delivered_imps < booked_imps:
    allow serving
else:
    skip serving
```

## Floor Pricing

Floor is the minimum CPM required to win an auction. Computed from rules that match request context.

### Rule Matching

Rules are evaluated in order. A rule matches if ALL its conditions match.

```python
rules = [
    {"floor": 5.0, "geo": "US", "device": "desktop"},
    {"floor": 3.0, "geo": "US", "device": "mobile"},
    {"floor": 1.0, "geo": "UK"},
    {"floor": 0.0},  # Catch-all
]
```

Request: geo=US, device=mobile
- Rule 1: geo matches but device doesn't → no match
- Rule 2: geo matches AND device matches → **match** → floor = $3.0
- (Rules 3+ not evaluated; highest match wins)

### Private Deals

Can override all rules with a custom floor.

```python
options = {
    "deal": {"floor": 10.0, "price": 9.5}
}
```

Private deal floor always wins.

## Decision Trace

Every request returns a detailed trace showing:

1. **Filtering steps**: Which line items were excluded and why
2. **Eligible line items**: Which line items passed all filters
3. **Floor computation**: How floor was calculated
4. **Winner selection**: Which line item won and at what price
5. **No-fill reason**: Why no ad was served (if applicable)

## Example Scenarios

### Scenario 1: Premium Sponsorship Wins

```json
Request:
{
    "adUnit": "tech/home/hero",
    "sizes": [{"w": 728, "h": 90}],
    "kv": {"section": "technology"},
    "geo": "US",
    "device": "desktop"
}

Eligible Line Items:
- LI-A (Priority 16, $15 CPM): sponsorship
- LI-B (Priority 12, $10 CPM): partner
- LI-C (Priority 10, $6 CPM): price priority

Decision:
1. Filter: All three pass targeting
2. Pacing: All three pass pacing
3. Auction: Priority 16 has eligible items
4. Winner: LI-A at $15 CPM
5. Floor: US desktop = $5.0 floor
6. Result: ✅ LI-A wins (15 > 5)
```

### Scenario 2: No Fill Due to Floor

```json
Request:
{
    "adUnit": "tech/home/hero",
    "geo": "MX",
    "device": "mobile"
}

Eligible Line Items:
- LI-A (Priority 8, $1.5 CPM)

Floor Rules:
- MX mobile: $2.0 floor

Decision:
1. All filters pass
2. Auction: LI-A selected
3. Floor: $2.0
4. Validation: $1.5 < $2.0
5. Result: ❌ No fill (floor)
```

### Scenario 3: Pacing Controls Delivery

```
Campaign: 100k imps, 10 days, EVEN pacing
Day 1: expected=10k, delivered=9.5k → shortfall=0.5k → serve
Day 5: expected=50k, delivered=55k → shortfall=-5k → don't serve
Day 10: expected=100k, delivered=95k → shortfall=5k → serve
```

## Best Practices for Students

1. **Start with priority**: Always think about priority first. It's the primary decision factor.

2. **Understand targeting**: Every dimension (inventory, KV, geo, device, size) must match.

3. **Pacing matters**: Don't ignore pacing. Real ad systems are obsessed with delivery rates.

4. **Floors protect yield**: Publishers use floors to maintain revenue. Low floors = inventory given away.

5. **Debug with traces**: Always use the `/debug` endpoint to understand why an auction went a certain way.

6. **Test edge cases**: Try requests that should no-fill or hit pacing limits.

## Common Misconceptions

❌ **"Highest CPM always wins"** → Only within the same priority bucket!

❌ **"Floor price is ignored if CPM > floor"** → Floor is a minimum gate; all bids below floor lose regardless of priority.

❌ **"Pacing is optional"** → Pacing is enforced for guaranteed line items; violating it breaks campaigns.

❌ **"All targeting must match"** → True! All specified targeting dimensions must match.
