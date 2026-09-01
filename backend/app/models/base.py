"""Shared SQLAlchemy model mixins.

Per skills/DATABASE.md: reusable mixins for common columns such as
created_at / updated_at timestamps.
"""
from sqlalchemy import Column, DateTime
from sqlalchemy.sql import func


class TimestampMixin:
    """Adds created_at / updated_at timestamp columns to a model."""

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
