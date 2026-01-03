-- GAM360 Database Schema with Optimizations for Large Datasets

USE gam360;

-- ===================================
-- CORE TABLES
-- ===================================

-- Organizations/Publishers
CREATE TABLE IF NOT EXISTS publishers (
    publisher_id INT PRIMARY KEY AUTO_INCREMENT,
    publisher_name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (publisher_name),
    INDEX idx_domain (domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Advertisers
CREATE TABLE IF NOT EXISTS advertisers (
    advertiser_id INT PRIMARY KEY AUTO_INCREMENT,
    advertiser_name VARCHAR(255) NOT NULL,
    advertiser_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_name (advertiser_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Campaigns
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id INT PRIMARY KEY AUTO_INCREMENT,
    campaign_name VARCHAR(255) NOT NULL,
    advertiser_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    budget DECIMAL(15, 2),
    status ENUM('ACTIVE', 'PAUSED', 'COMPLETED', 'DRAFT') DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (advertiser_id) REFERENCES advertisers(advertiser_id),
    INDEX idx_advertiser (advertiser_id),
    INDEX idx_status (status),
    INDEX idx_dates (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Orders (Line Items in GAM)
CREATE TABLE IF NOT EXISTS orders (
    order_id INT PRIMARY KEY AUTO_INCREMENT,
    order_name VARCHAR(255) NOT NULL,
    campaign_id INT NOT NULL,
    publisher_id INT NOT NULL,
    order_type ENUM('GUARANTEED', 'PROGRAMMATIC_GUARANTEED', 'PREFERRED', 'OPEN_AUCTION') DEFAULT 'OPEN_AUCTION',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    daily_budget DECIMAL(15, 2),
    lifetime_budget DECIMAL(15, 2),
    daily_impression_goal INT,
    lifetime_impression_goal INT,
    pacing_rate DECIMAL(5, 2) DEFAULT 100.00,
    status ENUM('ACTIVE', 'PAUSED', 'COMPLETED', 'DRAFT') DEFAULT 'DRAFT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
    FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id),
    INDEX idx_campaign (campaign_id),
    INDEX idx_publisher (publisher_id),
    INDEX idx_status (status),
    INDEX idx_dates (start_date, end_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Creatives
CREATE TABLE IF NOT EXISTS creatives (
    creative_id INT PRIMARY KEY AUTO_INCREMENT,
    creative_name VARCHAR(255) NOT NULL,
    campaign_id INT NOT NULL,
    creative_type ENUM('BANNER', 'VIDEO', 'NATIVE', 'INSTREAM', 'OUTSTREAM') DEFAULT 'BANNER',
    width INT,
    height INT,
    file_size INT,
    file_url VARCHAR(500),
    status ENUM('ACTIVE', 'PAUSED', 'APPROVED', 'REJECTED', 'PENDING') DEFAULT 'PENDING',
    approval_status ENUM('APPROVED', 'REJECTED', 'PENDING_REVIEW') DEFAULT 'PENDING_REVIEW',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(campaign_id),
    INDEX idx_campaign (campaign_id),
    INDEX idx_status (status),
    INDEX idx_approval (approval_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Impressions (Events)
CREATE TABLE IF NOT EXISTS impressions (
    impression_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    creative_id INT NOT NULL,
    publisher_id INT NOT NULL,
    user_id VARCHAR(128),
    device_type ENUM('DESKTOP', 'MOBILE', 'TABLET') DEFAULT 'DESKTOP',
    country_code CHAR(2),
    city VARCHAR(100),
    platform ENUM('WEB', 'MOBILE_APP', 'CONNECTED_TV') DEFAULT 'WEB',
    browser_type VARCHAR(50),
    os_type VARCHAR(50),
    ip_address VARCHAR(45),
    impression_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    viewable INT DEFAULT 0,
    view_duration INT,
    click_through INT DEFAULT 0,
    conversion INT DEFAULT 0,
    revenue DECIMAL(15, 6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (creative_id) REFERENCES creatives(creative_id),
    FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id),
    INDEX idx_order (order_id),
    INDEX idx_creative (creative_id),
    INDEX idx_publisher (publisher_id),
    INDEX idx_impression_time (impression_time),
    INDEX idx_user (user_id),
    INDEX idx_device (device_type),
    INDEX idx_country (country_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Audiences/Segments
CREATE TABLE IF NOT EXISTS audience_segments (
    segment_id INT PRIMARY KEY AUTO_INCREMENT,
    segment_name VARCHAR(255) NOT NULL,
    segment_type ENUM('BEHAVIOR', 'DEMOGRAPHIC', 'INTERESTS', 'LOOKALIKE', 'CUSTOM', 'COMBINATION') DEFAULT 'CUSTOM',
    publisher_id INT NOT NULL,
    segment_size INT,
    quality_score DECIMAL(3, 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id),
    INDEX idx_publisher (publisher_id),
    INDEX idx_type (segment_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Audience Users Mapping (Many-to-Many)
CREATE TABLE IF NOT EXISTS audience_users (
    audience_user_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    segment_id INT NOT NULL,
    user_id VARCHAR(128) NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (segment_id) REFERENCES audience_segments(segment_id) ON DELETE CASCADE,
    UNIQUE KEY unique_segment_user (segment_id, user_id),
    INDEX idx_segment (segment_id),
    INDEX idx_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Pacing Data
CREATE TABLE IF NOT EXISTS pacing (
    pacing_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    date DATE NOT NULL,
    hour INT,
    impressions_delivered INT,
    revenue_earned DECIMAL(15, 2),
    pacing_percentage DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    UNIQUE KEY unique_order_datetime (order_id, date, hour),
    INDEX idx_order (order_id),
    INDEX idx_date (date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Programmatic Deals
CREATE TABLE IF NOT EXISTS programmatic_deals (
    deal_id INT PRIMARY KEY AUTO_INCREMENT,
    deal_name VARCHAR(255) NOT NULL,
    advertiser_id INT NOT NULL,
    publisher_id INT NOT NULL,
    deal_type ENUM('PG', 'PREFERRED', 'OPEN_AUCTION') DEFAULT 'PREFERRED',
    floor_price DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (advertiser_id) REFERENCES advertisers(advertiser_id),
    FOREIGN KEY (publisher_id) REFERENCES publishers(publisher_id),
    INDEX idx_advertiser (advertiser_id),
    INDEX idx_publisher (publisher_id),
    INDEX idx_deal_type (deal_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Frequency Caps
CREATE TABLE IF NOT EXISTS frequency_caps (
    frequency_cap_id INT PRIMARY KEY AUTO_INCREMENT,
    order_id INT NOT NULL,
    cap_type ENUM('PER_USER', 'CROSS_DEVICE', 'HOUSEHOLD') DEFAULT 'PER_USER',
    impression_limit INT,
    time_period ENUM('HOURLY', 'DAILY', 'WEEKLY', 'MONTHLY', 'LIFETIME') DEFAULT 'DAILY',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    INDEX idx_order (order_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Analytics/Metrics
CREATE TABLE IF NOT EXISTS daily_metrics (
    metric_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id INT,
    metric_date DATE NOT NULL,
    impressions INT DEFAULT 0,
    clicks INT DEFAULT 0,
    conversions INT DEFAULT 0,
    revenue DECIMAL(15, 2) DEFAULT 0,
    viewable_impressions INT DEFAULT 0,
    ctr DECIMAL(5, 4),
    cvr DECIMAL(5, 4),
    cpm DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    INDEX idx_order (order_id),
    INDEX idx_date (metric_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ===================================
-- CREATE INITIAL DATA
-- ===================================

-- Insert Publishers
INSERT IGNORE INTO publishers (publisher_name, domain) VALUES
('New York Times', 'nytimes.com'),
('CNN', 'cnn.com'),
('ESPN', 'espn.com'),
('TechCrunch', 'techcrunch.com'),
('Forbes', 'forbes.com'),
('Wired', 'wired.com'),
('Mashable', 'mashable.com'),
('Vimeo', 'vimeo.com'),
('Medium', 'medium.com'),
('LinkedIn', 'linkedin.com');

-- Insert Advertisers
INSERT IGNORE INTO advertisers (advertiser_name, advertiser_url) VALUES
('Google', 'google.com'),
('Apple', 'apple.com'),
('Microsoft', 'microsoft.com'),
('Amazon', 'amazon.com'),
('Meta', 'meta.com'),
('Tesla', 'tesla.com'),
('Nike', 'nike.com'),
('Coca-Cola', 'coca-cola.com'),
('Samsung', 'samsung.com'),
('Intel', 'intel.com');

-- Insert Campaigns (100 campaigns)
INSERT IGNORE INTO campaigns (campaign_name, advertiser_id, start_date, end_date, budget, status)
SELECT 
    CONCAT('Campaign_', @campaign_num := @campaign_num + 1),
    (@advertiser_id := FLOOR(RAND() * 10) + 1),
    DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 30) DAY),
    DATE_ADD(CURDATE(), INTERVAL FLOOR(RAND() * 60) DAY),
    FLOOR(RAND() * 100000) + 10000,
    'ACTIVE'
FROM (SELECT 0) t1, (SELECT @campaign_num := 0) t2, (SELECT @advertiser_id := 0) t3
LIMIT 100;

COMMIT;
