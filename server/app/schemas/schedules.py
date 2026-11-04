"""Schema Pydantic - nhom schedules (tach tu app/schemas.py cua ban goc)."""
from datetime import date, time

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

__all__ = ["ScheduleCreate", "ScheduleUpdate", "ScheduleOut", "TodayScheduleOut", "ScheduleWithClassOut", "WeekSlotOut"]


def _check_weekday(v: int | None) -> int | None:
    if v is not None and not 0 <= v <= 6:
        raise ValueError("Thu trong tuan phai tu 0 (Thu 2) den 6 (Chu nhat)")
    return v


class ScheduleCreate(BaseModel):
    class_id: int
    weekday: int
    start_time: time
    end_time: time
    # Chon phong tu danh muc (room_id) la cach dung chinh; `room` dang chu chi con de
    # nhap tay cho phong chua kip dua vao danh muc.
    room_id: int | None = None
    room: str | None = None
    location_id: int | None = None

    @field_validator("weekday")
    @classmethod
    def _valid_weekday(cls, v: int | None) -> int | None:
        return _check_weekday(v)

    @model_validator(mode="after")
    def _valid(self):
        if self.start_time >= self.end_time:
            raise ValueError("Gio bat dau phai truoc gio ket thuc")
        if self.room_id is None and not (self.room or "").strip():
            raise ValueError("Phai chon phong hoc hoac nhap ten phong")
        return self


class ScheduleUpdate(BaseModel):
    weekday: int | None = None
    start_time: time | None = None
    end_time: time | None = None
    room_id: int | None = None
    room: str | None = None
    location_id: int | None = None

    @field_validator("weekday")
    @classmethod
    def _valid_weekday(cls, v: int | None) -> int | None:
        return _check_weekday(v)


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_id: int
    weekday: int
    start_time: time
    end_time: time
    room: str
    room_id: int | None = None
    room_name: str | None = None
    location_id: int | None = None


class TodayScheduleOut(BaseModel):
    """1 tiet hoc hom nay cua giang vien dang dang nhap."""
    schedule_id: int
    class_id: int
    class_code: str
    subject_name: str
    weekday: int
    start_time: time
    end_time: time
    room: str
    # Gio som nhat duoc mo phien (= start_time - EARLY_OPEN_MINUTES), tinh san o
    # backend de FE khong phai hardcode nguong cau hinh.
    open_from: time
    # Phien da mo hom nay cho lich nay (neu co) - FE vao thang phien thay vi mo lai.
    session_id: int | None = None
    session_status: str | None = None


class ScheduleWithClassOut(BaseModel):
    """1 lich hoc kem thong tin lop - dung cho trang quan tri lich hoc toan truong."""
    id: int
    class_id: int
    class_code: str
    subject_name: str
    weekday: int
    start_time: time
    end_time: time
    room: str
    room_id: int | None = None
    location_id: int | None = None
    location_name: str | None = None


class WeekSlotOut(BaseModel):
    """1 o lich trong tuan (ngay cu the), gop san trang thai phien/diem danh cho
    SV hoac GV dang dang nhap - dung cho trang lich tuan, tranh FE goi N+1."""
    date: date
    weekday: int
    schedule_id: int
    class_id: int
    class_code: str
    subject_name: str
    room: str
    start_time: time
    end_time: time
    session_id: int | None = None
    session_status: str | None = None  # None (chua mo phien) | open | closed
    # Gio som nhat duoc mo phien (= start_time - EARLY_OPEN_MINUTES) - GV dung de
    # biet nut "Mo phien" hop le tu luc nao ma khong phai hardcode nguong o FE.
    open_from: time | None = None
    my_status: str | None = None  # SV: trang thai diem danh cua chinh minh (neu co)
    present_count: int | None = None  # GV: so SV co mat khi phien da dong
    total_count: int | None = None  # GV: tong so SV ghi danh lop
    # Dia diem doi chieu GPS khi SV tu diem danh (rieng cua lich hoc hoac mac dinh cua truong).
    location_name: str | None = None
    location_radius_m: float | None = None
