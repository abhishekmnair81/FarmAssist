import base64
import io
import re
import json
import logging
import asyncio
import httpx
from typing import Optional, Dict, Any
from PIL import Image
from app.config import settings
from app.services.agrochemical_db import find_agrochemical_in_db, format_cibrc_dossier
from app.tools.web_search import search_duckduckgo

logger = logging.getLogger(__name__)

AGRI_HEADERS = {
    "English": {
        "what": "🧪 **What It Is & What To Use It For**",
        "dosage": "⚖️ **How Much To Use (Dosage - CIBRC Approved)**",
        "how": "⏰ **When & How To Apply**",
        "more": "💬 *Need more details on safety, harvest waiting time (PHI), or precautions? Just reply to ask!*"
    },
    "Malayalam": {
        "what": "🧪 **ഉൽപ്പന്നവും എന്തിനാണ് ഉപയോഗിക്കുന്നത് എന്നും**",
        "dosage": "⚖️ **ഉപയോഗിക്കേണ്ട അളവ് (Dosage - CIBRC അംഗീകൃതം)**",
        "how": "⏰ **എപ്പോൾ, എങ്ങനെ ഉപയോഗിക്കണം**",
        "more": "💬 *സുരക്ഷാ മുൻകരുതലുകൾ, വിളവെടുപ്പ് കാത്തിരിപ്പ് സമയം (PHI) എന്നിവ അറിയാൻ ചോദിക്കൂ!*"
    },
    "Tamil": {
        "what": "🧪 **தயாரிப்பு & எதற்கு பயன்படுத்த வேண்டும்**",
        "dosage": "⚖️ **பயன்படுத்த வேண்டிய அளவு (Dosage - CIBRC ஒப்புதல்)**",
        "how": "⏰ **எப்போது, எப்படி பயன்படுத்த வேண்டும்**",
        "more": "💬 *பாதுகாப்பு முறைகள், அறுவடை காத்திருப்பு காலம் (PHI) பற்றி அறிய கேட்கவும்!*"
    },
    "Hindi": {
        "what": "🧪 **उत्पाद व किस काम आता है**",
        "dosage": "⚖️ **प्रयोग की मात्रा (Dosage - CIBRC मान्यता प्राप्त)**",
        "how": "⏰ **कब और कैसे प्रयोग करें**",
        "more": "💬 *सुरक्षा सावधानियां, कटाई पूर्व प्रतीक्षा समय (PHI) जानने के लिए पूछें!*"
    }
}

CROP_HEADERS = {
    "English": {
        "issue": "🌿 **Crop & Problem Identified**",
        "treatment": "💊 **What To Spray & How Much (Treatment)**",
        "when": "⏰ **When & How To Spray**",
        "more": "💬 *Need root causes, prevention tips, or more organic options? Just reply to ask!*"
    },
    "Malayalam": {
        "issue": "🌿 **വിളയും കണ്ടെത്തിയ രോഗവും**",
        "treatment": "💊 **തളിക്കേണ്ട മരുന്നും അളവും (ചികിത്സ)**",
        "when": "⏰ **എപ്പോൾ, എങ്ങനെ തളിക്കണം**",
        "more": "💬 *രോഗകാരണങ്ങൾ, പ്രതിരോധ മാർഗ്ഗങ്ങൾ എന്നിവ അറിയാൻ ചോദിക്കൂ!*"
    },
    "Tamil": {
        "issue": "🌿 **பயிர் & கண்டறியப்பட்ட பிரச்சனை**",
        "treatment": "💊 **தெளிக்க வேண்டிய மருந்து & அளவு**",
        "when": "⏰ **எப்போது, எப்படி தெளிக்க வேண்டும்**",
        "more": "💬 *நோய் காரணங்கள், தடுப்பு முறைகள் பற்றி அறிய கேட்கவும்!*"
    },
    "Hindi": {
        "issue": "🌿 **फसल व पहचानी गई समस्या**",
        "treatment": "💊 **क्या छिड़कें और कितनी मात्रा (उपचार)**",
        "when": "⏰ **कब और कैसे छिड़कें**",
        "more": "💬 *रोग के मुख्य कारण और रोकथाम के उपाय जानने के लिए पूछें!*"
    }
}

