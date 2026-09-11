import httpx
from app.config import settings

async def transcribe_audio_groq(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """
    Transcribes raw audio bytes using Groq Cloud's whisper-large-v3.
    """
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}"
    }
    
    files = {
        "file": (filename, audio_bytes, "audio/ogg"),
    }
    
    data = {
        "model": "whisper-large-v3-turbo",
        "response_format": "json",
        "prompt": "Hello. नमस्ते. வணக்கம். നമസ്കാരം. English, Hindi, Tamil, Malayalam."
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        
        result = response.json()
        return result.get("text", "")
