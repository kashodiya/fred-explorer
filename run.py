#!/usr/bin/env python3
"""
FRED Explorer Startup Script
"""

import uvicorn

if __name__ == "__main__":
    print("🚀 Starting FRED Explorer...")
    print("📊 Access the application at: http://localhost:8888")
    print("🔗 API documentation at: http://localhost:8888/docs")
    print("⏹️  Press Ctrl+C to stop the server")
    print()
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8888,
        reload=True,
        log_level="info"
    )