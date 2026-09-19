import time
import uuid
import json
import os
from typing import Dict, TypedDict, Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class SessionInfo(TypedDict):
    thread_id: str
    last_active: float

# In-memory session store (resets after 3 mins of inactivity)
# Format: { sender_id: { "thread_id": str, "last_active": float } }
_sessions: Dict[str, SessionInfo] = {}

# In-memory location cache initialized on load
_locations_cache: Optional[Dict[str, Dict[str, float]]] = None

def _get_locations_db_path() -> str:
    path = settings.LOCATIONS_DB_PATH
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    return path

def _load_locations() -> dict:
    global _locations_cache
    if _locations_cache is not None:
        return _locations_cache

    path = _get_locations_db_path()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                _locations_cache = json.load(f)
                return _locations_cache
        except Exception as e:
            logger.error(f"Error loading locations from {path}: {e}")
            _locations_cache = {}
            return _locations_cache
    _locations_cache = {}
    return _locations_cache

def _save_locations(data: dict):
    global _locations_cache
    _locations_cache = data
    path = _get_locations_db_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving locations to {path}: {e}")

def update_user_location(sender_id: str, lat: float, lon: float):
    """Permanently caches the user's physical farm location."""
    locations = _load_locations()
    user_entry = locations.get(sender_id, {})
    user_entry["lat"] = lat
    user_entry["lon"] = lon
    locations[sender_id] = user_entry
    _save_locations(locations)

def get_user_location(sender_id: str) -> Optional[Dict[str, float]]:
    """Retrieves the user's permanently cached location, if any."""
    data = _load_locations().get(sender_id)
    if data and "lat" in data and "lon" in data:
        return {"lat": data["lat"], "lon": data["lon"]}
    return None

def update_user_language(sender_id: str, language: str):
    """Permanently stores the user's preferred language."""
    locations = _load_locations()
    user_entry = locations.get(sender_id, {})
    user_entry["language"] = language
    locations[sender_id] = user_entry
    _save_locations(locations)
    logger.info(f"Updated language preference for {sender_id}: {language}")

def get_user_language(sender_id: str) -> Optional[str]:
    """Retrieves the user's saved language preference."""
    data = _load_locations().get(sender_id)
    if data and "language" in data:
        return data["language"]
    return None

def sweep_expired_sessions(timeout_seconds: Optional[int] = None):
    """Passively cleans up expired dialogue sessions to prevent memory leaks."""
    ttl = timeout_seconds if timeout_seconds is not None else settings.SESSION_TTL_SECONDS
    current_time = time.time()
    expired_senders = [
        sender_id for sender_id, info in _sessions.items()
        if (current_time - info["last_active"]) > ttl
    ]
    for sender_id in expired_senders:
        del _sessions[sender_id]

async def get_or_create_thread_id(sender_id: str, timeout_seconds: Optional[int] = None) -> str:
    """
    Retrieves the active thread_id for a sender, or creates a new one if 
    their conversational session expired due to inactivity (> timeout_seconds).
    Defaults to settings.SESSION_TTL_SECONDS (24 hours).
    """
    ttl = timeout_seconds if timeout_seconds is not None else settings.SESSION_TTL_SECONDS
    sweep_expired_sessions(ttl)
    
    current_time = time.time()
    session = _sessions.get(sender_id)
    
    if session and (current_time - session["last_active"]) <= ttl:
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
