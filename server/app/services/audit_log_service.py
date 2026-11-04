"""Tra cuu nhat ky he thong (PH9). Admin xem toan truong; Lanh dao Khoa chi xem cac thao tac
lien quan den Khoa minh (theo cot faculty_id ghi luc phat sinh - xem services/audit.py)."""
from datetime import date

from sqlalchemy.orm import Session

from app.core.authz import staff_unit_id
from app.db import models
from app.db.models import ROLE_FACULTY_LEADER
from app.repositories import audit_log_repository
from app.repositories.base import Page


def list_audit_logs(db: Session, user: models.User, *, q: str | None, action: str | None,
                    success: bool | None, date_from: date | None, date_to: date | None,
                    limit: int, offset: int) -> Page[models.AuditLog]:
    faculty_scope = None
    if user.role == ROLE_FACULTY_LEADER:
        unit_id = staff_unit_id(user, db)
        faculty_scope = unit_id if unit_id is not None else -1
    return audit_log_repository.search(db, faculty_scope=faculty_scope, q=q, action=action,
                                       success=success, date_from=date_from, date_to=date_to,
                                       limit=limit, offset=offset)
