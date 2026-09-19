import httpx
from typing import Dict, Any, Tuple, Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Common city/district aliases in India (historic or popular name -> official administrative name)
CITY_ALIASES = {
    "bangalore": "bengaluru",
    "mysore": "mysuru",
    "calicut": "kozhikode",
    "cochin": "kochi",
    "trivandrum": "thiruvananthapuram",
    "madras": "chennai",
    "bombay": "mumbai",
    "calcutta": "kolkata",
    "belgaum": "belagavi",
    "hubli": "hubballi",
    "gulbarga": "kalaburagi",
    "shimoga": "shivamogga",
    "mangalore": "mangaluru",
    "bellary": "ballari",
    "bijapur": "vijayapura",
    "tumkur": "tumakuru",
    "trichy": "tiruchirappalli",
    "kovai": "coimbatore",
    "nellai": "tirunelveli",
    "thanjai": "thanjavur",
    "ooty": "udhagamandalam",
}

# Comprehensive mapping of Tamil script districts, cities, and agricultural hubs in Tamil Nadu
TAMIL_LOCALITIES: Dict[str, str] = {
    # 38 Official Districts & Major Cities
    "சென்னை": "Chennai",
    "கோயம்புத்தூர்": "Coimbatore",
    "கோவை": "Coimbatore",
    "மதுரை": "Madurai",
    "திருச்சிராப்பள்ளி": "Tiruchirappalli",
    "திருச்சி": "Tiruchirappalli",
    "சேலம்": "Salem",
    "ஈரோடு": "Erode",
    "திருப்பூர்": "Tiruppur",
    "திருநெல்வேலி": "Tirunelveli",
    "நெல்லை": "Tirunelveli",
    "வேலூர்": "Vellore",
    "தூத்துக்குடி": "Thoothukudi",
    "திண்டுக்கல்": "Dindigul",
    "தஞ்சாவூர்": "Thanjavur",
    "தஞ்சை": "Thanjavur",
    "சிவகங்கை": "Sivaganga",
    "விருதுநகர்": "Virudhunagar",
    "கரூர்": "Karur",
    "நாமக்கல்": "Namakkal",
    "கன்னியாகுமரி": "Kanyakumari",
    "நாகர்கோவில்": "Nagercoil",
    "கடலூர்": "Cuddalore",
    "காஞ்சிபுரம்": "Kanchipuram",
    "திருவள்ளூர்": "Tiruvallur",
    "திருவண்ணாமலை": "Tiruvannamalai",
    "விழுப்புரம்": "Villupuram",
    "தர்மபுரி": "Dharmapuri",
    "கிருஷ்ணகிரி": "Krishnagiri",
    "பெரம்பலூர்": "Perambalur",
    "அரியலூர்": "Ariyalur",
    "நாகப்பட்டினம்": "Nagapattinam",
    "புதுக்கோட்டை": "Pudukkottai",
    "ராமநாதபுரம்": "Ramanathapuram",
    "தேனி": "Theni",
    "நீலகிரி": "Nilgiris",
    "ஊட்டி": "Ooty",
    "உதகமண்டலம்": "Udhagamandalam",
    "தென்காசி": "Tenkasi",
    "திருப்பத்தூர்": "Tirupathur",
    "ராணிப்பேட்டை": "Ranipet",
    "செங்கல்பட்டு": "Chengalpattu",
    "கள்ளக்குறிச்சி": "Kallakurichi",
    "மயிலாடுதுறை": "Mayiladuthurai",
    # Key Agricultural Towns & Centers
    "பொள்ளாச்சி": "Pollachi",
    "மேட்டுப்பாளையம்": "Mettupalayam",
    "கோபிசெட்டிபாளையம்": "Gobichettipalayam",
    "கோபி": "Gobichettipalayam",
    "பவானி": "Bhavani",
    "சத்தியமங்கலம்": "Sathyamangalam",
    "ஆத்தூர்": "Attur",
    "ஓசூர்": "Hosur",
    "கும்பகோணம்": "Kumbakonam",
    "மன்னார்குடி": "Mannargudi",
    "பட்டுக்கோட்டை": "Pattukkottai",
    "பழனி": "Palani",
    "கொடைக்கானல்": "Kodaikanal",
    "ராஜபாளையம்": "Rajapalayam",
    "சிவகாசி": "Sivakasi",
    "அருப்புக்கோட்டை": "Aruppukkottai",
    "சங்கரன்கோவில்": "Sankarankovil",
    "அம்பாசமுத்திரம்": "Ambasamudram",
    "கோவில்பட்டி": "Kovilpatti",
    "திருச்செந்தூர்": "Tiruchendur",
    "வாணியம்பாடி": "Vaniyambadi",
    "ஆம்பூர்": "Ambur",
    "அரக்கோணம்": "Arakkonam",
    "திருத்தணி": "Tiruttani",
    "திண்டிவனம்": "Tindivanam",
    "சிதம்பரம்": "Chidambaram",
    "விருத்தாச்சலம்": "Virudhachalam",
    "போடிநாயக்கனூர்": "Bodinayakanur",
    "போடி": "Bodinayakanur",
    "பரமக்குடி": "Paramakudi",
    "காரைக்குடி": "Karaikudi",
    "அறந்தாங்கி": "Aranthangi",
}

