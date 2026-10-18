"""
Application Entry Point.
Delegates to the modular FastAPI application defined in app.main.
"""
import uvicorn
from app.main import app

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)