"""
Example data and scenarios for testing the system.
Demonstrates realistic line items, creatives, and floor rules.
"""
from services.delivery_engine.types import LineItem, Creative, Size
from uuid import uuid4
from datetime import datetime, timedelta

# === NETWORK SETUP ===
NETWORK_ID = "net-news-123"
SITE_ID = "site-techcrunch"

# === CREATIVES ===
CREATIVE_LEADERBOARD = Creative(
    id="cr-lb-728x90",
    size=Size(w=728, h=90),
    type='display',
    adm='<div style="background:blue;color:white;padding:10px;text-align:center;">Tech News Leaderboard</div>'
)

CREATIVE_MEDIUM = Creative(
    id="cr-med-300x250",
    size=Size(w=300, h=250),
    type='display',
    adm='<div style="background:green;color:white;padding:10px;text-align:center;">Medium Rectangle</div>'
)

CREATIVE_WIDE_SKYSCRAPER = Creative(
    id="cr-sky-300x600",
    size=Size(w=300, h=600),
    type='display',
    adm='<div style="background:purple;color:white;padding:10px;text-align:center;">Skyscraper</div>'
)

# === LINE ITEMS ===

# Premium sponsorship - highest priority (Priority 16)
# Guarantees delivery, controls flow
LI_SPONSOR = LineItem(
    id="li-sponsor-001",
    priority=16,
    cpm=15.0,
    targeting={
        "adUnits": ["tech/home/hero", "tech/home/sidebar"],
        "kv": {"section": "technology"},
        "geo": ["US"],
        "devices": ["desktop", "mobile"]
    },
    pacing="even",
    booked_imps=100000,
    delivered_imps=42000,
    start=(datetime.now() - timedelta(days=5)).timestamp(),
    end=(datetime.now() + timedelta(days=25)).timestamp(),
    creatives=[CREATIVE_LEADERBOARD, CREATIVE_MEDIUM]
)

# Partner content - high priority (Priority 12)
# Premium inventory guarantee
LI_PARTNER = LineItem(
    id="li-partner-001",
    priority=12,
    cpm=10.0,
    targeting={
        "adUnits": ["tech/home/hero"],
        "kv": {"section": ["technology", "ai"]},
        "geo": ["US", "CA"],
        "devices": ["desktop", "mobile"]
    },
    pacing="even",
    booked_imps=50000,
    delivered_imps=21000,
    start=(datetime.now() - timedelta(days=5)).timestamp(),
    end=(datetime.now() + timedelta(days=25)).timestamp(),
    creatives=[CREATIVE_LEADERBOARD, CREATIVE_MEDIUM]
)

# Price priority line item (Priority 10)
# Cost-based; fills at specified CPM
LI_PRICE_PRIORITY = LineItem(
    id="li-pp-001",
    priority=10,
    cpm=6.5,
    targeting={
        "adUnits": ["tech/home/hero", "tech/home/sidebar"],
        "kv": {},
        "geo": ["US", "CA", "MX"],
        "devices": ["desktop", "mobile"]
    },
    pacing="asap",
    booked_imps=200000,
    delivered_imps=95000,
    start=(datetime.now() - timedelta(days=5)).timestamp(),
    end=(datetime.now() + timedelta(days=25)).timestamp(),
    creatives=[CREATIVE_LEADERBOARD, CREATIVE_MEDIUM, CREATIVE_WIDE_SKYSCRAPER]
)

# Standard campaign (Priority 8)
# Regular guaranteed line item
LI_STANDARD = LineItem(
    id="li-std-001",
    priority=8,
    cpm=4.0,
    targeting={
        "adUnits": ["tech/home/hero", "tech/home/sidebar", "tech/articles"],
        "kv": {"category": ["news", "opinion", "analysis"]},
        "geo": ["US"],
        "devices": ["desktop", "mobile"]
    },
    pacing="even",
    booked_imps=150000,
    delivered_imps=60000,
    start=(datetime.now() - timedelta(days=3)).timestamp(),
    end=(datetime.now() + timedelta(days=27)).timestamp(),
    creatives=[CREATIVE_MEDIUM, CREATIVE_WIDE_SKYSCRAPER]
)

