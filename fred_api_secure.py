#!/usr/bin/env python3
"""
FRED API Release Observations - Secure Implementation
Uses environment variables for API key management
"""

import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FREDAPISecure:
    def __init__(self):
        self.api_key = os.getenv('FRED_API_KEY')
        self.base_url = os.getenv('FRED_BASE_URL', 'https://api.stlouisfed.org/fred')
        
        if not self.api_key:
            raise ValueError("FRED_API_KEY not found in environment variables. Check your .env file.")
    
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
    
    def get_releases(self, limit=10):
        """Get list of available releases"""
        return self.make_request('releases', {'limit': limit})
    
    def get_release_info(self, release_id):
        """Get information about a specific release"""
        return self.make_request('release', {'release_id': release_id})
    
    def get_release_series(self, release_id, limit=10):
        """Get series in a release"""
        return self.make_request('release/series', {
            'release_id': release_id,
            'limit': limit
        })
    
    def get_series_observations(self, series_id, limit=10, **kwargs):
        """Get observations for a specific series"""
        params = {
            'series_id': series_id,
            'limit': limit
        }
        
        # Add optional date parameters
        for param in ['realtime_start', 'realtime_end', 'observation_start', 'observation_end']:
            if param in kwargs:
                params[param] = kwargs[param]
        
        return self.make_request('series/observations', params)
    
    def get_release_observations_workaround(self, release_id, series_limit=5, obs_limit=10):
        """
        Workaround for the non-functional /release/observations endpoint
        Gets all observations for series in a release
        """
        print(f"\n=== Getting Release Observations (Release ID: {release_id}) ===")
        
        # Get release info
        release_info = self.get_release_info(release_id)
        if not release_info:
            return None
        
        # Get series in the release
        series_data = self.get_release_series(release_id, limit=series_limit)
        if not series_data:
            return None
        
        # Build combined response
        result = {
            'release': release_info['releases'][0],
            'series': [],
            'metadata': {
                'total_series_in_release': series_data.get('count', 0),
                'series_returned': len(series_data.get('seriess', [])),
                'observations_per_series': obs_limit
            }
        }
        
        # Get observations for each series
        for series in series_data['seriess']:
            series_id = series['id']
            print(f"  Getting observations for: {series_id}")
            
            obs_data = self.get_series_observations(series_id, limit=obs_limit)
            if obs_data and 'observations' in obs_data:
                series_with_obs = series.copy()
                series_with_obs['observations'] = obs_data['observations']
                result['series'].append(series_with_obs)
        
        return result

def main():
    try:
        # Initialize API client
        fred = FREDAPISecure()
        print(f"✅ FRED API initialized successfully")
        print(f"Base URL: {fred.base_url}")
        print(f"API Key: {fred.api_key[:8]}...{fred.api_key[-4:]}")  # Masked for security
        print()
        
        # Test 1: Get available releases
        print("1. Getting available releases...")
        releases = fred.get_releases(limit=5)
        if releases:
            print(f"Found {releases.get('count', 0)} total releases")
            for release in releases['releases']:
                print(f"  {release['id']}: {release['name']}")
        print()
        
        # Test 2: Get Consumer Price Index data
        release_id = 10
        print(f"2. Testing with Consumer Price Index (ID: {release_id})")
        
        # Get release observations using workaround
        cpi_data = fred.get_release_observations_workaround(
            release_id=release_id,
            series_limit=3,
            obs_limit=5
        )
        
        if cpi_data:
            print(f"\nRelease: {cpi_data['release']['name']}")
            print(f"Total series in release: {cpi_data['metadata']['total_series_in_release']}")
            print(f"Series with observations: {len(cpi_data['series'])}")
            
            # Show sample data
            for i, series in enumerate(cpi_data['series'][:2]):
                print(f"\nSeries {i+1}: {series['id']}")
                print(f"  Title: {series['title'][:60]}...")
                print(f"  Frequency: {series['frequency']}")
                print(f"  Recent observations:")
                
                obs = series.get('observations', [])
                for observation in obs[-3:]:  # Last 3 observations
                    print(f"    {observation['date']}: {observation['value']}")
        
        print("\n" + "="*50)
        print("✅ All tests completed successfully!")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nTo fix this:")
        print("1. Copy .env.example to .env")
        print("2. Add your FRED API key to the .env file")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()