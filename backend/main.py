import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.config import FRONTEND_DIR, UPLOADS_DIR
from backend.db.database import init_db
from backend.routers import product_router, batch_router, inspection_router, dashboard_router, expiry_router

app = FastAPI(
    title="AI Food Quality & Risk Detection System",
    description="Intelligent Food Quality, Safety, Risk Detection & OCR Verification System for F&B Manufacturing (Internship MVP)",
    version="1.0.0"
)

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database on Startup
@app.on_event("startup")
def startup_event():
    init_db()

# Register Routers
app.include_router(product_router.router)
app.include_router(batch_router.router)
app.include_router(inspection_router.router)
app.include_router(dashboard_router.router)
app.include_router(expiry_router.router)


# Mount Uploads directory
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Mount Frontend static files
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
def read_root():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "AI Food Quality System Backend API is active."}

# Part U API Endpoints Aliases
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.db.database import get_db
from backend.routers.inspection_router import get_inspections, get_active_alerts

@app.get("/api/inspections")
def get_inspections_alias(
    batch_id: int = None,
    status: str = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    return get_inspections(batch_id=batch_id, status=status, limit=limit, db=db)

@app.get("/api/alerts")
def get_alerts_alias(db: Session = Depends(get_db)):
    return get_active_alerts(db=db)

