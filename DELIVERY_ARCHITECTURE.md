# Google Ad Manager 360 - Delivery Section Architecture
## Complete Guide to Ad Server Design, UI Controls, and Backend Logic

---

## **OVERVIEW: The Delivery Pipeline**

The Delivery section is the **core engine** of any ad server. It controls:
- **WHO** sees ads (targeting)
- **WHAT** they see (creatives)
- **WHEN** they see it (pacing)
- **HOW MUCH** inventory gets reserved (forecasting)
- **HOW** bids compete (programmatic auction)

```
Order (Commercial) → Line Items (Rules) → Targeting (Who) → Creatives (What) → Pacing (Speed) → Auction (Bidding)
                                                                                                    ↓
                                                                            Real-Time Decision Engine
```

---

## **1️⃣ ORDERS - Commercial Container**

### **Purpose**
Orders are the **business wrapper** around campaigns. They group technical delivery (line items) with commercial agreements (contracts, dates, budgets).

### **Database Model**
```python
class Order:
    id: str                          # Unique ID (ORD-XXXXX)
    name: str                        # Order name
    advertiser_id: str              # Links to advertiser
    salesperson_id: str             # Account manager
    start_date: datetime            # Campaign starts
    end_date: datetime              # Campaign ends
    total_budget: float             # Order-level budget
    budget_type: str                # Impression, Revenue, Clicks
    status: str                     # Active, Paused, Archived, Pending
    line_items: List[LineItem]      # Child line items
    created_at: datetime
    updated_at: datetime
```

### **UI Control Mapping**
| UI Control | Backend Action | Purpose |
|-----------|----------------|---------|
| Create Order Form | `POST /api/orders` | Insert order + validate dates |
| Edit Order Details | `PUT /api/orders/{id}` | Update budget, dates, advertiser |
| Status Dropdown | Update `status` field | Pause/resume all child line items |
| Line Items Grid | Query `ORDER BY created_at` | Display associated line items |
| Delivery Status Badge | `SUM(line_items.delivered_imps)` | Aggregate child line item status |

### **Backend Logic**
```python
# When order is created:
1. Validate dates (start < end)
2. Check advertiser exists
3. Check salesperson exists
4. Allocate budget pool
5. Create order ID
6. Emit event: order_created

# When order status changes to PAUSED:
1. Pause all child line items
2. Release reserved inventory
3. Emit event: order_paused
4. Notify sales team

# When order reaches end_date:
1. Auto-pause all line items
2. Calculate final delivery rate
3. Generate billing invoice
4. Archive order
```

---

## **2️⃣ LINE ITEMS - Delivery Rules (⚠️ CORE)**

### **Purpose**
Line Items are the **heart of ad delivery**. They define:
- Priority (P1-P16)
- Targeting rules
- Pacing strategy
- Rate/pricing
- Creatives to use

### **Database Model**
```python
class LineItem:
    id: str                              # Unique ID (LI-XXXXX)
    order_id: str                        # Parent order
    name: str                            # Line item name
    line_item_type: str                  # Sponsorship, Standard, Network, Bulk, PP, PG, Preferred, Open
    priority: int                        # 1-16 (16=highest)
    targeting: TargetingRules           # See section 3
    start_date: datetime
    end_date: datetime
    booked_impressions: int              # Guaranteed impressions
    delivered_impressions: int           # Actual delivered
    status: str                          # Active, Paused, Completed, Archived
    rate_type: str                       # CPM, CPC, CPA, Fixed (Sponsorship)
    rate_value: float                    # Price per unit
    pacing_strategy: str                 # Even, Frontloaded, ASAP
    daily_cap: int                       # Max imps/day (0=unlimited)
    lifetime_cap: int                    # Max total imps
    frequency_cap: FrequencyCap          # User impression limits
    creative_rotation: str               # Even, Optimized, Sequential
    creatives: List[Creative]            # Associated ad assets
    catch_up_enabled: bool               # Auto-adjust if behind schedule
    created_at: datetime
    updated_at: datetime
    
# Priority Buckets (from highest to lowest guarantee):
# P16-P14: Sponsorship (guaranteed, exclusive inventory)
# P12-P10: Standard (guaranteed from available inventory)
# P8-P6: Network (premium inventory)
# P4-P1: Bulk/Remnant (whatever's left)
```

