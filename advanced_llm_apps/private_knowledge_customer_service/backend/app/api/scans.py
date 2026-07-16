from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.ingestion.service import ScanReport, ScanService


router = APIRouter(prefix="/admin/scans", tags=["scans"])


class ScanReportResponse(BaseModel):
    id: UUID
    trigger: str
    status: str
    added: int
    updated: int
    deleted: int
    failed: int
    skipped: int
    total: int
    processed: int
    current_path: str | None
    errors: list[dict[str, str]]

    @classmethod
    def from_report(cls, report: ScanReport) -> "ScanReportResponse":
        return cls(
            id=report.id,
            trigger=report.trigger,
            status=report.status,
            added=report.added,
            updated=report.updated,
            deleted=report.deleted,
            failed=report.failed,
            skipped=report.skipped,
            total=report.total,
            processed=report.processed,
            current_path=report.current_path,
            errors=report.errors,
        )


def get_scan_service(request: Request) -> ScanService:
    service = request.app.state.scan_service
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="扫描服务尚未配置",
        )
    return service


ScanServiceDependency = Annotated[ScanService, Depends(get_scan_service)]


@router.post("", response_model=ScanReportResponse, status_code=status.HTTP_202_ACCEPTED)
def start_manual_scan(
    background_tasks: BackgroundTasks,
    service: ScanServiceDependency,
) -> ScanReportResponse:
    try:
        report, started = service.start_scan(trigger="manual")
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if started:
        background_tasks.add_task(service.run_started_scan, report.id)
    return ScanReportResponse.from_report(report)


@router.get("/{run_id}", response_model=ScanReportResponse)
def get_scan(run_id: UUID, service: ScanServiceDependency) -> ScanReportResponse:
    report = service.get_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail="未找到扫描记录")
    return ScanReportResponse.from_report(report)
