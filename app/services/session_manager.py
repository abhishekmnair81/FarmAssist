import time
import uuid
import json
import os
from typing import Dict, TypedDict, Optional

class SessionInfo(TypedDict):
    thread_id: str
    last_active: float

# In-memory session store (resets after 3 mins of inactivity)
# Format: { sender_id: { "thread_id": str, "last_active": float } }
_sessions: Dict[str, SessionInfo] = {}

LOCATIONS_DB_PATH = "/app/data/locations.json"

def _load_locations() -> dict:
    if os.path.exists(LOCATIONS_DB_PATH):
        try:
            with open(LOCATIONS_DB_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_locations(data: dict):
    os.makedirs(os.path.dirname(LOCATIONS_DB_PATH), exist_ok=True)
    with open(LOCATIONS_DB_PATH, "w") as f:
        json.dump(data, f)

def update_user_location(sender_id: str, lat: float, lon: float):
    """Permanently caches the user's physical farm location."""
    locations = _load_locations()
    locations[sender_id] = {"lat": lat, "lon": lon}
    _save_locations(locations)

def get_user_location(sender_id: str) -> Optional[Dict[str, float]]:
    """Retrieves the user's permanently cached location, if any."""
    locations = _load_locations()
    return locations.get(sender_id)

def sweep_expired_sessions(timeout_seconds: int = 180):
    """Passively cleans up expired dialogue sessions to prevent memory leaks."""
    current_time = time.time()
    expired_senders = [
        sender_id for sender_id, info in _sessions.items()
        if (current_time - info["last_active"]) > timeout_seconds
    ]
    for sender_id in expired_senders:
        del _sessions[sender_id]

async def get_or_create_thread_id(sender_id: str, timeout_seconds: int = 180) -> str:
    """
    Retrieves the active thread_id for a sender, or creates a new one if 
    their conversational session expired due to inactivity (> timeout_seconds).
    Also performs a passive sweep of the entire session store.
    """
    # Passively sweep to prevent memory leaks
    sweep_expired_sessions(timeout_seconds)
    
    current_time = time.time()
    session = _sessions.get(sender_id)
    
    if session and (current_time - session["last_active"]) <= timeout_seconds:
        # User is active within TTL, update timestamp and return existing thread
        session["last_active"] = current_time
        return session["thread_id"]
        
    # Generate fresh thread UUID for clean LangGraph context
    new_thread_id = str(uuid.uuid4())
    _sessions[sender_id] = {
        "thread_id": new_thread_id,
        "last_active": current_time
    }
    
    return new_thread_id
