# Inventory Model

## Hierarchy
- Network → Site/App → Ad Unit (tree) → Placement.
- Ad unit has sizes, default key-values, optional size-mapping.
- Placement is a reusable grouping of ad units.

## Core Tables (Postgres)
See README for DDL reference. Additional operational tables:
```sql
CREATE TABLE ad_unit_ancestor (
  ad_unit_id UUID,
  ancestor_id UUID,
  depth INT,
  PRIMARY KEY (ad_unit_id, ancestor_id)
);

CREATE MATERIALIZED VIEW ad_unit_placement AS
SELECT pa.ad_unit_id, p.id AS placement_id
FROM placement p
JOIN placement_ad_unit pa ON pa.placement_id = p.id;
```

## API Surface (examples)
- `GET /inventory/tree?siteId=` — returns ad unit tree, placements, size mappings.
- `POST /inventory/ad-unit` — create/update ad unit, parent-child linkage, size mapping.
- `POST /inventory/placement` — create placement with ad unit membership.
- `GET /inventory/resolve?code=` — resolve ad unit and ancestors for a request.

## Request Normalization
- Resolve ad unit by code → pull ancestors and placements.
- Apply size mapping by viewport → eligible sizes list.
- Merge defaults key-values from ad unit with request-provided key-values.

## Example Resolution Output
```json
{
  "adUnitId": "au-hero",
  "ancestors": ["au-home", "au-root"],
  "placements": ["pl-home"],
  "eligibleSizes": [{"w":970,"h":250}],
  "kv": {"category":"news","logged_in":"true"}
}
```
