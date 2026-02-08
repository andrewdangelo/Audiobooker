from . import health

# MongoDB-based routers are imported directly in main.py
# auth_mongo and accounts_mongo replace the old SQLAlchemy versions

__all__ = ["health"]
