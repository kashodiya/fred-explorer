#!/usr/bin/env python3
"""
FRED API with SQLite Caching - Enhanced Implementation
Combines FRED API access with local SQLite caching for improved performance
"""

import os
import requests
import json
import asyncio
from datetime import datetime, timezone
from dotenv import load_dotenv
from database import FREDDatabase, init_database

# Load environment variables
load_dotenv()

class FREDAPICached:
    def __init__(self):
        self.api_key = os.getenv('FRED_API_KEY')
        self.base_url = os.getenv('FRED_BASE_URL', 'https://api.stlouisfed.org/fred')
        self.db = FREDDatabase()
        
        if not self.api_key:
            raise ValueError("FRED_API_KEY not found in environment variables. Check your .env file.")
        
        # Initialize database
        init_database()
    
    def make_request(self, endpoint, params=None):
        """Make a request to the FRED API"""
        if params is None:
            params = {}
        
        params['api_key'] = self.api_key
        params.setdefault('file_type', 'json')
        
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, params=params)
        
        print(f"Request: {endpoint}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.text}")
            return None
    
    async def get_releases_cached(self, limit=50, force_refresh=False):
        """Get releases with caching"""
        cache_key = f"releases_limit_{limit}"
        
        # Check cache first (unless force refresh)
        if not force_refresh and await self.db.is_cache_valid(cache_key):
            print("📦 Loading releases from cache...")
            cached_releases = await self.db.get_releases(limit)
            if cached_releases:
                return {
                    'releases': [self._release_to_dict(r) for r in cached_releases],
                    'count': len(cached_releases),
                    'cached': True
                }
        
        # Fetch from API
        print("🌐 Fetching releases from FRED API...")
        data = self.make_request('releases', {'limit': limit})
        if not data:
            return None
        
        # Store in database
        releases_data = data.get('releases', [])
        if releases_data:
            await self.db.store_releases(releases_data)
            await self.db.update_cache_metadata(cache_key, 'releases', len(releases_data))
        
        data['cached'] = False
        return data
    
    async def get_release_info_cached(self, release_id, force_refresh=False):
        """Get release info with caching"""
        cache_key = f"release_{release_id}"
        
        # Check cache first
        if not force_refresh and await self.db.is_cache_valid(cache_key):
            print(f"📦 Loading release {release_id} from cache...")
            cached_releases = await self.db.get_releases(1)
            for release in cached_releases:
                if release.id == release_id:
                    return {
                        'releases': [self._release_to_dict(release)],
                        'cached': True
                    }
        
        # Fetch from API
        print(f"🌐 Fetching release {release_id} from FRED API...")
        data = self.make_request('release', {'release_id': release_id})
        if not data:
            return None
        
        # Store in database
        releases_data = data.get('releases', [])
        if releases_data:
            await self.db.store_releases(releases_data)
            await self.db.update_cache_metadata(cache_key, 'release', 1)
        
        data['cached'] = False
        return data
    
    async def get_release_series_cached(self, release_id, limit=50, force_refresh=False):
        """Get release series with caching"""
        cache_key = f"series_release_{release_id}_limit_{limit}"
        
        # Check cache first
        if not force_refresh and await self.db.is_cache_valid(cache_key):
            print(f"📦 Loading series for release {release_id} from cache...")
            cached_series = await self.db.get_series(release_id, limit)
            if cached_series:
                return {
                    'seriess': [self._series_to_dict(s) for s in cached_series],
                    'count': len(cached_series),
                    'cached': True
                }
        
        # Fetch from API
        print(f"🌐 Fetching series for release {release_id} from FRED API...")
        data = self.make_request('release/series', {
            'release_id': release_id,
            'limit': limit
        })
        if not data:
            return None
        
        # Store in database
        series_data = data.get('seriess', [])
        if series_data:
            await self.db.store_series(series_data, release_id)
            await self.db.update_cache_metadata(cache_key, 'series', len(series_data))
        
        data['cached'] = False
        return data
    
    async def get_series_observations_cached(self, series_id, limit=1000, force_refresh=False, **kwargs):
        """Get series observations with caching"""
        cache_key = f"observations_{series_id}_limit_{limit}"
        
        # Add date parameters to cache key if provided
        for param in ['observation_start', 'observation_end']:
            if param in kwargs:
                cache_key += f"_{param}_{kwargs[param]}"
        
        # Check cache first
        if not force_refresh and await self.db.is_cache_valid(cache_key):
            print(f"📦 Loading observations for {series_id} from cache...")
            cached_obs = await self.db.get_observations(series_id, limit)
            if cached_obs:
                return {
                    'observations': [self._observation_to_dict(o) for o in cached_obs],
                    'count': len(cached_obs),
                    'cached': True
                }
        
        # Fetch from API
        print(f"🌐 Fetching observations for {series_id} from FRED API...")
        params = {
            'series_id': series_id,
            'limit': limit
        }
        
        # Add optional date parameters
        for param in ['realtime_start', 'realtime_end', 'observation_start', 'observation_end']:
            if param in kwargs:
                params[param] = kwargs[param]
        
        data = self.make_request('series/observations', params)
        if not data:
            return None
        
        # Store in database
        observations_data = data.get('observations', [])
        if observations_data:
            await self.db.store_observations(observations_data, series_id)
            await self.db.update_cache_metadata(cache_key, 'observations', len(observations_data))
        
        data['cached'] = False
        return data
    
    async def get_release_observations_cached(self, release_id, series_limit=10, obs_limit=50, force_refresh=False):
        """
        Enhanced workaround for release observations with caching
        """
        print(f"\n=== Getting Release Observations with Caching (Release ID: {release_id}) ===")
        
        # Get release info
        release_info = await self.get_release_info_cached(release_id, force_refresh)
        if not release_info:
            return None
        
        # Get series in the release
        series_data = await self.get_release_series_cached(release_id, series_limit, force_refresh)
        if not series_data:
            return None
        
        # Build combined response
        result = {
            'release': release_info['releases'][0],
            'series': [],
            'metadata': {
                'total_series_in_release': series_data.get('count', 0),
                'series_returned': len(series_data.get('seriess', [])),
                'observations_per_series': obs_limit,
                'cached': series_data.get('cached', False)
            }
        }
        
        # Get observations for each series
        for series in series_data['seriess']:
            series_id = series['id']
            print(f"  Getting observations for: {series_id}")
            
            obs_data = await self.get_series_observations_cached(series_id, obs_limit, force_refresh)
            if obs_data and 'observations' in obs_data:
                series_with_obs = series.copy()
                series_with_obs['observations'] = obs_data['observations']
                series_with_obs['cached'] = obs_data.get('cached', False)
                result['series'].append(series_with_obs)
        
        return result
    
    def _release_to_dict(self, release):
        """Convert Release model to dictionary"""
        return {
            'id': release.id,
            'name': release.name,
            'press_release': release.press_release,
            'link': release.link,
            'notes': release.notes,
            'realtime_start': release.realtime_start,
            'realtime_end': release.realtime_end
        }
    
    def _series_to_dict(self, series):
        """Convert Series model to dictionary"""
        return {
            'id': series.id,
            'title': series.title,
            'frequency': series.frequency,
            'frequency_short': series.frequency_short,
            'units': series.units,
            'units_short': series.units_short,
            'seasonal_adjustment': series.seasonal_adjustment,
            'seasonal_adjustment_short': series.seasonal_adjustment_short,
            'last_updated': series.last_updated,
            'popularity': series.popularity,
            'group_popularity': series.group_popularity,
            'notes': series.notes,
            'realtime_start': series.realtime_start,
            'realtime_end': series.realtime_end,
            'observation_start': series.observation_start,
            'observation_end': series.observation_end
        }
    
    def _observation_to_dict(self, observation):
        """Convert Observation model to dictionary"""
        return {
            'date': observation.date,
            'value': observation.value,
            'realtime_start': observation.realtime_start,
            'realtime_end': observation.realtime_end
        }
    
    async def get_database_stats(self):
        """Get database statistics"""
        return await self.db.get_database_stats()
    
    async def clear_cache(self, cache_type=None):
        """Clear cache data"""
        # This would implement cache clearing logic
        # For now, just return a placeholder
        return {"message": "Cache clearing not implemented yet"}