ENTITY_EXTRACTION_PROMPT = """Analyze this image carefully for an agricultural decision support system.
Classify the image into exactly ONE category and extract all details in strictly valid JSON format.

Categories:
1. "AGROCHEMICAL": A bottle, packet, can, sachet, drum, bag, or container of pesticide, insecticide, fungicide, herbicide, fertilizer, or plant growth regulator.
2. "CROP_LEAF": A growing plant, leaf, crop foliage, fruit, stem, or tree showing health, disease, fungal spots/lesions, blight, wilting, or insect pest damage.
3. "NON_AGRICULTURAL": Any image completely unrelated to agriculture, crops, plants, or farm chemicals (e.g. vehicles, indoor furniture, electronics, humans, pets).

CRITICAL RULES:
- If you see a leaf or plant foliage (even if diseased, dying, spotted, or pest-damaged), the classification is ALWAYS "CROP_LEAF", NEVER "AGROCHEMICAL".
- Only classify as "AGROCHEMICAL" if the photo shows an actual physical container, bottle, carton, sachet, packet, or printed label of a chemical product.

Respond ONLY with a single JSON object adhering strictly to this schema:
{
  "classification": "AGROCHEMICAL or CROP_LEAF or NON_AGRICULTURAL",
  "agrochemical": {
    "brand_name": null,
    "active_ingredient": null,
    "category": null,
    "visible_instructions": null
  },
  "crop_leaf": {
    "crop_name": null,
    "suspected_issue": null,
    "issue_type": null,
    "symptoms": null,
    "severity": null
  },
  "visual_summary": "factual description of image"
}"""

FALLBACK_CROP_DISE = {
    "English": (
        "🌿 **Crop & Problem Identified**\n"
        "- Suspected fungal leaf spot / blight or sucking pest damage.\n\n"
        "💊 **What To Spray & How Much (Treatment)**\n"
        "- **Organic:** Neem oil (10,000 ppm) @ 5 ml per liter of water.\n"
        "- **Chemical (CIBRC Approved):** Saaf (Carbendazim + Mancozeb) @ 2 g/L or Mancozeb 75% WP @ 2.5 g/L of water.\n\n"
        "⏰ **When & How To Spray**\n"
        "- Spray early in the morning or late afternoon, coating both sides of leaves. Repeat after 10–12 days if needed.\n\n"
        "💬 *Need root causes, prevention tips, or more organic options? Just reply to ask!*"
    ),
    "Malayalam": (
        "🌿 **വിളയും കണ്ടെത്തിയ രോഗവും**\n"
        "- കുമിൾ ബാധ മൂലമുള്ള ഇലപ്പുള്ളി രോഗം അല്ലെങ്കിൽ കീടബാധ.\n\n"
        "💊 **തളിക്കേണ്ട മരുന്നും അളവും (ചികിത്സ)**\n"
        "- **ജൈവ നിയന്ത്രണം:** വേപ്പെണ്ണ മിശ്രിതം 5 മില്ലി ഒരു ലിറ്റർ വെള്ളത്തിൽ കലക്കി തളിക്കുക.\n"
        "- **രാസ നിയന്ത്രണം (CIBRC അംഗീകൃതം):** സാഫ് (Saaf) അല്ലെങ്കിൽ മാങ്കോസെബ് (Mancozeb) 2 ഗ്രാം ഒരു ലിറ്റർ വെള്ളത്തിൽ കലക്കി തളിക്കുക.\n\n"
        "⏰ **എപ്പോൾ, എങ്ങനെ തളിക്കണം**\n"
        "- അതിരാവിലെയോ വൈകുന്നേരമോ ഇലകളുടെ ഇരുവശങ്ങളിലും നന്നായി നനയത്തക്കവിധം തളിക്കുക.\n\n"
        "💬 *രോഗകാരണങ്ങൾ, പ്രതിരോധ മാർഗ്ഗങ്ങൾ എന്നിവ അറിയാൻ ചോദിക്കൂ!*"
    ),
    "Tamil": (
        "🌿 **பயிர் & கண்டறியப்பட்ட பிரச்சனை**\n"
        "- பூஞ்சை இலைப்புள்ளி நோய் அல்லது சாறு உறிஞ்சும் பூச்சிகள்.\n\n"
        "💊 **தெளிக்க வேண்டிய மருந்து & அளவு**\n"
        "- **இயற்கை முறை:** வேப்ப எண்ணெய் 5 மி.லி ஒரு லிட்டர் தண்ணீரில் கலந்து தெளிக்கவும்.\n"
        "- **இரசாயன முறை (CIBRC ஒப்புதல்):** சாஃப் (Saaf) அல்லது மேன்கோசெப் 2 கிராம் ஒரு லிட்டர் தண்ணீரில் கலக்கவும்.\n\n"
        "⏰ **எப்போது, எப்படி தெளிக்க வேண்டும்**\n"
        "- காலையிலோ மாலையிலோ இலைகளின் இருபுறமும் படுமாறு தெளிக்கவும்.\n\n"
        "💬 *நோய் காரணங்கள், தடுப்பு முறைகள் பற்றி அறிய கேட்கவும்!*"
    ),
    "Hindi": (
        "🌿 **फसल व पहचानी गई समस्या**\n"
        "- फफूंद जनित पत्ती धब्बा / झुलसा या रस चूसक कीट।\n\n"
        "💊 **क्या छिड़कें और कितनी मात्रा (उपचार)**\n"
        "- **जैविक उपचार:** नीम का तेल 5 मिली प्रति लीटर पानी में मिलाकर छिड़कें।\n"
        "- **रासायनिक उपचार (CIBRC मान्यता प्राप्त):** साफ (Saaf) या मैंकोजेब 2 ग्राम प्रति लीटर पानी में घोलकर छिड़कें।\n\n"
        "⏰ **कब और कैसे छिड़कें**\n"
        "- सुबह या शाम के समय पत्तियों के दोनों तरफ अच्छी तरह छिड़काव करें।\n\n"
        "💬 *रोग के मुख्य कारण और रोकथाम के उपाय जानने के लिए पूछें!*"
    )
}