### **Line Item Types Explained**

#### **Sponsorship (P16-P14)**
- **What**: Exclusive, guaranteed, highest priority
- **Guarantee**: 100% of targeted inventory
- **Use Case**: Brand safety, marquee deals
- **Auction**: Pre-empts all others
- **Pricing**: Usually fixed CPM

#### **Standard (P12-P10)**
- **What**: Guaranteed from available inventory
- **Guarantee**: X impressions if inventory exists
- **Use Case**: Direct campaigns, contracts
- **Auction**: Beats Network/Bulk, loses to Sponsorship
- **Pricing**: CPM, CPC, CPA

#### **Network (P8-P6)**
- **What**: Medium priority, best-effort
- **Guarantee**: None (competes for remnant)
- **Use Case**: Portfolio deals, network campaigns
- **Auction**: Beats Bulk, loses to Standard+Sponsorship
- **Pricing**: Variable, CPM

#### **Bulk (P4-P1)**
- **What**: Lowest priority, cheapest
- **Guarantee**: None (fills unsold inventory)
- **Use Case**: Remnant sales, low-cost inventory
- **Auction**: Last to get inventory
- **Pricing**: Lowest CPM

#### **Programmatic Guaranteed (PG)**
- **What**: Automated guaranteed deals
- **Guarantee**: X impressions (seller commitment)
- **Workflow**: Pre-negotiated via PMP (Private Marketplace)
- **Auction**: Priority negotiated upfront
- **Pricing**: Fixed CPM agreed in contract

#### **Preferred Deals**
- **What**: Seller offers inventory first
- **Guarantee**: None (best effort at floor price)
- **Workflow**: Buyer must bid floor or higher
- **Auction**: Gets right of first refusal
- **Pricing**: Floor price set by seller

#### **Open Auction**
- **What**: All remaining inventory
- **Guarantee**: None
- **Workflow**: Highest bidder wins
- **Auction**: Last resort, all buyers compete
- **Pricing**: Market CPM

### **UI Control Mapping**

| UI Control | Backend Action | Logic |
|-----------|----------------|-------|
| Line Item Type Dropdown | Update `line_item_type` | Affects priority in auction |
| Priority Level (P1-P16) | Update `priority` | Used in delivery decision algorithm |
| Create Line Item Modal | `POST /api/line-items` | Validate targeting, create in DB |
| Targeting Panels (4 tabs) | Build `targeting` object | See section 3 |
| Pacing Strategy Select | Update `pacing_strategy` | Controls delivery curve |
| Daily/Lifetime Cap Input | Update `daily_cap`, `lifetime_cap` | Checked before serving ads |
| Creative Rotation Dropdown | Update `creative_rotation` | Affects which creative renders |
| Delivery Forecast Bar | `forecast_impressions(targeting)` | Predict available inventory |
| Status Indicator Badge | Check `status` + `delivered_imps` | Real-time delivery color |

### **Backend Logic: When Ad Request Arrives**

```python
def select_line_item(ad_request):
    """Decision algorithm for which line item wins the impression"""
    
    # Step 1: Filter eligible line items
    eligible = []
    for li in line_items:
        if not is_targeting_match(li, ad_request):
            continue
        if li.status != "ACTIVE":
            continue
        if li.daily_cap_reached():
            continue
        if li.lifetime_cap_reached():
            continue
        if li.frequency_cap_exceeded(ad_request.user_id):
            continue
        eligible.append(li)
    
    if not eligible:
        return None  # No fill
    
    # Step 2: Sort by priority + type
    # Sponsorship (P16-P14) → Standard (P12-P10) → Network (P8-P6) → Bulk (P4-P1)
    eligible.sort(key=lambda li: (-li.priority, -li_type_order[li.type]))
    
    # Step 3: Check guarantee fulfillment
    for li in eligible:
        if li.needs_impressions():  # Still below booked_impressions?
            return li  # Serve to this line item
    
    # Step 4: If all guarantees met, use pacing algorithm
    for li in eligible:
        if can_serve_under_pacing(li):
            return li
    
    # Step 5: No guaranteed line items available, go to auction
    return run_auction(eligible, floor_price, bid_requests)
```

