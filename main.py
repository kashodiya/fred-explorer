#!/usr/bin/env python3
"""
FRED Explorer FastAPI Backend with SQLite Caching
Serves Vue.js frontend and provides cached FRED API endpoints
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from fred_api_cached import FREDAPICached
from database import init_database

app = FastAPI(title="FRED Explorer", description="Federal Reserve Economic Data Explorer with SQLite Caching")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()

# Initialize FRED API client with caching
try:
    fred_client = FREDAPICached()
except ValueError as e:
    print(f"Warning: FRED API not configured - {e}")
    fred_client = None

# Pydantic models for request/response
class SeriesRequest(BaseModel):
    series_id: str
    limit: Optional[int] = 100
    observation_start: Optional[str] = None
    observation_end: Optional[str] = None
    force_refresh: Optional[bool] = False

class ReleaseRequest(BaseModel):
    release_id: int
    series_limit: Optional[int] = 10
    obs_limit: Optional[int] = 50
    force_refresh: Optional[bool] = False

# API Routes
@app.get("/api/releases")
async def get_releases(
    limit: int = Query(20, description="Number of releases to return"),
    force_refresh: bool = Query(False, description="Force refresh from API, bypass cache")
):
    """Get list of available FRED releases (cached)"""
    if not fred_client:
        raise HTTPException(status_code=503, detail="FRED API not configured")
    
    try:
        data = await fred_client.get_releases_cached(limit=limit, force_refresh=force_refresh)
        if not data:
            raise HTTPException(status_code=404, detail="No releases found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/release/{release_id}")
async def get_release_info(
    release_id: int,
    force_refresh: bool = Query(False, description="Force refresh from API, bypass cache")
):
    """Get information about a specific release (cached)"""
    if not fred_client:
        raise HTTPException(status_code=503, detail="FRED API not configured")
    
    try:
        data = await fred_client.get_release_info_cached(release_id, force_refresh=force_refresh)
        if not data:
            raise HTTPException(status_code=404, detail="Release not found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/release/{release_id}/series")
async def get_release_series(
    release_id: int, 
    limit: int = Query(20, description="Number of series to return"),
    force_refresh: bool = Query(False, description="Force refresh from API, bypass cache")
):
    """Get series in a release (cached)"""
    if not fred_client:
        raise HTTPException(status_code=503, detail="FRED API not configured")
    
    try:
        data = await fred_client.get_release_series_cached(release_id, limit=limit, force_refresh=force_refresh)
        if not data:
            raise HTTPException(status_code=404, detail="No series found for this release")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/release/observations")
async def get_release_observations(request: ReleaseRequest):
    """Get observations for all series in a release (cached)"""
    if not fred_client:
        raise HTTPException(status_code=503, detail="FRED API not configured")
    
    try:
        data = await fred_client.get_release_observations_cached(
            release_id=request.release_id,
            series_limit=request.series_limit,
            obs_limit=request.obs_limit,
            force_refresh=request.force_refresh
        )
        if not data:
            raise HTTPException(status_code=404, detail="No observations found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/series/observations")
async def get_series_observations(request: SeriesRequest):
    """Get observations for a specific series (cached)"""
    if not fred_client:
        raise HTTPException(status_code=503, detail="FRED API not configured")
    
    try:
        kwargs = {}
        if request.observation_start:
            kwargs['observation_start'] = request.observation_start
        if request.observation_end:
            kwargs['observation_end'] = request.observation_end
            
        data = await fred_client.get_series_observations_cached(
            series_id=request.series_id,
            limit=request.limit,
            force_refresh=request.force_refresh,
            **kwargs
        )
        if not data:
            raise HTTPException(status_code=404, detail="No observations found")
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/database/stats")
async def get_database_stats():
    """Get database statistics and cache information"""
    if not fred_client:
        raise HTTPException(status_code=503, detail="FRED API not configured")
    
    try:
        stats = await fred_client.get_database_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/database/clear-cache")
async def clear_cache(cache_type: Optional[str] = None):
    """Clear database cache"""
    if not fred_client:
        raise HTTPException(status_code=503, detail="FRED API not configured")
    
    try:
        result = await fred_client.clear_cache(cache_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint with database status"""
    db_stats = None
    if fred_client:
        try:
            db_stats = await fred_client.get_database_stats()
        except Exception as e:
            db_stats = {"error": str(e)}
    
    return {
        "status": "healthy",
        "fred_api_configured": fred_client is not None,
        "database": db_stats
    }

# Serve the Vue.js app
@app.get("/")
async def serve_app():
    """Serve the main Vue.js application"""
    return FileResponse("static/index.html")

# Mount static files (for any additional assets)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)