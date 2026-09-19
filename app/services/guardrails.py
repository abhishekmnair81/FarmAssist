import asyncio
import logging
import re
import os
import httpx
from typing import Tuple, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# Fast-path regex patterns for malicious prompt injections and jailbreaks (<1ms check)
MALICIOUS_PATTERNS = [
    r"(?i)\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)",
    r"(?i)\bdisregard\s+(all\s+)?(previous|prior)\s+(rules|prompts)",
    r"(?i)\b(reveal|show|give|tell)\s+.*?\b(system\s+prompt|hidden\s+instructions|api\s*key|secret\s*key)",
    r"(?i)\bwhat\s+(is|are)\s+your\s+(system\s+prompt|hidden\s+rules|api\s*key)",
    r"(?i)\b(dan|jailbreak|unrestricted|god\s*mode|evil\s*bot)\b",
    r"(?i)\bhow\s+to\s+(make|build|create)\s+(a\s+)?(bomb|explosive|weapon|poison|malware)",
    r"(?i)\bhack\s+(into|a|the)\b",
    r"(?i)\b(secret\s*key|api\s*key|access\s*token)\b",
]

GUARDRAIL_REFUSALS = {
    "English": "I cannot fulfill this request. FarmAssist is a secure, dedicated agricultural AI assistant focused strictly on farming, crops, weather, and mandi market advisory.",
    "Malayalam": "ഈ അഭ്യർത്ഥന സ്വീകരിക്കാൻ കഴിയില്ല. ഫാംഅസിസ്റ്റ് (FarmAssist) കൃഷി, വിളകൾ, കാലാവസ്ഥ, വിപണി വിലകൾ എന്നിവയിൽ കർഷകരെ സഹായിക്കാനായി മാത്രം രൂപകൽപ്പന ചെയ്തിട്ടുള്ള ഒരു കാർഷിക സഹായിയാണ്.",
    "Tamil": "இந்தக் கோரிக்கையை நிறைவேற்ற முடியாது. ஃபார்ம்அசிஸ்ட் (FarmAssist) விவசாயம், பயிர்கள், வானிலை மற்றும் சந்தை தகவல்களுக்கு மட்டுமே அர்ப்பணிக்கப்பட்ட ஒரு பாதுகாப்பான விவசாய உதவியாளர் ஆகும்.",
    "Hindi": "मैं इस अनुरोध को पूरा नहीं कर सकता। फार्मअसिस्ट (FarmAssist) केवल खेती, फसलों, मौसम और मंडी भाव के लिए समर्पित एक सुरक्षित कृषि सहायक है।"
}

async def check_nvidia_guardrail(text: str, user_language: str = "English") -> Tuple[bool, Optional[str]]:
    """
    Evaluates incoming user text against NVIDIA Security Guardrails.
    Returns:
        (is_safe: bool, refusal_message: Optional[str])
    """
    if not text or not text.strip():
        return True, None

    # 1. Fast zero-cost local pre-filter (<1ms)
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, text):
            logger.warning(f"Security Guardrail: Fast pre-filter triggered on query: {repr(text[:80])}")
            refusal = GUARDRAIL_REFUSALS.get(user_language, GUARDRAIL_REFUSALS["English"])
            return False, refusal

    # 2. NVIDIA Safety Guardrail Check via NVIDIA NIM API using existing key
    api_key = settings.effective_nvidia_api_key
    if not api_key:
        return True, None

    try:
        url = f"{settings.NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        # Using NVIDIA's dedicated lightweight content safety guard model with a tight 2s timeout
        payload = {
            "model": "nvidia/llama-3.1-nemoguard-8b-content-safety",
            "messages": [
                {"role": "user", "content": text}
            ],
            "max_tokens": 15,
            "temperature": 0.0
        }

        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip().lower()
                if "unsafe" in content:
                    logger.warning(f"NVIDIA Security Guardrail flagged input as unsafe: {repr(text[:80])}")
                    refusal = GUARDRAIL_REFUSALS.get(user_language, GUARDRAIL_REFUSALS["English"])
                    return False, refusal
    except asyncio.TimeoutError:
        logger.debug("NVIDIA Guardrail check timed out (2s); allowing non-malicious query through fast-path.")
    except Exception as e:
        logger.debug(f"NVIDIA Guardrail check skipped due to error: {e}")

    return True, None
