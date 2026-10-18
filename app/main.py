import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.routers import auth_router, views_router, api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("motivation-app")

# Initialize FastAPI application
app = FastAPI(
    title="Daily Motivation App",
    description="Personalized AI Motivation Quotes & Audio Powered by GCP Vertex AI & Cloud TTS",
    version="1.0.0"
)

# Mount static assets
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")

# Register routers
app.include_router(views_router)
app.include_router(auth_router)
app.include_router(api_router)
