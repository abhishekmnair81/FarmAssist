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

async def synthesize_speech(text: str, voice: str) -> bytes:
    """
    Synthesize text to speech using edge-tts.
    Converts the output to OGG Opus via ffmpeg for WhatsApp PTT compatibility.
    """
    logger.info(f"Preparing to synthesize speech for voice {voice}: {repr(text)}")
    communicate = edge_tts.Communicate(text, voice)
    audio_stream = io.BytesIO()
    
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_stream.write(chunk["data"])
            
    import tempfile
    import os
    
    mp3_bytes = audio_stream.getvalue()
    audio_stream.close()
    
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
            raise RuntimeError(f"FFmpeg conversion failed: {process.stderr.decode()}")
            
        with open(temp_out_path, "rb") as f:
            ogg_bytes = f.read()
            
    finally:
        if os.path.exists(temp_in_path):
            os.remove(temp_in_path)
        if os.path.exists(temp_out_path):
            os.remove(temp_out_path)
            
    return ogg_bytes
