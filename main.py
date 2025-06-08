"""
Main application entry point for the nutrition and exercise coach API.
Updated to support both web and Flutter applications with unified backend.
"""
import silence_sqlalchemy
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import traceback
from config import DATABASE_URL
from api import router as api_router  # Your existing web API routes
from database import init_database, User, SessionLocal
from tasks import start_background_worker
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text, select
from flutter_routes import health_router  # Flutter-specific routes
import bcrypt

# SQLAlchemy setup
Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Initialize FastAPI app
app = FastAPI(
    title="Unified Nutrition and Exercise Coach API",
    description="API for nutrition and exercise coaching - supports both web and mobile applications",
    version="2.0.0"
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
app.include_router(api_router, prefix="")  # Web frontend routes
app.include_router(health_router)  # Flutter/mobile routes

# Startup event to initialize database and run background worker
@app.on_event("startup")
async def startup():
    """Initialize database on application startup and start background worker"""
    print(f"🔍 DATABASE_URL: {DATABASE_URL}") 
    await init_database()
    start_background_worker()
    
    # Verify database connection and show accurate user count
    print("Verifying unified database connection...")
    try:
        async with SessionLocal() as session:
            # Test connection
            result = await session.execute(text("SELECT 1"))
            print("✅ Database connection verified.")
            
            # Get accurate count of all users
            count_result = await session.execute(text("SELECT COUNT(*) FROM users"))
            total_users = count_result.scalar()
            print(f"📊 Total users in database: {total_users}")
            
            # Check for existing users with more details
            result = await session.execute(select(User).order_by(User.created_at.desc()).limit(5))
            users = result.scalars().all()
            
            print(f"👤 Recent users:")
            for i, user in enumerate(users, 1):
                print(f"  {i}. {user.name} ({user.email}) - Created: {user.created_at}")
                
    except Exception as e:
        print(f"❌ Error during startup verification: {e}")
        traceback.print_exc()

# Root endpoint for health check
@app.get("/")
async def root():
    """API health check endpoint"""
    return {
        "status": "online",
        "message": "Unified Nutrition and Exercise Coach API is running",
        "version": "2.0.0",
        "supports": ["web", "flutter", "mobile"],
        "endpoints": {
            "web": "/api/*",
            "mobile": "/api/health/*",
            "onboarding": "/api/onboarding/complete",
            "auth": "/api/auth/login"
        }
    }

# Run the application
if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable for cloud deployments
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)