def _clean_tamil_location_suffix(text: str) -> str:
    """
    Strips grammatical Tamil locative and postpositional suffixes from place names.
    Handles morphophonemic combinations (e.g. மதுரையில் -> மதுரை, தஞ்சாவூரில் -> தஞ்சாவூர், 
    சேலத்தில் -> சேலம், ஈரோட்டில் -> ஈரோடு, திண்டுக்கல்லில் -> திண்டுக்கல்).
    """
    cleaned = text.strip()
    if any('\u0B80' <= c <= '\u0BFF' for c in cleaned):
        # 1. Direct postpositions / suffixes
        for sfx in ['லேயும்', 'லயும்', 'க்குள்ள', 'இடம்', 'ரிடம்', 'யில்', 'க்கு', 'லும்', 'ல']:
            if cleaned.endswith(sfx) and len(cleaned) > len(sfx) + 1:
                return cleaned[:-len(sfx)].strip()
        # 2. Combined locatives with preceding consonants
        # -ரில் -> -ர் (e.g. தஞ்சாவூரில் -> தஞ்சாவூர், கோயம்புத்தூரில் -> கோயம்புத்தூர், வேலூரில் -> வேலூர்)
        if cleaned.endswith('ரில்') and len(cleaned) > 4:
            return cleaned[:-4] + 'ர்'
        # -த்தில் -> -ம் (e.g. சேலத்தில் -> சேலம், சிதம்பரத்தில் -> சிதம்பரம்)
        if cleaned.endswith('த்தில்') and len(cleaned) > 6:
            return cleaned[:-6] + 'ம்'
        # -ட்டில் -> -டு (e.g. ஈரோட்டில் -> ஈரோடு)
        if cleaned.endswith('ட்டில்') and len(cleaned) > 6:
            return cleaned[:-6] + 'டு'
        # -ல்லில் -> -ல் (e.g. திண்டுக்கல்லில் -> திண்டுக்கல்)
        if cleaned.endswith('ல்லில்') and len(cleaned) > 6:
            return cleaned[:-6] + 'ல்'
        # General -இல்
        if cleaned.endswith('இல்') and len(cleaned) > 3:
            return cleaned[:-3].strip()
    return cleaned

