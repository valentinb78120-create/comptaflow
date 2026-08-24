"""FastAPI application entry point."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, billing, invoices, cabinets, pcg
from app.core.config import get_settings

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(
    title="ComptaFlow API",
    description="OCR automatique de factures + export EBP/Sage pour cabinets comptables FR",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(invoices.router, prefix="/api/v1")
app.include_router(cabinets.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(pcg.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    """Liveness probe."""
    return {"status": "ok", "version": "0.1.0"}
