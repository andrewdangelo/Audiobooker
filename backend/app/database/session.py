"""
Database Session Management
"""

from config.database import SessionLocal, engine, Base


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Get database session"""
    return SessionLocal()