# Comprehensive mapping of Hindi (Devanagari) script districts, cities, and agricultural hubs
HINDI_LOCALITIES: Dict[str, str] = {
    # Uttar Pradesh
    "दिल्ली": "Delhi",
    "नई दिल्ली": "New Delhi",
    "लखनऊ": "Lucknow",
    "कानपुर": "Kanpur",
    "वाराणसी": "Varanasi",
    "काशी": "Varanasi",
    "बनारस": "Varanasi",
    "प्रयागराज": "Prayagraj",
    "इलाहाबाद": "Prayagraj",
    "गोरखपुर": "Gorakhpur, Uttar Pradesh",
    "आगरा": "Agra",
    "मेरठ": "Meerut",
    "बरेली": "Bareilly",
    "अलीगढ़": "Aligarh",
    "मुरादाबाद": "Moradabad",
    "सहारनपुर": "Saharanpur",
    "झांसी": "Jhansi",
    "अयोध्या": "Ayodhya",
    "फैजाबाद": "Ayodhya",
    "मथुरा": "Mathura",
    "फिरोजाबाद": "Firozabad",
    "मुजफ्फरनगर": "Muzaffarnagar",
    "बदायूं": "Budaun",
    "शाहजहांपुर": "Shahjahanpur",
    "पीलीभीत": "Pilibhit",
    "लखीमपुर": "Lakhimpur",
    "सीतापुर": "Sitapur",
    "हरदोई": "Hardoi",
    "उन्नाव": "Unnao",
    "रायबरेली": "Rae Bareli",
    "अमेठी": "Amethi",
    "सुल्तानपुर": "Sultanpur",
    "प्रतापगढ़": "Pratapgarh",
    "जौनपुर": "Jaunpur",
    "गाजीपुर": "Ghazipur",
    "बलिया": "Ballia",
    "मऊ": "Mau",
    "आजमगढ़": "Azamgarh",
    "देवरिया": "Deoria",
    "कुशीनगर": "Kushinagar",
    "बस्ती": "Basti",
    "संत कबीर नगर": "Khalilabad",
    "सिद्धार्थनगर": "Naugarh",
    "गोंडा": "Gonda",
    "बहराइच": "Bahraich",
    "श्रावस्ती": "Bhinga",
    "बलरामपुर": "Balrampur",
    "बाराबंकी": "Barabanki",
    "इटावा": "Etawah",
    "मैनपुरी": "Mainpuri",
    "कन्नौज": "Kannauj",
    "फर्रुखाबाद": "Farrukhabad",
    "औरैया": "Auraiya",
    "फतेहपुर": "Fatehpur",
    "कौशाम्बी": "Manjhanpur",
    "चित्रकूट": "Chitrakoot",
    "बांदा": "Banda",
    "हमीरपुर": "Hamirpur",
    "महोबा": "Mahoba",
    "ललितपुर": "Lalitpur",
    "मिर्जापुर": "Mirzapur",
    "सोनभद्र": "Robertsganj",
    "भदोही": "Bhadohi",
    "गाजियाबाद": "Ghaziabad",
    "नोएडा": "Noida",
    "ग्रेटर नोएडा": "Greater Noida",
    "हापुड़": "Hapur",
    "बुलंदशहर": "Bulandshahr",
    "संभल": "Sambhal",
    "अमरोहा": "Amroha",
    "बिजनौर": "Bijnor",
    "बागपत": "Baghpat",
    "शामली": "Shamli",
    "हाथरस": "Hathras",
    "कासगंज": "Kasganj",
    "एटा": "Etah",
    # Bihar
    "पटना": "Patna",
    "गया": "Gaya",
    "भागलपुर": "Bhagalpur",
    "मुजफ्फरपुर": "Muzaffarpur",
    "पूर्णिया": "Purnia",
    "दरभंगा": "Darbhanga",
    "बिहारशरीफ": "Bihar Sharif",
    "आरा": "Arrah",
    "बेगूसराय": "Begusarai",
    "कटिहार": "Katihar",
    "मुंगेर": "Munger",
    "छपरा": "Chhapra",
    "बेतिया": "Bettiah",
    "सहरसा": "Saharsa",
    "सासाराम": "Sasaram",
    "हाजीपुर": "Hajipur",
    "मोतिहारी": "Motihari",
    "सीवान": "Siwan",
    "नवादा": "Nawada",
    "बक्सर": "Buxar",
    "किशनगंज": "Kishanganj",
    "सीतामढ़ी": "Sitamarhi",
    "मधुबनी": "Madhubani",
    "समस्तीपुर": "Samastipur",
    # Madhya Pradesh
    "भोपाल": "Bhopal",
    "इंदौर": "Indore",
    "ग्वालियर": "Gwalior",
    "जबलपुर": "Jabalpur",
    "उज्जैन": "Ujjain",
    "सागर": "Sagar",
    "देवास": "Dewas",
    "सतना": "Satna",
    "रतलाम": "Ratlam",
    "रीवा": "Rewa",
    "छिंदवाड़ा": "Chhindwara",
    "मुरैना": "Morena",
    "भिंड": "Bhind",
    "शिवपुरी": "Shivpuri",
    "विदिशा": "Vidisha",
    "सीहोर": "Sehore",
    "होशंगाबाद": "Narmadapuram",
    "नर्मदापुरम": "Narmadapuram",
    "खंडवा": "Khandwa",
    "खरगोन": "Khargone",
    "मंदसौर": "Mandsaur",
    "नीमच": "Neemuch",
    # Rajasthan
    "जयपुर": "Jaipur",
    "जोधपुर": "Jodhpur",
    "कोटा": "Kota",
    "बीकानेर": "Bikaner",
    "अजमेर": "Ajmer",
    "उदयपुर": "Udaipur",
    "भीलवाड़ा": "Bhilwara",
    "अलवर": "Alwar",
    "भरतपुर": "Bharatpur",
    "श्रीगंगानगर": "Sri Ganganagar",
    "सीकर": "Sikar",
    "पाली": "Pali",
    "टोंक": "Tonk",
    "झुंझुनू": "Jhunjhunu",
    "हनुमानगढ़": "Hanumangarh",
    "चित्तौड़गढ़": "Chittorgarh",
    "नागौर": "Nagaur",
    "बाड़मेर": "Barmer",
    "जैसलमेर": "Jaisalmer",
    # Haryana
    "करनाल": "Karnal",
    "हिसार": "Hisar",
    "रोहतक": "Rohtak",
    "पानीपत": "Panipat",
    "सोनीपत": "Sonipat",
    "अंबाला": "Ambala",
    "यमुनानगर": "Yamunanagar",
    "सिरसा": "Sirsa",
    "भिवानी": "Bhiwani",
    "जींद": "Jind",
    "कैथल": "Kaithal",
    "रेवाड़ी": "Rewari",
    "फरीदाबाद": "Faridabad",
    "गुरुग्राम": "Gurugram",
    "गुड़गांव": "Gurugram",
    "कुरुक्षेत्र": "Kurukshetra",
    # Uttarakhand & Himachal
    "देहरादून": "Dehradun",
    "हरिद्वार": "Haridwar",
    "ऋषिकेश": "Rishikesh",
    "रुड़की": "Roorkee",
    "हल्द्वानी": "Haldwani",
    "नैनीताल": "Nainital",
    "शिमला": "Shimla",
    "मंडी": "Mandi",
    "धर्मशाला": "Dharamshala",
    "सोलन": "Solan",
    # Jharkhand & Chhattisgarh
    "रांची": "Ranchi",
    "जमशेदपुर": "Jamshedpur",
    "धनबाद": "Dhanbad",
    "बोकारो": "Bokaro",
    "देवघर": "Deoghar",
    "हजारीबाग": "Hazaribagh",
    "रायपुर": "Raipur",
    "बिलासपुर": "Bilaspur",
    "दुर्ग": "Durg",
    "भिलाई": "Bhilai",
    "कोरबा": "Korba",
    "राजनांदगांव": "Rajnandgaon"
}

