"""Controller bao cao, thong ke chuyen can - PH8."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app import schemas
from app.api.deps import CurrentUser, DbSession, require_roles
from app.core.authz import OVERVIEW_VIEWERS
from app.db import models
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/attendance/warnings")
def attendance_warnings(class_id: int, db: DbSession, user: CurrentUser):
    """Danh sach SV vuot nguong vang (absent / tong buoi da hoc >= ABSENCE_WARN_RATIO).
    excused khong tinh la vang."""
    return report_service.attendance_warnings(db, user, class_id)


@router.get("/attendance/export")
def export_attendance(class_id: int, semester: str, db: DbSession, user: CurrentUser):
    """File Excel diem danh: sheet 1 ma tran SV x buoi hoc, sheet 2 thong ke lop."""
    excel = report_service.export_attendance(db, user, class_id, semester)
    return StreamingResponse(
        excel.content, media_type=excel.media_type,
        headers={"Content-Disposition": f'attachment; filename="{excel.filename}"'},
    )


@router.get("/overview", response_model=schemas.OverviewOut)
def attendance_overview(db: DbSession, semester: str | None = None,
                        user: models.User = Depends(require_roles(*OVERVIEW_VIEWERS))):
    """Thong ke tong hop theo hoc ky, chia theo Khoa (chi so lieu, khong ten/anh)."""
    return report_service.overview(db, user, semester)


@router.get("/attendance/{class_id}")
def class_attendance(class_id: int, db: DbSession, user: CurrentUser):
    """Thong ke chuyen can theo lop: ti le vang tung SV + canh bao."""
    return report_service.class_attendance(db, user, class_id)


@router.get("/my-attendance")
def my_attendance(db: DbSession, user: CurrentUser):
    """Sinh vien tu xem tom tat chuyen can theo tung lop (chi tinh phien da dong)."""
    return report_service.my_attendance_summary(db, user)
