"""
Database models and ORM configuration
"""
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, JSON, Boolean, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

Base = declarative_base()


class Network(Base):
    """Represents an ad network"""
    __tablename__ = "network"
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    sites = relationship("SiteApp", back_populates="network")
    placements = relationship("Placement", back_populates="network")


class SiteApp(Base):
    """Represents a website or app"""
    __tablename__ = "site_app"
    
    id = Column(String(36), primary_key=True)
    network_id = Column(String(36), ForeignKey("network.id"), nullable=False)
    name = Column(String(255), nullable=False)
    type = Column(Enum('web', 'app', 'ctv', name='site_type'), nullable=False)
    domain = Column(String(255))
    bundle_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    network = relationship("Network", back_populates="sites")
    ad_units = relationship("AdUnit", back_populates="site_app")


class AdUnit(Base):
    """Represents an ad unit (placement slot)"""
    __tablename__ = "ad_unit"
    
    id = Column(String(36), primary_key=True)
    site_app_id = Column(String(36), ForeignKey("site_app.id"), nullable=False)
    parent_id = Column(String(36), ForeignKey("ad_unit.id"))
    code = Column(String(255), nullable=False)
    description = Column(String(255))
    sizes = Column(JSON, nullable=False)  # [{"w": 300, "h": 250}, ...]
    key_values = Column(JSON, default={})
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    site_app = relationship("SiteApp", back_populates="ad_units")
    children = relationship("AdUnit", remote_side=[id])
    placements = relationship("PlacementAdUnit", back_populates="ad_unit")


class Placement(Base):
    """Represents a grouping of ad units for trafficking"""
    __tablename__ = "placement"
    
    id = Column(String(36), primary_key=True)
    network_id = Column(String(36), ForeignKey("network.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    network = relationship("Network", back_populates="placements")
    ad_units = relationship("PlacementAdUnit", back_populates="placement")


class PlacementAdUnit(Base):
    """Junction table for placement -> ad_unit many-to-many"""
    __tablename__ = "placement_ad_unit"
    
    placement_id = Column(String(36), ForeignKey("placement.id"), primary_key=True)
    ad_unit_id = Column(String(36), ForeignKey("ad_unit.id"), primary_key=True)
    
    placement = relationship("Placement", back_populates="ad_units")
    ad_unit = relationship("AdUnit", back_populates="placements")


class LineItem(Base):
    """Represents a line item (ad campaign)"""
    __tablename__ = "line_item"
    
    id = Column(String(36), primary_key=True)
    order_id = Column(String(36), ForeignKey("order.id"), nullable=False)
    name = Column(String(255), nullable=False)
    priority = Column(Integer, nullable=False)  # 4, 6, 8, 10, 12, 16
    cpm = Column(Float, nullable=False)  # Cost per mille (thousand impressions)
    targeting = Column(JSON, nullable=False)  # Complex targeting rules
    pacing = Column(Enum('even', 'asap', name='pacing_type'), default='even')
    booked_imps = Column(Integer)  # Total impressions to deliver
    delivered_imps = Column(Integer, default=0)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(Enum('draft', 'active', 'paused', 'completed', name='li_status'), default='draft')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    order = relationship("Order", back_populates="line_items")
    creatives = relationship("Creative", back_populates="line_item")
    pacing_state = relationship("PacingState", back_populates="line_item", uselist=False)


class Order(Base):
    """Represents an order (container for line items)"""
    __tablename__ = "order"
    
    id = Column(String(36), primary_key=True)
    network_id = Column(String(36), ForeignKey("network.id"), nullable=False)
    name = Column(String(255), nullable=False)
    advertiser = Column(String(255))
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(Enum('draft', 'active', 'completed', name='order_status'), default='draft')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    line_items = relationship("LineItem", back_populates="order")


class Creative(Base):
    """Represents a creative (ad content)"""
    __tablename__ = "creative"
    
    id = Column(String(36), primary_key=True)
    line_item_id = Column(String(36), ForeignKey("line_item.id"), nullable=False)
    name = Column(String(255), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    type = Column(Enum('display', 'video', 'native', name='creative_type'), default='display')
    duration_sec = Column(Integer)
    adm = Column(String(10000))  # Ad markup (HTML/VAST)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    line_item = relationship("LineItem", back_populates="creatives")


class PacingState(Base):
    """Tracks pacing state for line items"""
    __tablename__ = "pacing_state"
    
    id = Column(String(36), primary_key=True)
    line_item_id = Column(String(36), ForeignKey("line_item.id"), unique=True, nullable=False)
    delivered_today = Column(Integer, default=0)
    expected_today = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    line_item = relationship("LineItem", back_populates="pacing_state")


class AdRequest(Base):
    """Audit log of ad requests"""
    __tablename__ = "ad_request"
    
    id = Column(String(36), primary_key=True)
    ad_unit_id = Column(String(36), ForeignKey("ad_unit.id"))
    line_item_id = Column(String(36), ForeignKey("line_item.id"))
    sizes = Column(JSON)
    targeting = Column(JSON)
    geo = Column(String(10))
    device = Column(String(50))
    user_id = Column(String(255))
    winner_line_item_id = Column(String(36), ForeignKey("line_item.id"))
    no_fill_reason = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)


# Database connection setup
def get_db_engine(database_url: str):
    """Create and return database engine"""
    return create_engine(database_url, pool_pre_ping=True, echo=False)


def get_db_session(database_url: str):
    """Get database session factory"""
    engine = get_db_engine(database_url)
    return sessionmaker(bind=engine)


def init_db(database_url: str):
    """Initialize database tables"""
    engine = get_db_engine(database_url)
    Base.metadata.create_all(engine)
    return engine
