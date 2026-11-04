"""Phu thuoc dung chung cho cac controller (api/v1/endpoints).

    def handler(db: DbSession, user: CurrentUser): ...
    def handler(db: DbSession, user: models.User = Depends(require_roles(ROLE_ADMIN))): ...

Moi request dung MOT phien DB (get_db): service va repository nhan phien nay qua tham so,
khong tu mo phien rieng - nho vay nhat ky he thong (services/audit.py) gan dung nguoi thao tac
va moi thay doi nam trong cung giao dich cua request.
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.db import models
from app.db.database import get_db

DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[models.User, Depends(get_current_user)]

__all__ = ["DbSession", "CurrentUser", "get_db", "get_current_user", "require_roles"]