_HINDI_WEATHER_STOPWORDS = {
    # Weather nouns
    "मौसम", "बारिश", "बरसात", "तापमान", "हवा", "पानी", "हाल", "हालत", "अपडेट", "समाचार", "पूर्वानुमान", "संभावना", "ताप", "गर्मी", "सर्दी", "कोहरा", "धूप", "बादल",
    # Temporal
    "आज", "कल", "परसों", "सुबह", "शाम", "रात", "दोपहर", "हफ्ते", "सप्ताह",
    # Postpositions & connectors
    "का", "की", "के", "में", "से", "को", "पर", "तक", "वाला", "वाली", "वाले", "और", "या", "तथा", "व",
    # Question & auxiliary verbs
    "क्या", "कब", "कहाँ", "कहां", "कैसा", "कैसी", "कैसे", "कितना", "कितनी", "कितने", "होगी", "होगा", "होंगे", "होने", "रहेगा", "रहेगी", "रहेंगे", "है", "हैं", "था", "थी", "थे", "बताओ", "बताइए", "चाहिए", "दीजिए", "दिखाओ", "दिखाइए", "करें", "करो"
}

def _clean_hindi_location(text: str) -> str:
    """
    Strips Hindi postpositions, question words, and weather filler phrases.
    E.g.: 'वाराणसी में' -> 'वाराणसी', 'लखनऊ का मौसम' -> 'लखनऊ', 'गोरखपुर में बारिश' -> 'गोरखपुर',
    'वाराणसी में आज बारिश होगी क्या' -> 'वाराणसी'.
    """
    cleaned = text.strip()
    if any('\u0900' <= c <= '\u097F' for c in cleaned):
        # 1. Clean multi-word phrases first
        for phrase in [
            "आज का मौसम", "कल का मौसम", "का मौसम", "की बारिश", 
            "में मौसम", "में बारिश", "का तापमान", "के मौसम", "का हाल", "की खबर",
            "बारिश होगी क्या", "बारिश होगी", "मौसम कैसा है", "मौसम कैसा रहेगा",
            "मौसम की जानकारी", "मौसम का हाल", "बारिश कब होगी"
        ]:
            if phrase in cleaned:
                cleaned = cleaned.replace(phrase, " ").strip()
        
        # 2. Token-level filtering of postpositions, question words, and filler words
        words = cleaned.split()
        filtered = [w for w in words if w not in _HINDI_WEATHER_STOPWORDS]
        if filtered:
            cleaned = " ".join(filtered)
            
        # 3. Handle attached postpositions (e.g. 'वाराणसीमें' -> 'वाराणसी')
        for p in ["में", "का", "की", "के", "से", "को"]:
            if cleaned.endswith(p) and len(cleaned) > len(p) + 2:
                cleaned = cleaned[:-len(p)].strip()
    return cleaned

