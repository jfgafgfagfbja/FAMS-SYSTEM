"""Schema Pydantic - nhom locations (tach tu app/schemas.py cua ban goc)."""
from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["LocationCreate", "LocationUpdate", "LocationOut", "RoomCreate", "RoomUpdate", "RoomOut"]


# ---- Dia diem diem danh ----
class LocationCreate(BaseModel):
    code: str
    name: str
    latitude: float
    longitude: float
    radius_m: float = 150.0
    is_default: bool = False

    @model_validator(mode="after")
    def _valid_coordinates(self):
        if not -90 <= self.latitude <= 90 or not -180 <= self.longitude <= 180:
            raise ValueError("Toa do khong hop le")
        if not 10 <= self.radius_m <= 5000:
            raise ValueError("Ban kinh phai tu 10 den 5000 m")
        return self


class LocationUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_m: float | None = None
    is_default: bool | None = None

    @model_validator(mode="after")
    def _valid_coordinates(self):
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValueError("Vi do khong hop le")
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValueError("Kinh do khong hop le")
        if self.radius_m is not None and not 10 <= self.radius_m <= 5000:
            raise ValueError("Ban kinh phai tu 10 den 5000 m")
        return self


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    latitude: float
    longitude: float
    radius_m: float
    is_default: bool


# ---- Phong hoc ----
def _check_room_geo(obj):
    """Toa do phai di theo cap; ban kinh rieng cua phong bi chan duoi vi sai so GPS."""
    if (obj.latitude is None) != (obj.longitude is None):
        raise ValueError("Phai nhap ca vi do va kinh do, hoac de trong ca hai")
    if obj.latitude is not None and not -90 <= obj.latitude <= 90:
        raise ValueError("Vi do khong hop le")
    if obj.longitude is not None and not -180 <= obj.longitude <= 180:
        raise ValueError("Kinh do khong hop le")
    if obj.radius_m is not None and not 10 <= obj.radius_m <= 5000:
        raise ValueError("Ban kinh phai tu 10 den 5000 m")
    if obj.floor is not None and not -5 <= obj.floor <= 100:
        raise ValueError("Tang khong hop le")
    if obj.capacity is not None and not 1 <= obj.capacity <= 2000:
        raise ValueError("Suc chua phai tu 1 den 2000")
    return obj


class RoomCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=255)
    location_id: int
    building: str | None = None
    floor: int | None = None
    capacity: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_m: float | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def _valid(self):
        return _check_room_geo(self)


class RoomUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=30)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location_id: int | None = None
    building: str | None = None
    floor: int | None = None
    capacity: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_m: float | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _valid(self):
        return _check_room_geo(self)


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    location_id: int
    location_name: str | None = None
    building: str | None = None
    floor: int | None = None
    capacity: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_m: float | None = None
    is_active: bool
    # Ban kinh thuc su duoc ap dung khi doi chieu (da nang len muc san).
    effective_radius_m: float | None = None
    schedule_count: int = 0