---

## **3️⃣ TARGETING - Who Sees Ads**

### **Purpose**
Targeting controls **inventory availability** and **audience matching**. It's the WHERE clause of ad serving.

### **Targeting Rules Structure**
```python
class TargetingRules:
    # Inventory Targeting
    inventory: InventoryTargeting
        ad_unit_ids: List[str]          # Which ad units? ["/home/leaderboard", ...]
        placement_ids: List[str]        # Which placements?
        exclude_ad_units: List[str]     # Explicitly block these units
    
    # Geography Targeting
    geography: GeographyTargeting
        include_countries: List[str]    # ["US", "CA", "UK"]
        exclude_countries: List[str]    # ["CN", "RU"]
        include_cities: List[str]       # ["New York", "Los Angeles"]
        region_code: str                # State/province targeting
        metro_code: str                 # DMA targeting
    
    # Device Targeting
    device: DeviceTargeting
        device_types: List[str]         # ["desktop", "mobile", "tablet"]
        os_types: List[str]             # ["iOS", "Android", "Windows"]
        browsers: List[str]             # ["Chrome", "Safari", "Firefox"]
        carrier: str                    # Mobile carrier
        connection_type: str            # "broadband", "mobile"
    
    # Audience Targeting
    audience: AudienceTargeting
        first_party_segments: List[str] # Your own audience data
        third_party_segments: List[str] # DMP/DCM segments
        lookalike_segments: List[str]   # Similar to converters
        exclude_segments: List[str]     # Block certain audiences
    
    # Custom Key-Value Targeting
    custom_kv: Dict[str, List[str]]     # {"content_type": ["news", "sports"], ...}
    
    # Time Targeting
    time: TimeTargeting
        start_hour: int                 # 0-23
        end_hour: int                   # 0-23
        days_of_week: List[str]         # ["Monday", "Tuesday", ...]
        time_zone: str                  # "US/Eastern"
    
    # Advanced Targeting
    video: VideoTargeting
        position: str                   # "pre-roll", "mid-roll", "post-roll"
        content_category: str           # Video category
    
    # Logical Operators
    logic: str                          # "AND", "OR"
```

### **Targeting Matching Algorithm**

```python
def is_targeting_match(line_item, ad_request):
    """Check if ad_request matches line_item targeting"""
    
    # Inventory check (AND logic - must match)
    if not match_inventory(line_item.targeting.inventory, ad_request):
        return False
    
    # Geography check
    if not match_geography(line_item.targeting.geography, ad_request):
        return False
    
    # Device check
    if not match_device(line_item.targeting.device, ad_request):
        return False
    
    # Audience check
    if not match_audience(line_item.targeting.audience, ad_request):
        return False
    
    # Custom KV check
    if not match_custom_kv(line_item.targeting.custom_kv, ad_request):
        return False
    
    # Time check
    if not match_time(line_item.targeting.time, ad_request):
        return False
    
    return True  # All conditions met
```

### **UI Control Mapping**

| UI Control | Backend Value | Used In |
|-----------|---|---|
| Inventory Checkboxes | `targeting.inventory.ad_unit_ids` | `match_inventory()` |
| Geography Include Input | `targeting.geography.include_countries` | `match_geography()` |
| Device Type Checkboxes | `targeting.device.device_types` | `match_device()` |
| Custom KV Dynamic Fields | `targeting.custom_kv` | `match_custom_kv()` |
| Time Range Inputs | `targeting.time.start_hour/end_hour` | `match_time()` |

---

## **4️⃣ CREATIVES - Ad Assets**

### **Purpose**
Creatives are the **actual ad content** that renders on the page. Controls what users see.

