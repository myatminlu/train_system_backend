from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func
from typing import List, Optional, Tuple
from src.models import Station, StationFacility, TransferPoint, TrainLine, TrainCompany
from src.stations.schemas import StationCreate, StationUpdate, StationSearch
import math

class StationService:
    @staticmethod
    def get_station_by_id(db: Session, station_id: int) -> Optional[Station]:
        """Get station by ID with line and company info"""
        return db.query(Station).options(
            joinedload(Station.line).joinedload(TrainLine.company),
            joinedload(Station.facilities),
            joinedload(Station.transfer_points_a).joinedload(TransferPoint.station_b),
            joinedload(Station.transfer_points_b).joinedload(TransferPoint.station_a)
        ).filter(Station.id == station_id).first()
    
    @staticmethod
    def get_stations(
        db: Session, 
        skip: int = 0, 
        limit: int = 50,
        search: Optional[StationSearch] = None
    ) -> Tuple[List[Station], int]:
        """Get stations with optional search filters"""
        query = db.query(Station).options(
            joinedload(Station.line).joinedload(TrainLine.company)
        )
        
        # Apply filters
        if search:
            if search.query:
                query = query.filter(Station.name.ilike(f"%{search.query}%"))
            
            if search.line_id:
                query = query.filter(Station.line_id == search.line_id)
            
            if search.is_interchange is not None:
                query = query.filter(Station.is_interchange == search.is_interchange)
            
            # Geographic search
            if search.lat and search.lng and search.radius_km:
                # Simple distance calculation using Haversine formula approximation
                lat_range = search.radius_km / 111.32  # Approximate km per degree latitude
                lng_range = search.radius_km / (111.32 * math.cos(math.radians(search.lat)))
                
                query = query.filter(
                    and_(
                        Station.lat.between(search.lat - lat_range, search.lat + lat_range),
                        Station.long.between(search.lng - lng_range, search.lng + lng_range)
                    )
                )
        
        # Get total count
        total = query.count()
        
        # Get paginated results
        stations = query.offset(skip).limit(limit).all()
        
        return stations, total
    
    @staticmethod
    def search_stations_by_name(db: Session, name: str, limit: int = 10) -> List[Station]:
        """Search stations by name for autocomplete"""
        return db.query(Station).options(
            joinedload(Station.line).joinedload(TrainLine.company)
        ).filter(
            Station.name.ilike(f"%{name}%")
        ).limit(limit).all()
    
    @staticmethod
    def get_nearby_stations(
        db: Session, 
        lat: float, 
        lng: float, 
        radius_km: float = 1.0,
        limit: int = 10
    ) -> List[Station]:
        """Get stations within radius of given coordinates"""
        # Simple bounding box search
        lat_range = radius_km / 111.32  # Approximate km per degree latitude
        lng_range = radius_km / (111.32 * math.cos(math.radians(lat)))
        
        return db.query(Station).options(
            joinedload(Station.line).joinedload(TrainLine.company)
        ).filter(
            and_(
                Station.lat.between(lat - lat_range, lat + lat_range),
                Station.long.between(lng - lng_range, lng + lng_range)
            )
        ).limit(limit).all()
    
    @staticmethod
    def get_station_transfers(db: Session, station_id: int) -> List[dict]:
        """Get all transfer options from a station"""
        transfers = []
        
        # Get transfers where this station is station_a
        transfers_a = db.query(TransferPoint).options(
            joinedload(TransferPoint.station_b).joinedload(Station.line)
        ).filter(
            and_(
                TransferPoint.station_a_id == station_id,
                TransferPoint.is_active == True
            )
        ).all()
        
        for transfer in transfers_a:
            transfers.append({
                "id": transfer.id,
                "station_id": transfer.station_b_id,
                "station_name": transfer.station_b.name,
                "line_name": transfer.station_b.line.name if transfer.station_b.line else None,
                "walking_time_minutes": transfer.walking_time_minutes,
                "walking_distance_meters": transfer.walking_distance_meters,
                "transfer_fee": transfer.transfer_fee
            })
        
        # Get transfers where this station is station_b
        transfers_b = db.query(TransferPoint).options(
            joinedload(TransferPoint.station_a).joinedload(Station.line)
        ).filter(
            and_(
                TransferPoint.station_b_id == station_id,
                TransferPoint.is_active == True
            )
        ).all()
        
        for transfer in transfers_b:
            transfers.append({
                "id": transfer.id,
                "station_id": transfer.station_a_id,
                "station_name": transfer.station_a.name,
                "line_name": transfer.station_a.line.name if transfer.station_a.line else None,
                "walking_time_minutes": transfer.walking_time_minutes,
                "walking_distance_meters": transfer.walking_distance_meters,
                "transfer_fee": transfer.transfer_fee
            })
        
        return transfers
    
    @staticmethod
    def get_station_facilities(db: Session, station_id: int) -> List[StationFacility]:
        """Get all facilities for a station"""
        return db.query(StationFacility).filter(
            StationFacility.station_id == station_id
        ).all()
    
    @staticmethod
    def get_interchange_stations(db: Session) -> List[Station]:
        """Get all interchange stations"""
        return db.query(Station).options(
            joinedload(Station.line).joinedload(TrainLine.company)
        ).filter(Station.is_interchange == True).all()
    
    @staticmethod
    def get_stations_by_line(db: Session, line_id: int) -> List[Station]:
        """Get all stations for a specific line"""
        return db.query(Station).options(
            joinedload(Station.line).joinedload(TrainLine.company)
        ).filter(Station.line_id == line_id).order_by(Station.name).all()