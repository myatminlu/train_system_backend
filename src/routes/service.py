from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
import heapq
from decimal import Decimal
from sqlalchemy.orm import Session
from src.models import Station, TransferPoint, TrainLine, FareRule, PassengerType, Route
from src.routes.schemas import (
    RouteRequest, RouteOption, RouteSegment, RouteSummary, NetworkNode, NetworkEdge,
    RouteAlternativesRequest
)
import uuid

class NetworkGraph:
    """Graph representation of the train network for route planning"""
    
    def __init__(self):
        self.nodes: Dict[int, NetworkNode] = {}
        self.edges: Dict[int, List[NetworkEdge]] = {}
        self.station_line_map: Dict[int, List[int]] = {}
        
    def add_node(self, node: NetworkNode):
        """Add a station node to the graph"""
        self.nodes[node.station_id] = node
        if node.station_id not in self.edges:
            self.edges[node.station_id] = []
            
        # Track which lines serve this station
        if node.line_id:
            if node.station_id not in self.station_line_map:
                self.station_line_map[node.station_id] = []
            if node.line_id not in self.station_line_map[node.station_id]:
                self.station_line_map[node.station_id].append(node.line_id)
    
    def add_edge(self, edge: NetworkEdge):
        """Add a connection between stations"""
        if edge.from_station_id not in self.edges:
            self.edges[edge.from_station_id] = []
        self.edges[edge.from_station_id].append(edge)
    
    def get_neighbors(self, station_id: int) -> List[NetworkEdge]:
        """Get all direct connections from a station"""
        return self.edges.get(station_id, [])
    
    def is_interchange_station(self, station_id: int) -> bool:
        """Check if a station serves multiple lines (interchange)"""
        return len(self.station_line_map.get(station_id, [])) > 1


