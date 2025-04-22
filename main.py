"""
Main application entry point for the nutrition and exercise coach API.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import router as api_router
from database import init_database

# Initialize FastAPI app
app = FastAPI(
    title="Nutrition and Exercise Coach API",
    description="API for a virtual nutrition and exercise coach powered by AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include API routes
app.include_router(api_router, prefix="")


# Startup event to initialize database
@app.on_event("startup")
async def startup():
    """Initialize database on application startup"""
    await init_database()


# Root endpoint for health check
@app.get("/")
async def root():
    """API health check endpoint"""
    return {
        "status": "online",
        "message": "Nutrition and Exercise Coach API is running",
        "version": "1.0.0"
    }


# Run the application
if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable for cloud deployments
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)