import httpx
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def _detect_audio_mime_and_filename(audio_bytes: bytes, default_filename: str = "audio.ogg") -> tuple[str, str]:
    """Detects audio mime type and extension from leading magic bytes."""
    if audio_bytes.startswith(b"\x1aE\xdf\xa3"):
        return "audio/webm", "audio.webm"
    elif audio_bytes.startswith(b"OggS"):
        return "audio/ogg", "audio.ogg"
    elif audio_bytes.startswith(b"RIFF"):
        return "audio/wav", "audio.wav"
    elif audio_bytes.startswith(b"ID3") or (len(audio_bytes) > 2 and audio_bytes[:2] == b"\xff\xfb"):
        return "audio/mpeg", "audio.mp3"
    elif audio_bytes.startswith(b"\xff\xf1") or audio_bytes.startswith(b"\xff\xf9"):
        return "audio/aac", "audio.aac"
    return "audio/ogg", default_filename

TAMIL_WHISPER_PROMPT = (
    "விவசாயம், பயிர், வானிலை, மழை, காற்று, தட்பவெப்பநிலை. "
    "தமிழ்நாடு மாவட்டங்கள்: சென்னை, மதுரை, கோயம்புத்தூர், திருச்சி, சேலம், தஞ்சாவூர், "
    "ஈரோடு, திருநெல்வேலி, திண்டுக்கல், வேலூர், தூத்துக்குடி, நாமக்கல், கரூர், புதுக்கோட்டை, "
    "சிவகங்கை, விருதுநகர், தேனி, கன்னியாகுமரி, பொள்ளாச்சி, ஊட்டி."
)

HINDI_WHISPER_PROMPT = (
    "खेती, किसान, फसल, मौसम, बारिश, तापमान, हवा, खाद, कीटनाशक, रोग, उपचार, मंडी भाव। "
    "प्रमुख जिले और शहर: दिल्ली, लखनऊ, कानपुर, वाराणसी, गोरखपुर, प्रयागराज, इलाहाबाद, पटना, गया, "
    "इंदौर, भोपाल, ग्वालियर, जबलपुर, उज्जैन, जयपुर, जोधपुर, कोटा, करनाल, हिसार, रोहतक, पानीपत, "
    "देहरादून, हरिद्वार, रांची, जमशेदपुर, रायपुर, बिलासपुर, आगरा, मेरठ, बरेली, अलीगढ़, मुरादाबाद।"
)

DEFAULT_WHISPER_PROMPT = (
    "FarmAssist agricultural voice assistant. Weather, crops, mandi prices, rainfall. "
    "खेती, किसान, फसल, मौसम, बारिश, दिल्ली, लखनऊ, कानपुर, वाराणसी, गोरखपुर, पटना, इंदौर, भोपाल, जयपुर। "
    "விவசாயம், பயிர், வானிலை, மழை, சென்னை, மதுரை, கோவை, திருச்சி, தஞ்சாவூர், சேலம், நெல்லை. "
    "കൃഷി, കാലാവസ്ഥ, മഴ, കൊച്ചി, തിരുവനന്തപുരം, കോഴിക്കോട്, പാലക്കാട്."
)

async def transcribe_audio_groq(audio_bytes: bytes, filename: str = "audio.ogg", language: str = None) -> str:
    """
    Transcribes raw audio bytes using Groq Cloud's whisper-large-v3-turbo.
    Automatically detects audio format (WebM, OGG, WAV, MP3) and uses language/prompt
    biasing to recognize Indian regional languages, Hindi, and Tamil place names accurately.
    """
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    headers = {
        "Authorization": f"Bearer {settings.GROQ_API_KEY}"
    }
    
    mime_type, detected_filename = _detect_audio_mime_and_filename(audio_bytes, default_filename=filename)
    logger.info(f"Transcribing audio ({len(audio_bytes)} bytes, lang={language}) as {mime_type} / {detected_filename}")
    
    files = {
        "file": (detected_filename, audio_bytes, mime_type),
    }
    
    data = {
        "model": "whisper-large-v3-turbo",
        "response_format": "json",
        "temperature": 0.0,
    }

    if language:
        lang_clean = language.strip().lower()
        if lang_clean in ["tamil", "ta", "தமிழ்"]:
            data["language"] = "ta"
            data["prompt"] = TAMIL_WHISPER_PROMPT
        elif lang_clean in ["malayalam", "ml", "മലയാളം"]:
            data["language"] = "ml"
        elif lang_clean in ["hindi", "hi", "हिन्दी"]:
            data["language"] = "hi"
            data["prompt"] = HINDI_WHISPER_PROMPT
        elif lang_clean in ["english", "en"]:
            data["language"] = "en"
    else:
        data["prompt"] = DEFAULT_WHISPER_PROMPT

    async with httpx.AsyncClient(timeout=25.0, verify=False) as client:
        response = await client.post(url, headers=headers, files=files, data=data)
        response.raise_for_status()
        
        result = response.json()
        text = result.get("text", "")
        return text.strip() if text else ""

