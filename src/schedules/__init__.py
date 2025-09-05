"""
Schedules & Real-time System Module

This module provides comprehensive schedule management and real-time data simulation
for the Bangkok Train Transport System. It includes:

- Train schedule calculation based on frequency patterns
- Real-time departure predictions with delay modeling
- Service status management and alert system
- Mock real-time data simulation (delays, disruptions, crowd levels)
- Weather impact simulation on train services
- Maintenance window scheduling and management

Key Components:
- service.py: Core schedule calculation with frequency-based algorithms
- realtime_service.py: Real-time data simulation and train position tracking
- service_status.py: Service status management and alert system
- router.py: FastAPI endpoints for schedules and real-time data
- schemas.py: Pydantic models for schedule and real-time data structures

Features:
- Realistic Bangkok train schedules (BTS, MRT, SRT)
- Rush hour vs off-peak frequency variations
- Holiday and special event schedule handling
- Intelligent delay prediction based on time patterns
- Crowd density estimation and simulation
- Weather condition impact on services
- Comprehensive service alert categorization
- Maintenance window management with user notifications
"""

from .router import router
from .service import ScheduleCalculationService
from .realtime_service import RealTimeSimulator, realtime_simulator
from .service_status import ServiceStatusManager
from .schemas import (
    TrainSchedule, DeparturePrediction, StationSchedule, LineSchedule,
    ServiceAlert, ServiceStatus, RealTimeUpdate, TrainPosition, CrowdData,
    WeatherImpact, MaintenanceWindow, SchedulePerformance, ServiceStatusFilter
)

__all__ = [
    "router",
    "ScheduleCalculationService", 
    "RealTimeSimulator",
    "realtime_simulator",
    "ServiceStatusManager",
    "TrainSchedule",
    "DeparturePrediction",
    "StationSchedule", 
    "LineSchedule",
    "ServiceAlert",
    "ServiceStatus",
    "RealTimeUpdate",
    "TrainPosition",
    "CrowdData",
    "WeatherImpact",
    "MaintenanceWindow",
    "SchedulePerformance",
    "ServiceStatusFilter"
]