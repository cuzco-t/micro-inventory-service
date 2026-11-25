"""
Database Infrastructure: Connection and Session Management.

This module configures the SQLAlchemy engine via SQLModel and defines
the dependency injection pattern used by the API endpoints to interact
with the PostgreSQL database.
"""

import logging
from typing import Annotated

from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine

import os
from .config import config

logger = logging.getLogger(__name__)

# Soporta DATABASE_URL directa de proveedores como Render, Neon o Supabase
db_url_env = os.getenv("DATABASE_URL")
if db_url_env:
    # Render y algunos proveedores usan postgres:// que SQLAlchemy 1.4+ depreca a favor de postgresql://
    if db_url_env.startswith("postgres://"):
        db_url_env = db_url_env.replace("postgres://", "postgresql://", 1)
    db_connection_str = db_url_env
else:
    db_connection_str = f"postgresql://{config.db_username}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"

engine = create_engine(
    db_connection_str,
    echo=config.debug,
    connect_args={"sslmode": "prefer"},
)


def create_db_and_tables():
    """
    Scans all SQLModel classes with 'table=True' and creates them in PostgreSQL.

    This is called during the FastAPI 'lifespan' startup phase to ensure
    the database schema stays in sync with your Python models.
    """
    SQLModel.metadata.create_all(engine)
    logger.info("Database tables created or verified successfully.")


def get_session():
    """
    Provides a transactional scope for database operations.

    Yields a Session object and ensures it is properly closed after the
    request is finished, even if an error occurs.
    """
    # Use of Generator here so FastAPI can handle the 'teardown'.
    # This prevents the database from running out of connections.
    with Session(engine) as session:
        yield session


# SessionDep is a type alias that simplifies dependency injection in main.py.
# It tells FastAPI: "Whenever you see SessionDep, call get_session() and give me the result."
SessionDep = Annotated[Session, Depends(get_session)]
