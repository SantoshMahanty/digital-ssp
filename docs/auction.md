# Auction & Decisioning

## Priority Buckets (GAM-style)
- Sponsorship (4), Standard (6), Network (8), Price Priority (10), Bulk (12), House (16).
- Lower number wins before price; within bucket, use price and pacing state.

## Flow
1. Inventory/targeting filter produces eligible line items.
2. Enforce frequency caps and pacing per candidate.
3. Pick top candidate of highest-priority bucket (guaranteed tiers) unless open auction allowed to compete with non-guaranteed price tiers.
4. If auction allowed: fan-out OpenRTB 2.5, filter by floors, run first-price among internal candidate + bids.
5. Emit decision trace for inspector.

## OpenRTB 2.5 Request Template
See /examples/openrtb-bid-request.json.

## Winner Selection (first-price)
- Filter bids by effective floor.
- Include internal price-priority/house candidate as a synthetic bid.
- Sort by price desc; tie-break by priority bucket, then random.

## No-Fill Reasons (diagnostics)
- inventory, targeting, pacing, frequency, floor, nobid, creative_error.

## Logging Keys
- reqId, adUnitId, winningLineItemId/null, bids[], floorApplied, pacingState, fcState, noFillReason.
