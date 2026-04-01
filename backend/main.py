"""
MedReport AI - FastAPI Backend
Main application entry point
"""
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from routes.analyze import router as analyze_router
from models.schemas import HealthResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _get_allowed_origins() -> list[str]:
    """
    Build CORS allowlist from env with safe local defaults.

    Expected format:
        ALLOWED_ORIGINS=http://localhost:3000,https://your-app.vercel.app
    """
    raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]

    # Avoid invalid wildcard + credentials combination in production configs.
    origins = [origin for origin in origins if origin != "*"]

    if not origins:
        origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

    return origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler
    """
    logger.info("Starting MedReport AI backend...")
    logger.info("Initializing services...")
    yield
    logger.info("Shutting down MedReport AI backend...")


# Initialize FastAPI app
app = FastAPI(
    title="MedReport AI",
    description="AI-powered medical lab report analysis API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
allowed_origins = _get_allowed_origins()
logger.info(f"Configured CORS allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint

    Returns:
        Health status
    """
    return HealthResponse(status="ok")


# Include routers
app.include_router(
    analyze_router,
    prefix="/api",
    tags=["Analysis"]
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler for unhandled errors
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred",
            "error_type": "InternalServerError"
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
