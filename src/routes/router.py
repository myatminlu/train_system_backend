from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import time

from src.database import get_db
from src.routes.schemas import (
    RouteRequest, RouteResponse, RouteOption, FareCalculationRequest, 
    FareCalculationResponse, RouteAlternativesRequest, RouteValidationError
)
from src.routes.service import RouteService
from src.routes.fare_service import FareCalculationService
from src.routes.validation import RouteValidator

router = APIRouter()

# In-memory cache for route results (in production, use Redis)
route_cache = {}

@router.post("/plan", response_model=RouteResponse)
def plan_route(
    request: RouteRequest,
    db: Session = Depends(get_db)
):
    """Plan routes between two stations with optimization preferences"""
    
    start_time = time.time()
    
    # Validate request
    validator = RouteValidator(db)
    validation_errors = validator.validate_route_request(request)
    
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Route request validation failed",
                "errors": [
                    {
                        "code": error.error_code,
                        "message": error.error_message,
                        "field": error.field
                    }
                    for error in validation_errors
                ]
            }
        )
    
    # Check route feasibility
    is_feasible, feasibility_warnings = validator.validate_route_feasibility(request)
    if not is_feasible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Route is not feasible",
                "warnings": feasibility_warnings
            }
        )
    
    # Calculate routes
    route_service = RouteService(db)
    routes = route_service.plan_route(request)
    
    if not routes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No routes found between the specified stations"
        )
    
    # Cache the routes for later retrieval
    for route in routes:
        route_cache[route.route_id] = route
    
    calculation_time = int((time.time() - start_time) * 1000)  # Convert to milliseconds
    
    response = RouteResponse(
        request=request,
        routes=routes,
        total_options=len(routes),
        calculation_time_ms=calculation_time
    )
    
    # Add warnings if any
    if feasibility_warnings:
        # In a real implementation, you might add warnings to the response schema
        pass
    
    return response