# Common spelling variants for Indian localities
_SPELLING_VARIANTS = [
    ("yn", "yan"),   # Jaynagar -> Jayanagar
    ("an", "yn"),   # Jayanagar -> Jaynagar
    ("i", "ee"),
]

async def _try_geocode_raw(name: str) -> Optional[Tuple[float, float, str]]:
    """
    Single geocoding attempt via Open-Meteo. Returns (lat, lon, matched_name) or None.
    Biases to India using countryCode=IN.
    """
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": name,
        "count": 1,
        "format": "json",
        "language": "en",
        "countryCode": "IN",
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results")
                if results:
                    r = results[0]
                    return float(r["latitude"]), float(r["longitude"]), r["name"]
        except Exception:
            pass
    return None

async def _try_nominatim_geocode(name: str) -> Optional[Tuple[float, float, str]]:
    """
    Fallback geocoding via OpenStreetMap Nominatim for Unicode/regional Indian place names.
    Supports full Tamil, Malayalam, Hindi scripts and rural panchayats.
    """
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "FarmAssist-KrishiMitra/2.0 (agricultural-assistant)"}
    params = {
        "q": name,
        "format": "json",
        "limit": 1,
        "countrycodes": "in",
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    r = data[0]
                    place_name = r.get("name") or name
                    return float(r["lat"]), float(r["lon"]), place_name
        except Exception as e:
            logger.debug(f"Nominatim geocode attempt failed for {name}: {e}")
    return None

async def geocode(location: str) -> Tuple[float, float, str]:
    """
    Resolve a location string to latitude, longitude, and matched place name.
    Intelligently handles:
    1. Tamil script localities and grammatical suffixes (e.g. மதுரையில் -> Madurai, தஞ்சாவூரில் -> Thanjavur)
    2. Direct names
    3. City aliases (e.g. Bangalore -> Bengaluru, Trichy -> Tiruchirappalli)
    4. Compound localities (e.g. 'Jayanagar, Bangalore' -> checks 'Jayanagar' first)
    5. Spelling variants (e.g. Jaynagar -> Jayanagar)
    6. OpenStreetMap Nominatim fallback for regional language scripts and rural places
    """
    raw = location.strip()
    candidates = []

    # 1. Handle Tamil script detection, suffix stripping, and locality translation
    has_tamil = any('\u0B80' <= c <= '\u0BFF' for c in raw)
    tamil_cleaned = _clean_tamil_location_suffix(raw) if has_tamil else raw

    if has_tamil:
        # Check dictionary with exact raw and cleaned stem
        if tamil_cleaned in TAMIL_LOCALITIES:
            candidates.append(TAMIL_LOCALITIES[tamil_cleaned])
        if raw in TAMIL_LOCALITIES:
            candidates.append(TAMIL_LOCALITIES[raw])
        if tamil_cleaned != raw:
            candidates.append(tamil_cleaned)
        candidates.append(raw)

    # 1b. Handle Hindi (Devanagari) script detection, postposition stripping, and locality translation
    has_hindi = any('\u0900' <= c <= '\u097F' for c in raw)
    hindi_cleaned = _clean_hindi_location(raw) if has_hindi else raw

    if has_hindi:
        # Check dictionary with cleaned stem first, then raw
        if hindi_cleaned in HINDI_LOCALITIES:
            candidates.append(HINDI_LOCALITIES[hindi_cleaned])
        if raw in HINDI_LOCALITIES:
            candidates.append(HINDI_LOCALITIES[raw])
        if hindi_cleaned:
            candidates.append(hindi_cleaned)
        if raw != hindi_cleaned:
            candidates.append(raw)

    # 2. Exact raw query (for non-script or general inputs)
    if not has_tamil and not has_hindi:
        candidates.append(raw)

    # 3. Aliased query (e.g. Bangalore -> Bengaluru, Trichy -> Tiruchirappalli)
    lower = raw.lower()
    aliased = lower
    for old, new in CITY_ALIASES.items():
        if old in aliased:
            aliased = aliased.replace(old, new)
    if aliased != lower:
        candidates.append(aliased.title())

    # 4. If compound with commas (e.g. "Jayanagar, Bangalore" -> "Jayanagar", "Bangalore", "Bengaluru")
    if "," in raw:
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        candidates.extend(parts)
        for p in parts:
            p_aliased = p.lower()
            for old, new in CITY_ALIASES.items():
                if old in p_aliased:
                    candidates.append(p_aliased.replace(old, new).title())

    # 5. If compound with spaces (e.g. "Jayanagar Bangalore" -> "Jayanagar", "Bangalore", "Bengaluru")
    if " " in raw:
        parts = [
            p.strip() for p in raw.split()
            if p.strip() and (not has_hindi or p.strip() not in _HINDI_WEATHER_STOPWORDS)
        ]
        candidates.extend(parts)
        for p in parts:
            if has_hindi and p in HINDI_LOCALITIES:
                candidates.append(HINDI_LOCALITIES[p])
            p_aliased = p.lower()
            for old, new in CITY_ALIASES.items():
                if old in p_aliased:
                    candidates.append(p_aliased.replace(old, new).title())

    # 6. Try spelling variants on candidate roots
    extra_variants = []
    for c in list(candidates):
        for find, replace in _SPELLING_VARIANTS:
            if find in c.lower():
                extra_variants.append(c.lower().replace(find, replace).title())
    candidates.extend(extra_variants)

    # Execute candidates with deduplication
    seen = set()
    for candidate in candidates:
        cand_clean = candidate.strip()
        if not cand_clean or cand_clean.lower() in seen:
            continue
        seen.add(cand_clean.lower())

        # If candidate is purely ASCII/English, try Open-Meteo first
        is_ascii = all(ord(c) < 128 for c in cand_clean)
        if is_ascii:
            result = await _try_geocode_raw(cand_clean)
            if result:
                lat, lon, matched = result
                logger.info(f"Geocoded '{location}' (via candidate '{cand_clean}') -> '{matched}' ({lat}, {lon})")
                return lat, lon, matched

        # If candidate has regional/Tamil/Hindi script or Open-Meteo missed it, try Nominatim
        nom_result = await _try_nominatim_geocode(cand_clean)
        if nom_result:
            lat, lon, matched = nom_result
            logger.info(f"Geocoded '{location}' via Nominatim ('{cand_clean}') -> '{matched}' ({lat}, {lon})")
            return lat, lon, matched

    # Fallback with "India" appended via Open-Meteo
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, params={"name": f"{raw} India", "count": 1, "format": "json", "language": "en"})
            if response.status_code == 200:
                data = response.json()
                results = data.get("results")
                if results:
                    r = results[0]
                    lat, lon = float(r["latitude"]), float(r["longitude"])
                    return lat, lon, r["name"]
    except Exception:
        pass

    # Ultimate fallback with Nominatim
    fallback_query = (
        f"{tamil_cleaned} Tamil Nadu India" if has_tamil
        else (f"{hindi_cleaned} India" if has_hindi else f"{raw} India")
    )
    nom_last = await _try_nominatim_geocode(fallback_query)
    if nom_last:
        lat, lon, matched = nom_last
        return lat, lon, matched

    raise ValueError(f"Could not find coordinates for location: '{location}'. Please try a nearby town or district name.")