### **Database Model**
```python
class Creative:
    id: str                         # Unique ID (CRE-XXXXX)
    line_item_id: str              # Parent line item
    name: str                       # Creative name
    creative_type: str              # "display", "video", "native"
    
    # Display Creative
    display: Optional[DisplayCreative]
        image_url: str              # URL to image file
        width: int                  # 728
        height: int                 # 90
        format: str                 # "JPEG", "PNG", "GIF", "WebP"
        file_size_kb: int
        click_url: str              # Destination URL
        backup_image_url: str       # Fallback
    
    # Video Creative
    video: Optional[VideoCreative]
        video_url: str              # URL to MP4/WebM/FLV
        duration_seconds: int       # 30, 15, 6, etc
        thumbnail_url: str          # Preview image
        vast_xml: str               # VAST wrapper for video ads
        clickthrough_url: str       # Where clicks go
        video_format: str           # "instream", "outstream"
    
    # Native Creative
    native: Optional[NativeCreative]
        headline: str               # (max 50 chars)
        body_text: str              # (max 150 chars)
        image_url: str              # 300x200 to 1200x628
        icon_url: str               # Optional icon
        click_url: str              # Destination
        json_metadata: Dict         # Custom properties
    
    # Delivery Controls
    approval_status: str            # "approved", "pending", "rejected"
    start_serving: datetime         # When to start using
    stop_serving: datetime          # When to stop using
    status: str                     # "active", "archived"
    
    # Targeting (Creative-level)
    creative_targeting: Dict        # Can target by device, geo, etc
    creative_rotation: str          # Inherited from line item
    
    # Tracking & Metrics
    impressions: int                # Times served
    clicks: int                     # User clicks
    ctr: float                      # CTR %
    conversions: int                # Conversions tracked
    created_at: datetime
    updated_at: datetime
```

### **Creative Selection Algorithm**

```python
def select_creative(line_item, ad_request):
    """Pick which creative to serve based on rotation strategy"""
    
    eligible_creatives = [
        c for c in line_item.creatives
        if c.status == "ACTIVE" and c.approval_status == "APPROVED"
        and is_within_serving_dates(c)
    ]
    
    if not eligible_creatives:
        return None
    
    if line_item.creative_rotation == "EVEN":
        # Round-robin: each creative gets equal impressions
        return rotate_evenly(eligible_creatives)
    
    elif line_item.creative_rotation == "OPTIMIZED":
        # Machine learning: serve highest CTR/CPA creative
        best_ctr = max(c.ctr for c in eligible_creatives)
        return [c for c in eligible_creatives if c.ctr == best_ctr][0]
    
    elif line_item.creative_rotation == "SEQUENTIAL":
        # Serve in order of creation
        return eligible_creatives[0]
    
    else:
        return random.choice(eligible_creatives)
```

### **UI Control Mapping**

| UI Control | Backend Action | Purpose |
|-----------|----------------|---------|
| Upload Creative Form | `POST /api/creatives` with multipart | Store asset, validate format/size |
| Creative Type Radio | Set `creative_type` | Route to correct parser |
| Image/Video Upload | Store in CDN, return URL | File handling |
| Click URL Input | Set `click_url` | Used in ad HTML/VAST |
| Creative Rotation Dropdown | Update `creative_rotation` | Affects `select_creative()` |
| Start/Stop Serving Dates | Update serving date windows | Checked in eligibility filter |
| Approval Status Badge | Show `approval_status` | QA workflow indicator |

---

## **5️⃣ PACING - Delivery Speed Control**

### **Purpose**
Pacing controls **HOW FAST** impressions deliver. Prevents:
- Burning budget too quickly
- Over-delivering to cheap inventory
- Under-delivering on guarantees

### **Database Model**
```python
class PacingStrategy:
    pacing_type: str                # "EVEN", "FRONTLOADED", "ASAP"
    daily_cap: int                  # Max impressions/day (0=unlimited)
    lifetime_cap: int               # Max total impressions
    catch_up_enabled: bool          # Auto-adjust if behind
    catch_up_threshold: float       # % behind to trigger (default 5%)
    catch_up_multiplier: float      # Increase factor (default 1.1x)
    
    # Calculated fields (updated hourly)
    impressions_today: int
    impressions_lifetime: int
    expected_pace: float            # (booked_imps / days_remaining)
    current_pace: float             # (imps_today / hours_elapsed)
    variance: float                 # (current - expected) / expected
    catch_up_active: bool
```

### **Pacing Algorithms**

#### **EVEN Pacing**
```python
def should_serve_even_pacing(line_item):
    """Can we serve under EVEN pacing?"""
    
    daily_target = line_item.booked_impressions / line_item.days_remaining
    
    if line_item.impressions_today >= daily_target:
        return False  # Daily cap hit
    
    if line_item.impressions_lifetime >= line_item.booked_impressions:
        return False  # Lifetime cap hit
    
    return True
```

