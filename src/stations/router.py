from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from src.database import get_db
from src.stations.schemas import StationDetail, StationSearchResult, StationSearch
from src.stations.service import StationService

router = APIRouter()

@router.get("/", response_model=StationSearchResult)
def get_stations(
    skip: int = Query(0, ge=0, description="Number of stations to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of stations to return"),
    query: Optional[str] = Query(None, description="Search by station name"),
    line_id: Optional[int] = Query(None, description="Filter by line ID"),
    is_interchange: Optional[bool] = Query(None, description="Filter interchange stations"),
    lat: Optional[float] = Query(None, description="Latitude for location-based search"),
    lng: Optional[float] = Query(None, description="Longitude for location-based search"),
    radius_km: Optional[float] = Query(1.0, ge=0.1, le=50, description="Search radius in kilometers"),
    db: Session = Depends(get_db)
):
    """Get stations with optional search and filters"""
    search = StationSearch(
        query=query,
        line_id=line_id,
        is_interchange=is_interchange,
        lat=lat,
        lng=lng,
        radius_km=radius_km
    )
    
    stations, total = StationService.get_stations(db, skip=skip, limit=limit, search=search)
    
    # Convert to detailed format
    detailed_stations = []
    for station in stations:
        station_data = {
            "id": station.id,
            "name": station.name,
            "lat": station.lat,
            "long": station.long,
            "zone_number": station.zone_number,
            "is_interchange": station.is_interchange,
            "platform_count": station.platform_count,
            "status": station.status,
            "line_id": station.line_id,
            "created_at": station.created_at,
            "updated_at": station.updated_at,
            "line": None,
            "facilities": [],
            "transfer_points": []
        }
        
        if station.line:
            station_data["line"] = {
                "id": station.line.id,
                "name": station.line.name,
                "color": station.line.color,
                "company_name": station.line.company.name if station.line.company else None
            }
        
        detailed_stations.append(station_data)
    
    page = (skip // limit) + 1
    
    return StationSearchResult(
        stations=detailed_stations,
        total=total,
        page=page,
        per_page=limit
    )

@router.get("/search", response_model=List[StationDetail])
def search_stations(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """Search stations by name for autocomplete"""
    stations = StationService.search_stations_by_name(db, name=q, limit=limit)
    
    detailed_stations = []
    for station in stations:
        station_data = {
            "id": station.id,
            "name": station.name,
            "lat": station.lat,
            "long": station.long,
            "zone_number": station.zone_number,
            "is_interchange": station.is_interchange,
            "platform_count": station.platform_count,
            "status": station.status,
            "line_id": station.line_id,
            "created_at": station.created_at,
            "updated_at": station.updated_at,
            "line": None,
            "facilities": [],
            "transfer_points": []
        }
        
        if station.line:
            station_data["line"] = {
                "id": station.line.id,
                "name": station.line.name,
                "color": station.line.color,
                "company_name": station.line.company.name if station.line.company else None
            }
        
        detailed_stations.append(station_data)
    
    return detailed_stations

@router.get("/nearby", response_model=List[StationDetail])
def get_nearby_stations(
    lat: float = Query(..., description="Latitude"),
    lng: float = Query(..., description="Longitude"),
    radius_km: float = Query(1.0, ge=0.1, le=50, description="Search radius in kilometers"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of results"),
    db: Session = Depends(get_db)
):
    """Get stations near given coordinates"""
    stations = StationService.get_nearby_stations(db, lat=lat, lng=lng, radius_km=radius_km, limit=limit)
    
    detailed_stations = []
    for station in stations:
        station_data = {
            "id": station.id,
            "name": station.name,
            "lat": station.lat,
            "long": station.long,
            "zone_number": station.zone_number,
            "is_interchange": station.is_interchange,
            "platform_count": station.platform_count,
            "status": station.status,
            "line_id": station.line_id,
            "created_at": station.created_at,
            "updated_at": station.updated_at,
            "line": None,
            "facilities": [],
            "transfer_points": []
        }
        
        if station.line:
            station_data["line"] = {
                "id": station.line.id,
                "name": station.line.name,
                "color": station.line.color,
                "company_name": station.line.company.name if station.line.company else None
            }
        
        detailed_stations.append(station_data)
    
    return detailed_stations

@router.get("/interchanges", response_model=List[StationDetail])
def get_interchange_stations(db: Session = Depends(get_db)):
    """Get all interchange stations"""
    stations = StationService.get_interchange_stations(db)
    
    detailed_stations = []
    for station in stations:
        station_data = {
            "id": station.id,
            "name": station.name,
            "lat": station.lat,
            "long": station.long,
            "zone_number": station.zone_number,
            "is_interchange": station.is_interchange,
            "platform_count": station.platform_count,
            "status": station.status,
            "line_id": station.line_id,
            "created_at": station.created_at,
            "updated_at": station.updated_at,
            "line": None,
            "facilities": [],
            "transfer_points": []
        }
        
        if station.line:
            station_data["line"] = {
                "id": station.line.id,
                "name": station.line.name,
                "color": station.line.color,
                "company_name": station.line.company.name if station.line.company else None
            }
        
        detailed_stations.append(station_data)
    
    return detailed_stations

@router.get("/{station_id}", response_model=StationDetail)
def get_station(station_id: int, db: Session = Depends(get_db)):
    """Get station details by ID"""
    station = StationService.get_station_by_id(db, station_id=station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found"
        )
    
    # Get facilities and transfers
    facilities = StationService.get_station_facilities(db, station_id)
    transfers = StationService.get_station_transfers(db, station_id)
    
    station_data = {
        "id": station.id,
        "name": station.name,
        "lat": station.lat,
        "long": station.long,
        "zone_number": station.zone_number,
        "is_interchange": station.is_interchange,
        "platform_count": station.platform_count,
        "status": station.status,
        "line_id": station.line_id,
        "created_at": station.created_at,
        "updated_at": station.updated_at,
        "line": None,
        "facilities": [
            {
                "id": f.id,
                "station_id": f.station_id,
                "facility_type": f.facility_type,
                "is_available": f.is_available,
                "location_description": f.location_description,
                "created_at": f.created_at
            } for f in facilities
        ],
        "transfer_points": [
            {
                "id": t["id"],
                "station_b_id": t["station_id"],
                "station_b_name": t["station_name"],
                "walking_time_minutes": t["walking_time_minutes"],
                "walking_distance_meters": t["walking_distance_meters"],
                "transfer_fee": t["transfer_fee"]
            } for t in transfers
        ]
    }
    
    if station.line:
        station_data["line"] = {
            "id": station.line.id,
            "name": station.line.name,
            "color": station.line.color,
            "company_name": station.line.company.name if station.line.company else None
        }
    
    return station_data

@router.get("/{station_id}/transfers")
def get_station_transfers(station_id: int, db: Session = Depends(get_db)):
    """Get transfer options from a station"""
    # Verify station exists
    station = StationService.get_station_by_id(db, station_id)
    if not station:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Station not found"
        )
    
    transfers = StationService.get_station_transfers(db, station_id)
    return {"transfers": transfers}