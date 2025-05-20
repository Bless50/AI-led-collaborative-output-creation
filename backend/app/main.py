from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.db.init_db import init_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully!")
    yield
    # Shutdown code (if needed)
    logger.info("Shutting down application...")

# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Led Collaborative Report Generator API",
    version="0.1.0",
    lifespan=lifespan
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include API routers
from app.api.api_v1.api import api_router

app.include_router(api_router, prefix=settings.API_V1_STR)

# Database initialization moved to lifespan context manager above


@app.get("/")
async def root():
    """
    Root endpoint for health check
    """
    return {"message": "Welcome to the AI-Led Collaborative Report Generator API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
