#!/usr/bin/env python3
"""
Seed database with sample data (for development/testing)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from config.database import SessionLocal
from app.models.audiobook import Audiobook, AudiobookStatus
import uuid
from datetime import datetime


def seed_data():
    """Seed database with sample audiobooks"""
    db = SessionLocal()
    
    try:
        # Create sample audiobooks
        sample_audiobooks = [
            {
                "id": str(uuid.uuid4()),
                "title": "Sample Audiobook 1",
                "original_file_name": "sample1.pdf",
                "file_size": 1024000,
                "status": AudiobookStatus.COMPLETED,
                "duration": 3600.0,
            },
            {
                "id": str(uuid.uuid4()),
                "title": "Sample Audiobook 2",
                "original_file_name": "sample2.pdf",
                "file_size": 2048000,
                "status": AudiobookStatus.PROCESSING,
            },
        ]
        
        for audiobook_data in sample_audiobooks:
            audiobook = Audiobook(**audiobook_data)
            db.add(audiobook)
        
        db.commit()
        print(f"✅ Seeded {len(sample_audiobooks)} sample audiobooks")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
