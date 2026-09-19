import re
import edge_tts
import asyncio
import logging

logger = logging.getLogger(__name__)
import io

def detect_voice(text: str, default_voice: str = "en-IN-NeerjaNeural") -> str:
    """
    Detects the best Indian neural voice based on Unicode script matching.
    """
    if re.search(r"[\u0C80-\u0CFF]", text):
        return "kn-IN-GaganNeural"
    elif re.search(r"[\u0D00-\u0D7F]", text):
        return "ml-IN-SobhanaNeural"
    elif re.search(r"[\u0900-\u097F]", text):
        return "hi-IN-SwaraNeural"
    elif re.search(r"[\u0B80-\u0BFF]", text):
        return "ta-IN-PallaviNeural"
    elif re.search(r"[\u0C00-\u0C7F]", text):
        return "te-IN-ShrutiNeural"
    return default_voice

import subprocess
import shutil
import tempfile
import os
from app.services.text_cleaner import clean_text_for_speech

async def synthesize_speech(text: str, voice: str) -> bytes:
    """
    Synthesize text to speech using edge-tts.
    Strips markdown, emojis, citation brackets, and formats units for natural human speech.
    Converts the output to OGG Opus via ffmpeg if available for WhatsApp PTT compatibility.
    Falls back gracefully to clean MP3 bytes if ffmpeg is not installed.
    """
    spoken_text = clean_text_for_speech(text)
    if not spoken_text:
        spoken_text = text

    logger.info(f"Preparing to synthesize speech for voice {voice}: {repr(spoken_text[:120])}")
    communicate = edge_tts.Communicate(spoken_text, voice)
    audio_stream = io.BytesIO()
    
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_stream.write(chunk["data"])
            
    mp3_bytes = audio_stream.getvalue()
    audio_stream.close()

    # If ffmpeg is not available on the host system, return native MP3 bytes
    if not shutil.which("ffmpeg"):
        logger.info("ffmpeg not found on system; returning native MP3 audio bytes.")
        return mp3_bytes
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_in:
        temp_in.write(mp3_bytes)
        temp_in_path = temp_in.name
        
    temp_out_path = temp_in_path.replace(".mp3", ".ogg")
    
    try:
        # Transcode to WhatsApp PTT format (OGG Opus)
        process = subprocess.run(
            ['ffmpeg', '-y', '-i', temp_in_path, '-c:a', 'libopus', '-b:a', '32k', '-ar', '16000', '-ac', '1', '-vbr', 'on', temp_out_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        if process.returncode != 0:
            logger.warning(f"FFmpeg conversion failed ({process.stderr.decode()[:100]}); falling back to MP3.")
            return mp3_bytes
            
        with open(temp_out_path, "rb") as f:
            ogg_bytes = f.read()
        return ogg_bytes
            
    except Exception as e:
        logger.warning(f"Error during ffmpeg conversion: {e}; falling back to MP3.")
        return mp3_bytes
    finally:
        if os.path.exists(temp_in_path):
            try:
                os.remove(temp_in_path)
            except Exception:
                pass
        if os.path.exists(temp_out_path):
            try:
                os.remove(temp_out_path)
            except Exception:
                pass