#### **FRONTLOADED Pacing**
```python
def should_serve_frontloaded_pacing(line_item):
    """Front-load: deliver 50% in first half"""
    
    halfway_point = line_item.days_remaining / 2
    days_elapsed = (datetime.now() - line_item.start_date).days
    
    if days_elapsed < halfway_point:
        # First half: target 50% / (days_remaining/2) per day
        daily_target = (line_item.booked_impressions * 0.5) / halfway_point
    else:
        # Second half: target remaining 50% / (days_remaining/2) per day
        remaining = line_item.booked_impressions - line_item.impressions_lifetime
        days_left = line_item.days_remaining - days_elapsed
        daily_target = remaining / days_left
    
    return line_item.impressions_today < daily_target
```

#### **ASAP Pacing**
```python
def should_serve_asap_pacing(line_item):
    """Serve as fast as possible"""
    
    if line_item.impressions_lifetime >= line_item.booked_impressions:
        return False
    
    if line_item.daily_cap and line_item.impressions_today >= line_item.daily_cap:
        return False
    
    return True  # No artificial delays
```

#### **Catch-Up Logic**
```python
def apply_catch_up_delivery(line_item):
    """If behind schedule, increase cap automatically"""
    
    if not line_item.catch_up_enabled:
        return
    
    variance = (line_item.current_pace - line_item.expected_pace) / line_item.expected_pace
    
    if variance < -line_item.catch_up_threshold:
        # Behind by 5%+ → increase daily cap
        shortfall = line_item.booked_impressions - line_item.impressions_lifetime
        days_left = line_item.days_remaining
        
        new_daily_cap = (shortfall / days_left) * line_item.catch_up_multiplier
        line_item.daily_cap = new_daily_cap
        
        log_event("catch_up_activated", {
            "line_item_id": line_item.id,
            "new_daily_cap": new_daily_cap,
            "variance": variance
        })
```

### **UI Control Mapping**

| UI Control | Backend Field | Algorithm Used |
|-----------|---|---|
| Pacing Strategy Dropdown | `pacing_type` | Routes to Even/Frontloaded/ASAP function |
| Daily Cap Input | `daily_cap` | Checked before each serve decision |
| Lifetime Cap Input | `lifetime_cap` | Checked before each serve decision |
| Catch-Up Toggle | `catch_up_enabled` | Triggers `apply_catch_up_delivery()` |
| Progress Bars | `impressions_today / daily_target` | Real-time visualization |
| Status Indicator | `variance` threshold | Color coded (green/yellow/red) |

---

## **6️⃣ FORECASTING - Predict Delivery Capability**

### **Purpose**
Forecasting answers: **"Can I deliver X impressions on Y targeting?"**

Used by sales teams to check availability before promising inventory.

### **Forecasting Algorithm**

```python
def forecast_impressions(targeting_rules, start_date, end_date, booked_imps):
    """Predict how many impressions are available"""
    
    # Step 1: Get historical traffic
    traffic_data = query_traffic_by_targeting(targeting_rules, start_date, end_date)
    # Returns: daily_impressions = [100K, 102K, 98K, 105K, ...]
    
    # Step 2: Calculate available inventory after guaranteed line items
    reserved = sum(
        li.booked_impressions
        for li in line_items
        if li.priority >= 10  # Sponsorship + Standard
        and targets_same_inventory(li.targeting, targeting_rules)
    )
    
    available = total_traffic - reserved
    
    # Step 3: Apply competition factor
    # If many Standard line items target same inventory, discount forecast
    competing_line_items = count_targeting_overlaps(targeting_rules)
    discount_factor = 1.0 / (1.0 + competing_line_items * 0.1)
    
    # Step 4: Forecast for requested period
    forecast = available * discount_factor
    
    # Step 5: Check for overbooking risk
    if forecast < booked_imps:
        overbooking_risk = (booked_imps / forecast) - 1
        return {
            "available_impressions": forecast,
            "requested_impressions": booked_imps,
            "overbooking_risk_percent": overbooking_risk * 100,
            "status": "AT_RISK" if overbooking_risk > 0.2 else "OK"
        }
    
    return {
        "available_impressions": forecast,
        "requested_impressions": booked_imps,
        "overbooking_risk_percent": 0,
        "status": "OK"
    }
```

