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
import re
from .config import config

logger = logging.getLogger(__name__)

# 1. Prioridad: DATABASE_URL o DB_URL directa (ej. provista por Render, Neon, Supabase)
db_url_env = os.getenv("DATABASE_URL") or os.getenv("DB_URL")

if db_url_env:
    # Render y Heroku usan postgres:// que SQLAlchemy depreca a favor de postgresql://
    if db_url_env.startswith("postgres://"):
        db_url_env = db_url_env.replace("postgres://", "postgresql://", 1)
    db_connection_str = db_url_env
else:
    # 2. Soporte para variables desglosadas (DB_HOST, DB_USER/DB_USERNAME, etc.)
    user = os.getenv("DB_USER") or os.getenv("DB_USERNAME") or config.db_username
    password = os.getenv("DB_PASSWORD") or config.db_password
    host = os.getenv("DB_HOST") or config.db_host
    port = os.getenv("DB_PORT") or config.db_port
    name = os.getenv("DB_NAME") or config.db_name

    if user and password:
        auth = f"{user}:{password}@"
    elif user:
        auth = f"{user}@"
    else:
        auth = ""

    db_connection_str = f"postgresql://{auth}{host}:{port}/{name}"

# Sanitizar URL para logging seguro (ocultar password)
sanitized_url = re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", db_connection_str)
logger.info(f"Target Database URL: {sanitized_url}")

# Manejo de SSL: si la URL no incluye sslmode, usar prefer
connect_args = {}
if "sslmode" not in db_connection_str:
    connect_args["sslmode"] = "prefer"

engine = create_engine(
    db_connection_str,
    echo=config.debug,
    connect_args=connect_args,
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