FALLBACK_AGROCHEMICAL = {
    "English": (
        "🧪 **What It Is & What To Use It For**\n"
        "- Farm crop protection chemical (Insecticide / Fungicide).\n"
        "- Protects crops against damaging insect pests or fungal diseases.\n\n"
        "⚖️ **How Much To Use (Dosage - CIBRC Approved)**\n"
        "- **Granules (GR):** 7.5 to 10 kg per acre broadcast evenly in field. *(Do not mix in spray tank)*\n"
        "- **Liquid (SC / EC):** 1.5 to 2.0 ml per liter of water (350–400 ml/acre) for leaf spray.\n"
        "- **Powder (WP / WG):** 2.0 to 2.5 grams per liter of water.\n\n"
        "⏰ **When & How To Apply**\n"
        "- Apply at first pest sighting, early in the morning or late afternoon.\n\n"
        "💬 *Need more details on safety, harvest waiting time (PHI), or precautions? Just reply to ask!*"
    ),
    "Malayalam": (
        "🧪 **ഉൽപ്പന്നവും എന്തിനാണ് ഉപയോഗിക്കുന്നത് എന്നും**\n"
        "- വിള സംരക്ഷണത്തിനായുള്ള കീടനാശിനി / കുമിൾനാശിനി.\n"
        "- വിളകളിലെ കീടങ്ങളെയും രോഗങ്ങളെയും നിയന്ത്രിക്കാൻ ഉപയോഗിക്കുന്നു.\n\n"
        "⚖️ **ഉപയോഗിക്കേണ്ട അളവ് (Dosage - CIBRC അംഗീകൃതം)**\n"
        "- **തരി രൂപത്തിലുള്ളവ (GR):** ഏക്കറിന് 7.5 മുതൽ 10 കിലോഗ്രാം വരെ മണ്ണിലോ വെള്ളം കെട്ടിനിൽക്കുന്ന പാടത്തോ വിതറുക. *(സ്പ്രേയറിൽ കലക്കരുത്)*\n"
        "- **ദ്രാവക രൂപത്തിലുള്ളവ (SC / EC):** ഒരു ലിറ്റർ വെള്ളത്തിൽ 1.5 മുതൽ 2 മില്ലി വരെ കലക്കി തളിക്കുക.\n"
        "- **പൊടി രൂപത്തിലുള്ളവ (WP / WG):** ഒരു ലിറ്റർ വെള്ളത്തിൽ 2 മുതൽ 2.5 ഗ്രാം വരെ കലക്കുക.\n\n"
        "⏰ **എപ്പോൾ, എങ്ങനെ ഉപയോഗിക്കണം**\n"
        "- കീടബാധ കാണുമ്പോൾ അതിരാവിലെയോ വൈകുന്നേരമോ ഉപയോഗിക്കുക.\n\n"
        "💬 *സുരക്ഷാ മുൻകരുതലുകൾ, വിളവെടുപ്പ് കാത്തിരിപ്പ് സമയം (PHI) എന്നിവ അറിയാൻ ചോദിക്കൂ!*"
    ),
    "Tamil": (
        "🧪 **தயாரிப்பு & எதற்கு பயன்படுத்த வேண்டும்**\n"
        "- பயிர் பாதுகாப்பு பூச்சிக்கொல்லி / பூஞ்சைக்கொல்லி.\n"
        "- பயிர்களை தாக்கும் பூச்சிகள் மற்றும் நோய்களை கட்டுப்படுத்த உதவுகிறது.\n\n"
        "⚖️ **பயன்படுத்த வேண்டிய அளவு (Dosage - CIBRC ஒப்புதல்)**\n"
        "- **குறுணை மருந்துகள் (GR):** ஏக்கருக்கு 7.5 முதல் 10 கிலோ வரை வயலில் சீராக தூவவும். *(ஸ்ப்ரேயரில் கலக்க வேண்டாம்)*\n"
        "- **திரவ மருந்துகள் (SC / EC):** 1 லிட்டர் தண்ணீருக்கு 1.5 முதல் 2 மி.லி கலந்து தெளிக்கவும்.\n"
        "- **பொடி மருந்துகள் (WP / WG):** 1 லிட்டர் தண்ணீருக்கு 2 முதல் 2.5 கிராம் கலக்கவும்.\n\n"
        "⏰ **எப்போது, எப்படி பயன்படுத்த வேண்டும்**\n"
        "- பூச்சிகள் தென்படும் போது, காலையிலோ மாலையிலோ பயன்படுத்தவும்.\n\n"
        "💬 *பாதுகாப்பு முறைகள், அறுவடை காத்திருப்பு காலம் (PHI) பற்றி அறிய கேட்கவும்!*"
    ),
    "Hindi": (
        "🧪 **उत्पाद व किस काम आता है**\n"
        "- फसल सुरक्षा रसायन (कीटनाशक / फफूंदनाशक)।\n"
        "- फसलों में हानिकारक कीटों व रोगों की रोकथाम के लिए।\n\n"
        "⚖️ **प्रयोग की मात्रा (Dosage - CIBRC मान्यता प्राप्त)**\n"
        "- **दानेदार कीटनाशक (GR):** 7.5 से 10 किलोग्राम प्रति एकड़ खेत में समान रूप से बिखेरें। *(स्प्रे पंप में न घोलें)*\n"
        "- **तरल कीटनाशक (SC / EC):** 1.5 से 2.0 मिली प्रति लीटर पानी में मिलाकर पत्तियों पर छिड़कें।\n"
        "- **घुलनशील पाउडर (WP / WG):** 2 से 2.5 ग्राम प्रति लीटर पानी में घोलें।\n\n"
        "⏰ **कब और कैसे प्रयोग करें**\n"
        "- कीट दिखने पर सुबह या शाम के ठंडे समय प्रयोग करें।\n\n"
        "💬 *सुरक्षा सावधानियां, कटाई पूर्व प्रतीक्षा समय (PHI) जानने के लिए पूछें!*"
    )
}

