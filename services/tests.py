"""
Unit tests for decision engine, auction, and pacing logic
"""
import pytest
import time
from datetime import datetime, timedelta
from services.delivery_engine.types import (
    AdRequest, LineItem, Creative, Size, Bid, DecisionTrace
)
from services.delivery_engine.decision import (
    evaluate_request, matches_inventory, matches_kv, matches_geo, 
    matches_device, size_compatible
)
from services.delivery_engine.auction import run_auction, select_winner
from services.delivery_engine.pacing import even_pacing_allows, pacing_allows
from services.delivery_engine.floors import compute_floor, rule_matches


# === FIXTURES ===

@pytest.fixture
def sample_creatives():
    """Standard creatives"""
    return [
        Creative(id="cr-728x90", size=Size(w=728, h=90), type='display'),
        Creative(id="cr-300x250", size=Size(w=300, h=250), type='display'),
    ]


@pytest.fixture
def sample_line_items(sample_creatives):
    """Line items with different priorities and targeting"""
    return [
        LineItem(
            id="li-sponsor",
            priority=16,
            cpm=10.0,
            targeting={"adUnits": ["home/hero"], "kv": {"type": "news"}},
            pacing="even",
            booked_imps=100000,
            delivered_imps=50000,
            start=time.time() - 86400 * 5,
            end=time.time() + 86400 * 5,
            creatives=sample_creatives
        ),
        LineItem(
            id="li-standard",
            priority=8,
            cpm=4.0,
            targeting={"adUnits": ["home/hero", "home/sidebar"]},
            pacing="even",
            booked_imps=200000,
            delivered_imps=100000,
            start=time.time() - 86400 * 5,
            end=time.time() + 86400 * 5,
            creatives=sample_creatives
        ),
        LineItem(
            id="li-remnant",
            priority=6,
            cpm=1.0,
            targeting={"adUnits": ["home"]},
            pacing="asap",
            booked_imps=None,
            delivered_imps=0,
            start=time.time() - 86400 * 30,
            end=time.time() + 86400 * 30,
            creatives=sample_creatives
        ),
    ]


# === TARGETING TESTS ===

class TestTargetingMatching:
    
    def test_matches_inventory_exact(self):
        li = LineItem(id="1", priority=10, cpm=5.0, targeting={"adUnits": ["home/hero"]})
        assert matches_inventory(
            AdRequest("1", "home/hero", [], {}, "US", "desktop"),
            li
        )
    
    def test_matches_inventory_no_match(self):
        li = LineItem(id="1", priority=10, cpm=5.0, targeting={"adUnits": ["home/hero"]})
        assert not matches_inventory(
            AdRequest("1", "home/sidebar", [], {}, "US", "desktop"),
            li
        )
    
    def test_matches_inventory_any_if_not_specified(self):
        li = LineItem(id="1", priority=10, cpm=5.0, targeting={})
        assert matches_inventory(
            AdRequest("1", "home/hero", [], {}, "US", "desktop"),
            li
        )
    
    def test_matches_kv_exact(self):
        li = LineItem(id="1", priority=10, cpm=5.0, targeting={"kv": {"type": "news"}})
        assert matches_kv({"type": "news"}, li.targeting["kv"])
    
    def test_matches_kv_list_value(self):
        li = LineItem(id="1", priority=10, cpm=5.0, targeting={"kv": {"type": ["news", "sports"]}})
        assert matches_kv({"type": "news"}, li.targeting["kv"])
        assert matches_kv({"type": "sports"}, li.targeting["kv"])
        assert not matches_kv({"type": "opinion"}, li.targeting["kv"])
    
    def test_matches_kv_missing_required(self):
        li = LineItem(id="1", priority=10, cpm=5.0, targeting={"kv": {"type": "news", "author": "alice"}})
        assert not matches_kv({"type": "news"}, li.targeting["kv"])  # Missing author
    
    def test_matches_geo(self):
        assert matches_geo("US", ["US", "CA"])
        assert not matches_geo("MX", ["US", "CA"])
        assert matches_geo("US", [])  # No geo targeting
    
    def test_matches_device(self):
        assert matches_device("desktop", ["desktop", "mobile"])
        assert not matches_device("tablet", ["desktop", "mobile"])


# === PACING TESTS ===

