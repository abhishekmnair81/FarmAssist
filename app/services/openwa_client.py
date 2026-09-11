import httpx
import base64
from app.config import settings
import logging

logger = logging.getLogger(__name__)

async def send_text_message(phone_number: str, text: str):
    """
    Sends a text message via OpenWA Gateway.
    """
    url = f"{settings.OPENWA_API_URL}/sessions/{settings.OPENWA_SESSION_ID}/messages/send-text"
    
    headers = {}
    if settings.OPENWA_API_KEY:
        headers["X-API-Key"] = settings.OPENWA_API_KEY
        
    payload = {
        "chatId": phone_number,
        "text": text
    }
    logger.info(f"Preparing to send text to {phone_number}: {repr(text)}")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
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
    url = f"{settings.OPENWA_API_URL}/sessions/{settings.OPENWA_SESSION_ID}/messages/send-audio"
    
    headers = {}
    if settings.OPENWA_API_KEY:
        headers["X-API-Key"] = settings.OPENWA_API_KEY
        
    base64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    
    payload = {
        "chatId": phone_number,
        "base64": base64_audio,
        "ptt": True
    }
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            logger.info(f"Successfully sent voice message to {phone_number}")
        except httpx.HTTPError as e:
            logger.error(f"Error sending voice message to {phone_number}: {e}")
            raise
