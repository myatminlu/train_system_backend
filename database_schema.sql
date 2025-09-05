-- Enhanced Bangkok Train Transport Database Schema
-- ================================
-- Users & Roles
-- ================================
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE roles (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_has_roles (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    role_id BIGINT NOT NULL REFERENCES roles(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- Passenger Categories
-- ================================
CREATE TABLE passenger_types (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL, -- adult, child, senior, student
    discount_percentage DECIMAL(5,2) DEFAULT 0.00,
    age_min INT,
    age_max INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- Regions / Systems / Stations
-- ================================
CREATE TABLE regions (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL, -- e.g. Bangkok, Osaka
    country VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE train_companies (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL, -- e.g. BTS, BMCL (MRT), SRT
    status VARCHAR(50),
    region_id BIGINT NOT NULL REFERENCES regions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE train_lines (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL REFERENCES train_companies(id),
    name VARCHAR(255) NOT NULL, -- e.g. Sukhumvit Line, Blue Line
    color VARCHAR(20), -- Line color for UI display
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stations (
    id BIGSERIAL PRIMARY KEY,
    line_id BIGINT REFERENCES train_lines(id),
    name VARCHAR(255) NOT NULL,
    lat DECIMAL(10,6),
    long DECIMAL(10,6),
    zone_number INT,
    is_interchange BOOLEAN DEFAULT false,
    platform_count INT DEFAULT 1,
    status VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- Distance Zones for Fare Calculation
-- ================================
CREATE TABLE distance_zones (
    id BIGSERIAL PRIMARY KEY,
    line_id BIGINT NOT NULL REFERENCES train_lines(id),
    zone_number INT NOT NULL,
    base_fare DECIMAL(10,2) NOT NULL,
    per_station_fare DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- Transfer Points (Interchange Stations)
-- ================================
CREATE TABLE transfer_points (
    id BIGSERIAL PRIMARY KEY,
    station_a_id BIGINT NOT NULL REFERENCES stations(id),
    station_b_id BIGINT NOT NULL REFERENCES stations(id),
    walking_time_minutes INT DEFAULT 5,
    walking_distance_meters INT,
    transfer_fee DECIMAL(10,2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- Station Facilities
-- ================================
CREATE TABLE station_facilities (
    id BIGSERIAL PRIMARY KEY,
    station_id BIGINT NOT NULL REFERENCES stations(id),
    facility_type VARCHAR(50) NOT NULL, -- elevator, escalator, restroom, atm, shop
    is_available BOOLEAN DEFAULT true,
    location_description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- Train Services & Schedules
-- ================================
CREATE TABLE train_services (
    id BIGSERIAL PRIMARY KEY,
    line_id BIGINT NOT NULL REFERENCES train_lines(id),
    service_name VARCHAR(100), -- Express, Local, etc.
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    frequency_minutes INT NOT NULL, -- Train every X minutes
    direction VARCHAR(50), -- Northbound, Southbound, etc.
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- Service Status (Delays, Maintenance)
-- ================================
CREATE TABLE service_status (
    id BIGSERIAL PRIMARY KEY,
    line_id BIGINT REFERENCES train_lines(id),
    station_id BIGINT REFERENCES stations(id),
    status_type VARCHAR(50) NOT NULL, -- delay, maintenance, disruption
    severity VARCHAR(20) DEFAULT 'low', -- low, medium, high, critical
    message TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- Routes & Fare Rules
-- ================================
CREATE TABLE routes (
    id BIGSERIAL PRIMARY KEY,
    from_station BIGINT NOT NULL REFERENCES stations(id),
    to_station BIGINT NOT NULL REFERENCES stations(id),
    transport_type VARCHAR(50) NOT NULL, -- train, walk, bus
    duration_minutes INT,
    distance_km DECIMAL(8,2),
    avg_travel_time_minutes INT,
    service_frequency_minutes INT,
    base_cost DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Passenger-based pricing
CREATE TABLE fare_rules (
    id BIGSERIAL PRIMARY KEY,
    route_id BIGINT NOT NULL REFERENCES routes(id),
    passenger_type_id BIGINT NOT NULL REFERENCES passenger_types(id),
    price DECIMAL(10,2) NOT NULL,
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_to DATE
);

-- ================================
-- Journey (planned trips, not tickets)
-- ================================
CREATE TABLE journeys (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    total_cost DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE journey_segments (
    id BIGSERIAL PRIMARY KEY,
    journey_id BIGINT NOT NULL REFERENCES journeys(id),
    route_id BIGINT NOT NULL REFERENCES routes(id),
    segment_order INT NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- Tickets & Bookings (without payment)
-- ================================
CREATE TABLE tickets (
    id BIGSERIAL PRIMARY KEY,
    ticket_unique_string VARCHAR(100) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL REFERENCES users(id),
    journey_id BIGINT REFERENCES journeys(id),
    passenger_type_id BIGINT NOT NULL REFERENCES passenger_types(id),
    total_amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(50) DEFAULT 'reserved', -- reserved, used, cancelled, expired
    valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    valid_until TIMESTAMP,
    qr_code_data TEXT,
    issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    issued_by BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ticket_routes (
    id BIGSERIAL PRIMARY KEY,
    ticket_id BIGINT NOT NULL REFERENCES tickets(id),
    route_id BIGINT NOT NULL REFERENCES routes(id),
    depart_station_id BIGINT NOT NULL REFERENCES stations(id),
    arrive_station_id BIGINT NOT NULL REFERENCES stations(id),
    sequence_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ================================
-- Create Indexes for Performance
-- ================================

-- User indexes
CREATE INDEX idx_users_email ON users(email);

-- Station indexes
CREATE INDEX idx_stations_line_id ON stations(line_id);
CREATE INDEX idx_stations_name ON stations(name);
CREATE INDEX idx_stations_location ON stations(lat, long);
CREATE INDEX idx_stations_interchange ON stations(is_interchange);

-- Route indexes
CREATE INDEX idx_routes_from_station ON routes(from_station);
CREATE INDEX idx_routes_to_station ON routes(to_station);
CREATE INDEX idx_routes_stations ON routes(from_station, to_station);

-- Transfer point indexes
CREATE INDEX idx_transfer_points_station_a ON transfer_points(station_a_id);
CREATE INDEX idx_transfer_points_station_b ON transfer_points(station_b_id);
CREATE INDEX idx_transfer_points_active ON transfer_points(is_active);

-- Service status indexes
CREATE INDEX idx_service_status_line_id ON service_status(line_id);
CREATE INDEX idx_service_status_station_id ON service_status(station_id);
CREATE INDEX idx_service_status_active ON service_status(is_active);

-- Ticket indexes
CREATE INDEX idx_tickets_user_id ON tickets(user_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_valid_dates ON tickets(valid_from, valid_until);
CREATE INDEX idx_ticket_routes_ticket_id ON ticket_routes(ticket_id);