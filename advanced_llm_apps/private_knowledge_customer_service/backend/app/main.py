from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from app.api.scans import router as scans_router
from app.ingestion.service import ScanService


DependencyStatus = Literal["ok", "not_configured", "not_started"]


class HealthResponse(BaseModel):
    service: DependencyStatus
    database: DependencyStatus
    scheduler: DependencyStatus
    embedding: DependencyStatus
    model: DependencyStatus
    feishu: DependencyStatus


def create_app(scan_service: ScanService | None = None) -> FastAPI:
    app = FastAPI(title="Private Knowledge Customer Service")
    app.state.scan_service = scan_service
    app.include_router(scans_router)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            service="ok",
            database="not_configured",
            scheduler="not_started",
            embedding="not_configured",
            model="not_configured",
            feishu="not_configured",
        )

    return app


app = create_app()
