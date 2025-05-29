"""
Main application entry point for the nutrition and exercise coach API.
"""
import silence_sqlalchemy
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import traceback
from config import DATABASE_URL
from api import router as api_router
from database import init_database, User, SessionLocal
from tasks import start_background_worker
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text, select
from flutter_routes import health_router


# SQLAlchemy setup
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


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

app.include_router(health_router)

# Startup event to initialize database and run background worker for user's data
@app.on_event("startup")
async def startup():
    """Initialize database on application startup and start background worker"""
    print(f"🔍 DATABASE_URL: {DATABASE_URL}") 
    await init_database()
    start_background_worker()
    

    """
    # Add verification of database connection and data loading
    print("Verifying database connection and data loading...")
    try:
        async with SessionLocal() as session:
            # Force connection test
            result = await session.execute(text("SELECT 1"))
            print("Database connection verified.")
            
            # Check for existing users and their data
            result = await session.execute(select(User).limit(5))
            users = result.scalars().all()
            
            print(f"Found {len(users)} users in database")
            
            # Debug first user's data if exists
            if users:
                first_user = users[0]
                print(f"First user ID: {first_user.id}")
                print(f"First user physical stats: {first_user.physicalStats}")
                
                if first_user.physicalStats:
                    ps = first_user.physicalStats
                    print(f"Physical stats type: {type(ps)}")
                    
                    if isinstance(ps, dict):
                        for key, value in ps.items():
                            print(f"  {key}: {value} (type: {type(value)})")
    except Exception as e:
        print(f"Error during startup verification: {e}")
        traceback.print_exc()
        """

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