# UI Design (GAM-360-inspired)

Goal: functional console that surfaces inventory, orders/line items, yield, reporting, and diagnostics without copying GAM visuals.

## Tech Stack
- **Framework**: Flask with Jinja2 templates
- **Frontend**: HTML5, CSS3, vanilla JavaScript (or lightweight Alpine.js)
- **Styling**: Custom CSS with CSS Grid/Flexbox
- **Charts**: Chart.js for visualizations

## Layout & Theme
- Shell: left nav, top bar with network selector/search/user, main content with cards and tables.
- Palette: neutral base, charcoal text, teal/amber accents; avoid purple; light mode default, optional dark.
- Typography: Work Sans or Source Sans; purposeful weights; avoid default system stacks.
- Motion: staged fade/slide on view transitions and filter changes only.

## Pages
- Inventory
  - Tree of sites/apps → ad units → children; breadcrumb + search.
  - Detail drawer: sizes, size mapping, defaults, key-values, placements, responsive preview.
  - Placement composer: add/remove ad units, view membership.
- Orders & Line Items
  - Orders table with status (booked/running/ended), pacing indicator.
  - Line item editor: priority select (4/6/8/10/12/16), targeting builder (inventory, geo, device, k/v), pacing (even/asap), freq cap, competitive keys, creatives upload/select, preview sizes.
  - Pacing chart: delivered vs expected; caps indicators.
- Yield
  - Unified floor rules grid (geo/device/placement, video duration tiers).
  - Deal overrides table with precedence summary.
  - Effective floor preview: context selector shows resulting floor.
- Reports
  - Query builder: dimensions (time, placement, ad unit, geo, device), metrics (requests, imps, revenue, fill, win, eCPM).
  - Visualization: line/area for fill/eCPM, table with totals, CSV export.
- Ad Inspector
  - Search by reqId/time window; filter by site/ad unit.
  - Timeline of decision steps (inventory, targeting, pacing/fc, floor, bids, winner/no-fill).
  - Request/response payload viewer; no-fill reason badges.

## Components (reusable)
- TreeNav, Breadcrumb, SizeMappingTable, KeyValueChips, TargetingBuilder, PacingCard, FloorsTable, PodTimeline (CTV pods), DecisionTracePanel, Chart widget, DataTable with column filters.

## Routing (Flask)
- `/` - Overview dashboard
- `/inventory` - Inventory management
- `/orders` - Orders list
- `/orders/<order_id>` - Order detail
- `/line-items/<line_item_id>` - Line item editor
- `/yield` - Yield management
- `/reports` - Reporting interface
- `/inspector` - Ad inspector

## API Integration
- All CRUD via services/api; inspector via `/debug/{reqId}`; reports via ClickHouse HTTP or mocked API in dev.

## Non-goals
- No visual cloning of GAM; no proprietary icons/skins; focus on functional parity and data flows.
