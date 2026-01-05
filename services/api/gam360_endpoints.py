"""
GAM360 API Endpoints - CRUD operations for all major entities
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import json

# Pydantic Models for request/response
class AdUnitCreate(BaseModel):
    ad_unit_name: str
    ad_unit_code: str
    ad_unit_type: str = "PLACEMENT"
    publisher_id: int
    parent_ad_unit_id: Optional[int] = None
    sizes: Optional[List[Dict]] = None

class PlacementCreate(BaseModel):
    placement_name: str
    ad_unit_ids: List[int]
    description: Optional[str] = None

class TargetingRuleCreate(BaseModel):
    line_item_id: int
    targeting_type: str
    targeting_value: Dict
    is_include: bool = True

class FrequencyCapCreate(BaseModel):
    line_item_id: int
    cap_type: str
    frequency: int
    time_unit: str

class CreativeMetadataCreate(BaseModel):
    creative_id: int
    duration_sec: Optional[int] = None
    file_size: int
    mime_type: str
    ssl_compliant: bool = True
    vast_validated: bool = False

class ProgrammaticSettingsCreate(BaseModel):
    publisher_id: int
    exchange_type: str
    floor_price: float
    ssps: Optional[List[str]] = None

class PreferredDealCreate(BaseModel):
    deal_name: str
    advertiser_id: int
    publisher_id: int
    floor_price: Optional[float] = None
    deal_type: str = "PREFERRED"
    start_date: str
    end_date: str

class AudienceCreate(BaseModel):
    audience_name: str
    audience_type: str = "FIRST_PARTY"
    description: Optional[str] = None
    size: int = 0

class AgencyCreate(BaseModel):
    agency_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

class SalespersonCreate(BaseModel):
    salesperson_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    agency_id: Optional[int] = None

# ============================================================================
# 1. INVENTORY MANAGEMENT ENDPOINTS
# ============================================================================

def register_inventory_endpoints(app: FastAPI):
    """Register all inventory management endpoints"""
    
    @app.post("/api/ad-units/create")
    async def create_ad_unit(data: AdUnitCreate):
        """Create a new ad unit"""
        from services.api.mysql_queries import execute_query
        
        try:
            query = """
                INSERT INTO ad_units (ad_unit_name, ad_unit_code, ad_unit_type, 
                                     publisher_id, parent_ad_unit_id, sizes, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'ACTIVE')
            """
            
            execute_query(query, (
                data.ad_unit_name,
                data.ad_unit_code,
                data.ad_unit_type,
                data.publisher_id,
                data.parent_ad_unit_id,
                json.dumps(data.sizes) if data.sizes else None
            ))
            
            return {"success": True, "message": "Ad unit created successfully"}
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/api/ad-units")
    async def list_ad_units(publisher_id: Optional[int] = None):
        """List all ad units, optionally filtered by publisher"""
        from services.api.mysql_queries import execute_query
        
        if publisher_id:
            query = "SELECT * FROM ad_units WHERE publisher_id = %s ORDER BY ad_unit_name"
            results = execute_query(query, (publisher_id,))
        else:
            query = "SELECT * FROM ad_units ORDER BY ad_unit_name"
            results = execute_query(query)
        
        return {"ad_units": results}
    
    @app.post("/api/placements/create")
    async def create_placement(data: PlacementCreate):
        """Create a new placement"""
        from services.api.mysql_queries import execute_query
        
        try:
            query = """
                INSERT INTO placements (placement_name, ad_unit_ids, description, status)
                VALUES (%s, %s, %s, 'ACTIVE')
            """
            
            execute_query(query, (
                data.placement_name,
                json.dumps(data.ad_unit_ids),
                data.description
            ))
            
            return {"success": True, "message": "Placement created successfully"}
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/api/placements")
    async def list_placements():
        """List all placements"""
        from services.api.mysql_queries import execute_query
        
        query = "SELECT * FROM placements ORDER BY placement_name"
        results = execute_query(query)
        
        return {"placements": results}
    
    @app.post("/api/inventory-forecast")
    async def forecast_inventory(ad_unit_id: int, forecast_date: str):
        """Get inventory forecast for an ad unit"""
        from services.api.mysql_queries import execute_query
        
        query = """
            SELECT * FROM inventory_forecast 
            WHERE ad_unit_id = %s AND forecast_date = %s
        """
        
        results = execute_query(query, (ad_unit_id, forecast_date))
        return {"forecast": results[0] if results else None}

# ============================================================================
# 2. TARGETING ENDPOINTS
# ============================================================================

def register_targeting_endpoints(app: FastAPI):
    """Register all targeting control endpoints"""
    
    @app.post("/api/targeting-rules/create")
    async def create_targeting_rule(data: TargetingRuleCreate):
        """Create a targeting rule for a line item"""
        from services.api.mysql_queries import execute_query
        
        try:
            query = """
                INSERT INTO targeting_rules (line_item_id, targeting_type, targeting_value, is_include)
                VALUES (%s, %s, %s, %s)
            """
            
            execute_query(query, (
                data.line_item_id,
                data.targeting_type,
                json.dumps(data.targeting_value),
                data.is_include
            ))
            
            return {"success": True, "message": "Targeting rule created"}
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/api/targeting-rules/{line_item_id}")
    async def get_targeting_rules(line_item_id: int):
        """Get all targeting rules for a line item"""
        from services.api.mysql_queries import execute_query
        
        query = "SELECT * FROM targeting_rules WHERE line_item_id = %s"
        results = execute_query(query, (line_item_id,))
        
        return {"targeting_rules": results}
    
    @app.post("/api/frequency-caps/create")
    async def create_frequency_cap(data: FrequencyCapCreate):
        """Create frequency cap for a line item"""
        from services.api.mysql_queries import execute_query
        
        try:
            query = """
                INSERT INTO frequency_caps (line_item_id, cap_type, frequency, time_unit)
                VALUES (%s, %s, %s, %s)
            """
            
            execute_query(query, (
                data.line_item_id,
                data.cap_type,
                data.frequency,
                data.time_unit
            ))
            
            return {"success": True, "message": "Frequency cap created"}
        except Exception as e:
            return {"error": str(e)}

# ============================================================================
# 3. CREATIVE MANAGEMENT ENDPOINTS
# ============================================================================

def register_creative_endpoints(app: FastAPI):
    """Register creative management endpoints"""
    
    @app.post("/api/creatives/metadata")
    async def add_creative_metadata(data: CreativeMetadataCreate):
        """Add metadata to a creative"""
        from services.api.mysql_queries import execute_query
        
        try:
            query = """
                INSERT INTO creative_metadata (creative_id, duration_sec, file_size, 
                                              mime_type, ssl_compliant, vast_validated)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            execute_query(query, (
                data.creative_id,
                data.duration_sec,
                data.file_size,
                data.mime_type,
                data.ssl_compliant,
                data.vast_validated
            ))
            
            return {"success": True, "message": "Creative metadata added"}
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/api/creatives/{creative_id}/metadata")
    async def get_creative_metadata(creative_id: int):
        """Get metadata for a creative"""
        from services.api.mysql_queries import execute_query
        
        query = "SELECT * FROM creative_metadata WHERE creative_id = %s"
        results = execute_query(query, (creative_id,))
        
        return {"metadata": results[0] if results else None}