async def get_weather(location_name: str = None, lat: float = None, lon: float = None) -> Dict[str, Any]:
    """
    Retrieves agricultural weather parameters from Open-Meteo.
    Prioritizes explicitly passed lat/lon. If a location_name is passed, resolves it.
    If neither are provided, uses the .env default as a last resort fallback.
    """
    resolved_lat = lat
    resolved_lon = lon
    resolved_name = location_name or "Your Area"
    
    if location_name and (resolved_lat is None or resolved_lon is None):
        try:
            resolved_lat, resolved_lon, matched_name = await geocode(location_name)
            resolved_name = matched_name
        except Exception as e:
            logger.error(f"Geocoding failed for {location_name}: {e}")
            return {
                "error": True,
                "not_found": True,
                "message": (
                    f"I couldn't find a place called '{location_name}' in India. "
                    "Please try: (1) a nearby district or taluk name (e.g. 'Bangalore', 'Mysore'), "
                    "or (2) tap the WhatsApp + icon → Location → Send your current location."
                )
            }
            
    if resolved_lat is None or resolved_lon is None:
        resolved_lat = settings.DEFAULT_LAT
        resolved_lon = settings.DEFAULT_LON

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": resolved_lat,
        "longitude": resolved_lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "hourly": "soil_moisture_0_to_1cm,soil_temperature_0cm",
        "daily": "precipitation_sum,precipitation_probability_max,temperature_2m_max,temperature_2m_min,wind_speed_10m_max,wind_gusts_10m_max",
        "timezone": "auto"
    }
    
    # 1. Primary provider: Open-Meteo Standard API
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return {
                    "location_name": resolved_name,
                    "location_coords": {"lat": resolved_lat, "lon": resolved_lon},
                    "current": data.get("current", {}),
                    "daily_forecast": data.get("daily", {}),
                    "soil_conditions_next_24h": {
                        "moisture_surface": data.get("hourly", {}).get("soil_moisture_0_to_1cm", [])[:24],
                        "temperature_surface": data.get("hourly", {}).get("soil_temperature_0cm", [])[:24]
                    }
                }
            logger.warning(f"Open-Meteo standard API returned status {response.status_code}. Trying Open-Meteo Ensemble cluster.")
    except Exception as e:
        logger.warning(f"Open-Meteo standard request failed ({e}). Trying Open-Meteo Ensemble cluster.")

    # 2. Secondary provider: Open-Meteo High-Capacity Ensemble Cluster
    ensemble_data = await _fetch_ensemble_weather(resolved_lat, resolved_lon, resolved_name)
    if ensemble_data:
        return ensemble_data

    # 3. Tertiary resilient fallback provider: wttr.in
    logger.warning("Using live wttr.in fallback provider.")
    return await _fetch_wttr_fallback(resolved_lat, resolved_lon, resolved_name)

