#!/usr/bin/env python3

import sys
import os
from datetime import datetime, time
from decimal import Decimal

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy.orm import sessionmaker
from src.database import engine
from src.models import (
    PassengerType, Region, TrainCompany, TrainLine, Station, DistanceZone, 
    TransferPoint, StationFacility, TrainService, Route, FareRule, Role
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_seed_data():
    db = SessionLocal()
    
    try:
        print("🚀 Creating seed data for Bangkok Train Transport System...")
        
        # Clear existing data (in reverse dependency order)
        print("Clearing existing data...")
        db.query(FareRule).delete()
        db.query(Route).delete()
        db.query(TrainService).delete()
        db.query(StationFacility).delete()
        db.query(TransferPoint).delete()
        db.query(DistanceZone).delete()
        db.query(Station).delete()
        db.query(TrainLine).delete()
        db.query(TrainCompany).delete()
        db.query(Region).delete()
        db.query(PassengerType).delete()
        db.query(Role).delete()
        
        # 1. Create Passenger Types
        print("Creating passenger types...")
        passenger_types = [
            PassengerType(name="adult", discount_percentage=0.00, age_min=18, age_max=65),
            PassengerType(name="child", discount_percentage=50.00, age_min=0, age_max=12),
            PassengerType(name="senior", discount_percentage=30.00, age_min=65, age_max=120),
            PassengerType(name="student", discount_percentage=20.00, age_min=13, age_max=25),
        ]
        db.add_all(passenger_types)
        db.flush()
        
        # 2. Create Roles
        print("Creating roles...")
        roles = [
            Role(name="admin"),
            Role(name="user"),
            Role(name="operator")
        ]
        db.add_all(roles)
        db.flush()
        
        # 3. Create Region
        print("Creating Bangkok region...")
        bangkok_region = Region(name="Bangkok", country="Thailand")
        db.add(bangkok_region)
        db.flush()
        
        # 4. Create Train Companies
        print("Creating train companies...")
        companies = [
            TrainCompany(name="Bangkok Transit System (BTS)", status="active", region_id=bangkok_region.id),
            TrainCompany(name="Bangkok Expressway and Metro (BEM)", status="active", region_id=bangkok_region.id),
            TrainCompany(name="State Railway of Thailand (SRT)", status="active", region_id=bangkok_region.id),
            TrainCompany(name="Bangkok Mass Transit Authority (BMTA)", status="active", region_id=bangkok_region.id)
        ]
        db.add_all(companies)
        db.flush()
        
        bts_company = companies[0]
        bem_company = companies[1]  # Operates MRT Blue, Purple lines
        srt_company = companies[2]
        bmta_company = companies[3]  # Operates Yellow, Pink lines
        
        # 5. Create Train Lines
        print("Creating train lines...")
        train_lines = [
            # BTS Lines
            TrainLine(company_id=bts_company.id, name="BTS Sukhumvit Line", color="#00A651", status="active"),
            TrainLine(company_id=bts_company.id, name="BTS Silom Line", color="#00A651", status="active"),
            TrainLine(company_id=bts_company.id, name="BTS Gold Line", color="#FFD700", status="active"),
            
            # MRT Lines
            TrainLine(company_id=bem_company.id, name="MRT Blue Line", color="#1E4D8C", status="active"),
            TrainLine(company_id=bem_company.id, name="MRT Purple Line", color="#8B008B", status="active"),
            TrainLine(company_id=bmta_company.id, name="MRT Yellow Line", color="#FFD700", status="active"),
            TrainLine(company_id=bmta_company.id, name="MRT Pink Line", color="#FFC0CB", status="active"),
            
            # SRT Lines
            TrainLine(company_id=srt_company.id, name="SRT Dark Red Line", color="#8B0000", status="active"),
            TrainLine(company_id=srt_company.id, name="Airport Rail Link", color="#E74C3C", status="active"),
        ]
        db.add_all(train_lines)
        db.flush()
        
        # Get line references
        sukhumvit_line = train_lines[0]
        silom_line = train_lines[1]
        gold_line = train_lines[2]
        blue_line = train_lines[3]
        purple_line = train_lines[4]
        yellow_line = train_lines[5]
        pink_line = train_lines[6]
        dark_red_line = train_lines[7]
        arl_line = train_lines[8]
        
        # 6. Create Distance Zones (Fare Zones)
        print("Creating distance zones...")
        distance_zones = [
            # BTS Zones
            DistanceZone(line_id=sukhumvit_line.id, zone_number=1, base_fare=17, per_station_fare=3),
            DistanceZone(line_id=silom_line.id, zone_number=1, base_fare=17, per_station_fare=3),
            DistanceZone(line_id=gold_line.id, zone_number=1, base_fare=15, per_station_fare=2),
            
            # MRT Zones
            DistanceZone(line_id=blue_line.id, zone_number=1, base_fare=17, per_station_fare=2),
            DistanceZone(line_id=purple_line.id, zone_number=1, base_fare=14, per_station_fare=1),
            DistanceZone(line_id=yellow_line.id, zone_number=1, base_fare=15, per_station_fare=2),
            DistanceZone(line_id=pink_line.id, zone_number=1, base_fare=15, per_station_fare=2),
            
            # SRT Zones
            DistanceZone(line_id=dark_red_line.id, zone_number=1, base_fare=12, per_station_fare=2),
            DistanceZone(line_id=arl_line.id, zone_number=1, base_fare=15, per_station_fare=5),
        ]
        db.add_all(distance_zones)
        db.flush()
        
        # 7. Create Stations (Key stations for demonstration)
        print("Creating major stations...")
        stations = [
            # BTS Sukhumvit Line - Key Stations
            Station(line_id=sukhumvit_line.id, name="Mo Chit", lat=13.8024, long=100.5531, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Saphan Phut", lat=13.7954, long=100.5513, zone_number=1, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Victory Monument", lat=13.7655, long=100.5376, zone_number=1, is_interchange=False, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Phaya Thai", lat=13.7582, long=100.5329, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Ratchathewi", lat=13.7530, long=100.5312, zone_number=1, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Siam", lat=13.7456, long=100.5347, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Chit Lom", lat=13.7439, long=100.5430, zone_number=1, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Asok", lat=13.7374, long=100.5602, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Nana", lat=13.7378, long=100.5546, zone_number=1, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Phrom Phong", lat=13.7308, long=100.5697, zone_number=1, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Thong Lo", lat=13.7244, long=100.5824, zone_number=1, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="On Nut", lat=13.7054, long=100.6001, zone_number=2, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Bang Chak", lat=13.6996, long=100.6059, zone_number=2, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Bearing", lat=13.6621, long=100.6073, zone_number=2, platform_count=2, status="active"),
            Station(line_id=sukhumvit_line.id, name="Kheha", lat=13.6063, long=100.5992, zone_number=3, platform_count=2, status="active"),
            
            # BTS Silom Line - Key Stations
            Station(line_id=silom_line.id, name="National Stadium", lat=13.7465, long=100.5299, zone_number=1, platform_count=2, status="active"),
            Station(line_id=silom_line.id, name="Ratchadamri", lat=13.7386, long=100.5404, zone_number=1, platform_count=2, status="active"),
            Station(line_id=silom_line.id, name="Sala Daeng", lat=13.7282, long=100.5347, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=silom_line.id, name="Chong Nonsi", lat=13.7200, long=100.5347, zone_number=1, platform_count=2, status="active"),
            Station(line_id=silom_line.id, name="Surasak", lat=13.7198, long=100.5204, zone_number=1, platform_count=2, status="active"),
            Station(line_id=silom_line.id, name="Saphan Taksin", lat=13.7197, long=100.5148, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=silom_line.id, name="Krung Thon Buri", lat=13.7189, long=100.5072, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=silom_line.id, name="Wongwian Yai", lat=13.7196, long=100.4973, zone_number=2, platform_count=2, status="active"),
            Station(line_id=silom_line.id, name="Bang Wa", lat=13.6844, long=100.4358, zone_number=3, platform_count=2, status="active"),
            
            # MRT Blue Line - Key Stations
            Station(line_id=blue_line.id, name="Hua Lamphong", lat=13.7370, long=100.5167, zone_number=1, platform_count=2, status="active"),
            Station(line_id=blue_line.id, name="Si Lom", lat=13.7282, long=100.5334, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=blue_line.id, name="Sukhumvit", lat=13.7374, long=100.5602, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=blue_line.id, name="Queen Sirikit National Convention Centre", lat=13.7222, long=100.5602, zone_number=1, platform_count=2, status="active"),
            Station(line_id=blue_line.id, name="Chatuchak Park", lat=13.7983, long=100.5532, zone_number=1, platform_count=2, status="active"),
            Station(line_id=blue_line.id, name="Chatuchak", lat=13.8024, long=100.5531, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=blue_line.id, name="Bang Sue", lat=13.8153, long=100.5348, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=blue_line.id, name="Tao Poon", lat=13.8069, long=100.5239, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            
            # MRT Purple Line - Key Stations
            Station(line_id=purple_line.id, name="Khlong Bang Phai", lat=13.9127, long=100.4547, zone_number=1, platform_count=2, status="active"),
            Station(line_id=purple_line.id, name="Talad Bang Yai", lat=13.8958, long=100.4653, zone_number=1, platform_count=2, status="active"),
            Station(line_id=purple_line.id, name="Sam Yaek Bang Yai", lat=13.8813, long=100.4768, zone_number=1, platform_count=2, status="active"),
            Station(line_id=purple_line.id, name="Bang Phlu", lat=13.8469, long=100.5065, zone_number=1, platform_count=2, status="active"),
            Station(line_id=purple_line.id, name="Bang Pho", lat=13.8307, long=100.5238, zone_number=1, platform_count=2, status="active"),
            
            # Airport Rail Link - Key Stations
            Station(line_id=arl_line.id, name="Phaya Thai", lat=13.7582, long=100.5329, zone_number=1, is_interchange=True, platform_count=2, status="active"),
            Station(line_id=arl_line.id, name="Ratchaprarop", lat=13.7516, long=100.5477, zone_number=1, platform_count=2, status="active"),
            Station(line_id=arl_line.id, name="Makkasan", lat=13.7516, long=100.5668, zone_number=1, platform_count=2, status="active"),
            Station(line_id=arl_line.id, name="Ramkhamhaeng", lat=13.7516, long=100.6037, zone_number=2, platform_count=2, status="active"),
            Station(line_id=arl_line.id, name="Hua Mak", lat=13.7516, long=100.6425, zone_number=2, platform_count=2, status="active"),
            Station(line_id=arl_line.id, name="Ban Thap Chang", lat=13.7516, long=100.6878, zone_number=3, platform_count=2, status="active"),
            Station(line_id=arl_line.id, name="Lat Krabang", lat=13.7294, long=100.7425, zone_number=3, platform_count=2, status="active"),
            Station(line_id=arl_line.id, name="Suvarnabhumi", lat=13.6900, long=100.7501, zone_number=4, platform_count=2, status="active"),
        ]
        
        db.add_all(stations)
        db.flush()
        
        # Get station references for transfer points
        siam_station = next(s for s in stations if s.name == "Siam")
        asok_station = next(s for s in stations if s.name == "Asok")
        sukhumvit_station = next(s for s in stations if s.name == "Sukhumvit")
        sala_daeng_station = next(s for s in stations if s.name == "Sala Daeng")
        si_lom_station = next(s for s in stations if s.name == "Si Lom")
        mo_chit_bts = next(s for s in stations if s.name == "Mo Chit")
        chatuchak_mrt = next(s for s in stations if s.name == "Chatuchak")
        phaya_thai_bts = next(s for s in stations if s.name == "Phaya Thai" and s.line_id == sukhumvit_line.id)
        phaya_thai_arl = next(s for s in stations if s.name == "Phaya Thai" and s.line_id == arl_line.id)
        
        # 8. Create Transfer Points
        print("Creating transfer points...")
        transfer_points = [
            # BTS Siam ↔ National Stadium (same station complex)
            TransferPoint(station_a_id=siam_station.id, station_b_id=next(s for s in stations if s.name == "National Stadium").id, 
                         walking_time_minutes=3, walking_distance_meters=100, transfer_fee=0.00, is_active=True),
            
            # BTS Asok ↔ MRT Sukhumvit
            TransferPoint(station_a_id=asok_station.id, station_b_id=sukhumvit_station.id,
                         walking_time_minutes=5, walking_distance_meters=200, transfer_fee=0.00, is_active=True),
            
            # BTS Sala Daeng ↔ MRT Si Lom
            TransferPoint(station_a_id=sala_daeng_station.id, station_b_id=si_lom_station.id,
                         walking_time_minutes=4, walking_distance_meters=150, transfer_fee=0.00, is_active=True),
            
            # BTS Mo Chit ↔ MRT Chatuchak
            TransferPoint(station_a_id=mo_chit_bts.id, station_b_id=chatuchak_mrt.id,
                         walking_time_minutes=6, walking_distance_meters=250, transfer_fee=0.00, is_active=True),
            
            # BTS Phaya Thai ↔ ARL Phaya Thai
            TransferPoint(station_a_id=phaya_thai_bts.id, station_b_id=phaya_thai_arl.id,
                         walking_time_minutes=3, walking_distance_meters=100, transfer_fee=0.00, is_active=True),
        ]
        db.add_all(transfer_points)
        db.flush()
        
        # 9. Create Station Facilities
        print("Creating station facilities...")
        facilities = []
        for station in stations:
            # Add basic facilities for each station
            facilities.extend([
                StationFacility(station_id=station.id, facility_type="escalator", is_available=True, location_description="Platform entrance"),
                StationFacility(station_id=station.id, facility_type="elevator", is_available=True, location_description="Platform access"),
                StationFacility(station_id=station.id, facility_type="restroom", is_available=True, location_description="Concourse level"),
                StationFacility(station_id=station.id, facility_type="atm", is_available=True, location_description="Station entrance"),
            ])
            
            # Add shops for major interchange stations
            if station.is_interchange:
                facilities.extend([
                    StationFacility(station_id=station.id, facility_type="shop", is_available=True, location_description="7-Eleven convenience store"),
                    StationFacility(station_id=station.id, facility_type="cafe", is_available=True, location_description="Coffee shop"),
                ])
        
        db.add_all(facilities)
        db.flush()
        
        # 10. Create Train Services
        print("Creating train services...")
        train_services = [
            # BTS Services (6 AM - Midnight, every 3-6 minutes)
            TrainService(line_id=sukhumvit_line.id, service_name="Regular Service", 
                        start_time=time(6, 0), end_time=time(23, 59), frequency_minutes=4, 
                        direction="Northbound", is_active=True),
            TrainService(line_id=sukhumvit_line.id, service_name="Regular Service", 
                        start_time=time(6, 0), end_time=time(23, 59), frequency_minutes=4, 
                        direction="Southbound", is_active=True),
            
            TrainService(line_id=silom_line.id, service_name="Regular Service", 
                        start_time=time(6, 0), end_time=time(23, 59), frequency_minutes=4, 
                        direction="Eastbound", is_active=True),
            TrainService(line_id=silom_line.id, service_name="Regular Service", 
                        start_time=time(6, 0), end_time=time(23, 59), frequency_minutes=4, 
                        direction="Westbound", is_active=True),
            
            # MRT Services
            TrainService(line_id=blue_line.id, service_name="Regular Service", 
                        start_time=time(6, 0), end_time=time(23, 59), frequency_minutes=5, 
                        direction="Clockwise", is_active=True),
            TrainService(line_id=blue_line.id, service_name="Regular Service", 
                        start_time=time(6, 0), end_time=time(23, 59), frequency_minutes=5, 
                        direction="Counter-clockwise", is_active=True),
            
            # Airport Rail Link
            TrainService(line_id=arl_line.id, service_name="City Line", 
                        start_time=time(6, 0), end_time=time(23, 59), frequency_minutes=15, 
                        direction="To Airport", is_active=True),
            TrainService(line_id=arl_line.id, service_name="City Line", 
                        start_time=time(6, 0), end_time=time(23, 59), frequency_minutes=15, 
                        direction="To City", is_active=True),
        ]
        db.add_all(train_services)
        db.flush()
        
        # 11. Create Sample Routes (between adjacent stations)
        print("Creating sample routes...")
        routes = []
        
        # Create routes between consecutive stations on Sukhumvit Line
        sukhumvit_stations = [s for s in stations if s.line_id == sukhumvit_line.id]
        sukhumvit_stations.sort(key=lambda x: x.name)  # In practice, you'd sort by station order
        
        for i in range(len(sukhumvit_stations) - 1):
            from_station = sukhumvit_stations[i]
            to_station = sukhumvit_stations[i + 1]
            
            routes.append(Route(
                from_station=from_station.id,
                to_station=to_station.id,
                transport_type="train",
                duration_minutes=3,
                distance_km=1.2,
                avg_travel_time_minutes=3,
                service_frequency_minutes=4,
                base_cost=17
            ))
            
            # Create reverse route
            routes.append(Route(
                from_station=to_station.id,
                to_station=from_station.id,
                transport_type="train",
                duration_minutes=3,
                distance_km=1.2,
                avg_travel_time_minutes=3,
                service_frequency_minutes=4,
                base_cost=17
            ))
        
        db.add_all(routes)
        db.flush()
        
        # 12. Create Fare Rules
        print("Creating fare rules...")
        fare_rules = []
        for route in routes:
            for passenger_type in passenger_types:
                base_price = route.base_cost or 17
                discount = passenger_type.discount_percentage / 100
                final_price = base_price * (1 - discount)
                
                fare_rules.append(FareRule(
                    route_id=route.id,
                    passenger_type_id=passenger_type.id,
                    price=final_price,
                    valid_from=datetime.now().date()
                ))
        
        db.add_all(fare_rules)
        
        # Commit all changes
        db.commit()
        print("✅ Successfully created seed data for Bangkok Train Transport System!")
        print(f"Created:")
        print(f"  - {len(passenger_types)} passenger types")
        print(f"  - {len(roles)} user roles")
        print(f"  - 1 region (Bangkok)")
        print(f"  - {len(companies)} train companies")
        print(f"  - {len(train_lines)} train lines")
        print(f"  - {len(distance_zones)} distance zones")
        print(f"  - {len(stations)} stations")
        print(f"  - {len(transfer_points)} transfer points")
        print(f"  - {len(facilities)} station facilities")
        print(f"  - {len(train_services)} train services")
        print(f"  - {len(routes)} routes")
        print(f"  - {len(fare_rules)} fare rules")
        
    except Exception as e:
        print(f"❌ Error creating seed data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_seed_data()