async def main():
    """Test the cached FRED API"""
    try:
        # Initialize API client
        fred = FREDAPICached()
        print(f"✅ FRED API with caching initialized successfully")
        print()
        
        # Test 1: Get available releases (cached)
        print("1. Getting available releases (with caching)...")
        releases = await fred.get_releases_cached(limit=5)
        if releases:
            print(f"Found {releases.get('count', 0)} releases (Cached: {releases.get('cached', False)})")
            for release in releases['releases']:
                print(f"  {release['id']}: {release['name']}")
        print()
        
        # Test 2: Get Consumer Price Index data (cached)
        release_id = 10
        print(f"2. Testing with Consumer Price Index (ID: {release_id}) - with caching")
        
        cpi_data = await fred.get_release_observations_cached(
            release_id=release_id,
            series_limit=3,
            obs_limit=5
        )
        
        if cpi_data:
            print(f"\nRelease: {cpi_data['release']['name']}")
            print(f"Total series in release: {cpi_data['metadata']['total_series_in_release']}")
            print(f"Series with observations: {len(cpi_data['series'])}")
            print(f"Data cached: {cpi_data['metadata']['cached']}")
            
            # Show sample data
            for i, series in enumerate(cpi_data['series'][:2]):
                print(f"\nSeries {i+1}: {series['id']} (Cached: {series.get('cached', False)})")
                print(f"  Title: {series['title'][:60]}...")
                print(f"  Frequency: {series['frequency']}")
                print(f"  Recent observations:")
                
                obs = series.get('observations', [])
                for observation in obs[-3:]:  # Last 3 observations
                    print(f"    {observation['date']}: {observation['value']}")
        
        # Test 3: Database statistics
        print("\n3. Database Statistics:")
        stats = await fred.get_database_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*50)
        print("✅ All cached tests completed successfully!")
        print("💡 Run again to see caching in action!")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nTo fix this:")
        print("1. Copy .env.example to .env")
        print("2. Add your FRED API key to the .env file")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())