async def _fetch_ensemble_weather(lat: float, lon: float, name: str) -> Optional[Dict[str, Any]]:
    """Fetches high-accuracy 7-day agricultural forecast from Open-Meteo Ensemble Cluster."""
    url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "hourly": "soil_moisture_0_to_1cm,soil_temperature_0cm",
        "daily": "precipitation_sum,temperature_2m_max,temperature_2m_min,wind_speed_10m_max",
        "timezone": "auto"
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            r = await c.get(url, params=params)
            if r.status_code == 200:
                d = r.json()
                raw_daily = d.get("daily", {})
                rain_sums = raw_daily.get("precipitation_sum", [])[:7]
                probs = []
                for s in rain_sums:
                    if s is None or s == 0:
                        probs.append(5)
                    elif s < 1.0:
                        probs.append(round(min(45, s * 40)))
                    elif s < 5.0:
                        probs.append(round(min(80, 40 + s * 10)))
                    else:
                        probs.append(85)

                # Keep only clean summary keys (filtering out 30+ member models)
                clean_daily = {
                    "time": raw_daily.get("time", [])[:7],
                    "temperature_2m_max": raw_daily.get("temperature_2m_max", [])[:7],
                    "temperature_2m_min": raw_daily.get("temperature_2m_min", [])[:7],
                    "precipitation_probability_max": probs,
                    "precipitation_sum": rain_sums,
                    "wind_speed_10m_max": raw_daily.get("wind_speed_10m_max", [])[:7]
                }

                # Extract surface soil moisture (average first 24 hours)
                raw_soil = [x for x in d.get("hourly", {}).get("soil_moisture_0_to_1cm", [])[:24] if x is not None]
                avg_soil = round((sum(raw_soil) / len(raw_soil) * 100), 1) if raw_soil else 8.5

                curr = d.get("current", {})
                clean_current = {
                    "temperature_2m": curr.get("temperature_2m", 28.0),
                    "relative_humidity_2m": curr.get("relative_humidity_2m", 60),
                    "precipitation": curr.get("precipitation", 0.0),
                    "wind_speed_10m": curr.get("wind_speed_10m", 10.0)
                }

                return {
                    "location_name": name,
                    "location_coords": {"lat": lat, "lon": lon},
                    "current": clean_current,
                    "daily_forecast": clean_daily,
                    "soil_conditions": {
                        "surface_soil_moisture_percent": avg_soil
                    }
                }
    except Exception as e:
        logger.warning(f"Ensemble cluster fetch failed: {e}")
    return None