def _prepare_optimized_image(image_bytes: bytes) -> str:
    """Resizes and compresses image to optimal resolution (max 1024x1024, quality 85) for fast, sharp OCR."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img = img.convert("RGB")
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=85)
            return base64.b64encode(output.getvalue()).decode("utf-8")
    except Exception as e:
        logger.warning(f"Image optimization failed: {e}; falling back to raw base64")
        return base64.b64encode(image_bytes).decode("utf-8")

def _parse_entity_output(raw_text: str) -> Dict[str, Any]:
    """
    Parses JSON output from vision model with strict schema validation.
    Guarantees unambiguous separation between CROP_LEAF and AGROCHEMICAL.
    """
    result = {
        "classification": "CROP_LEAF",
        "brand_name": "",
        "active_ingredient": "",
        "category": "",
        "crop_name": "",
        "suspected_issue": "",
        "symptoms": "",
        "severity": "MODERATE",
        "summary": ""
    }
    
    if not raw_text or not raw_text.strip():
        return result

    cleaned_json = raw_text.strip()
    if "```" in cleaned_json:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned_json, re.DOTALL)
        if m:
            cleaned_json = m.group(1)

    json_match = re.search(r"(\{.*\})", cleaned_json, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            cls = str(data.get("classification", "")).upper().strip()
            # Check if agrochemical brand or chemical is clearly identified
            agri = data.get("agrochemical", {}) if isinstance(data.get("agrochemical"), dict) else {}
            brand_val = str(agri.get("brand_name") or "").strip()
            chem_val = str(agri.get("active_ingredient") or "").strip()
            
            if brand_val or chem_val or "AGRO" in cls or "PESTICIDE" in cls or "BOTTLE" in cls or "CHEMICAL" in cls:
                result["classification"] = "AGROCHEMICAL"
                result["brand_name"] = brand_val
                result["active_ingredient"] = chem_val
                result["category"] = str(agri.get("category") or "").strip()
                if agri.get("visible_instructions"):
                    result["summary"] = str(agri.get("visible_instructions")).strip()
                result["crop_name"] = ""
                result["suspected_issue"] = ""
                result["symptoms"] = ""
            elif "NON" in cls or "OTHER" in cls:
                result["classification"] = "NON_AGRICULTURAL"
                result["brand_name"] = ""
                result["active_ingredient"] = ""
                result["crop_name"] = ""
                result["suspected_issue"] = ""
                result["symptoms"] = ""
            else:
                result["classification"] = "CROP_LEAF"
                crop = data.get("crop_leaf", {}) if isinstance(data.get("crop_leaf"), dict) else {}
                result["crop_name"] = str(crop.get("crop_name") or "").strip()
                result["suspected_issue"] = str(crop.get("suspected_issue") or "").strip()
                result["symptoms"] = str(crop.get("symptoms") or "").strip()
                result["severity"] = str(crop.get("severity") or "MODERATE").strip()
                result["brand_name"] = ""
                result["active_ingredient"] = ""
                result["category"] = ""

            if data.get("visual_summary"):
                result["summary"] = (result["summary"] + " " + str(data.get("visual_summary"))).strip()

            return result
        except Exception as e:
            logger.warning(f"Failed to parse vision JSON: {e}; attempting regex fallback")

    # Fallback regex extraction if model returned plain key: value format
    for line in raw_text.splitlines():
        line = line.strip().strip("*").strip("-").strip()
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip().upper()
            val = val.strip().strip("*").strip()
            if val.lower() in {"none", "null", "n/a", ""}:
                continue
            if "CLASSIFICATION" in key or "ITEM_TYPE" in key:
                if any(x in val.upper() for x in ["AGROCHEMICAL", "PESTICIDE", "BOTTLE", "CHEMICAL"]):
                    result["classification"] = "AGROCHEMICAL"
                elif any(x in val.upper() for x in ["NON", "OTHER"]):
                    result["classification"] = "NON_AGRICULTURAL"
                else:
                    result["classification"] = "CROP_LEAF"
            elif "BRAND" in key:
                result["brand_name"] = val
            elif "ACTIVE" in key or "INGREDIENT" in key:
                result["active_ingredient"] = val
            elif "CATEGORY" in key:
                result["category"] = val
            elif "CROP" in key:
                result["crop_name"] = val
            elif "SYMPTOM" in key:
                result["symptoms"] = val
            elif "ISSUE" in key or "DISEASE" in key:
                result["suspected_issue"] = val
            elif "SUMMARY" in key:
                result["summary"] = val

    return result

async def _synthesize_advisory(system_prompt: str, user_prompt: str) -> str:
    """
    Synthesizes fluent, practical multilingual agronomist reports using high-speed Groq models
    (with multi-tier fallback to fast Groq models and NVIDIA NIM text models).
    """
    # Tier 1: Groq Ultra-Fast Models (openai/gpt-oss-120b -> openai/gpt-oss-20b -> qwen/qwen3.8-27b)
    if settings.GROQ_API_KEY:
        groq_candidates = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
        headers = {"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"}
        for model_name in groq_candidates:
            try:
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 700,
                    "temperature": 0.2
                }
                async with httpx.AsyncClient(timeout=12.0) as client:
                    resp = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                    if resp.status_code == 200:
                        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                        if content and content.strip():
                            logger.info(f"Groq synthesis succeeded with model {model_name}")
                            return content.strip()
                    elif resp.status_code == 429:
                        logger.warning(f"Groq model {model_name} rate limit reached; trying next candidate...")
                        continue
            except Exception as e:
                logger.warning(f"Groq model {model_name} failed: {e}")

    # Tier 2: NVIDIA NIM Fast Text Models
    key = settings.effective_nvidia_api_key
    if key:
        nvidia_candidates = ["nvidia/nemotron-3.5-lightning-30b-a3b", "openai/gpt-oss-20b"]
        base_url = settings.NVIDIA_BASE_URL.rstrip('/')
        n_headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        for n_model in nvidia_candidates:
            try:
                payload = {
                    "model": n_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "max_tokens": 700,
                    "temperature": 0.2
                }
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(f"{base_url}/chat/completions", headers=n_headers, json=payload)
                    if resp.status_code == 200:
                        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                        if content and content.strip():
                            logger.info(f"NVIDIA synthesis succeeded with model {n_model}")
                            return content.strip()
            except Exception as e:
                logger.warning(f"NVIDIA model {n_model} failed: {e}")

    return ""

async def diagnose_plant_disease(image_bytes: bytes, caption: str = "", language: str = "English") -> str:
    """
    Two-Stage Vision + Search Agrochemical & Crop Pathology Pipeline:
    1. Fast Multimodal Vision AI classifies CROP_LEAF vs AGROCHEMICAL vs NON_AGRICULTURAL.
    2. Searches official CIBRC agrochemical database and live DuckDuckGo web search.
    3. Synthesizes a deep, accurate advisory in the farmer's native language.
    """
    if not image_bytes:
        return "No image data received for agricultural diagnosis."

    b64_image = await asyncio.to_thread(_prepare_optimized_image, image_bytes)
    api_key = settings.effective_nvidia_api_key
    
    if not api_key:
        logger.info("No NVIDIA API key found; returning curated fallback advisory.")
        return FALLBACK_CROP_DISE.get(language, FALLBACK_CROP_DISE["English"])

    # Stage 1: Fast Multimodal Entity & Classification Extraction (JSON schema)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    extract_payload = {
        "model": "meta/llama-3.2-11b-vision-instruct",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": ENTITY_EXTRACTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                ]
            }
        ],
        "max_tokens": 300,
        "temperature": 0.1
    }

    raw_extraction = ""
    try:
        logger.info("Stage 1: Calling NVIDIA Vision for visual classification and entity extraction...")
        url = f"{settings.NVIDIA_BASE_URL.rstrip('/')}/chat/completions"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=extract_payload)
            if resp.status_code == 200:
                raw_extraction = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                logger.info(f"Vision extraction output: {repr(raw_extraction[:120])}")
            else:
                logger.warning(f"NVIDIA Vision extraction failed with status {resp.status_code}")
    except Exception as e:
        logger.error(f"NVIDIA Vision extraction call failed: {repr(e)}")

    entities = _parse_entity_output(raw_extraction) if raw_extraction else {}
    classification = entities.get("classification", "CROP_LEAF")
    brand = entities.get("brand_name", "")
    chem = entities.get("active_ingredient", "")
    crop = entities.get("crop_name", "")
    issue = entities.get("suspected_issue", "")
    symptoms = entities.get("symptoms", "")
    severity = entities.get("severity", "MODERATE")
    summary = entities.get("summary", "")

    logger.info(f"Vision Classified: {classification} (brand='{brand}', chem='{chem}', crop='{crop}', issue='{issue}')")

    # Stage 2: Routing based on strictly validated classification
    if classification == "AGROCHEMICAL":
        db_query = f"{brand} {chem}".strip()
        db_match = find_agrochemical_in_db(db_query)
        
        search_query = f"{brand or chem or 'pesticide'} CIBRC PPQS India dosage application target crops".strip()
        web_info = ""
        try:
            logger.info(f"Stage 2: Querying DuckDuckGo search for agrochemical: '{search_query}'...")
            web_info = await asyncio.wait_for(search_duckduckgo.ainvoke(search_query), timeout=8.0)
        except Exception as e:
            logger.warning(f"DuckDuckGo search for agrochemical failed: {e}")

        db_context = format_cibrc_dossier(db_match) if db_match else ""
        headers_map = AGRI_HEADERS.get(language, AGRI_HEADERS["English"])

        system_prompt = (
            f"You are FarmAssist's Senior Regulatory Agrochemical Specialist referencing official "
            f"Directorate of Plant Protection, Quarantine & Storage (PPQS) and Central Insecticides Board & Registration Committee (CIBRC) standards.\n"
            f"Provide an Indian farmer with an easy, simple-to-understand first response for this agrochemical.\n"
            f"LANGUAGE RULE: Strictly respond ONLY in {language}. Do NOT include words or translations from any other languages.\n"
            f"FARMER SIMPLICITY & CONCISENESS:\n"
            f"- Make this first response very easy for a farmer to understand with ONLY the basic essential need info.\n"
            f"- Do NOT dump technical jargon, chemical classes, GABA inhibitors, or long paragraphs.\n"
            f"- State directly: What to use it for, How much to use (dosage), and When/how to apply.\n"
            f"CRITICAL DOSAGE RULE: You MUST report the EXACT official CIBRC/PPQS government dosage provided in the verified technical section below.\n"
            f"- If Granules (GR): State exact kg per acre (broadcast evenly in standing water/soil). Explicitly warn: 'Do NOT mix or dissolve granules in spray water tanks.'\n"
            f"- If Liquid (SC/EC/SL): State exact ml per liter of water (and ml per acre) for foliar spray.\n"
            f"- If Wettable Powder (WP/WG): State exact grams per liter of water."
        )

        user_prompt = (
            f"Product Identified from Photo:\n"
            f"- Brand Name: {brand or 'Unknown brand'}\n"
            f"- Active Ingredient / Formulation: {chem or 'Not explicitly labeled'}\n"
            f"- Label Notes: {summary}\n"
            f"- Farmer's Note / Question: {caption if caption else 'None'}\n\n"
            f"Verified Government Registration Data (CIBRC & PPQS, Ministry of Agriculture, Govt of India):\n"
            f"{db_context if db_context else 'None in local database; refer to official CIBRC standards'}\n\n"
            f"Supplemental Search Data:\n{web_info if web_info else 'None'}\n\n"
            f"Format your response simply with these EXACT sections in {language} (do not mix other languages):\n\n"
            f"{headers_map['what']}\n"
            f"- Product & formulation name in simple words.\n"
            f"- Which crops and what target pests/insects it is used for.\n\n"
            f"{headers_map['dosage']}\n"
            f"- The exact CIBRC/PPQS dosage (e.g. Granules: 7.5–10 kg per acre broadcast in field; or Liquid: 1.5–2 ml per liter water).\n"
            f"- If granules, add the critical warning: 'Do NOT mix granules in spray water tanks.'\n\n"
            f"{headers_map['how']}\n"
            f"- Best time/stage to apply (e.g. 15–25 days after transplanting, morning or late afternoon) and simple application steps.\n\n"
            f"{headers_map['more']}"
        )

        logger.info(f"Stage 3: Synthesizing agrochemical advisory in {language}...")
        report = await _synthesize_advisory(system_prompt, user_prompt)
        if report:
            return report
        return FALLBACK_AGROCHEMICAL.get(language, FALLBACK_AGROCHEMICAL["English"])

    elif classification == "NON_AGRICULTURAL":
        logger.info("Detected non-agricultural photo; returning polite domain boundary guidance.")
        redirection_map = {
            "English": (
                "⚠️ It appears that the uploaded image shows a non-agricultural item.\n\n"
                "FarmAssist's vision diagnostic system is exclusively designed to analyze:\n"
                "1. **Crops & Plant Leaves:** Diagnosing leaf diseases, fungal blights, and insect pests.\n"
                "2. **Farm Inputs & Chemicals:** Reading pesticide bottles, insecticide labels, and fertilizer bags to provide approved dosages and safety instructions.\n\n"
                "Kindly upload a clear photo of your crop, leaf, or farm chemical product!"
            ),
            "Malayalam": (
                "⚠️ നിങ്ങൾ നൽകിയ ചിത്രം കാർഷികേതരമായ ഒരു വസ്തുവാണ്.\n\n"
                "ഫാംഅസിസ്റ്റ് വിഷൻ സംവിധാനം ഇവ വിശകലനം ചെയ്യാൻ രൂപകൽപ്പന ചെയ്തിട്ടുള്ളതാണ്:\n"
                "1. **വിളകളും ഇലകളും:** ഇലപ്പുള്ളി രോഗങ്ങൾ, കീടബാധകൾ, വിള രോഗനിർണയം.\n"
                "2. **കീടനാശിനികളും വളങ്ങളും:** കീടനാശിനി കുപ്പികൾ, വളങ്ങളുടെ പാക്കറ്റുകൾ എന്നിവ പരിശോധിച്ച് കൃത്യമായ അളവും സുരക്ഷയും നൽകൽ.\n\n"
                "ദയവായി നിങ്ങളുടെ വിളയുടെയോ ഇലയുടെയോ കീടനാശിനി കുപ്പിയുടെയോ ചിത്രം അയച്ചുതരിക!"
            ),
            "Tamil": (
                "⚠️ பதிவேற்றப்பட்ட படம் விவசாயம் சாராத ஒன்றாக தெரிகிறது.\n\n"
                "ஃபார்ம்அசிஸ்ட் விஷன் அமைப்பு இவற்றை பகுப்பாய்வு செய்ய வடிவமைக்கப்பட்டுள்ளது:\n"
                "1. **பயிர்கள் & இலைகள்:** பயிர் நோய்கள், பூச்சி தாக்குதல்கள் மற்றும் சிகிச்சை முறைகள்.\n"
                "2. **பூச்சிக்கொல்லிகள் & உரங்கள்:** பூச்சிக்கொல்லி பாட்டில்கள் மற்றும் உர லேபிள்களைப் படித்து சரியான தெளிப்பு அளவு வழங்குதல்.\n\n"
                "தயவுசெய்து உங்கள் பயிர், இலை அல்லது பூச்சிக்கொல்லி பாட்டிலின் தெளிவான படத்தை அனுப்பவும்!"
            ),
            "Hindi": (
                "⚠️ ऐसा प्रतीत होता है कि यह छवि कृषि से संबंधित नहीं है।\n\n"
                "फार्मअसिस्ट विज़न सिस्टम विशेष रूप से इनके लिए बनाया गया है:\n"
                "1. **फसलें व पत्तियां:** पत्तियों के रोग, कीट प्रकोप और उनका उपचार।\n"
                "2. **कीटनाशक व खाद:** कीटनाशक की बोतलें व खाद के पैकेट पढ़कर उनकी सही मात्रा और सुरक्षा निर्देश देना।\n\n"
                "कृपया अपनी फसल, पत्ती या कीटनाशक की बोतल की साफ तस्वीर भेजें!"
            )
        }
        return redirection_map.get(language, redirection_map["English"])

    else:
        # classification == "CROP_LEAF"
        search_query = f"{crop or 'crop'} {issue or symptoms or 'leaf disease'} symptoms treatment ICAR India".strip()
        web_info = ""
        try:
            logger.info(f"Stage 2: Querying DuckDuckGo search for crop pathology: '{search_query}'...")
            web_info = await asyncio.wait_for(search_duckduckgo.ainvoke(search_query), timeout=8.0)
        except Exception as e:
            logger.warning(f"DuckDuckGo search for crop pathology failed: {e}")

        crop_headers_map = CROP_HEADERS.get(language, CROP_HEADERS["English"])

        system_prompt = (
            f"You are FarmAssist's Senior Plant Pathologist and Agronomist referencing ICAR / SAU recommendations.\n"
            f"Provide an Indian farmer with an easy, simple-to-understand first response for this diseased crop leaf.\n"
            f"LANGUAGE RULE: Respond ONLY in {language}. Do NOT mix other languages.\n"
            f"FARMER SIMPLICITY & CONCISENESS:\n"
            f"- Make this first response very easy for a farmer to understand with ONLY basic essential need info.\n"
            f"- Focus on: What problem/disease it is, What to spray and how much (1 organic + 1 chemical remedy), and When to spray.\n"
            f"- Do NOT dump heavy textbook theory, causal pathogen biology, or long paragraphs unless asked.\n"
            f"- Be specific with exact practical dosages (ml/L or g/L)."
        )

        user_prompt = (
            f"Crop Information from Photo:\n"
            f"- Crop Name: {crop if crop else 'Agricultural Crop'}\n"
            f"- Suspected Condition / Disease: {issue if issue else 'Leaf Spot / Foliar Infection'}\n"
            f"- Severity Level: {severity}\n"
            f"- Observed Visual Symptoms: {symptoms if symptoms else 'Lesions / discoloration'}\n"
            f"- Farmer's Note / Question: {caption if caption else 'None'}\n\n"
            f"Supplemental Live Search:\n{web_info if web_info else 'None'}\n\n"
            f"Format your response simply with these EXACT sections in {language} (do not mix other languages):\n\n"
            f"{crop_headers_map['issue']}\n"
            f"- Crop name and identified problem/disease in simple farmer-friendly terms.\n\n"
            f"{crop_headers_map['treatment']}\n"
            f"- **Organic Remedy:** Name and exact dosage (e.g. Neem oil @ 5 ml per liter water).\n"
            f"- **Chemical Remedy (CIBRC Approved):** Name and exact dosage (e.g. Saaf or Mancozeb @ 2 to 2.5 g per liter water).\n\n"
            f"{crop_headers_map['when']}\n"
            f"- When to spray (morning or evening, both sides of leaf) and repeat interval.\n\n"
            f"{crop_headers_map['more']}"
        )

        logger.info(f"Stage 3: Synthesizing crop pathology advisory in {language}...")
        report = await _synthesize_advisory(system_prompt, user_prompt)
        if report:
            return report
        return FALLBACK_CROP_DISE.get(language, FALLBACK_CROP_DISE["English"])
