"""
app/main.py

Purpose: Application entry point

- Initializes FastAPI app
- Loads configuration and logging
- Registers API routes (webhook)
- No business logic should be written here
- Manages application lifecycle (startup/shutdown)
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.core.config import settings, validate_settings
from app.core.logging import setup_logging, get_logger
from app.db.mongo import connect_to_mongo, close_mongo_connection, check_database_health
from app.db.indexes import create_indexes
from app.services.gst_service import close_gst_service
from app.api import webhook

# Initialize logging first
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 Starting NilEasy application...")
    
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        validate_settings()
        logger.info("✅ Configuration validated")
        
        # Connect to MongoDB
        logger.info("Connecting to MongoDB...")
        await connect_to_mongo()
        logger.info("✅ MongoDB connected")
        
        # Create database indexes
        logger.info("Creating database indexes...")
        await create_indexes()
        logger.info("✅ Database indexes created")
        
        # Health check
        is_healthy = await check_database_health()
        if not is_healthy:
            logger.warning("⚠️ Database health check failed during startup")
        else:
            logger.info("✅ Database health check passed")
        
        logger.info("🎉 NilEasy application started successfully!")
        logger.info(f"Environment: {settings.ENVIRONMENT}")
        logger.info(f"Debug Mode: {settings.DEBUG}")
        
    except Exception as e:
        logger.critical(f"Failed to start application: {str(e)}", exc_info=True)
        raise
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 Shutting down NilEasy application...")
    
    try:
        # Close GST service
        await close_gst_service()
        logger.info("✅ GST service closed")
        
        # Close MongoDB connection
        await close_mongo_connection()
        logger.info("✅ MongoDB connection closed")
        
        logger.info("👋 NilEasy application shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}", exc_info=True)


# Create FastAPI app with lifespan
app = FastAPI(
    title="NilEasy - GST Nil Filing Assistant",
    description="WhatsApp-based conversational GST Nil filing system",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.DEBUG,
    docs_url="/docs" if settings.is_development else None,  # Disable docs in production
    redoc_url="/redoc" if settings.is_development else None,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time header to all responses."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 5.0:  # More than 5 seconds
        logger.warning(
            f"Slow request detected: {request.method} {request.url.path}",
            extra={"process_time": process_time}
        )
    
    return response


# Error handler for unexpected exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to catch unexpected errors.
    """
    logger.error(
        f"Unhandled exception: {str(exc)}",
        extra={
            "method": request.method,
            "url": str(request.url),
            "client": request.client.host if request.client else "unknown"
        },
        exc_info=True
    )
    
    # Don't expose internal errors in production
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={
                "error": "An internal error occurred. Please try again later.",
                "code": "INTERNAL_ERROR"
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "type": type(exc).__name__,
                "code": "INTERNAL_ERROR"
            }
        )


# Register API routes
from app.api import otp_callback

app.include_router(webhook.router, prefix=settings.API_PREFIX, tags=["Webhook"])
app.include_router(otp_callback.router, tags=["OTP Callback"])


# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint - basic info."""
    return {
        "name": "NilEasy API",
        "version": "1.0.0",
        "description": "WhatsApp-based GST Nil Filing Assistant",
        "status": "running",
        "environment": settings.ENVIRONMENT
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Comprehensive health check endpoint.
    Checks database connectivity and service status.
    """
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "checks": {}
    }
    
    # Check database
    try:
        db_healthy = await check_database_health()
        health_status["checks"]["database"] = "healthy" if db_healthy else "unhealthy"
        
        if not db_healthy:
            health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        health_status["checks"]["database"] = "unhealthy"
        health_status["status"] = "unhealthy"
    
    # Check GST service (optional - can be slow)
    health_status["checks"]["gst_service"] = "not_checked"
    
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(content=health_status, status_code=status_code)


# Readiness probe (for Kubernetes/orchestration)
@app.get("/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness probe - indicates if app is ready to receive traffic.
    """
    try:
        db_healthy = await check_database_health()
        if db_healthy:
            return {"status": "ready"}
        else:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "database_unavailable"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": str(e)}
        )


# Liveness probe (for Kubernetes/orchestration)
@app.get("/live", tags=["Health"])
async def liveness_check():
    """
    Liveness probe - indicates if app is alive.
    """
    return {"status": "alive"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower()
    )
