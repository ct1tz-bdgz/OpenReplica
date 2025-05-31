"""
Event serialization for OpenReplica
"""
import json
from typing import Dict, Any, Union
from datetime import datetime

from .base import Event
from .action import Action, ACTION_TYPE_MAP, ActionType
from .observation import Observation, OBSERVATION_TYPE_MAP, ObservationType


class EventSerializer:
    """Handles serialization and deserialization of events"""
    
    @staticmethod
    def serialize_event(event: Event) -> str:
        """Serialize an event to JSON string"""
        return json.dumps(event.to_dict(), default=EventSerializer._json_serializer)
    
    @staticmethod
    def deserialize_event(data: Union[str, Dict[str, Any]]) -> Event:
        """Deserialize JSON string or dict to an event"""
        if isinstance(data, str):
            data = json.loads(data)
        
        event_type = data.get("event_type")
        
        if event_type == "action":
            action_type = ActionType(data.get("action_type"))
            action_class = ACTION_TYPE_MAP.get(action_type, Action)
            return action_class.from_dict(data)
        
        elif event_type == "observation":
            observation_type = ObservationType(data.get("observation_type"))
            observation_class = OBSERVATION_TYPE_MAP.get(observation_type, Observation)
            return observation_class.from_dict(data)
        
        else:
            raise ValueError(f"Unknown event type: {event_type}")
    
    @staticmethod
    def serialize_events(events: list[Event]) -> str:
        """Serialize a list of events to JSON string"""
        return json.dumps(
            [event.to_dict() for event in events],
            default=EventSerializer._json_serializer
        )
    
    @staticmethod
    def deserialize_events(data: Union[str, list[Dict[str, Any]]]) -> list[Event]:
        """Deserialize JSON string or list of dicts to events"""
        if isinstance(data, str):
            data = json.loads(data)
        
        return [EventSerializer.deserialize_event(event_data) for event_data in data]
    
    @staticmethod
    def _json_serializer(obj: Any) -> str:
        """Custom JSON serializer for non-serializable objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    @staticmethod
    def event_to_websocket_message(event: Event) -> Dict[str, Any]:
        """Convert event to WebSocket message format"""
        return {
            "type": "event",
            "data": event.to_dict(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def events_to_websocket_message(events: list[Event]) -> Dict[str, Any]:
        """Convert list of events to WebSocket message format"""
        return {
            "type": "events",
            "data": [event.to_dict() for event in events],
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def error_to_websocket_message(error: str, error_type: str = "error") -> Dict[str, Any]:
        """Convert error to WebSocket message format"""
        return {
            "type": "error",
            "data": {
                "error": error,
                "error_type": error_type
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def status_to_websocket_message(status: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Convert status update to WebSocket message format"""
        return {
            "type": "status",
            "data": {
                "status": status,
                "data": data or {}
            },
            "timestamp": datetime.utcnow().isoformat()
        }


def serialize_for_storage(event: Event) -> Dict[str, Any]:
    """Serialize event for database storage"""
    data = event.to_dict()
    # Ensure datetime fields are properly serialized
    if "timestamp" in data and isinstance(data["timestamp"], datetime):
        data["timestamp"] = data["timestamp"].isoformat()
    return data


def deserialize_from_storage(data: Dict[str, Any]) -> Event:
    """Deserialize event from database storage"""
    # Convert ISO timestamp back to datetime if needed
    if "timestamp" in data and isinstance(data["timestamp"], str):
        try:
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        except ValueError:
            pass  # Keep as string if parsing fails
    
    return EventSerializer.deserialize_event(data)
