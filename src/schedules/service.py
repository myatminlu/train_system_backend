from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta, time, date
from sqlalchemy.orm import Session
from decimal import Decimal
import random
import math
from collections import defaultdict

from src.models import Station, TrainLine, TrainService
from src.schedules.schemas import (
    TrainSchedule, DeparturePrediction, StationSchedule, LineSchedule,
    ScheduleType, ServiceStatus, CrowdLevel, WeatherCondition, WeatherImpact,
    RealTimeUpdate, TrainPosition, CrowdData, SchedulePerformance,
    DisruptionSeverity
)

class ScheduleCalculationService:
    """Service for calculating train schedules based on frequency and variations"""
    
    def __init__(self, db: Session):
        self.db = db
        self._schedule_cache = {}
        self._real_time_data = {}
        self._load_base_schedules()
    
    def _load_base_schedules(self):
        """Load base schedule data from database"""
        # In a real system, this would load from the database
        # For now, we'll create realistic Bangkok train schedules
        self._base_schedules = {
            # BTS Sukhumvit Line
            1: {
                "weekday": {"start": time(5, 30), "end": time(0, 30), "frequency": 3},
                "weekend": {"start": time(6, 0), "end": time(0, 0), "frequency": 4},
                "rush_hour": {"frequency": 2, "times": [("07:00", "09:30"), ("17:30", "20:00")]},
                "off_peak": {"frequency": 5}
            },
            # BTS Silom Line  
            2: {
                "weekday": {"start": time(5, 30), "end": time(0, 30), "frequency": 3},
                "weekend": {"start": time(6, 0), "end": time(0, 0), "frequency": 4},
                "rush_hour": {"frequency": 2, "times": [("07:00", "09:30"), ("17:30", "20:00")]},
                "off_peak": {"frequency": 5}
            },
            # MRT Blue Line
            3: {
                "weekday": {"start": time(6, 0), "end": time(0, 0), "frequency": 4},
                "weekend": {"start": time(6, 0), "end": time(0, 0), "frequency": 5},
                "rush_hour": {"frequency": 3, "times": [("07:00", "09:00"), ("18:00", "20:00")]},
                "off_peak": {"frequency": 6}
            }
        }
    
    def calculate_departures_for_station(
        self, 
        station_id: int, 
        target_date: date = None,
        hours_ahead: int = 2
    ) -> List[DeparturePrediction]:
        """Calculate predicted departures for a station"""
        
        if not target_date:
            target_date = datetime.now().date()
        
        current_time = datetime.now()
        end_time = current_time + timedelta(hours=hours_ahead)
        
        # Get station and associated line
        station = self.db.query(Station).filter(Station.id == station_id).first()
        if not station or not station.line_id:
            return []
        
        line_id = station.line_id
        departures = []
        
        # Get base schedule for the line
        if line_id not in self._base_schedules:
            return []
        
        schedule_config = self._base_schedules[line_id]
        
        # Determine schedule type
        schedule_type = self._get_schedule_type(target_date)
        base_schedule = schedule_config.get(schedule_type, schedule_config["weekday"])
        
        # Generate departures
        current = current_time.replace(second=0, microsecond=0)
        service_start = datetime.combine(target_date, base_schedule["start"])
        service_end = datetime.combine(target_date, base_schedule["end"])
        
        # Handle overnight service (end time next day)
        if base_schedule["end"] < base_schedule["start"]:
            service_end += timedelta(days=1)
        
        while current <= end_time and current <= service_end:
            if current >= service_start:
                # Determine frequency for current time
                frequency = self._get_frequency_for_time(current.time(), schedule_config)
                
                # Create departure prediction
                departure = DeparturePrediction(
                    station_id=station_id,
                    line_id=line_id,
                    direction="inbound",  # Would determine based on station position
                    scheduled_time=current,
                    predicted_time=current + timedelta(minutes=self._calculate_delay(current)),
                    delay_minutes=self._calculate_delay(current),
                    confidence_level=self._calculate_confidence(current),
                    last_updated=datetime.now()
                )
                departures.append(departure)
                
                # Add opposite direction
                departure_outbound = DeparturePrediction(
                    station_id=station_id,
                    line_id=line_id,
                    direction="outbound",
                    scheduled_time=current + timedelta(minutes=1),
                    predicted_time=current + timedelta(minutes=1 + self._calculate_delay(current)),
                    delay_minutes=self._calculate_delay(current),
                    confidence_level=self._calculate_confidence(current),
                    last_updated=datetime.now()
                )
                departures.append(departure_outbound)
            
            # Move to next departure
            frequency = self._get_frequency_for_time(current.time(), schedule_config)
            current += timedelta(minutes=frequency)
        
        return sorted(departures, key=lambda x: x.scheduled_time)
    
    def _get_schedule_type(self, target_date: date) -> str:
        """Determine schedule type for given date"""
        weekday = target_date.weekday()
        
        # Check for holidays (simplified - would use holiday calendar)
        if self._is_holiday(target_date):
            return "holiday"
        
        # Weekend schedule
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            return "weekend"
        
        return "weekday"
    
    def _is_holiday(self, target_date: date) -> bool:
        """Check if date is a Thai holiday"""
        # Simplified holiday check - would use proper holiday calendar
        thai_holidays_2024 = [
            date(2024, 1, 1),   # New Year
            date(2024, 4, 13),  # Songkran
            date(2024, 4, 14),  # Songkran
            date(2024, 4, 15),  # Songkran
            date(2024, 5, 1),   # Labor Day
            date(2024, 12, 5),  # King's Birthday
            date(2024, 12, 25), # Christmas (observed)
        ]
        return target_date in thai_holidays_2024
    
    def _get_frequency_for_time(self, current_time: time, schedule_config: dict) -> int:
        """Get frequency in minutes for specific time"""
        
        # Check if current time is in rush hour
        if "rush_hour" in schedule_config:
            rush_config = schedule_config["rush_hour"]
            for time_range in rush_config.get("times", []):
                start_str, end_str = time_range
                start_time = datetime.strptime(start_str, "%H:%M").time()
                end_time = datetime.strptime(end_str, "%H:%M").time()
                
                if start_time <= current_time <= end_time:
                    return rush_config["frequency"]
        
        # Default to off-peak or base frequency
        if "off_peak" in schedule_config:
            return schedule_config["off_peak"]["frequency"]
        
        return schedule_config.get("weekday", {}).get("frequency", 5)
    
    def _calculate_delay(self, departure_time: datetime) -> int:
        """Calculate realistic delay for departure time"""
        base_delay = 0
        
        # Rush hour increases delays
        if self._is_rush_hour(departure_time.time()):
            base_delay += random.randint(1, 3)
        
        # Random operational delays
        if random.random() < 0.3:  # 30% chance of delay
            base_delay += random.randint(1, 5)
        
        # Weather impact
        weather_delay = self._get_weather_delay()
        base_delay += weather_delay
        
        return max(0, base_delay)
    
    def _is_rush_hour(self, check_time: time) -> bool:
        """Check if time is during rush hour"""
        morning_start = time(7, 0)
        morning_end = time(9, 30)
        evening_start = time(17, 30)
        evening_end = time(20, 0)
        
        return (morning_start <= check_time <= morning_end or 
                evening_start <= check_time <= evening_end)
    
    def _get_weather_delay(self) -> int:
        """Get current weather-related delay"""
        # Simplified weather simulation
        weather_conditions = [
            (WeatherCondition.CLEAR, 0),
            (WeatherCondition.RAIN, 2),
            (WeatherCondition.HEAVY_RAIN, 5),
            (WeatherCondition.STORM, 10),
            (WeatherCondition.FOG, 3),
        ]
        
        # Random weather condition (would use real weather API)
        condition, delay = random.choice(weather_conditions)
        return delay if random.random() < 0.2 else 0  # 20% chance of weather impact
    
    def _calculate_confidence(self, departure_time: datetime) -> float:
        """Calculate confidence level for prediction"""
        time_until_departure = (departure_time - datetime.now()).total_seconds() / 60
        
        if time_until_departure <= 5:
            return 0.95  # Very high confidence for imminent departures
        elif time_until_departure <= 15:
            return 0.85  # High confidence
        elif time_until_departure <= 60:
            return 0.70  # Medium confidence
        else:
            return 0.50  # Lower confidence for distant predictions
    
    def get_line_schedule(self, line_id: int) -> LineSchedule:
        """Get complete schedule for a train line"""
        
        line = self.db.query(TrainLine).filter(TrainLine.id == line_id).first()
        if not line:
            return None
        
        # Get all stations on the line
        stations = self.db.query(Station).filter(Station.line_id == line_id).all()
        
        station_schedules = []
        total_delays = []
        
        for station in stations:
            departures = self.calculate_departures_for_station(station.id)
            
            # Get next arrival
            next_arrival = None
            if departures:
                next_arrival = min(departures, key=lambda x: x.predicted_time)
            
            # Calculate crowd level (simplified)
            crowd_level = self._estimate_crowd_level(station.id)
            
            station_schedule = StationSchedule(
                station_id=station.id,
                station_name=station.name,
                departures=departures[:10],  # Limit to next 10 departures
                next_arrival=next_arrival,
                service_alerts=[],
                crowd_level=crowd_level,
                last_updated=datetime.now()
            )
            station_schedules.append(station_schedule)
            
            # Collect delay data
            if departures:
                avg_delay = sum(d.delay_minutes for d in departures) / len(departures)
                total_delays.append(avg_delay)
        
        # Calculate line-wide metrics
        average_delay = int(sum(total_delays) / len(total_delays)) if total_delays else 0
        service_status = self._determine_service_status(average_delay)
        current_frequency = self._get_current_frequency(line_id)
        
        return LineSchedule(
            line_id=line_id,
            line_name=line.name,
            service_status=service_status,
            current_frequency=current_frequency,
            average_delay=average_delay,
            stations=station_schedules,
            service_alerts=[],
            last_updated=datetime.now()
        )
    
    def _estimate_crowd_level(self, station_id: int) -> CrowdLevel:
        """Estimate crowd level for a station"""
        current_time = datetime.now().time()
        
        # Rush hour is more crowded
        if self._is_rush_hour(current_time):
            return random.choice([CrowdLevel.HIGH, CrowdLevel.VERY_HIGH])
        
        # Off-peak hours
        if time(22, 0) <= current_time or current_time <= time(6, 0):
            return random.choice([CrowdLevel.LOW, CrowdLevel.MODERATE])
        
        return random.choice([CrowdLevel.MODERATE, CrowdLevel.HIGH])
    
    def _determine_service_status(self, average_delay: int) -> ServiceStatus:
        """Determine service status based on delays"""
        if average_delay <= 2:
            return ServiceStatus.NORMAL
        elif average_delay <= 5:
            return ServiceStatus.DELAYED
        else:
            return ServiceStatus.DISRUPTED
    
    def _get_current_frequency(self, line_id: int) -> int:
        """Get current frequency for a line"""
        if line_id not in self._base_schedules:
            return 5
        
        current_time = datetime.now().time()
        schedule_config = self._base_schedules[line_id]
        
        return self._get_frequency_for_time(current_time, schedule_config)
    
    def update_real_time_data(self, update: RealTimeUpdate):
        """Update real-time data for schedules"""
        key = f"{update.line_id}_{update.station_id}_{update.train_id or 'general'}"
        
        if key not in self._real_time_data:
            self._real_time_data[key] = []
        
        self._real_time_data[key].append(update)
        
        # Keep only recent updates (last hour)
        cutoff_time = datetime.now() - timedelta(hours=1)
        self._real_time_data[key] = [
            u for u in self._real_time_data[key] 
            if u.timestamp > cutoff_time
        ]
    
    def get_schedule_performance(
        self, 
        line_id: Optional[int] = None,
        station_id: Optional[int] = None,
        days_back: int = 7
    ) -> SchedulePerformance:
        """Calculate schedule performance metrics"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # In a real system, this would query historical data
        # For simulation, generate realistic performance metrics
        
        if line_id == 1 or line_id == 2:  # BTS lines
            on_time_percentage = random.uniform(85, 95)
            average_delay = random.uniform(1.5, 3.0)
        elif line_id == 3:  # MRT
            on_time_percentage = random.uniform(88, 96)
            average_delay = random.uniform(1.2, 2.5)
        else:
            on_time_percentage = random.uniform(82, 92)
            average_delay = random.uniform(2.0, 4.0)
        
        return SchedulePerformance(
            line_id=line_id,
            station_id=station_id,
            date_range_start=start_date,
            date_range_end=end_date,
            on_time_percentage=round(on_time_percentage, 2),
            average_delay_minutes=round(average_delay, 1),
            total_departures=random.randint(800, 1200) * days_back,
            cancelled_departures=random.randint(0, 5) * days_back,
            peak_hour_performance=round(on_time_percentage - 5, 2),
            off_peak_performance=round(on_time_percentage + 3, 2)
        )