# ============================================================================
# 4. PROGRAMMATIC & YIELD ENDPOINTS
# ============================================================================

def register_programmatic_endpoints(app: FastAPI):
    """Register programmatic and yield management endpoints"""
    
    @app.post("/api/programmatic-settings/create")
    async def create_programmatic_settings(data: ProgrammaticSettingsCreate):
        """Create programmatic settings for a publisher"""
        from services.api.mysql_queries import execute_query
        
        try:
            query = """
                INSERT INTO programmatic_settings (publisher_id, exchange_type, 
                                                   floor_price, ssps)
                VALUES (%s, %s, %s, %s)
            """
            
            execute_query(query, (
                data.publisher_id,
                data.exchange_type,
                data.floor_price,
                json.dumps(data.ssps) if data.ssps else None
            ))
            
            return {"success": True, "message": "Programmatic settings created"}
        except Exception as e:
            return {"error": str(e)}
    
    @app.post("/api/preferred-deals/create")
    async def create_preferred_deal(data: PreferredDealCreate):
        """Create a preferred deal"""
        from services.api.mysql_queries import execute_query
        
        try:
            query = """
                INSERT INTO preferred_deals (deal_name, advertiser_id, publisher_id, 
                                            floor_price, deal_type, start_date, end_date, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
            """
            
            execute_query(query, (
                data.deal_name,
                data.advertiser_id,
                data.publisher_id,
                data.floor_price,
                data.deal_type,
                data.start_date,
                data.end_date
            ))
            
            return {"success": True, "message": "Preferred deal created"}
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/api/preferred-deals")
    async def list_preferred_deals():
        """List all preferred deals"""
        from services.api.mysql_queries import execute_query
        
        query = "SELECT * FROM preferred_deals WHERE status = 'ACTIVE' ORDER BY deal_name"
        results = execute_query(query)
        
        return {"deals": results}

# ============================================================================
# 5. AUDIENCE MANAGEMENT ENDPOINTS
# ============================================================================

