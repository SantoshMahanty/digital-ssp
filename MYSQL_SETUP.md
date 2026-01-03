# MySQL Setup Guide for GAM-360 Simulator

## Quick Setup

Your project is now configured to use **MySQL** instead of PostgreSQL or Redis. No external services required beyond MySQL itself.

## 1. Install MySQL

### Windows (Using Installer)
1. Download: https://dev.mysql.com/downloads/installer/
2. Run the installer
3. Choose "Server only" or "Full" installation
4. Configure MySQL Server:
   - Port: 3306 (default)
   - TCP/IP enabled
   - Create a Windows service (recommended)

### macOS (Using Homebrew)
```bash
brew install mysql
brew services start mysql
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install mysql-server
sudo mysql_secure_installation
```

## 2. Create Database and User

Open MySQL command line:
```bash
mysql -u root -p
```

Enter root password when prompted, then run:
```sql
-- Create database
CREATE DATABASE gam360;

-- Create user
CREATE USER 'gam360'@'localhost' IDENTIFIED BY 'gam360';

-- Grant permissions
GRANT ALL PRIVILEGES ON gam360.* TO 'gam360'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify
SHOW DATABASES;
```

## 3. Verify Connection

Test the connection:
```bash
mysql -u gam360 -p -h localhost gam360
```

Enter password: `gam360`

You should see: `mysql> `

## 4. Initialize Database Tables

Option A: **Using Python (recommended)**
```bash
python -c "from services.api.database import init_db; init_db('mysql+mysqlconnector://gam360:gam360@localhost:3306/gam360')"
```

Option B: **Manual SQL**
```bash
mysql -u gam360 -p gam360 < schema.sql
```

## 5. Start the API

The server is already running! Visit:
- **API**: http://localhost:8001
- **Docs**: http://localhost:8001/docs

## Configuration

The `.env` file has been updated:
```env
# Database (MySQL)
DATABASE_URL=mysql+mysqlconnector://gam360:gam360@localhost:3306/gam360

# MySQL Connection Details
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=gam360
MYSQL_PASSWORD=gam360
MYSQL_DATABASE=gam360
```

Modify these values if you used different credentials.

## Using the API

### Test Connection
```bash
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": 1234567890,
  "line_items_count": 6
}
```

### Submit an Ad Request
```bash
curl -X POST http://localhost:8001/ad \
  -H "Content-Type: application/json" \
  -d '{
    "adUnit": "tech/home/hero",
    "sizes": [{"w": 728, "h": 90}],
    "kv": {"section": "technology"},
    "geo": "US",
    "device": "desktop"
  }'
```

### View All Line Items
```bash
curl http://localhost:8001/line-items | python -m json.tool
```

## Database Schema

The system creates these tables automatically:

- **network** - Ad networks
- **site_app** - Websites/apps
- **ad_unit** - Placement slots
- **placement** - Ad unit collections
- **line_item** - Ad campaigns
- **order** - Campaign containers
- **creative** - Ad content
- **pacing_state** - Delivery tracking
- **ad_request** - Request audit log

## Troubleshooting

### MySQL Server Not Running
```bash
# Windows
net start MySQL80

# macOS
brew services start mysql

# Linux
sudo systemctl start mysql
```

### Connection Refused
1. Verify MySQL is running
2. Check port 3306: `netstat -an | findstr 3306` (Windows)
3. Verify credentials in `.env`
4. Ensure user exists: `mysql -u gam360 -p`

### Database Doesn't Exist
```bash
mysql -u root -p -e "CREATE DATABASE gam360; GRANT ALL ON gam360.* TO 'gam360'@'localhost';"
```

### Permission Denied
```bash
mysql -u root -p
GRANT ALL PRIVILEGES ON gam360.* TO 'gam360'@'localhost';
FLUSH PRIVILEGES;
```

## Running Tests

```bash
python -m pytest services/tests.py -v
```

Tests use in-memory data, so they work without database.

## What Changed

✅ **PostgreSQL → MySQL** (using `mysql-connector-python`)
✅ **Removed Redis** (not needed for in-memory operation)
✅ **Removed Kafka** (not needed for basic operation)
✅ **Simplified configuration** (MySQL only)

## Next Steps

1. ✅ Install MySQL
2. ✅ Create database and user
3. ✅ Start the API server
4. ✅ Try an example request at `/examples`
5. ✅ View interactive docs at `/docs`

## MySQL Basics

### Connect
```bash
mysql -u gam360 -p -h localhost gam360
```

### List databases
```sql
SHOW DATABASES;
```

### List tables
```sql
SHOW TABLES;
```

### View table structure
```sql
DESCRIBE line_item;
```

### Query data
```sql
SELECT id, name, priority, cpm FROM line_item LIMIT 5;
```

## Connection String Format

```
mysql+mysqlconnector://username:password@host:port/database
```

Example:
```
mysql+mysqlconnector://gam360:gam360@localhost:3306/gam360
```

## Backup and Restore

### Backup
```bash
mysqldump -u gam360 -p gam360 > backup.sql
```

### Restore
```bash
mysql -u gam360 -p gam360 < backup.sql
```

---

**Your system is now configured for MySQL!** 🎉

The API will automatically create tables when you first run it. No manual schema setup required.
