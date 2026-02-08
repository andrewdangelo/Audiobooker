"""
Payments & Subscriptions Endpoints
"""

__author__ = "Mohammad Saifan"

from fastapi import APIRouter, Depends, HTTPException, Query
import logging
import uuid

from app.database.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


