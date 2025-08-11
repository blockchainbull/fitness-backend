# sleep_api.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator
from datetime import datetime, date, timedelta
from typing import Optional, List
from database import SessionLocal, DailySleep
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import uuid

router = APIRouter(prefix="/sleep", tags=["Sleep Tracking"])

class SleepEntryCreate(BaseModel):
    user_id: str
    date: date
    bedtime: Optional[datetime] = None
    wake_time: Optional[datetime] = None
    total_hours: float = Field(0.0, ge=0, le=24)
    quality_score: float = Field(0.0, ge=0, le=1)
    deep_sleep_hours: float = Field(0.0, ge=0, le=24)

class SleepEntryResponse(BaseModel):
    id: str
    user_id: str
    date: date
    bedtime: Optional[datetime]
    wake_time: Optional[datetime]
    total_hours: float
    quality_score: float
    deep_sleep_hours: float
    created_at: datetime

    @validator('id', 'user_id', pre=True)
    def convert_uuid_to_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v

    class Config:
        from_attributes = True

class SleepEntryUpdate(BaseModel):
    bedtime: Optional[datetime] = None
    wake_time: Optional[datetime] = None
    total_hours: Optional[float] = Field(None, ge=0, le=24)
    quality_score: Optional[float] = Field(None, ge=0, le=1)
    deep_sleep_hours: Optional[float] = Field(None, ge=0, le=24)

class SleepStatsResponse(BaseModel):
    avg_sleep: float
    avg_quality: float
    avg_deep_sleep: float
    entries_count: int
    first_entry: Optional[date]
    last_entry: Optional[date]

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

@router.post("/entries", response_model=SleepEntryResponse)
async def create_sleep_entry(
    sleep_entry: SleepEntryCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new sleep entry"""
    try:
        # Check if entry already exists for this date
        existing_query = select(DailySleep).where(
            DailySleep.user_id == sleep_entry.user_id,
            func.date(DailySleep.date) == sleep_entry.date
        )
        existing_result = await db.execute(existing_query)
        existing_entry = existing_result.scalar_one_or_none()
        
        if existing_entry:
            raise HTTPException(
                status_code=400,
                detail="Sleep entry already exists for this date"
            )
        
        # Create new entry
        db_sleep_entry = DailySleep(
            id=uuid.uuid4(),
            user_id=sleep_entry.user_id,
            date=datetime.combine(sleep_entry.date, datetime.min.time()),
            bedtime=sleep_entry.bedtime,
            wake_time=sleep_entry.wake_time,
            total_hours=sleep_entry.total_hours,
            quality_score=sleep_entry.quality_score,
            deep_sleep_hours=sleep_entry.deep_sleep_hours
        )
        
        db.add(db_sleep_entry)
        await db.commit()
        await db.refresh(db_sleep_entry)
        
        return db_sleep_entry
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entries/{user_id}", response_model=List[SleepEntryResponse])
async def get_sleep_history(
    user_id: str,
    limit: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get sleep history for a user"""
    try:
        query = select(DailySleep).where(
            DailySleep.user_id == user_id
        ).order_by(DailySleep.date.desc()).limit(limit)
        
        result = await db.execute(query)
        sleep_entries = result.scalars().all()
        
        return sleep_entries
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/entries/{user_id}/{entry_date}", response_model=SleepEntryResponse)
async def get_sleep_entry_by_date(
    user_id: str,
    entry_date: str,  # Changed from date to str to handle the format
    db: AsyncSession = Depends(get_db)
):
    """Get sleep entry for a specific date"""
    try:
        # Parse the date string
        from datetime import datetime
        date_obj = datetime.strptime(entry_date, "%Y-%m-%d").date()
        
        query = select(DailySleep).where(
            DailySleep.user_id == user_id,
            func.date(DailySleep.date) == date_obj
        )
        
        result = await db.execute(query)
        sleep_entry = result.scalar_one_or_none()
        
        if not sleep_entry:
            # Return 404 but this is expected when no entry exists
            raise HTTPException(status_code=404, detail="No sleep entry for this date")
        
        # Convert UUIDs to strings
        return SleepEntryResponse(
            id=str(sleep_entry.id),
            user_id=str(sleep_entry.user_id),
            date=sleep_entry.date.date() if sleep_entry.date else date_obj,
            bedtime=sleep_entry.bedtime,
            wake_time=sleep_entry.wake_time,
            total_hours=sleep_entry.total_hours,
            quality_score=sleep_entry.quality_score,
            deep_sleep_hours=sleep_entry.deep_sleep_hours,
            created_at=sleep_entry.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting sleep entry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/entries/{entry_id}", response_model=SleepEntryResponse)
async def update_sleep_entry(
    entry_id: str,
    sleep_update: SleepEntryUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing sleep entry"""
    try:
        query = select(DailySleep).where(DailySleep.id == entry_id)
        result = await db.execute(query)
        sleep_entry = result.scalar_one_or_none()
        
        if not sleep_entry:
            raise HTTPException(status_code=404, detail="Sleep entry not found")
        
        # Update fields if provided
        update_data = sleep_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(sleep_entry, field, value)
        
        await db.commit()
        await db.refresh(sleep_entry)
        
        return sleep_entry
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{user_id}", response_model=SleepStatsResponse)
async def get_sleep_stats(
    user_id: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get sleep statistics for a user"""
    try:
        since_date = datetime.now() - timedelta(days=days)
        
        query = select(
            func.avg(DailySleep.total_hours).label('avg_sleep'),
            func.avg(DailySleep.quality_score).label('avg_quality'),
            func.avg(DailySleep.deep_sleep_hours).label('avg_deep_sleep'),
            func.count(DailySleep.id).label('entries_count'),
            func.min(DailySleep.date).label('first_entry'),
            func.max(DailySleep.date).label('last_entry')
        ).where(
            DailySleep.user_id == user_id,
            DailySleep.date >= since_date
        )
        
        result = await db.execute(query)
        stats = result.first()
        
        return SleepStatsResponse(
            avg_sleep=float(stats.avg_sleep or 0),
            avg_quality=float(stats.avg_quality or 0),
            avg_deep_sleep=float(stats.avg_deep_sleep or 0),
            entries_count=int(stats.entries_count or 0),
            first_entry=stats.first_entry.date() if stats.first_entry else None,
            last_entry=stats.last_entry.date() if stats.last_entry else None
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/entries/{entry_id}")
async def delete_sleep_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a sleep entry"""
    try:
        query = select(DailySleep).where(DailySleep.id == entry_id)
        result = await db.execute(query)
        sleep_entry = result.scalar_one_or_none()
        
        if not sleep_entry:
            raise HTTPException(status_code=404, detail="Sleep entry not found")
        
        await db.delete(sleep_entry)
        await db.commit()
        
        return {"message": "Sleep entry deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))