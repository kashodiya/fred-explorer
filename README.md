# FRED Explorer

A Python tool for exploring the Federal Reserve Economic Data (FRED) API, with a focus on release observations.

## Overview

This project provides a comprehensive study and working implementation for the FRED API Release Observations endpoint. While the documented `/release/observations` endpoint is non-functional, this tool provides a robust workaround.

## Quick Start

1. **Clone and setup:**
   ```bash
   git clone <your-repo-url>
   cd fred-explorer
   pip install -r requirements.txt
   ```

2. **Configure API key:**
   ```bash
   cp .env.example .env
   # Edit .env and add your FRED API key from https://fred.stlouisfed.org/docs/api/api_key.html
   ```

3. **Run the explorer:**
   ```bash
   python fred_api_secure.py
   ```

## Key Features

- ✅ **Secure API key management** using environment variables
- ✅ **Working release observations** via multi-endpoint workaround
- ✅ **Comprehensive error handling** and logging
- ✅ **Production-ready code** with proper security practices
- ✅ **Detailed documentation** of API findings and limitations

## API Findings

❌ **Issue**: The documented `/release/observations` endpoint returns 404 errors  
✅ **Solution**: 2-step workaround using `/release/series` + `/series/observations`

## Files

- `fred_api_secure.py` - Main implementation (recommended)
- `FRED_API_FINDINGS.md` - Concise technical findings
- `FRED_API_STUDY_SUMMARY.md` - Detailed analysis
- `.env.example` - Environment setup template
- `requirements.txt` - Python dependencies

## Usage Example

```python
from fred_api_secure import FREDAPISecure

# Initialize (reads API key from .env)
fred = FREDAPISecure()

# Get Consumer Price Index data with observations
cpi_data = fred.get_release_observations_workaround(
    release_id=10,  # Consumer Price Index
    series_limit=5,
    obs_limit=10
)

print(f"Release: {cpi_data['release']['name']}")
print(f"Series with observations: {len(cpi_data['series'])}")
```

## Security

- API keys stored in `.env` (git-ignored)
- Keys masked in console output
- No hardcoded credentials in source code

## Contributing

This project documents the current state of the FRED API and provides working alternatives. Contributions welcome for additional endpoints or improvements.