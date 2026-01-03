# CTV & SSAI

## Ad Pod Model
- Inputs: totalDuration, maxAds, slotFloors, competitive keys.
- Pod split strategies: fixed arrays (e.g., [60,30,15,15]) or greedy fit from creative durations.

## Pod Assembly Algorithm (outline)
1. Generate candidate set per slot: match targeting + duration <= slot cap.
2. Enforce competitive separation: track `brand_category` used; skip conflicts.
3. Apply per-slot floor; reject bids/line items below.
4. Build VAST 4.x with sequence numbers aligned to slot order.

## SSAI Considerations
- Return server-side stitched media URLs (no client macros).
- Impression beacons server-fired to avoid ad blockers.
- Support VMAP wrapper if multiple pods.

## Example Pod Request
See /examples/vast-pod-response.xml for response shape; request example is in README.
