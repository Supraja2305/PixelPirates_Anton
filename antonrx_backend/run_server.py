#!/usr/bin/env python3
"""
Fast API Server Startup Script for Anton RX Backend
Run this with: python run_server.py
"""

import os
import sys
import uvicorn

# Set the working directory to parent directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(backend_dir)
os.chdir(parent_dir)

# Add parent directory to Python path so antonrx_backend can be imported as a module
sys.path.insert(0, parent_dir)

if __name__ == "__main__":
    print("🚀 Starting Anton RX Backend Server...")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🐍 Python path: {sys.path[0]}")
    print(f"📍 Starting server on http://0.0.0.0:8000")
    print(f"📚 API Docs: http://localhost:8000/docs")
    print(f"🏥 Health Check: http://localhost:8000/health")
    
    uvicorn.run(
        "antonrx_backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
