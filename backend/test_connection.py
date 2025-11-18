"""Test Railway PostgreSQL connection"""
from config.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    result = db.execute(text('SELECT COUNT(*) FROM audiobooks'))
    count = result.scalar()
    print(f'✅ Connected to Railway PostgreSQL!')
    print(f'📊 Audiobooks table exists with {count} records')
except Exception as e:
    print(f'❌ Connection failed: {e}')
finally:
    db.close()