class RouteCalculator:
    """Main route calculation service using Dijkstra's algorithm"""
    
    def __init__(self, db: Session):
        self.db = db
        self.graph = NetworkGraph()
        self._build_network_graph()
    
    def _build_network_graph(self):
        """Build the network graph from database"""
        # Load all stations as nodes
        stations = self.db.query(Station).all()
        for station in stations:
            node = NetworkNode(
                station_id=station.id,
                station_name=station.name,
                line_id=station.line_id,
                line_name=station.line.name if station.line else None,
                lat=station.lat,
                long=station.long,
                is_interchange=station.is_interchange
            )
            self.graph.add_node(node)
        
        # Load train line connections (sequential stations on same line)
        lines = self.db.query(TrainLine).all()
        for line in lines:
            line_stations = self.db.query(Station).filter(
                Station.line_id == line.id
            ).order_by(Station.name).all()  # In real system, would order by station sequence
            
            # Create edges between consecutive stations on the line
            for i in range(len(line_stations) - 1):
                current_station = line_stations[i]
                next_station = line_stations[i + 1]
                
                # Calculate approximate travel time (2-4 minutes between stations)
                duration = 3  # Average 3 minutes between stations
                
                # Get fare for this segment
                base_fare = self._get_base_fare(line.id, current_station.id, next_station.id)
                
                # Forward direction
                edge = NetworkEdge(
                    from_station_id=current_station.id,
                    to_station_id=next_station.id,
                    transport_type="train",
                    duration_minutes=duration,
                    cost=base_fare,
                    distance_km=None,  # Would be calculated based on coordinates
                    line_id=line.id
                )
                self.graph.add_edge(edge)
                
                # Reverse direction
                edge_reverse = NetworkEdge(
                    from_station_id=next_station.id,
                    to_station_id=current_station.id,
                    transport_type="train",
                    duration_minutes=duration,
                    cost=base_fare,
                    distance_km=None,
                    line_id=line.id
                )
                self.graph.add_edge(edge_reverse)
        
        # Load transfer connections
        transfers = self.db.query(TransferPoint).filter(
            TransferPoint.is_active == True
        ).all()
        
        for transfer in transfers:
            # Transfer from A to B
            transfer_edge = NetworkEdge(
                from_station_id=transfer.station_a_id,
                to_station_id=transfer.station_b_id,
                transport_type="transfer",
                duration_minutes=transfer.walking_time_minutes,
                cost=transfer.transfer_fee,
                distance_km=None,
                transfer_time_minutes=transfer.walking_time_minutes
            )
            self.graph.add_edge(transfer_edge)
            
            # Transfer from B to A (bidirectional)
            transfer_edge_reverse = NetworkEdge(
                from_station_id=transfer.station_b_id,
                to_station_id=transfer.station_a_id,
                transport_type="transfer",
                duration_minutes=transfer.walking_time_minutes,
                cost=transfer.transfer_fee,
                distance_km=None,
                transfer_time_minutes=transfer.walking_time_minutes
            )
            self.graph.add_edge(transfer_edge_reverse)
    
    def _get_base_fare(self, line_id: int, from_station_id: int, to_station_id: int) -> Decimal:
        """Get base fare for a segment"""
        # Simplified fare calculation - base fare of 15 THB
        # In a real system, this would calculate based on distance, zones, etc.
        return Decimal("15.00")
    
    def calculate_route(self, request: RouteRequest) -> List[RouteOption]:
        """Calculate optimal routes using Dijkstra's algorithm"""
        routes = []
        
        # Primary route with requested optimization
        primary_route = self._dijkstra_shortest_path(
            request.from_station_id,
            request.to_station_id,
            request.optimization,
            request.max_walking_time,
            request.max_transfers,
            request.departure_time
        )
        
        if primary_route:
            routes.append(primary_route)
        
        # Generate alternative routes if primary route found
        if primary_route and len(routes) < 3:
            # Try different optimization strategies for alternatives
            alt_optimizations = ["time", "cost", "transfers"]
            alt_optimizations.remove(request.optimization)
            
            for alt_opt in alt_optimizations:
                if len(routes) >= 3:
                    break
                    
                alt_route = self._dijkstra_shortest_path(
                    request.from_station_id,
                    request.to_station_id,
                    alt_opt,
                    request.max_walking_time,
                    request.max_transfers,
                    request.departure_time,
                    exclude_route=primary_route
                )
                
                if alt_route and self._is_significantly_different(alt_route, routes):
                    routes.append(alt_route)
        
        return routes
    
    def _dijkstra_shortest_path(
        self,
        start_id: int,
        end_id: int,
        optimization: str,
        max_walking_time: int,
        max_transfers: int,
        departure_time: Optional[datetime] = None,
        exclude_route: Optional[RouteOption] = None
    ) -> Optional[RouteOption]:
        """Dijkstra's algorithm implementation for route finding"""
        
        if start_id == end_id:
            return None
        
        # Priority queue: (cost, station_id, path, transfers, walking_time)
        pq = [(0, start_id, [], 0, 0, None)]  # last param is previous line_id
        visited: Set[int] = set()
        distances: Dict[int, float] = {start_id: 0}
        
        while pq:
            current_cost, current_station, path, transfers, walking_time, prev_line_id = heapq.heappop(pq)
            
            if current_station in visited:
                continue
                
            visited.add(current_station)
            
            # Found destination
            if current_station == end_id:
                return self._construct_route_option(
                    path, start_id, end_id, departure_time, optimization
                )
            
            # Check transfer and walking time constraints
            if transfers > max_transfers or walking_time > max_walking_time:
                continue
            
            # Explore neighbors
            for edge in self.graph.get_neighbors(current_station):
                next_station = edge.to_station_id
                
                if next_station in visited:
                    continue
                
                # Calculate cost based on optimization preference
                edge_cost = self._calculate_edge_cost(edge, optimization)
                new_cost = current_cost + edge_cost
                
                # Track transfers and walking time
                new_transfers = transfers
                new_walking_time = walking_time
                
                if edge.transport_type == "transfer":
                    new_transfers += 1
                    new_walking_time += edge.duration_minutes
                elif edge.transport_type == "train" and prev_line_id and prev_line_id != edge.line_id:
                    new_transfers += 1
                
                # Skip if constraints exceeded
                if new_transfers > max_transfers or new_walking_time > max_walking_time:
                    continue
                
                # Add to queue if better path found
                if next_station not in distances or new_cost < distances[next_station]:
                    distances[next_station] = new_cost
                    new_path = path + [edge]
                    heapq.heappush(pq, (
                        new_cost, next_station, new_path, new_transfers, 
                        new_walking_time, edge.line_id
                    ))
        
        return None  # No route found
    
    def _calculate_edge_cost(self, edge: NetworkEdge, optimization: str) -> float:
        """Calculate edge cost based on optimization preference"""
        base_time = float(edge.duration_minutes)
        base_cost = float(edge.cost)
        
        if optimization == "time":
            return base_time
        elif optimization == "cost":
            return base_cost
        elif optimization == "transfers":
            # Heavily penalize transfers
            if edge.transport_type == "transfer":
                return base_time * 5  # 5x penalty for transfers
            return base_time
        else:
            # Balanced approach
            return base_time + (base_cost / 10)
    
    def _construct_route_option(
        self, 
        path: List[NetworkEdge], 
        start_id: int, 
        end_id: int,
        departure_time: Optional[datetime],
        optimization: str
    ) -> RouteOption:
        """Construct RouteOption from path"""
        
        if not departure_time:
            departure_time = datetime.now().replace(second=0, microsecond=0)
        
        segments = []
        current_time = departure_time
        total_cost = Decimal('0')
        total_duration = 0
        total_transfers = 0
        walking_time = 0
        lines_used = set()
        
        for i, edge in enumerate(path):
            from_station = self.graph.nodes[edge.from_station_id]
            to_station = self.graph.nodes[edge.to_station_id]
            
            # Track transfers
            if edge.transport_type == "transfer":
                total_transfers += 1
                walking_time += edge.duration_minutes
            
            # Track lines used
            if edge.line_id:
                lines_used.add(edge.line_id)
            
            segment = RouteSegment(
                segment_order=i + 1,
                transport_type=edge.transport_type,
                from_station_id=edge.from_station_id,
                from_station_name=from_station.station_name,
                to_station_id=edge.to_station_id,
                to_station_name=to_station.station_name,
                line_id=edge.line_id,
                line_name=to_station.line_name,
                line_color=None,  # Would get from database
                duration_minutes=edge.duration_minutes,
                distance_km=edge.distance_km,
                cost=edge.cost,
                departure_time=current_time,
                arrival_time=current_time + timedelta(minutes=edge.duration_minutes),
                instructions=self._generate_instructions(edge, from_station, to_station),
                platform_info=None
            )
            
            segments.append(segment)
            total_cost += edge.cost
            total_duration += edge.duration_minutes
            current_time += timedelta(minutes=edge.duration_minutes)
        
        # Get line names
        line_names = []
        if lines_used:
            lines = self.db.query(TrainLine).filter(
                TrainLine.id.in_(lines_used)
            ).all()
            line_names = [line.name for line in lines]
        
        summary = RouteSummary(
            total_duration_minutes=total_duration,
            total_cost=total_cost,
            total_distance_km=None,  # Would calculate from segments
            total_transfers=total_transfers,
            total_walking_time_minutes=walking_time,
            departure_time=departure_time,
            arrival_time=departure_time + timedelta(minutes=total_duration),
            lines_used=line_names
        )
        
        # Calculate optimization score
        score = self._calculate_optimization_score(summary, optimization)
        
        return RouteOption(
            route_id=str(uuid.uuid4()),
            segments=segments,
            summary=summary,
            optimization_score=score,
            carbon_footprint_kg=None  # Would calculate based on distance
        )
    
    def _generate_instructions(
        self, 
        edge: NetworkEdge, 
        from_station: NetworkNode, 
        to_station: NetworkNode
    ) -> str:
        """Generate human-readable instructions for a route segment"""
        if edge.transport_type == "train":
            return f"Take {to_station.line_name} from {from_station.station_name} to {to_station.station_name}"
        elif edge.transport_type == "transfer":
            return f"Walk {edge.duration_minutes} minutes from {from_station.station_name} to {to_station.station_name}"
        else:
            return f"Travel from {from_station.station_name} to {to_station.station_name}"
    
    def _calculate_optimization_score(self, summary: RouteSummary, optimization: str) -> float:
        """Calculate optimization score for ranking routes"""
        if optimization == "time":
            return 1000 - summary.total_duration_minutes  # Higher score = shorter time
        elif optimization == "cost":
            return 1000 - float(summary.total_cost)  # Higher score = lower cost
        elif optimization == "transfers":
            return 1000 - (summary.total_transfers * 100)  # Higher score = fewer transfers
        else:
            # Balanced score
            time_score = 500 - (summary.total_duration_minutes / 2)
            cost_score = 500 - (float(summary.total_cost) / 2)
            return time_score + cost_score
    
    def _is_significantly_different(
        self, 
        route: RouteOption, 
        existing_routes: List[RouteOption]
    ) -> bool:
        """Check if route is significantly different from existing routes"""
        for existing in existing_routes:
            # Compare key metrics
            time_diff = abs(route.summary.total_duration_minutes - existing.summary.total_duration_minutes)
            cost_diff = abs(float(route.summary.total_cost - existing.summary.total_cost))
            transfer_diff = abs(route.summary.total_transfers - existing.summary.total_transfers)
            
            # If very similar in all aspects, consider it not significantly different
            if time_diff < 10 and cost_diff < 10 and transfer_diff == 0:
                return False
        
        return True