### **UI Control Mapping**

| UI Control | Backend Data | Displayed Info |
|-----------|---|---|
| Delivery Forecast Bar | `forecast_impressions()` result | % availability |
| Conflict Warning | `competing_line_items` count | "X other line items competing" |
| Overbooking Alert | `overbooking_risk_percent` | Red warning if > 20% |
| Estimated Completion Date | `booked_imps / (avg_daily_traffic)` | Predicted end date |

---

## **7️⃣ PROGRAMMATIC DELIVERY - Automated Auction**

### **Purpose**
Programmatic delivery handles **real-time bidding** and **automated guaranteed deals**. It's where programmatic buyers and sellers connect.

### **Types of Programmatic Deals**

#### **Programmatic Guaranteed (PG)**
```python
class ProgrammaticGuaranteed:
    deal_id: str                    # Deal ID (unique per buyer)
    buyer_id: str                   # Programmatic buyer account
    guaranteed_impressions: int     # Seller commitment
    fixed_cpm: float                # Pre-negotiated price
    start_date: datetime
    end_date: datetime
    inventory_targeting: Dict       # What inventory included
    buyer_frequency_cap: int        # Impressions per user
    
    # Ranking in auction
    auction_priority: int           # Higher = gets served first
    
    # Fulfillment tracking
    impressions_delivered: int
    impressions_shortfall: int
    pacing_status: str              # "on_pace", "behind", "ahead"
```

**Algorithm**: PG line items get **PRIORITY** in delivery. System ensures seller delivers guaranteed impressions.

```python
def should_serve_pg_deal(deal, ad_request):
    """Always serve PG if targeting matches (it's guaranteed)"""
    
    if not is_targeting_match(deal, ad_request):
        return False
    
    if deal.impressions_delivered >= deal.guaranteed_impressions:
        return False  # Guarantee fulfilled
    
    if not is_within_dates(deal, datetime.now()):
        return False
    
    return True  # Serve to fulfill guarantee
```

#### **Preferred Deals**
```python
class PreferredDeal:
    deal_id: str
    buyer_id: str
    floor_price: float              # Minimum CPM buyer must bid
    inventory_targeting: Dict
    auction_priority: int           # Gets right of first refusal
    
    # Buyer signals interest by bidding >= floor_price
    buyer_signals_received: int
    buyer_acceptance_rate: float
```

**Algorithm**: Preferred deals get **FIRST LOOK** at inventory, but buyers must bid >= floor.

```python
def should_offer_preferred_deal(deal, ad_request, floor_price):
    """Offer to buyer before open auction"""
    
    if not is_targeting_match(deal, ad_request):
        return False
    
    # Send to buyer, say "here's floor price: $X"
    # Buyer decides: bid >= X (accept) or pass (skip)
    
    buyer_response = send_bid_request_to_buyer(
        deal_id=deal.deal_id,
        floor_price=floor_price,
        targeting=ad_request
    )
    
    if buyer_response.bid >= floor_price:
        return True  # Buyer won preferred deal
    else:
        return False  # Buyer passed, go to open auction
```

#### **Open Auction**
```python
class OpenAuctionBid:
    buyer_id: str
    bid_price: float                # CPM they're willing to pay
    bid_time: datetime
    winning: bool
```

**Algorithm**: Highest bidder wins. All programmatic buyers compete.

```python
def run_open_auction(ad_request, minimum_floor):
    """Auction for remaining inventory"""
    
    # Send bid request to all buyers
    bids = []
    for buyer in programmatic_buyers:
        bid = send_bid_request(
            ad_request=ad_request,
            minimum_floor=minimum_floor
        )
        if bid.price >= minimum_floor:
            bids.append(bid)
    
    if not bids:
        return None  # No bids
    
    # Winner = highest bidder
    winner = max(bids, key=lambda b: b.price)
    return winner
```

### **Unified Auction Logic - When Request Arrives**

