import httpx
import base64
import collections
import time
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Keep a ring-buffer of recently sent messages to prevent echo/infinite loops
_recently_sent_messages = collections.deque(maxlen=100)
_recently_sent_audio_lengths = collections.deque(maxlen=50)

def record_sent_message(text: str):
    """Records an outbound message text so webhook echos can be identified and ignored."""
    if text:
        _recently_sent_messages.append((text.strip(), time.time()))

def is_bot_own_message(text: str) -> bool:
    """Checks if the given text matches a recently sent outbound message."""
    if not text:
        return False
    cleaned = text.strip()
    now = time.time()
    for sent_text, timestamp in list(_recently_sent_messages):
        # Match within 5 minutes
        if now - timestamp < 300 and (cleaned == sent_text or cleaned in sent_text or sent_text in cleaned):
            return True
    return False

def record_sent_audio(audio_bytes: bytes):
    """Records byte length and timestamp of outbound audio to ignore echoes."""
    if audio_bytes:
        _recently_sent_audio_lengths.append((len(audio_bytes), time.time()))

def is_bot_own_audio(audio_bytes: bytes) -> bool:
    """Checks if incoming audio matches recently sent outbound audio."""
    if not audio_bytes:
        return False
    now = time.time()
    size = len(audio_bytes)
    for sent_size, timestamp in list(_recently_sent_audio_lengths):
        if now - timestamp < 120 and abs(size - sent_size) < 10:
            return True
    return False

def get_openwa_base_url() -> str:
    """Returns the base API URL for OpenWA, ensuring the /api suffix is present."""
    base = settings.OPENWA_API_URL.rstrip('/')
    if not base.endswith('/api'):
        base = f"{base}/api"
    return base

def format_chat_id(phone: str) -> str:
    """Ensures recipient ID has a valid suffix expected by OpenWA (@c.us, @lid, @g.us)."""
    cleaned = phone.strip()
    if cleaned.endswith("@c.us") or cleaned.endswith("@lid") or cleaned.endswith("@g.us"):
        return cleaned
    # Remove any leading + sign
    cleaned = cleaned.lstrip("+")
    return f"{cleaned}@c.us"

async def send_text_message(phone_number: str, text: str):
    """
    Sends a text message via OpenWA Gateway.
    """
    url = f"{get_openwa_base_url()}/sessions/{settings.OPENWA_SESSION_ID}/messages/send-text"
    
    headers = {"Content-Type": "application/json"}
    if settings.OPENWA_API_KEY:
        headers["X-API-Key"] = settings.OPENWA_API_KEY
        headers["Authorization"] = f"Bearer {settings.OPENWA_API_KEY}"
        
    payload = {
        "chatId": format_chat_id(phone_number),
        "text": text
    }
    logger.info(f"Preparing to send text to {phone_number}: {repr(text)}")
    record_sent_message(text)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"Successfully sent text message to {phone_number}")
        except httpx.HTTPError as e:
            logger.error(f"Error sending text message to {phone_number}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Gateway response body: {e.response.text}")
            raise

async def send_voice_message(phone_number: str, audio_bytes: bytes, filename: str = "voice_reply.mp3"):
    """
    Sends a voice memo (PTT) via OpenWA Gateway.
    """
    url = f"{get_openwa_base_url()}/sessions/{settings.OPENWA_SESSION_ID}/messages/send-audio"
    
    headers = {"Content-Type": "application/json"}
    if settings.OPENWA_API_KEY:
        headers["X-API-Key"] = settings.OPENWA_API_KEY
        headers["Authorization"] = f"Bearer {settings.OPENWA_API_KEY}"
        
    base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    mimetype = "audio/ogg; codecs=opus" if audio_bytes.startswith(b"OggS") else "audio/mp3"
    
    payload = {
        "chatId": format_chat_id(phone_number),
        "base64": base64_audio,
        "mimetype": mimetype,
        "ptt": True
    }
    logger.info(f"Preparing to send voice message to {phone_number} ({len(audio_bytes)} bytes)")
    record_sent_audio(audio_bytes)
    
    async with httpx.AsyncClient(timeout=25.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"Successfully sent voice message to {phone_number}")
        except httpx.HTTPError as e:
            logger.error(f"Error sending voice message to {phone_number}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Gateway response body: {e.response.text}")
            raise