# Remnant (Priority 6)
# Non-guaranteed, fills remaining inventory
LI_REMNANT = LineItem(
    id="li-remnant-001",
    priority=6,
    cpm=1.5,
    targeting={
        "adUnits": ["tech/home", "tech/articles", "tech/sidebar"],
        "kv": {},
        "geo": ["US", "CA", "MX", "GB"],
        "devices": ["desktop", "mobile", "app"]
    },
    pacing="asap",
    booked_imps=None,  # No guaranteed volume
    delivered_imps=0,
    start=(datetime.now() - timedelta(days=30)).timestamp(),
    end=(datetime.now() + timedelta(days=30)).timestamp(),
    creatives=[CREATIVE_LEADERBOARD, CREATIVE_MEDIUM, CREATIVE_WIDE_SKYSCRAPER]
)

# House ads (Priority 4)
# Lowest priority, fills unsold inventory
LI_HOUSE = LineItem(
    id="li-house-001",
    priority=4,
    cpm=0.0,
    targeting={
        "adUnits": ["tech/home", "tech/articles", "tech/sidebar"],
        "kv": {},
        "geo": [],  # All geos
        "devices": []  # All devices
    },
    pacing="asap",
    booked_imps=None,
    delivered_imps=0,
    start=(datetime.now() - timedelta(days=365)).timestamp(),
    end=(datetime.now() + timedelta(days=365)).timestamp(),
    creatives=[CREATIVE_LEADERBOARD, CREATIVE_MEDIUM, CREATIVE_WIDE_SKYSCRAPER]
)

# All line items
ALL_LINE_ITEMS = [
    LI_SPONSOR,
    LI_PARTNER,
    LI_PRICE_PRIORITY,
    LI_STANDARD,
    LI_REMNANT,
    LI_HOUSE,
]

# === FLOOR RULES ===
# Hierarchical floor pricing based on context
FLOOR_RULES = [
    # Premium inventory gets higher floor
    {
        "floor": 5.0,
        "ad_unit": "tech/home/hero",
        "device": "desktop",
        "geo": "US"
    },
    # Mobile is slightly lower
    {
        "floor": 3.5,
        "ad_unit": "tech/home/hero",
        "device": "mobile",
        "geo": "US"
    },
    # Articles section
    {
        "floor": 2.5,
        "ad_unit": "tech/articles",
        "device": "desktop",
        "geo": "US"
    },
    {
        "floor": 1.5,
        "ad_unit": "tech/articles",
        "device": "mobile",
        "geo": "US"
    },
    # International gets lower floor
    {
        "floor": 1.0,
        "geo": "GB"
    },
    {
        "floor": 0.5,
        "geo": "MX"
    },
    # Catch-all minimum
    {
        "floor": 0.0
    }
]

# === EXAMPLE REQUESTS ===
# Demonstrates different targeting scenarios

REQUEST_HERO_US_DESKTOP = {
    "adUnit": "tech/home/hero",
    "sizes": [{"w": 728, "h": 90}, {"w": 300, "h": 250}],
    "kv": {"section": "technology", "pageType": "homepage"},
    "geo": "US",
    "device": "desktop",
    "userId": "user-123"
}

REQUEST_ARTICLE_US_MOBILE = {
    "adUnit": "tech/articles",
    "sizes": [{"w": 300, "h": 250}, {"w": 300, "h": 600}],
    "kv": {"section": "news", "pageType": "article"},
    "geo": "US",
    "device": "mobile",
    "userId": "user-456"
}

REQUEST_SIDEBAR_GB_MOBILE = {
    "adUnit": "tech/sidebar",
    "sizes": [{"w": 300, "h": 600}],
    "kv": {"section": "opinion"},
    "geo": "GB",
    "device": "mobile",
    "userId": "user-789"
}

REQUEST_HERO_MEXICO = {
    "adUnit": "tech/home/hero",
    "sizes": [{"w": 728, "h": 90}],
    "kv": {},
    "geo": "MX",
    "device": "desktop",
    "userId": "user-999"
}

# All example requests
EXAMPLE_REQUESTS = [
    REQUEST_HERO_US_DESKTOP,
    REQUEST_ARTICLE_US_MOBILE,
    REQUEST_SIDEBAR_GB_MOBILE,
    REQUEST_HERO_MEXICO,
]