@router.get("/{route_id}/details", response_model=RouteOption)
def get_route_details(
    route_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific route"""
    
    # Check cache first
    if route_id in route_cache:
        return route_cache[route_id]
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Route with ID {route_id} not found"
    )

@router.post("/fare-calculate", response_model=FareCalculationResponse)
def calculate_fare(
    request: FareCalculationRequest,
    db: Session = Depends(get_db)
):
    """Calculate fare for a route with specific segments"""
    
    if not request.route_segments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Route segments are required for fare calculation"
        )
    
    fare_service = FareCalculationService(db)
    fare_response = fare_service.calculate_fare_from_request(request)
    
    return fare_response

@router.get("/alternatives", response_model=List[RouteOption])
def get_route_alternatives(
    from_station_id: int = Query(..., description="Origin station ID"),
    to_station_id: int = Query(..., description="Destination station ID"),
    departure_time: Optional[datetime] = Query(None, description="Departure time"),
    passenger_type_id: int = Query(1, description="Passenger type ID"),
    max_alternatives: int = Query(5, ge=1, le=10, description="Maximum number of alternatives"),
    avoid_lines: Optional[str] = Query(None, description="Comma-separated line IDs to avoid"),
    prefer_lines: Optional[str] = Query(None, description="Comma-separated preferred line IDs"),
    db: Session = Depends(get_db)
):
    """Get alternative routes with specific preferences"""
    
    # Parse comma-separated line IDs
    avoid_lines_list = None
    if avoid_lines:
        try:
            avoid_lines_list = [int(x.strip()) for x in avoid_lines.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid avoid_lines format. Use comma-separated integers."
            )
    
    prefer_lines_list = None
    if prefer_lines:
        try:
            prefer_lines_list = [int(x.strip()) for x in prefer_lines.split(",")]
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid prefer_lines format. Use comma-separated integers."
            )
    
    # Create alternatives request
    request = RouteAlternativesRequest(
        from_station_id=from_station_id,
        to_station_id=to_station_id,
        departure_time=departure_time,
        passenger_type_id=passenger_type_id,
        max_alternatives=max_alternatives,
        avoid_lines=avoid_lines_list,
        prefer_lines=prefer_lines_list
    )
    
    # Validate request
    validator = RouteValidator(db)
    validation_errors = validator.validate_alternatives_request(request)
    
    if validation_errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Route alternatives request validation failed",
                "errors": [
                    {
                        "code": error.error_code,
                        "message": error.error_message,
                        "field": error.field
                    }
                    for error in validation_errors
                ]
            }
        )
    
    # Get alternatives
    route_service = RouteService(db)
    alternatives = route_service.get_route_alternatives(request)
    
    # Cache the routes
    for route in alternatives:
        route_cache[route.route_id] = route
    
    return alternatives

@router.post("/{route_id}/fare", response_model=FareCalculationResponse)
def calculate_route_fare(
    route_id: str,
    passenger_type_id: int = Query(1, description="Passenger type ID"),
    db: Session = Depends(get_db)
):
    """Calculate fare for a specific route"""
    
    # Get route from cache
    if route_id not in route_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route with ID {route_id} not found"
        )
    
    route = route_cache[route_id]
    fare_service = FareCalculationService(db)
    fare_response = fare_service.calculate_route_fare(route, passenger_type_id)
    
    return fare_response

@router.post("/compare-fares")
def compare_route_fares(
    route_ids: List[str],
    passenger_type_id: int = Query(1, description="Passenger type ID"),
    db: Session = Depends(get_db)
):
    """Compare fares across multiple routes"""
    
    if not route_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one route ID is required"
        )
    
    if len(route_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare more than 10 routes at once"
        )
    
    # Get routes from cache
    routes = []
    missing_routes = []
    
    for route_id in route_ids:
        if route_id in route_cache:
            routes.append(route_cache[route_id])
        else:
            missing_routes.append(route_id)
    
    if missing_routes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Routes not found: {', '.join(missing_routes)}"
        )
    
    # Compare fares
    fare_service = FareCalculationService(db)
    comparisons = fare_service.compare_route_fares(routes, passenger_type_id)
    
    return {
        "passenger_type_id": passenger_type_id,
        "total_routes": len(routes),
        "comparisons": comparisons
    }

@router.get("/passenger-types")
def get_passenger_types(db: Session = Depends(get_db)):
    """Get available passenger types and their discount information"""
    
    try:
        # Get passenger types directly from database
        passenger_types_db = db.query(PassengerType).all()
        
        passenger_types = []
        for pt in passenger_types_db:
            passenger_types.append({
                "id": pt.id,
                "name": pt.name,
                "discount_percentage": float(pt.discount_percentage),
                "age_min": pt.age_min,
                "age_max": pt.age_max
            })
        
        return {
            "passenger_types": passenger_types
        }
    except Exception as e:
        # Return default passenger types if database query fails
        return {
            "passenger_types": [
                {
                    "id": 1,
                    "name": "Adult",
                    "discount_percentage": 0.0,
                    "age_min": 18,
                    "age_max": 64
                },
                {
                    "id": 2,
                    "name": "Student",
                    "discount_percentage": 15.0,
                    "age_min": 13,
                    "age_max": 25
                },
                {
                    "id": 3,
                    "name": "Senior",
                    "discount_percentage": 20.0,
                    "age_min": 65,
                    "age_max": None
                },
                {
                    "id": 4,
                    "name": "Child",
                    "discount_percentage": 50.0,
                    "age_min": 3,
                    "age_max": 12
                }
            ]
        }

@router.get("/validate")
def validate_route_request(
    from_station_id: int = Query(..., description="Origin station ID"),
    to_station_id: int = Query(..., description="Destination station ID"),
    departure_time: Optional[datetime] = Query(None, description="Departure time"),
    passenger_type_id: int = Query(1, description="Passenger type ID"),
    max_walking_time: int = Query(10, ge=1, le=60, description="Maximum walking time"),
    max_transfers: int = Query(3, ge=0, le=5, description="Maximum transfers"),
    optimization: str = Query("time", description="Optimization preference"),
    db: Session = Depends(get_db)
):
    """Validate a route request without calculating the actual route"""
    
    request = RouteRequest(
        from_station_id=from_station_id,
        to_station_id=to_station_id,
        departure_time=departure_time,
        passenger_type_id=passenger_type_id,
        optimization=optimization,
        max_walking_time=max_walking_time,
        max_transfers=max_transfers
    )
    
    validator = RouteValidator(db)
    validation_errors = validator.validate_route_request(request)
    is_feasible, feasibility_warnings = validator.validate_route_feasibility(request)
    
    return {
        "is_valid": len(validation_errors) == 0,
        "is_feasible": is_feasible,
        "validation_errors": [
            {
                "code": error.error_code,
                "message": error.error_message,
                "field": error.field
            }
            for error in validation_errors
        ],
        "feasibility_warnings": feasibility_warnings
    }