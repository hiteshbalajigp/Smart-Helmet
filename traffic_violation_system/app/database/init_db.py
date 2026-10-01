"""Database initialization and optional bootstrap data."""

from __future__ import annotations

import os

from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.database.base import Base
from app.database.models import User
from app.database.models.user import UserRole
from app.database.session import SessionLocal, engine
from app.utils.logging_config import get_logger

logger = get_logger(__name__)


def init_database() -> None:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured.")


def seed_default_admin(db: Session) -> None:
    username = os.getenv("BOOTSTRAP_ADMIN_USERNAME", "admin")
    password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@traffic.local")

    if not password:
        logger.info("Bootstrap admin skipped (BOOTSTRAP_ADMIN_PASSWORD not set).")
        return

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        return

    admin = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    logger.info("Bootstrap admin user created: %s", username)


def initialize_application_database() -> None:
    init_database()
    db = SessionLocal()
    try:
        seed_default_admin(db)
    finally:
        db.close()