```python
def select_line_item_unified_auction(ad_request):
    """Complete decision tree mixing guaranteed + programmatic"""
    
    # TIER 1: Check direct guaranteed line items first
    for li in line_items.filter(type="SPONSORSHIP"):
        if is_eligible(li, ad_request) and needs_impressions(li):
            return li
    
    # TIER 2: Check Programmatic Guaranteed deals
    for deal in pg_deals.filter(status="ACTIVE"):
        if is_eligible(deal, ad_request) and needs_impressions(deal):
            send_ad(deal)
            return
    
    # TIER 3: Check Standard line items
    for li in line_items.filter(type="STANDARD"):
        if is_eligible(li, ad_request) and needs_impressions(li):
            return li
    
    # TIER 4: Check Preferred Deals (get first look)
    for deal in preferred_deals.filter(status="ACTIVE"):
        if is_eligible(deal, ad_request):
            bid = request_bid(deal, floor_price=deal.floor_price)
            if bid >= deal.floor_price:
                return bid  # Preferred deal won
    
    # TIER 5: Open Auction (remaining inventory, all buyers)
    bids = request_bids_from_all_buyers(ad_request, floor=floor_price)
    if bids:
        winner_bid = max(bids, key=lambda b: b.price)
        return winner_bid
    
    # TIER 6: Network/Bulk line items (fill remnant)
    for li in line_items.filter(type="NETWORK", "BULK"):
        if is_eligible(li, ad_request):
            return li
    
    # TIER 7: No fill
    return None
```

### **UI Control Mapping for Programmatic**

| UI Control | Backend Field | Used In |
|-----------|---|---|
| Deal Type Select (PG/Preferred/Open) | `deal_type` | Routes to correct algorithm |
| Guaranteed Impressions | `guaranteed_impressions` | Fulfillment tracking |
| Floor Price Input | `floor_price` | Minimum bid validation |
| Buyer Allow List Checkboxes | `allowed_buyers` | Pre-filters bid requests |
| Buyer Block List Checkboxes | `blocked_buyers` | Excludes from auction |
| Auction Priority Slider | `auction_priority` | Affects tier ranking |
| Deal Status Badge | `impressions_delivered / guaranteed` | Real-time fulfillment % |

---

## **ARCHITECTURE: How It All Flows**

### **Request Flow Diagram**
```
┌─────────────────────┐
│ Ad Request Arrives  │  (Page load, /ads?url=X&device=mobile&geo=US)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ Parse & Validate Request            │  Extract: URL, device, geo, user_id, etc
│ - Extract parameters                │
│ - Look up user audience segments    │
│ - Validate security (brand safety)  │
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│ Find Eligible Line Items                 │  Run targeting match for all line items
│ - Match against targeting rules          │
│ - Check status (active, within dates)    │
│ - Verify caps not hit (daily/lifetime)   │
│ - Validate frequency caps (per user)     │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│ Tier-Based Selection                     │  TIER 1: Sponsorship (P16-14)
│ 1. Sponsorship guarantees               │  TIER 2: PG deals
│ 2. Programmatic Guaranteed deals         │  TIER 3: Standard (P12-10)
│ 3. Standard guarantees (P12-10)          │  TIER 4: Preferred deals
│ 4. Preferred deals (Bid → Win)           │  TIER 5: Open auction
│ 5. Open auction (Highest bidder)         │  TIER 6: Network/Bulk
│ 6. Network line items (P8-6)             │
│ 7. Bulk remnant (P4-1)                   │
└──────────┬───────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│ Check Pacing                           │  - Daily cap hit?
│ - Apply pacing strategy (Even/etc)    │  - Lifetime cap hit?
│ - Apply catch-up logic                 │  - Catch-up needed?
└──────────┬─────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│ Select Creative                         │  - Even rotation?
│ - Apply creative rotation               │  - Optimized (highest CTR)?
│ - Check creative targeting              │  - Sequential?
│ - Validate creative approval            │
└──────────┬─────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│ Build Ad Response                       │  - Render HTML with creative
│ - Render HTML/VAST                      │  - Insert click macros
│ - Insert tracking pixels                │  - Add impression tracking
│ - Apply dynamic content                 │
└──────────┬─────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────┐
│ Return Ad to Browser                    │  Delivered!
│ + Log Impression                        │  Update counters
└────────────────────────────────────────┘
```

