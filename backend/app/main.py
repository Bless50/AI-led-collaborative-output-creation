from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.db.init_db import init_db

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Led Collaborative Report Generator API",
    version="0.1.0",
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

# Initialize database on startup
@app.on_event("startup")
def initialize_database():
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized successfully!")


@app.get("/")
async def root():
    """
    Root endpoint for health check
    """
    return {"message": "Welcome to the AI-Led Collaborative Report Generator API"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