class RouteService:
    """High-level route planning service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.calculator = RouteCalculator(db)
    
    def plan_route(self, request: RouteRequest) -> List[RouteOption]:
        """Plan routes based on request"""
        # Validate stations exist
        from_station = self.db.query(Station).filter(Station.id == request.from_station_id).first()
        to_station = self.db.query(Station).filter(Station.id == request.to_station_id).first()
        
        if not from_station or not to_station:
            return []
        
        return self.calculator.calculate_route(request)
    
    def get_route_alternatives(self, request: RouteAlternativesRequest) -> List[RouteOption]:
        """Get alternative routes with specific preferences"""
        base_request = RouteRequest(
            from_station_id=request.from_station_id,
            to_station_id=request.to_station_id,
            departure_time=request.departure_time,
            passenger_type_id=request.passenger_type_id,
            max_alternatives=request.max_alternatives
        )
        
        routes = self.calculator.calculate_route(base_request)
        
        # Filter out avoided lines
        if request.avoid_lines:
            routes = self._filter_avoided_lines(routes, request.avoid_lines)
        
        # Boost preferred lines
        if request.prefer_lines:
            routes = self._boost_preferred_lines(routes, request.prefer_lines)
        
        return routes[:request.max_alternatives]
    
    def _filter_avoided_lines(self, routes: List[RouteOption], avoid_lines: List[int]) -> List[RouteOption]:
        """Filter out routes that use avoided lines"""
        filtered = []
        for route in routes:
            uses_avoided = False
            for segment in route.segments:
                if segment.line_id in avoid_lines:
                    uses_avoided = True
                    break
            if not uses_avoided:
                filtered.append(route)
        return filtered
    
    def _boost_preferred_lines(self, routes: List[RouteOption], prefer_lines: List[int]) -> List[RouteOption]:
        """Boost optimization scores for routes using preferred lines"""
        for route in routes:
            for segment in route.segments:
                if segment.line_id in prefer_lines:
                    route.optimization_score += 100  # Bonus for preferred lines
                    break
        
        # Re-sort by optimization score
        return sorted(routes, key=lambda r: r.optimization_score, reverse=True)