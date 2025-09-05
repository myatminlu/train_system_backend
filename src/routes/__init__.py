"""
Route Planning Module

This module provides comprehensive route planning functionality for the Bangkok Train Transport System.
It includes:

- Route calculation using Dijkstra's algorithm
- Multi-modal journey planning (train + transfers)
- Fare calculation for different train systems (BTS, MRT, SRT)  
- Route optimization by time, cost, or transfer preferences
- Route validation and feasibility checking
- Alternative route generation

Key Components:
- service.py: Core route calculation algorithms and graph representation
- fare_service.py: Fare calculation logic for different train systems
- validation.py: Request validation and route feasibility checking
- router.py: FastAPI endpoints for route planning APIs
- schemas.py: Pydantic models for request/response structures
"""

from .router import router
from .service import RouteService, RouteCalculator, NetworkGraph
from .fare_service import FareCalculationService
from .validation import RouteValidator
from .schemas import (
    RouteRequest, RouteResponse, RouteOption, RouteSegment, RouteSummary,
    FareCalculationRequest, FareCalculationResponse, FareBreakdown,
    RouteAlternativesRequest, RouteValidationError,
    NetworkNode, NetworkEdge
)

__all__ = [
    "router",
    "RouteService", 
    "RouteCalculator",
    "NetworkGraph",
    "FareCalculationService",
    "RouteValidator",
    "RouteRequest",
    "RouteResponse", 
    "RouteOption",
    "RouteSegment",
    "RouteSummary",
    "FareCalculationRequest",
    "FareCalculationResponse",
    "FareBreakdown", 
    "RouteAlternativesRequest",
    "RouteValidationError",
    "NetworkNode",
    "NetworkEdge"
]