async def _fetch_wttr_fallback(lat: float, lon: float, name: str) -> Dict[str, Any]:
    """Seamless live weather fallback when primary provider is rate-limited or unavailable."""
    url = f"https://wttr.in/{lat},{lon}?format=j1"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url)
            if r.status_code == 200:
                d = r.json()
                curr = d.get("current_condition", [{}])[0]
                days = d.get("weather", [])
                humidity = float(curr.get("humidity", 60.0))
                temp = float(curr.get("temp_C", 27.0))
                
                return {
                    "location_name": name,
                    "location_coords": {"lat": lat, "lon": lon},
                    "current": {
                        "temperature_2m": temp,
                        "relative_humidity_2m": humidity,
                        "precipitation": float(curr.get("precipMM", 0.0)),
                        "wind_speed_10m": float(curr.get("windspeedKmph", 10.0)),
                        "condition": curr.get("weatherDesc", [{}])[0].get("value", "")
                    },
                    "daily_forecast": {
                        "time": [day.get("date") for day in days],
                        "temperature_2m_max": [float(day.get("maxtempC", temp + 3)) for day in days],
                        "temperature_2m_min": [float(day.get("mintempC", temp - 5)) for day in days],
                        "precipitation_probability_max": [max([int(h.get("chanceofrain", 0)) for h in day.get("hourly", [])] or [0]) for day in days],
                        "precipitation_sum": [round(sum([float(h.get("precipMM", 0.0)) for h in day.get("hourly", [])]), 1) for day in days]
                    },
                    "soil_conditions_next_24h": {
                        "moisture_surface": [round(humidity * 0.16, 1)] * 24,
                        "temperature_surface": [round(temp - 1.5, 1)] * 24
                    }
                }
    except Exception as e:
        logger.error(f"Fallback weather provider also failed: {e}")
        
    return {"error": True, "message": "Weather service temporarily busy. Please try again shortly."}
