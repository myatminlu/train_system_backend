from fastapi import WebSocket, WebSocketDisconnect
from typing import List, Dict, Set
import json
import asyncio
from datetime import datetime

from src.schedules.realtime_service import realtime_simulator

class WebSocketManager:
    """Manager for WebSocket connections and real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.line_subscriptions: Dict[int, Set[WebSocket]] = {}
        self.station_subscriptions: Dict[int, Set[WebSocket]] = {}
        self._broadcast_task = None
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Start broadcasting task if not already running
        if not self._broadcast_task or self._broadcast_task.done():
            self._broadcast_task = asyncio.create_task(self._broadcast_updates())
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from subscriptions
        for line_subs in self.line_subscriptions.values():
            line_subs.discard(websocket)
        
        for station_subs in self.station_subscriptions.values():
            station_subs.discard(websocket)
    
    async def subscribe_to_line(self, websocket: WebSocket, line_id: int):
        """Subscribe WebSocket to line updates"""
        if line_id not in self.line_subscriptions:
            self.line_subscriptions[line_id] = set()
        self.line_subscriptions[line_id].add(websocket)
        
        # Send current line status
        from src.schedules.service import ScheduleCalculationService
        from src.database import get_db
        
        # This would normally use dependency injection
        # For now, we'll send a simple status message
        await self.send_personal_message(websocket, {
            "type": "subscription_confirmed",
            "line_id": line_id,
            "timestamp": datetime.now().isoformat()
        })
    
    async def subscribe_to_station(self, websocket: WebSocket, station_id: int):
        """Subscribe WebSocket to station updates"""
        if station_id not in self.station_subscriptions:
            self.station_subscriptions[station_id] = set()
        self.station_subscriptions[station_id].add(websocket)
        
        await self.send_personal_message(websocket, {
            "type": "subscription_confirmed",
            "station_id": station_id,
            "timestamp": datetime.now().isoformat()
        })
    
    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except:
            # Connection might be closed
            self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        message_text = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_text)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_line_subscribers(self, line_id: int, message: dict):
        """Broadcast message to line subscribers"""
        if line_id not in self.line_subscriptions:
            return
        
        message_text = json.dumps(message)
        disconnected = []
        
        for connection in self.line_subscriptions[line_id].copy():
            try:
                await connection.send_text(message_text)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.line_subscriptions[line_id].discard(connection)
    
    async def broadcast_to_station_subscribers(self, station_id: int, message: dict):
        """Broadcast message to station subscribers"""
        if station_id not in self.station_subscriptions:
            return
        
        message_text = json.dumps(message)
        disconnected = []
        
        for connection in self.station_subscriptions[station_id].copy():
            try:
                await connection.send_text(message_text)
            except:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.station_subscriptions[station_id].discard(connection)
    
    async def _broadcast_updates(self):
        """Background task to broadcast real-time updates"""
        while self.active_connections:
            try:
                # Get current system status
                current_time = datetime.now()
                
                # Broadcast service alerts
                active_alerts = realtime_simulator.get_service_alerts(active_only=True)
                if active_alerts:
                    alert_message = {
                        "type": "service_alerts",
                        "alerts": [
                            {
                                "id": alert.id,
                                "title": alert.title,
                                "severity": alert.severity,
                                "affected_lines": alert.affected_lines,
                                "affected_stations": alert.affected_stations
                            }
                            for alert in active_alerts[-5:]  # Last 5 alerts
                        ],
                        "timestamp": current_time.isoformat()
                    }
                    await self.broadcast_to_all(alert_message)
                
                # Broadcast train positions (sample)
                active_trains = realtime_simulator.get_active_trains()
                if active_trains:
                    train_message = {
                        "type": "train_positions",
                        "trains": [
                            {
                                "train_id": train.train_id,
                                "line_id": train.line_id,
                                "current_station_id": train.current_station_id,
                                "delay_minutes": train.delay_minutes,
                                "occupancy_level": train.occupancy_level
                            }
                            for train in active_trains[:10]  # Sample of trains
                        ],
                        "timestamp": current_time.isoformat()
                    }
                    await self.broadcast_to_all(train_message)
                
                # Wait before next broadcast
                await asyncio.sleep(30)  # Broadcast every 30 seconds
                
            except Exception as e:
                print(f"Error in broadcast task: {e}")
                await asyncio.sleep(5)  # Wait before retrying

# Global WebSocket manager instance
ws_manager = WebSocketManager()

# WebSocket endpoint function
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for real-time updates"""
    await ws_manager.connect(websocket)
    
    try:
        while True:
            # Wait for client messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Handle subscription requests
                if message.get("type") == "subscribe_line":
                    line_id = message.get("line_id")
                    if line_id:
                        await ws_manager.subscribe_to_line(websocket, line_id)
                
                elif message.get("type") == "subscribe_station":
                    station_id = message.get("station_id")
                    if station_id:
                        await ws_manager.subscribe_to_station(websocket, station_id)
                
                elif message.get("type") == "ping":
                    # Respond to ping with pong
                    await ws_manager.send_personal_message(websocket, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
            except json.JSONDecodeError:
                # Invalid JSON, ignore
                pass
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)