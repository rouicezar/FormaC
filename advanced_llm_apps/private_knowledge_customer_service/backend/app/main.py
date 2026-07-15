from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.ask import router as ask_router
from app.api.scans import router as scans_router
from app.api.search import router as search_router
from app.config import get_settings
from app.customer_service.answers import AskService
from app.ingestion.service import ScanService
from app.retrieval.search_service import OriginalSearchService
from app.runtime import ApplicationRuntime, build_runtime


DependencyStatus = Literal["ok", "not_configured", "not_started"]


class HealthResponse(BaseModel):
    service: DependencyStatus
    database: DependencyStatus
    scheduler: DependencyStatus
    embedding: DependencyStatus
    model: DependencyStatus
    feishu: DependencyStatus


def create_app(
    scan_service: ScanService | None = None,
    search_service: OriginalSearchService | None = None,
    ask_service: AskService | None = None,
    *,
    auto_configure: bool = False,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime: ApplicationRuntime | None = None
        if auto_configure:
            runtime = build_runtime(get_settings())
            app.state.runtime = runtime
            app.state.scan_service = runtime.scan_service
            app.state.search_service = runtime.search_service
            app.state.ask_service = runtime.ask_service
        try:
            yield
        finally:
            if runtime:
                runtime.close()

    app = FastAPI(title="私有知识库客服系统", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5177",
            "http://127.0.0.1:5177",
        ],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )
    app.state.scan_service = scan_service
    app.state.search_service = search_service
    app.state.ask_service = ask_service
    app.include_router(scans_router)
    app.include_router(search_router)
    app.include_router(ask_router)

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        knowledge_ready = app.state.scan_service is not None
        answer_ready = app.state.ask_service is not None
        return HealthResponse(
            service="ok",
            database="ok" if knowledge_ready else "not_configured",
            scheduler="not_started",
            embedding="ok" if knowledge_ready else "not_configured",
            model="ok" if answer_ready else "not_configured",
            feishu="not_configured",
        )

    return app


app = create_app(auto_configure=True)