def register_audience_endpoints(app: FastAPI):
    """Register audience management endpoints"""
    
    @app.post("/api/audiences/create")
    async def create_audience(data: AudienceCreate):
        """Create an audience"""
        from services.api.mysql_queries import execute_query
        
        try:
            query = """
                INSERT INTO audiences (audience_name, audience_type, description, size)
                VALUES (%s, %s, %s, %s)
            """
            
            execute_query(query, (
                data.audience_name,
                data.audience_type,
                data.description,
                data.size
            ))
            
            return {"success": True, "message": "Audience created"}
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/api/audiences")
    async def list_audiences():
        """List all audiences"""
        from services.api.mysql_queries import execute_query
        
        query = "SELECT * FROM audiences ORDER BY audience_name"
        results = execute_query(query)
        
        return {"audiences": results}

# ============================================================================
# 6. AGENCY & SALESPERSON ENDPOINTS
# ============================================================================

def register_sales_endpoints(app: FastAPI):
    """Register sales management endpoints"""
    
    @app.post("/api/agencies/create")
    async def create_agency(data: AgencyCreate):
        """Create an agency"""
        from services.api.mysql_queries import execute_query
        
        try:
            query = """
                INSERT INTO agencies (agency_name, contact_email, contact_phone)
                VALUES (%s, %s, %s)
            """
            
            execute_query(query, (
                data.agency_name,
                data.contact_email,
                data.contact_phone
            ))
            
            return {"success": True, "message": "Agency created"}
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/api/agencies")
    async def list_agencies():
        """List all agencies"""
        from services.api.mysql_queries import execute_query
        
        query = "SELECT * FROM agencies ORDER BY agency_name"
        results = execute_query(query)
        
        return {"agencies": results}
    
    @app.post("/api/salespeople/create")
    async def create_salesperson(data: SalespersonCreate):
        """Create a salesperson"""
        from services.api.mysql_queries import execute_query
        
        try:
            query = """
                INSERT INTO salespeople (salesperson_name, email, phone, agency_id)
                VALUES (%s, %s, %s, %s)
            """
            
            execute_query(query, (
                data.salesperson_name,
                data.email,
                data.phone,
                data.agency_id
            ))
            
            return {"success": True, "message": "Salesperson created"}
        except Exception as e:
            return {"error": str(e)}
    
    @app.get("/api/salespeople")
    async def list_salespeople():
        """List all salespeople"""
        from services.api.mysql_queries import execute_query
        
        query = "SELECT sp.*, a.agency_name FROM salespeople sp LEFT JOIN agencies a ON sp.agency_id = a.agency_id ORDER BY sp.salesperson_name"
        results = execute_query(query)
        
        return {"salespeople": results}

# ============================================================================
# 7. REPORTING ENDPOINTS
# ============================================================================

def register_reporting_endpoints(app: FastAPI):
    """Register reporting endpoints"""
    
    @app.get("/api/reports/delivery")
    async def get_delivery_report(line_item_id: Optional[int] = None, days: int = 7):
        """Get delivery report"""
        from services.api.mysql_queries import execute_query
        from datetime import datetime, timedelta
        
        start_date = (datetime.now() - timedelta(days=days)).date()
        
        if line_item_id:
            query = """
                SELECT metric_date, line_item_id, impressions_delivered, impressions_goal,
                       pacing_percentage, under_delivery_alert, over_delivery_alert
                FROM delivery_metrics
                WHERE line_item_id = %s AND metric_date >= %s
                ORDER BY metric_date DESC
            """
            results = execute_query(query, (line_item_id, start_date))
        else:
            query = """
                SELECT metric_date, line_item_id, impressions_delivered, impressions_goal,
                       pacing_percentage, under_delivery_alert, over_delivery_alert
                FROM delivery_metrics
                WHERE metric_date >= %s
                ORDER BY metric_date DESC, line_item_id
            """
            results = execute_query(query, (start_date,))
        
        return {"report": results}
    
    @app.get("/api/reports/yield")
    async def get_yield_report(publisher_id: Optional[int] = None):
        """Get yield report"""
        from services.api.mysql_queries import execute_query
        
        query = """
            SELECT DATE(report_hour) as date, SUM(impressions) as impressions,
                   SUM(revenue) as revenue, AVG(ecpm) as avg_ecpm,
                   SUM(clicks) as clicks, AVG(ctr) as avg_ctr
            FROM report_data
            WHERE report_hour >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(report_hour)
            ORDER BY date DESC
        """
        
        results = execute_query(query)
        return {"report": results}

# ============================================================================
# Main Registration Function
# ============================================================================

def register_gam360_endpoints(app: FastAPI):
    """Register all GAM360 endpoints"""
    register_inventory_endpoints(app)
    register_targeting_endpoints(app)
    register_creative_endpoints(app)
    register_programmatic_endpoints(app)
    register_audience_endpoints(app)
    register_sales_endpoints(app)
    register_reporting_endpoints(app)
