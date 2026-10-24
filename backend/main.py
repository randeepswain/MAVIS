import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import settings
from backend.database.session import init_db, AsyncSessionLocal
from backend.services.seed_data import seed_database
from backend.services.redis_service import redis_service

from backend.api.auth import router as auth_router
from backend.api.scheduling_routes import router as scheduling_router
from backend.api.doctor_routes import router as doctor_router
from backend.api.admin_routes import router as admin_router
from backend.api.voice import router as voice_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("mavis.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting MAVIS - Multi-Agent Voice Intake System backend...")
    await init_db()
    await redis_service.initialize()
    
    # Seed initial hospital data
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    
    logger.info("MAVIS backend initialization complete. Ready for telephony and web portal traffic.")
    yield
    # Shutdown
    logger.info("Shutting down MAVIS backend services...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Multi-Agent Voice Intake & Hospital Management System (Batch 45, Ramaiah University of Applied Sciences)",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router, prefix=settings.API_PREFIX)
app.include_router(scheduling_router, prefix=settings.API_PREFIX)
app.include_router(doctor_router, prefix=settings.API_PREFIX)
app.include_router(admin_router, prefix=settings.API_PREFIX)
app.include_router(voice_router, prefix=settings.API_PREFIX)

@app.get("/api/health")
async def health_check():
    return {
        "status": "HEALTHY",
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "layers": {
            "layer_1_telephony": "LiveKit / Faster-Whisper / Piper TTS Active",
            "layer_2_agents": "LangGraph F1 Triage / F4 Safety Gate / F3 Handoff Active",
            "layer_3_backend": "SQLAlchemy ACID / Redis Soft-Hold Active",
            "layer_4_portals": "Unified Patient, Doctor, Admin RBAC Active"
        }
    }

# Mount frontend static directory if exists
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    async def serve_frontend():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "MAVIS API is running. Build frontend in /frontend directory."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
