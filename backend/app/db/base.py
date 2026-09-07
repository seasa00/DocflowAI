"""SQLAlchemy declarative base shared by all persistence models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for the application's ORM models."""

