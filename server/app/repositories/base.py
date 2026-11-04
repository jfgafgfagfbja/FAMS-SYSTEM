"""Thanh phan dung chung cho tang truy cap du lieu.

Repository = cac ham truy van SQLAlchemy theo bang/nhom bang, nhan Session cua request qua
tham so (khong tu mo phien, khong commit). Commit la viec cua service - mot use case mot
giao dich, dung voi diem commit cua ban goc.
"""
from dataclasses import dataclass
from typing import Generic, TypeVar

from sqlalchemy.orm import Query

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    """Mot trang ket qua + tong so ban ghi khop bo loc (tra ve client qua X-Total-Count)."""
    items: list[T]
    total: int


def paginate(query: Query, *order_by, limit: int | None, offset: int = 0) -> Page:
    """Dem tong truoc khi phan trang; khong truyen limit -> lay het tu offset."""
    total = query.count()
    query = query.order_by(*order_by).offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return Page(items=query.all(), total=total)
