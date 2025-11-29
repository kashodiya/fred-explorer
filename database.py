#!/usr/bin/env python3
"""
FRED Explorer Database Models and Operations
SQLite database for caching FRED API data
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from datetime import datetime, timezone
import json
import os

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./fred_data.db"
SYNC_DATABASE_URL = "sqlite:///./fred_data.db"

# Create async engine
async_engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# Create sync engine for initialization
sync_engine = create_engine(SYNC_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

class Release(Base):
    """FRED Release model"""
    __tablename__ = "releases"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    press_release = Column(Boolean, default=False)
    link = Column(String)
    notes = Column(Text)
    realtime_start = Column(String)
    realtime_end = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    series = relationship("Series", back_populates="release")

class Series(Base):
    """FRED Series model"""
    __tablename__ = "series"
    
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    frequency = Column(String)
    frequency_short = Column(String)
    units = Column(String)
    units_short = Column(String)
    seasonal_adjustment = Column(String)
    seasonal_adjustment_short = Column(String)
    last_updated = Column(String)
    popularity = Column(Integer, default=0)
    group_popularity = Column(Integer, default=0)
    notes = Column(Text)
    
    # FRED API fields
    realtime_start = Column(String)
    realtime_end = Column(String)
    observation_start = Column(String)
    observation_end = Column(String)
    
    # Foreign key to release
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    release = relationship("Release", back_populates="series")
    observations = relationship("Observation", back_populates="series")

class Observation(Base):
    """FRED Observation model"""
    __tablename__ = "observations"
    
    id = Column(Integer, primary_key=True, index=True)
    series_id = Column(String, ForeignKey("series.id"), nullable=False, index=True)
    date = Column(String, nullable=False, index=True)
    value = Column(String)  # Store as string to handle "." values
    realtime_start = Column(String)
    realtime_end = Column(String)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    series = relationship("Series", back_populates="observations")
    
    # Composite index for efficient queries
    __table_args__ = (
        {"sqlite_autoincrement": True}
    )

class CacheMetadata(Base):
    """Cache metadata for tracking data freshness"""
    __tablename__ = "cache_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String, unique=True, nullable=False, index=True)
    cache_type = Column(String, nullable=False)  # 'releases', 'series', 'observations'
    last_fetched = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime)
    data_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

# Database operations class
class FREDDatabase:
    def __init__(self):
        self.async_session = AsyncSessionLocal
    
    async def get_session(self):
        """Get async database session"""
        async with self.async_session() as session:
            yield session
    
    async def init_db(self):
        """Initialize database tables"""
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    async def get_releases(self, limit: int = 50):
        """Get cached releases"""
        async with self.async_session() as session:
            from sqlalchemy import select
            stmt = select(Release).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def store_releases(self, releases_data: list):
        """Store releases in database"""
        async with self.async_session() as session:
            try:
                for release_data in releases_data:
                    # Check if release exists
                    from sqlalchemy import select
                    stmt = select(Release).where(Release.id == release_data['id'])
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    if existing:
                        # Update existing
                        for key, value in release_data.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        existing.updated_at = datetime.now(timezone.utc)
                    else:
                        # Create new
                        release = Release(**release_data)
                        session.add(release)
                
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                print(f"Error storing releases: {e}")
                return False
    
    async def get_series(self, release_id: int = None, limit: int = 50):
        """Get cached series"""
        async with self.async_session() as session:
            from sqlalchemy import select
            stmt = select(Series)
            if release_id:
                stmt = stmt.where(Series.release_id == release_id)
            stmt = stmt.limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def store_series(self, series_data: list, release_id: int = None):
        """Store series in database"""
        async with self.async_session() as session:
            try:
                for series_item in series_data:
                    # Check if series exists
                    from sqlalchemy import select
                    stmt = select(Series).where(Series.id == series_item['id'])
                    result = await session.execute(stmt)
                    existing = result.scalar_one_or_none()
                    
                    # Add release_id if provided
                    if release_id:
                        series_item['release_id'] = release_id
                    
                    if existing:
                        # Update existing
                        for key, value in series_item.items():
                            if hasattr(existing, key):
                                setattr(existing, key, value)
                        existing.updated_at = datetime.now(timezone.utc)
                    else:
                        # Create new
                        series = Series(**series_item)
                        session.add(series)
                
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                print(f"Error storing series: {e}")
                return False
    
    async def get_observations(self, series_id: str, limit: int = 1000):
        """Get cached observations for a series"""
        async with self.async_session() as session:
            from sqlalchemy import select, desc
            stmt = select(Observation).where(
                Observation.series_id == series_id
            ).order_by(desc(Observation.date)).limit(limit)
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def store_observations(self, observations_data: list, series_id: str):
        """Store observations in database"""
        async with self.async_session() as session:
            try:
                # Delete existing observations for this series to avoid duplicates
                from sqlalchemy import delete
                delete_stmt = delete(Observation).where(Observation.series_id == series_id)
                await session.execute(delete_stmt)
                
                # Insert new observations
                for obs_data in observations_data:
                    obs_data['series_id'] = series_id
                    observation = Observation(**obs_data)
                    session.add(observation)
                
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                print(f"Error storing observations: {e}")
                return False
    
    async def update_cache_metadata(self, cache_key: str, cache_type: str, data_count: int = 0, expires_hours: int = 24):
        """Update cache metadata"""
        async with self.async_session() as session:
            try:
                from sqlalchemy import select
                from datetime import timedelta
                
                stmt = select(CacheMetadata).where(CacheMetadata.cache_key == cache_key)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                
                now = datetime.now(timezone.utc)
                expires_at = now + timedelta(hours=expires_hours)
                
                if existing:
                    existing.last_fetched = now
                    existing.expires_at = expires_at
                    existing.data_count = data_count
                    existing.updated_at = now
                else:
                    metadata = CacheMetadata(
                        cache_key=cache_key,
                        cache_type=cache_type,
                        last_fetched=now,
                        expires_at=expires_at,
                        data_count=data_count
                    )
                    session.add(metadata)
                
                await session.commit()
                return True
            except Exception as e:
                await session.rollback()
                print(f"Error updating cache metadata: {e}")
                return False
    
    async def is_cache_valid(self, cache_key: str):
        """Check if cache is still valid"""
        async with self.async_session() as session:
            from sqlalchemy import select
            stmt = select(CacheMetadata).where(CacheMetadata.cache_key == cache_key)
            result = await session.execute(stmt)
            metadata = result.scalar_one_or_none()
            
            if not metadata:
                return False
            
            now = datetime.now(timezone.utc)
            # Ensure expires_at is timezone-aware
            expires_at = metadata.expires_at
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            return expires_at > now
    
    async def get_database_stats(self):
        """Get database statistics"""
        async with self.async_session() as session:
            from sqlalchemy import select, func
            
            # Count records in each table
            releases_count = await session.execute(select(func.count(Release.id)))
            series_count = await session.execute(select(func.count(Series.id)))
            observations_count = await session.execute(select(func.count(Observation.id)))
            cache_count = await session.execute(select(func.count(CacheMetadata.id)))
            
            return {
                "releases": releases_count.scalar(),
                "series": series_count.scalar(),
                "observations": observations_count.scalar(),
                "cache_entries": cache_count.scalar(),
                "database_file": "fred_data.db",
                "database_exists": os.path.exists("fred_data.db")
            }

# Initialize database function
def init_database():
    """Initialize database synchronously"""
    Base.metadata.create_all(bind=sync_engine)
    print("✅ Database initialized successfully")

# Global database instance
db = FREDDatabase()

if __name__ == "__main__":
    # Initialize database when run directly
    init_database()