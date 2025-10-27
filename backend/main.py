"""
FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from app.routers import audiobooks, upload, conversion, health

# Create FastAPI app instance
app = FastAPI(
    title="Audiobooker API",
    description="PDF to Audiobook conversion API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5175",  # Add support for alternate port
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    audiobooks.router,
    prefix=f"{settings.API_V1_PREFIX}/audiobooks",
    tags=["Audiobooks"]
)
app.include_router(
    upload.router,
    prefix=f"{settings.API_V1_PREFIX}/upload",
    tags=["Upload"]
)
app.include_router(
    conversion.router,
    prefix=f"{settings.API_V1_PREFIX}/conversion",
    tags=["Conversion"]
)


@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    print("🚀 Audiobooker API starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown"""
    print("👋 Audiobooker API shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