class TestPacing:
    
    def test_even_pacing_on_pace(self):
        """When delivered == expected, should allow"""
        now = time.time()
        li = LineItem(
            id="1", priority=10, cpm=5.0, pacing="even",
            booked_imps=100000, delivered_imps=50000,
            start=now - 86400 * 5,
            end=now + 86400 * 5
        )
        assert even_pacing_allows(li, now)
    
    def test_even_pacing_behind(self):
        """When delivered < expected, should allow"""
        now = time.time()
        li = LineItem(
            id="1", priority=10, cpm=5.0, pacing="even",
            booked_imps=100000, delivered_imps=40000,
            start=now - 86400 * 5,
            end=now + 86400 * 5
        )
        assert even_pacing_allows(li, now)
    
    def test_even_pacing_ahead(self):
        """When delivered > expected, should NOT allow"""
        now = time.time()
        li = LineItem(
            id="1", priority=10, cpm=5.0, pacing="even",
            booked_imps=100000, delivered_imps=60000,
            start=now - 86400 * 5,
            end=now + 86400 * 5
        )
        assert not even_pacing_allows(li, now)
    
    def test_asap_pacing_below_goal(self):
        """ASAP should allow if below booked_imps"""
        li = LineItem(
            id="1", priority=10, cpm=5.0, pacing="asap",
            booked_imps=100000, delivered_imps=50000
        )
        assert pacing_allows(li, time.time())
    
    def test_asap_pacing_reached_goal(self):
        """ASAP should NOT allow if reached booked_imps"""
        li = LineItem(
            id="1", priority=10, cpm=5.0, pacing="asap",
            booked_imps=100000, delivered_imps=100000
        )
        assert not pacing_allows(li, time.time())


# === FLOOR TESTS ===

class TestFloors:
    
    def test_floor_rule_matching_all_conditions(self):
        rule = {"floor": 5.0, "geo": "US", "device": "desktop"}
        req = AdRequest("1", "home/hero", [], {}, "US", "desktop")
        assert rule_matches(rule, req)
    
    def test_floor_rule_mismatch_device(self):
        rule = {"floor": 5.0, "geo": "US", "device": "desktop"}
        req = AdRequest("1", "home/hero", [], {}, "US", "mobile")
        assert not rule_matches(rule, req)
    
    def test_floor_rule_partial_specification(self):
        rule = {"floor": 5.0, "geo": "US"}  # Only geo specified
        req = AdRequest("1", "home/hero", [], {}, "US", "mobile")
        assert rule_matches(rule, req)  # Device not required
    
    def test_compute_floor_first_match(self):
        rules = [
            {"floor": 5.0, "geo": "US", "device": "desktop"},
            {"floor": 3.0, "geo": "US", "device": "mobile"},
            {"floor": 0.0},
        ]
        req = AdRequest("1", "home/hero", [], {}, "US", "mobile")
        floor = compute_floor(req, rules)
        assert floor == 3.0
    
    def test_compute_floor_catch_all(self):
        rules = [
            {"floor": 5.0, "geo": "US"},
            {"floor": 0.0},  # Catch-all
        ]
        req = AdRequest("1", "home/hero", [], {}, "MX", "desktop")
        floor = compute_floor(req, rules)
        assert floor == 0.0


# === AUCTION TESTS ===

class TestAuction:
    
    def test_select_winner_price_comparison(self):
        bids = [
            Bid(source='internal', price=5.0, line_item_id='li-1'),
            Bid(source='internal', price=3.0, line_item_id='li-2'),
        ]
        winner = select_winner(bids, floor=2.0)
        assert winner.line_item_id == 'li-1'
        assert winner.price == 5.0
    
    def test_select_winner_floor_filtering(self):
        bids = [
            Bid(source='internal', price=3.0, line_item_id='li-1'),
            Bid(source='internal', price=1.0, line_item_id='li-2'),
        ]
        winner = select_winner(bids, floor=2.0)
        assert winner.line_item_id == 'li-1'  # li-2 filtered by floor
    
    def test_select_winner_no_fill_floor(self):
        bids = [
            Bid(source='internal', price=1.0, line_item_id='li-1'),
        ]
        winner = select_winner(bids, floor=5.0)
        assert winner is None
    
    def test_run_auction_priority_wins_over_price(self, sample_line_items):
        """Priority 16 at $10 CPM should beat Priority 8 at $4 CPM"""
        eligible = sample_line_items[:2]  # sponsor and standard
        winner = run_auction(eligible, floor=2.0)
        assert winner.line_item_id == "li-sponsor"
        assert winner.price == 10.0


# === DECISION TESTS ===

class TestDecisionEngine:
    
    def test_evaluate_request_no_matching_inventory(self, sample_line_items):
        req = AdRequest(
            "1", "articles/top", [Size(728, 90)], {},
            "US", "desktop"
        )
        trace = evaluate_request(req, sample_line_items, {})
        assert trace.winner is None
        assert trace.no_fill_reason == 'targeting'
    
    def test_evaluate_request_winner(self, sample_line_items):
        req = AdRequest(
            "1", "home/hero", [Size(728, 90)],
            {"type": "news"}, "US", "desktop"
        )
        trace = evaluate_request(req, sample_line_items, {"floor_rules": []})
        assert trace.winner is not None
        assert trace.winner.line_item_id == "li-sponsor"
    
    def test_evaluate_request_no_fill_size(self, sample_line_items):
        req = AdRequest(
            "1", "home/hero", [Size(600, 400)],  # Incompatible size
            {}, "US", "desktop"
        )
        trace = evaluate_request(req, sample_line_items, {})
        assert trace.winner is None
        assert trace.no_fill_reason == 'targeting'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
