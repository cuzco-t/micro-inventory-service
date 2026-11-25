"""
Application launcher.

Creates the FastAPI app, registers routers, and manages the database lifespan.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core import config, create_db_and_tables, setup_logging  # noqa: F401
from app.core.errors import (
    AppException,
    DatabaseException,
    app_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)
from app.middleware import security_headers_middleware
from app.routers import (
    analytics_router,
    health_router,
    home_router,
    inventory_router,
    products_router,
    variants_router,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles the application startup and shutdown events.

    Ensures the database engine is ready and tables are created before
    the API starts accepting traffic.
    """
    logger.info(
        "Lifespan Startup: Verifying database connectivity and creating tables."
    )
    # This ensures the database is ready before the first request arrives.
    try:
        create_db_and_tables()
    except Exception as e:
        raise DatabaseException(details={"error": str(e)})
    yield
    logger.info("Lifespan Shutdown: Cleaning up resources.")


app = FastAPI(
    title=config.app_name,
    description="A robust FastAPI service for managing warehouse stock using PostgreSQL and SQLModel.",
    version=config.version,
    lifespan=lifespan,
    root_path=os.getenv("ROOT_PATH", ""),
    swagger_ui_parameters={"docExpansion": "none"},
)

# CORS abierto a todo el mundo para pruebas y experimentos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.middleware("http")(security_headers_middleware)
app.include_router(health_router)
app.include_router(home_router)
app.include_router(inventory_router)
app.include_router(analytics_router)
app.include_router(products_router)
app.include_router(variants_router)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
