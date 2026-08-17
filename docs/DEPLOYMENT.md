# Deployment, Scaling & Disaster Recovery Guide

## 1. Prerequisites & Containerized Architecture

The application requires:
- Docker & Docker Compose v2.0+
- PostgreSQL 16+
- Redis 7+
- Python 3.12+ (for bare-metal or local virtual environment execution)

---

## 2. Quickstart with Docker Compose

```bash
# 1. Clone & enter backend directory
cd backend

# 2. Copy environment file
cp .env.example .env

# 3. Edit production secrets in .env (SECRET_KEY, DB passwords, API credentials)
nano .env

# 4. Start all services
docker compose up -d --build

# 5. Check container health
docker compose ps

# 6. Verify health endpoint
curl http://localhost:8000/api/v1/health/ready
```

---

## 3. Database Migration & Initialization

Migrations are managed with Alembic:

```bash
# Apply migrations to latest revision
docker compose exec api alembic upgrade head

# Generate a new migration revision
docker compose exec api alembic revision --autogenerate -m "add_new_feature_fields"
```

---

## 4. Automated Backup & Disaster Recovery

### Automated PostgreSQL Backup Script (`backup_db.sh`)
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/voting_db"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

docker exec -t voting_db pg_dump -U postgres voting_db | gzip > "$BACKUP_DIR/backup_$TIMESTAMP.sql.gz"

# Retain last 30 days
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +30 -delete
```

### Point-in-Time Database Restoration (`restore_db.sh`)
```bash
#!/bin/bash
BACKUP_FILE=$1
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore_db.sh <path_to_backup.sql.gz>"
    exit 1
fi

gunzip -c "$BACKUP_FILE" | docker exec -i voting_db psql -U postgres -d voting_db
```