---

## **DATABASE SCHEMA SUMMARY**

```sql
-- Core Tables
TABLE orders (
    id, name, advertiser_id, salesperson_id,
    start_date, end_date, total_budget, status
);

TABLE line_items (
    id, order_id, name, type, priority,
    booked_impressions, delivered_impressions,
    rate_type, rate_value, pacing_strategy,
    daily_cap, lifetime_cap, frequency_cap,
    creative_rotation, status
);

TABLE targeting_rules (
    id, line_item_id,
    ad_unit_ids, placements,
    geo_include, geo_exclude,
    device_types, browsers,
    custom_kv, time_targeting
);

TABLE creatives (
    id, line_item_id, type,
    image_url / video_url / native_fields,
    click_url, approval_status,
    start_serving, stop_serving,
    impressions, clicks
);

TABLE pacing (
    id, line_item_id, pacing_type,
    daily_cap, lifetime_cap, catch_up_enabled,
    impressions_today, impressions_lifetime
);

TABLE programmatic_deals (
    id, deal_id, buyer_id, deal_type,  -- PG / Preferred / Open
    guaranteed_impressions, fixed_cpm / floor_price,
    allowed_buyers, blocked_buyers
);

TABLE impression_logs (
    id, line_item_id, creative_id, user_id,
    ad_unit_id, geo, device, timestamp,
    click, conversion
);
```

---

## **KEY DESIGN DECISIONS**

### **1. Priority System (P1-P16)**
Higher priority line items get served first. This ensures:
- Sponsorships are always fulfilled
- Network inventory fills last
- Fair allocation across buyers

### **2. Tier-Based Auction**
Guarantees are served before open auction:
- **Direct guarantees** (Sponsorship/Standard) = 100% serve
- **PG deals** = Seller commitment fulfilled
- **Preferred deals** = Right of first refusal
- **Open auction** = Market CPM, highest bidder wins
- **Remnant** = Fills unsold inventory cheaply

### **3. Pacing Strategies**
- **Even**: Predictable, consistent delivery
- **Frontloaded**: Creates visibility spike
- **ASAP**: Completes quickly
- **Catch-up**: Auto-adjusts if falling behind schedule

### **4. Targeting as Boolean Logic**
All targeting is AND logic (must match ALL rules):
- Inventory match AND Geography match AND Device match AND Audience match = eligible
- This ensures precise audience matching

### **5. Frequency Capping at Request Time**
Checked for every impression to prevent over-serving:
- If user already saw 3 ads today → don't serve
- Prevents user annoyance, maintains brand safety

---

## **PERFORMANCE OPTIMIZATION**

### **Caching Strategy**
```
Line Item targeting rules → Cache (5 min TTL)
Programmatic buyer config → Cache (1 hour TTL)
Forecasting data → Cache (1 hour TTL)
User frequency cap → Redis (fast lookup)
```

### **Database Indexing**
```sql
CREATE INDEX idx_line_items_status ON line_items(status, priority);
CREATE INDEX idx_line_items_dates ON line_items(start_date, end_date);
CREATE INDEX idx_targeting_ad_unit ON targeting_rules(ad_unit_ids);
CREATE INDEX idx_impression_logs_user ON impression_logs(user_id, timestamp);
```

### **Real-Time Updates**
- Impression counters updated via message queue (Kafka/RabbitMQ)
- Pacing checks run asynchronously
- Forecasting refreshed hourly

---

## **MONITORING & ALERTS**

### **Key Metrics to Track**
```
- Line item delivery rate (% of booked delivered)
- Pacing variance (actual vs expected)
- Over-delivery/under-delivery percentage
- Programmatic deal fulfillment rate
- Average fill rate
- CPM trends
- Frequency cap hits (users seeing too many ads)
- Creative approval time
```

### **Alerts to Trigger**
```
- Under-delivery risk (>20% behind schedule)
- Overbooking detected (guaranteed imps exceed available)
- Creative approval pending >2 days
- PG deal on pace to under-deliver
- Floor price below cost (unprofitable)
- Frequency cap hit rate >10%
```

---

This architecture represents a **production ad server** design that balances guaranteed delivery, auction economics, and advertiser/publisher needs.