async def download_message_media(chat_id: str, message_id: str) -> bytes | None:
    """Downloads stored media for a message from OpenWA if omitted from webhook."""
    base_url = get_openwa_base_url()
    headers = {}
    if settings.OPENWA_API_KEY:
        headers["X-API-Key"] = settings.OPENWA_API_KEY
        headers["Authorization"] = f"Bearer {settings.OPENWA_API_KEY}"
        
    url = f"{base_url}/sessions/{settings.OPENWA_SESSION_ID}/messages/{chat_id}/{message_id}/media"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200 and resp.content:
                logger.info(f"Successfully downloaded {len(resp.content)} media bytes for {message_id}")
                return resp.content
            else:
                logger.warning(f"Download media returned {resp.status_code} for {message_id}: {resp.text[:100]}")
    except Exception as e:
        logger.warning(f"Failed to download media for {message_id}: {e}")
    return None

async def ensure_session_started():
    """
    Ensures that the OpenWA engine for settings.OPENWA_SESSION_ID is loaded and active.
    """
    base_url = get_openwa_base_url()
    headers = {}
    if settings.OPENWA_API_KEY:
        headers["X-API-Key"] = settings.OPENWA_API_KEY
        headers["Authorization"] = f"Bearer {settings.OPENWA_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{base_url}/sessions", headers=headers)
            if resp.status_code == 200:
                sessions = resp.json()
                for s in sessions:
                    if s.get("id") == settings.OPENWA_SESSION_ID or s.get("name") == "default":
                        if not s.get("engineLoaded"):
                            logger.info(f"OpenWA session {s.get('id')} engineLoaded is False. Starting engine...")
                            start_resp = await client.post(f"{base_url}/sessions/{s.get('id')}/start", headers=headers)
                            logger.info(f"Session start triggered: {start_resp.status_code}")
                        else:
                            logger.info(f"OpenWA session {s.get('id')} is ready and engine is loaded.")
                        return
    except Exception as e:
        logger.warning(f"Failed to verify/start OpenWA session engine: {e}")

async def register_webhook_if_needed(webhook_url: str = "http://fastapi-bot:8000/webhook"):
    """
    Helper to register the FastAPI webhook with OpenWA gateway for the current session,
    avoiding duplicate registrations.
    """
    headers = {}
    if settings.OPENWA_API_KEY:
        headers["X-API-Key"] = settings.OPENWA_API_KEY
        headers["Authorization"] = f"Bearer {settings.OPENWA_API_KEY}"
        
    base_url = get_openwa_base_url()
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check existing webhooks
            resp = await client.get(f"{base_url}/webhooks", headers=headers)
            if resp.status_code == 200:
                webhooks = resp.json()
                for wh in webhooks:
                    if wh.get("url") == webhook_url and wh.get("sessionId") == settings.OPENWA_SESSION_ID and wh.get("active"):
                        logger.info(f"OpenWA webhook already registered and active: {wh.get('id')}")
                        return

            url = f"{base_url}/sessions/{settings.OPENWA_SESSION_ID}/webhooks"
            payload = {
                "url": webhook_url,
                "events": ["message.received", "session.status"]
            }
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code in [200, 201]:
                logger.info(f"OpenWA webhook registered successfully to {webhook_url}")
            else:
                logger.warning(f"Could not register OpenWA webhook: {resp.status_code} - {resp.text}")
    except Exception as e:
        logger.warning(f"OpenWA webhook auto-registration skipped or failed: {e}")
