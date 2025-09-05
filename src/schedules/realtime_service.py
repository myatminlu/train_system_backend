from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import random
import asyncio
import uuid
from collections import defaultdict

from src.schedules.schemas import (
    RealTimeUpdate, TrainPosition, CrowdData, WeatherImpact,
    ServiceAlert, DisruptionSeverity, WeatherCondition, CrowdLevel,
    ServiceStatus, MaintenanceWindow
)

class RealTimeSimulator:
    """Service for simulating real-time train data and disruptions"""
    
    def __init__(self):
        self.active_trains: Dict[str, TrainPosition] = {}
        self.service_alerts: List[ServiceAlert] = []
        self.weather_conditions: Dict[int, WeatherImpact] = {}  # line_id -> weather
        self.maintenance_windows: List[MaintenanceWindow] = []
        self.crowd_data: Dict[int, CrowdData] = {}  # station_id -> crowd data
        self._simulation_running = False
        self._update_callbacks: List[callable] = []
        
        # Bangkok train lines configuration
        self.line_config = {
            1: {"name": "BTS Sukhumvit", "stations": list(range(1, 23)), "trains": 15},
            2: {"name": "BTS Silom", "stations": list(range(23, 35)), "trains": 12},
            3: {"name": "MRT Blue", "stations": list(range(35, 45)), "trains": 18},
            4: {"name": "Airport Rail Link", "stations": list(range(45, 51)), "trains": 8}
        }
        
        self._initialize_simulation()
    
    def _initialize_simulation(self):
        """Initialize the simulation with baseline data"""
        # Create initial train positions
        for line_id, config in self.line_config.items():
            for i in range(config["trains"]):
                train_id = f"L{line_id}T{i+1:03d}"
                station_idx = random.randint(0, len(config["stations"]) - 1)
                
                train = TrainPosition(
                    train_id=train_id,
                    line_id=line_id,
                    current_station_id=config["stations"][station_idx],
                    next_station_id=config["stations"][(station_idx + 1) % len(config["stations"])],
                    direction=random.choice(["inbound", "outbound"]),
                    estimated_arrival=datetime.now() + timedelta(minutes=random.randint(1, 10)),
                    delay_minutes=random.randint(0, 3),
                    occupancy_level=random.choice(list(CrowdLevel)),
                    status="in_service",
                    last_updated=datetime.now()
                )
                self.active_trains[train_id] = train
        
        # Initialize crowd data for stations
        for line_id, config in self.line_config.items():
            for station_id in config["stations"]:
                self.crowd_data[station_id] = CrowdData(
                    station_id=station_id,
                    crowd_level=self._get_realistic_crowd_level(),
                    occupancy_percentage=random.randint(20, 80),
                    estimated_wait_time=random.randint(1, 8),
                    peak_times=["07:00-09:00", "17:30-19:30"],
                    last_updated=datetime.now()
                )
    
    async def start_simulation(self):
        """Start the real-time simulation"""
        self._simulation_running = True
        
        # Start concurrent simulation tasks
        tasks = [
            self._simulate_train_movements(),
            self._simulate_delays(),
            self._simulate_service_disruptions(),
            self._simulate_crowd_levels(),
            self._simulate_weather_conditions(),
            self._simulate_maintenance_events()
        ]
        
        await asyncio.gather(*tasks)
    
    def stop_simulation(self):
        """Stop the real-time simulation"""
        self._simulation_running = False
    
    async def _simulate_train_movements(self):
        """Simulate train movements between stations"""
        while self._simulation_running:
            for train_id, train in self.active_trains.items():
                # Simulate train arriving at next station
                if random.random() < 0.1:  # 10% chance per cycle
                    self._move_train_to_next_station(train)
                    
                    # Create arrival update
                    update = RealTimeUpdate(
                        update_id=str(uuid.uuid4()),
                        timestamp=datetime.now(),
                        update_type="arrival",
                        train_id=train_id,
                        line_id=train.line_id,
                        station_id=train.current_station_id,
                        original_time=train.estimated_arrival - timedelta(minutes=train.delay_minutes),
                        updated_time=train.estimated_arrival,
                        delay_minutes=train.delay_minutes
                    )
                    
                    await self._broadcast_update(update)
            
            await asyncio.sleep(10)  # Update every 10 seconds
    
    async def _simulate_delays(self):
        """Simulate realistic delay patterns"""
        while self._simulation_running:
            # Random delays during rush hours
            current_time = datetime.now().time()
            is_rush_hour = (
                (current_time.hour >= 7 and current_time.hour <= 9) or
                (current_time.hour >= 17 and current_time.hour <= 19)
            )
            
            if is_rush_hour and random.random() < 0.3:  # Higher chance during rush hour
                # Select random train for delay
                train_id = random.choice(list(self.active_trains.keys()))
                train = self.active_trains[train_id]
                
                # Add delay
                additional_delay = random.randint(1, 5)
                train.delay_minutes += additional_delay
                train.estimated_arrival += timedelta(minutes=additional_delay)
                train.last_updated = datetime.now()
                
                # Create delay update
                update = RealTimeUpdate(
                    update_id=str(uuid.uuid4()),
                    timestamp=datetime.now(),
                    update_type="delay",
                    train_id=train_id,
                    line_id=train.line_id,
                    station_id=train.current_station_id,
                    original_time=train.estimated_arrival - timedelta(minutes=train.delay_minutes),
                    updated_time=train.estimated_arrival,
                    delay_minutes=train.delay_minutes,
                    reason="High passenger volume"
                )
                
                await self._broadcast_update(update)
            
            await asyncio.sleep(30)  # Check every 30 seconds
    
    async def _simulate_service_disruptions(self):
        """Simulate service disruptions and alerts"""
        while self._simulation_running:
            # Random disruption (low probability)
            if random.random() < 0.002:  # Very low chance per cycle
                line_id = random.choice(list(self.line_config.keys()))
                
                disruption_types = [
                    ("Signal failure", DisruptionSeverity.MODERATE, "Technical issue with signaling system"),
                    ("Track maintenance", DisruptionSeverity.LOW, "Scheduled maintenance work"),
                    ("Medical emergency", DisruptionSeverity.HIGH, "Medical assistance required"),
                    ("Power supply issue", DisruptionSeverity.HIGH, "Electrical system problem"),
                    ("Security incident", DisruptionSeverity.CRITICAL, "Security-related service suspension")
                ]
                
                disruption_type, severity, description = random.choice(disruption_types)
                
                # Create service alert
                alert = ServiceAlert(
                    id=len(self.service_alerts) + 1,
                    title=f"{disruption_type} on {self.line_config[line_id]['name']}",
                    description=description,
                    alert_type="disruption",
                    severity=severity,
                    affected_lines=[line_id],
                    affected_stations=self.line_config[line_id]["stations"][:3],  # First 3 stations
                    start_time=datetime.now(),
                    end_time=datetime.now() + timedelta(minutes=random.randint(15, 90)),
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                
                self.service_alerts.append(alert)
                await self._broadcast_service_alert(alert)
            
            # Resolve expired alerts
            current_time = datetime.now()
            for alert in self.service_alerts:
                if alert.is_active and alert.end_time and alert.end_time <= current_time:
                    alert.is_active = False
                    await self._broadcast_alert_resolution(alert)
            
            await asyncio.sleep(60)  # Check every minute
    
    async def _simulate_crowd_levels(self):
        """Simulate crowd density changes"""
        while self._simulation_running:
            current_time = datetime.now()
            
            for station_id, crowd_data in self.crowd_data.items():
                # Update based on time of day
                new_crowd_level = self._get_realistic_crowd_level()
                
                if new_crowd_level != crowd_data.crowd_level:
                    crowd_data.crowd_level = new_crowd_level
                    crowd_data.occupancy_percentage = self._crowd_level_to_percentage(new_crowd_level)
                    crowd_data.estimated_wait_time = random.randint(1, 10)
                    crowd_data.last_updated = current_time
            
            await asyncio.sleep(120)  # Update every 2 minutes
    
    async def _simulate_weather_conditions(self):
        """Simulate weather impact on train services"""
        while self._simulation_running:
            # Random weather events (low probability)
            if random.random() < 0.001:  # Very low chance
                weather_events = [
                    (WeatherCondition.HEAVY_RAIN, 3, "Heavy rainfall causing service delays", 1.2),
                    (WeatherCondition.STORM, 5, "Storm conditions affecting operations", 1.5),
                    (WeatherCondition.FOG, 2, "Poor visibility due to fog", 1.1),
                    (WeatherCondition.EXTREME_HEAT, 1, "High temperatures affecting equipment", 1.05)
                ]
                
                condition, severity, description, delay_factor = random.choice(weather_events)
                affected_lines = random.sample(list(self.line_config.keys()), 
                                             random.randint(1, 2))
                
                weather_impact = WeatherImpact(
                    condition=condition,
                    severity=severity,
                    affected_lines=affected_lines,
                    impact_description=description,
                    delay_factor=delay_factor,
                    service_reduction=random.uniform(0.1, 0.3),
                    start_time=datetime.now(),
                    end_time=datetime.now() + timedelta(hours=random.randint(1, 4))
                )
                
                for line_id in affected_lines:
                    self.weather_conditions[line_id] = weather_impact
                
                await self._broadcast_weather_alert(weather_impact)
            
            await asyncio.sleep(300)  # Check every 5 minutes
    
    async def _simulate_maintenance_events(self):
        """Simulate maintenance windows and their impact"""
        while self._simulation_running:
            # Check for scheduled maintenance (would come from database)
            current_time = datetime.now()
            
            # Random maintenance event (very low probability)
            if random.random() < 0.0005:  # Very rare
                line_id = random.choice(list(self.line_config.keys()))
                
                maintenance = MaintenanceWindow(
                    id=len(self.maintenance_windows) + 1,
                    title=f"Track maintenance on {self.line_config[line_id]['name']}",
                    description="Routine track inspection and maintenance",
                    maintenance_type="routine",
                    affected_lines=[line_id],
                    affected_stations=random.sample(
                        self.line_config[line_id]["stations"], 
                        random.randint(2, 5)
                    ),
                    start_time=current_time + timedelta(hours=random.randint(1, 12)),
                    end_time=current_time + timedelta(hours=random.randint(13, 24)),
                    impact_level="moderate",
                    alternative_routes=[],
                    is_active=True,
                    created_at=current_time
                )
                
                self.maintenance_windows.append(maintenance)
                await self._broadcast_maintenance_alert(maintenance)
            
            await asyncio.sleep(600)  # Check every 10 minutes
    
    def _move_train_to_next_station(self, train: TrainPosition):
        """Move train to the next station"""
        line_stations = self.line_config[train.line_id]["stations"]
        current_idx = line_stations.index(train.current_station_id)
        
        if train.direction == "inbound":
            next_idx = (current_idx + 1) % len(line_stations)
        else:
            next_idx = (current_idx - 1) % len(line_stations)
        
        train.current_station_id = line_stations[next_idx]
        train.next_station_id = line_stations[(next_idx + 1) % len(line_stations)]
        train.estimated_arrival = datetime.now() + timedelta(minutes=random.randint(2, 8))
        train.status = "approaching"
        train.last_updated = datetime.now()
    
    def _get_realistic_crowd_level(self) -> CrowdLevel:
        """Get realistic crowd level based on time of day"""
        current_hour = datetime.now().hour
        
        if 7 <= current_hour <= 9 or 17 <= current_hour <= 19:  # Rush hours
            return random.choice([CrowdLevel.HIGH, CrowdLevel.VERY_HIGH])
        elif 22 <= current_hour or current_hour <= 6:  # Late night/early morning
            return random.choice([CrowdLevel.LOW, CrowdLevel.MODERATE])
        else:  # Regular hours
            return random.choice([CrowdLevel.MODERATE, CrowdLevel.HIGH])
    
    def _crowd_level_to_percentage(self, crowd_level: CrowdLevel) -> int:
        """Convert crowd level to occupancy percentage"""
        mapping = {
            CrowdLevel.LOW: random.randint(10, 30),
            CrowdLevel.MODERATE: random.randint(30, 60),
            CrowdLevel.HIGH: random.randint(60, 85),
            CrowdLevel.VERY_HIGH: random.randint(85, 95),
            CrowdLevel.OVERCROWDED: random.randint(95, 100)
        }
        return mapping[crowd_level]
    
    def add_update_callback(self, callback: callable):
        """Add callback for real-time updates"""
        self._update_callbacks.append(callback)
    
    async def _broadcast_update(self, update: RealTimeUpdate):
        """Broadcast update to all registered callbacks"""
        for callback in self._update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(update)
                else:
                    callback(update)
            except Exception as e:
                print(f"Error broadcasting update: {e}")
    
    async def _broadcast_service_alert(self, alert: ServiceAlert):
        """Broadcast service alert"""
        for callback in self._update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback({"type": "service_alert", "data": alert})
                else:
                    callback({"type": "service_alert", "data": alert})
            except Exception as e:
                print(f"Error broadcasting service alert: {e}")
    
    async def _broadcast_alert_resolution(self, alert: ServiceAlert):
        """Broadcast alert resolution"""
        for callback in self._update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback({"type": "alert_resolved", "data": alert})
                else:
                    callback({"type": "alert_resolved", "data": alert})
            except Exception as e:
                print(f"Error broadcasting alert resolution: {e}")
    
    async def _broadcast_weather_alert(self, weather: WeatherImpact):
        """Broadcast weather alert"""
        for callback in self._update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback({"type": "weather_alert", "data": weather})
                else:
                    callback({"type": "weather_alert", "data": weather})
            except Exception as e:
                print(f"Error broadcasting weather alert: {e}")
    
    async def _broadcast_maintenance_alert(self, maintenance: MaintenanceWindow):
        """Broadcast maintenance alert"""
        for callback in self._update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback({"type": "maintenance_alert", "data": maintenance})
                else:
                    callback({"type": "maintenance_alert", "data": maintenance})
            except Exception as e:
                print(f"Error broadcasting maintenance alert: {e}")
    
    # Public methods for getting current state
    def get_active_trains(self, line_id: Optional[int] = None) -> List[TrainPosition]:
        """Get all active trains, optionally filtered by line"""
        trains = list(self.active_trains.values())
        if line_id:
            trains = [t for t in trains if t.line_id == line_id]
        return trains
    
    def get_service_alerts(self, active_only: bool = True) -> List[ServiceAlert]:
        """Get service alerts"""
        alerts = self.service_alerts
        if active_only:
            alerts = [a for a in alerts if a.is_active]
        return alerts
    
    def get_crowd_data(self, station_id: Optional[int] = None) -> List[CrowdData]:
        """Get crowd data"""
        if station_id:
            return [self.crowd_data.get(station_id)] if station_id in self.crowd_data else []
        return list(self.crowd_data.values())
    
    def get_weather_conditions(self, line_id: Optional[int] = None) -> List[WeatherImpact]:
        """Get weather conditions affecting lines"""
        if line_id:
            return [self.weather_conditions.get(line_id)] if line_id in self.weather_conditions else []
        return list(self.weather_conditions.values())
    
    def get_maintenance_windows(self, active_only: bool = True) -> List[MaintenanceWindow]:
        """Get maintenance windows"""
        maintenance = self.maintenance_windows
        if active_only:
            current_time = datetime.now()
            maintenance = [m for m in maintenance if m.is_active and 
                          m.start_time <= current_time <= m.end_time]
        return maintenance

# Global simulator instance
realtime_simulator = RealTimeSimulator()