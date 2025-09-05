from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

class StationBase(BaseModel):
    name: str
    lat: Optional[Decimal] = None
    long: Optional[Decimal] = None
    zone_number: Optional[int] = None
    is_interchange: bool = False
    platform_count: int = 1
    status: Optional[str] = "active"

class StationCreate(StationBase):
    line_id: int

class StationUpdate(BaseModel):
    name: Optional[str] = None
    lat: Optional[Decimal] = None
    long: Optional[Decimal] = None
    zone_number: Optional[int] = None
    is_interchange: Optional[bool] = None
    platform_count: Optional[int] = None
    status: Optional[str] = None

class StationFacilityBase(BaseModel):
    facility_type: str
    is_available: bool = True
    location_description: Optional[str] = None

class StationFacility(StationFacilityBase):
    id: int
    station_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class TrainLineInfo(BaseModel):
    id: int
    name: str
    color: Optional[str] = None
    company_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class TransferPoint(BaseModel):
    id: int
    station_b_id: int
    station_b_name: str
    walking_time_minutes: int
    walking_distance_meters: Optional[int] = None
    transfer_fee: Decimal
    
    class Config:
        from_attributes = True

class Station(StationBase):
    id: int
    line_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class StationDetail(Station):
    line: Optional[TrainLineInfo] = None
    facilities: List[StationFacility] = []
    transfer_points: List[TransferPoint] = []

class StationSearch(BaseModel):
    query: Optional[str] = None
    line_id: Optional[int] = None
    is_interchange: Optional[bool] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    radius_km: Optional[float] = 1.0

class StationSearchResult(BaseModel):
    stations: List[StationDetail]
    total: int
    page: int
    per_page: int