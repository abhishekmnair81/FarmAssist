from typing import TypedDict, Annotated, List, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode
from app.config import settings
from app.tools import weather
from app.tools.rag_tool import query_agri_knowledge_base
from app.tools.web_search import search_duckduckgo, search_live_web
from app.tools.mandi_rates import fetch_live_mandi_rates
import json
import asyncio
import logging
import time
import re

logger = logging.getLogger(__name__)

_groq_rate_limited_until = 0.0

def is_groq_rate_limited() -> bool:
    global _groq_rate_limited_until
    return time.time() < _groq_rate_limited_until

def mark_groq_rate_limited(seconds: float = 600.0):
    global _groq_rate_limited_until
    _groq_rate_limited_until = time.time() + seconds

# Define the State
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    sender_phone: str
    user_lat: float
    user_lon: float
    user_language: str

# Define Tools
@tool
async def fetch_weather_tool(location_name: str = "", location: str = "", lat: float = None, lon: float = None) -> str:
    """
    Fetches agricultural weather data including temperature, precipitation, wind, and soil moisture.
    Provide a `location_name` or `location` (e.g. 'Bangalore', 'Delhi', 'Kolar') if the user asks for a specific place.
    If the user has a saved GPS location, pass it via `lat` and `lon`.
    DO NOT call this tool for greetings (like 'hey' or 'hi') or if the user did not ask about weather.
    """
    target_loc = (location_name or location).strip()
    if target_loc.lower() in ["hey", "hi", "hello", "halo", "start", "none", "null", "undefined"]:
        target_loc = ""

    if not target_loc and lat is None and lon is None:
        return "NO_LOCATION_SPECIFIED: Please ask the farmer for their village, town, or district name, or to share their GPS location."

    data = await weather.get_weather(target_loc if target_loc else None, lat, lon)
    if data.get("error"):
        if data.get("not_found"):
            return f"LOCATION_NOT_FOUND: {data.get('message', 'Location could not be resolved.')}"
        return f"WEATHER_ERROR: {data.get('message', 'Weather service temporarily busy. Please try again.')}"
    return json.dumps(data)

tools = [fetch_weather_tool, fetch_live_mandi_rates, search_duckduckgo, query_agri_knowledge_base]

# Initialize LLM with automatic connection retry and fast failover
llm = ChatGroq(
    model=settings.LLM_MODEL,
    api_key=settings.GROQ_API_KEY,
    temperature=0.2,
    max_tokens=450,
    max_retries=1,
    request_timeout=20.0
)
llm_with_tools = llm.bind_tools(tools)

def get_nvidia_llm_with_tools(model_name: str = None, bind_tools: bool = True):
    """Initializes NVIDIA NIM LLM (with or without tool binding) as a high-reliability fallback."""
    key = settings.effective_nvidia_api_key
    if not key:
        return None
    model = model_name or settings.NVIDIA_MODEL or "meta/llama-3.2-11b-vision-instruct"
    try:
        from langchain_openai import ChatOpenAI
        n_llm = ChatOpenAI(
            model=model,
            api_key=key,
            base_url=settings.NVIDIA_BASE_URL,
            temperature=0.2,
            max_tokens=450,
            max_retries=1,
            request_timeout=20.0
        )
        return n_llm.bind_tools(tools) if bind_tools else n_llm
    except Exception as e:
        logger.error(f"Failed to initialize NVIDIA NIM LLM ({model}): {e}")
        return None

SUPPORTED_LANGUAGES_MAP = {
    "english": "English",
    "malayalam": "Malayalam",
    "മലയാളം": "Malayalam",
    "hindi": "Hindi",
    "हिन्दी": "Hindi",
    "tamil": "Tamil",
    "தமிழ்": "Tamil",
}

def is_greeting(text: str) -> bool:
    """Detects any greeting or conversational opener, including slang, repeated letters ('hy', 'hyyy', 'heyy', 'yo')."""
    if not text:
        return False
    cleaned = re.sub(r"[^\w\s]", "", text.strip().lower())
    if not cleaned:
        return False
    
    GREETING_PHRASES = {
        "good morning", "good afternoon", "good evening", "good day",
        "hey there", "hi there", "hello there", "hy there",
        "hey bro", "hi bro", "hy bro", "hello bro",
        "hey bot", "hi bot", "hy bot", "hello bot",
        "hi farmassist", "hey farmassist", "hy farmassist", "hello farmassist",
        "farmassist", "start"
    }
    if cleaned in GREETING_PHRASES:
        return True

    collapsed = re.sub(r"(.)\1+", r"\1", cleaned).strip()
    
    GREETING_WORDS = {
        "hi", "hey", "hy", "hello", "helo", "halo", "hlo", "hlw", "hai", "haai",
        "hola", "yo", "sup", "gm", "ge",
        "start", "vanakkam", "namaste", "namaskar", "namaskaram",
        "pranam", "salaam", "adaab"
    }
    
    if cleaned in GREETING_WORDS or collapsed in GREETING_WORDS:
        return True
        
    words = cleaned.split()
    if len(words) <= 3:
        first_word = words[0]
        first_collapsed = re.sub(r"(.)\1+", r"\1", first_word)
        if (first_word in GREETING_WORDS or first_collapsed in GREETING_WORDS) and all(
            w in GREETING_WORDS or w in {"there", "bro", "buddy", "sir", "friend", "bot", "farmassist", "farm", "assist"}
            for w in words
        ):
            return True

    return False

def is_help_or_persona_query(text: str) -> bool:
    """Detects common prompts asking who FarmAssist is, what it can do, or general help/capabilities."""
    if not text:
        return False
    t = text.strip().lower().rstrip("?.!,")
    common_help_triggers = {
        "who are you", "what are you", "what can you do", "help", "help me",
        "how does this work", "how to use", "features", "services", "menu",
        "kya kar sakte ho", "aap kaun ho", "madad", "sahayata",
        "aaranu nee", "enthellam cheyyam", "sahayam",
        "neenga yaar", "enna seiya mudiyum", "udhavi"
    }
    if t in common_help_triggers:
        return True
    return any(t.startswith(prefix) for prefix in [
        "who are you", "what can you do", "what do you do", "help me with",
        "aap kaun", "kya kar sakte", "aaranu", "enthellam cheyyam", "neenga yaar", "enna seiya"
    ])

def detect_language_choice_fast(text: str) -> str | None:
    """Checks if message is pure language selection."""
    if not text:
        return None
    cleaned = text.strip().lower().rstrip(".!,")
    if cleaned in SUPPORTED_LANGUAGES_MAP:
        return SUPPORTED_LANGUAGES_MAP[cleaned]
    words = cleaned.split()
    if len(words) <= 2:
        for kw, lang in SUPPORTED_LANGUAGES_MAP.items():
            if kw in words:
                return lang
    return None

# Define Nodes
async def agent_node(state: AgentState):
    messages = state["messages"]
    
    user_language = state.get("user_language")
    user_lat = state.get("user_lat")
    user_lon = state.get("user_lon")
    location_context = f"\nThe user's saved GPS location is Lat: {user_lat}, Lon: {user_lon}." if user_lat and user_lon else "\nThe user HAS NOT provided their location yet."

    # Fast-path for greetings, persona queries & language selection: Never call tools or LLM
    last_human_text = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            last_human_text = m.content.strip().lower().rstrip("!.,")
            break

    # Auto-detect language if not explicitly provided
    if not user_language and last_human_text:
        if re.search(r"[\u0900-\u097F]", last_human_text):
            user_language = "Hindi"
        elif re.search(r"[\u0B80-\u0BFF]", last_human_text):
            user_language = "Tamil"
        elif re.search(r"[\u0D00-\u0D7F]", last_human_text):
            user_language = "Malayalam"
        elif re.search(r"[a-zA-Z]", last_human_text):
            user_language = "English"

    # 1. Help & Krishi Mitra Persona Fast Path
    if is_help_or_persona_query(last_human_text):
        lang = user_language or "English"
        persona_cards = {
            "English": (
                "🌾 **Namaste! I am FarmAssist, your AI Krishi Mitra & Agricultural Advisor.** 🚜\n\n"
                "Here is how I can help your farm:\n"
                "1. 🌿 **Crop Care:** Fertilizer schedules, soil health, irrigation advice.\n"
                "2. 📸 **Plant Disease Diagnosis:** Send a photo of any diseased leaf or pest for instant remedies.\n"
                "3. 🌦️ **Weather Forecasts:** Hyperlocal rain, temperature, and safe spray windows.\n"
                "4. 📈 **Live Mandi Prices:** Real-time APMC commodity market rates across India.\n"
                "5. 🏛️ **Government Schemes:** PM-KISAN, crop insurance (PMFBY), and subsidies.\n"
                "6. 🐄 **Dairy & Livestock Care:** Cattle health, feed nutrition, and management.\n\n"
                "Type your query or send a voice note / photo to get started!"
            ),
            "Malayalam": (
                "🌾 **നമസ്കാരം! ഞാൻ ഫാംഅസിസ്റ്റ് (FarmAssist), നിങ്ങളുടെ വിശ്വസ്ത കാർഷിക സഹായി (Krishi Mitra).** 🚜\n\n"
                "എനിക്ക് നിങ്ങളെ താഴെ പറയുന്ന കാര്യങ്ങളിൽ സഹായിക്കാനാകും:\n"
                "1. 🌿 **വിള പരിപാലനം:** വളപ്രയോഗം, നടീൽ രീതികൾ, നനയ്ക്കൽ ഉപദേശങ്ങൾ.\n"
                "2. 📸 **ഇല രോഗനിർണ്ണയം:** രോഗം ബാധിച്ച ഇലയുടെ ഫോട്ടോ അയച്ചാൽ ഉടൻ രോഗനിർണ്ണയവും പ്രതിവിധിയും.\n"
                "3. 🌦️ **കാലാവസ്ഥാ മുന്നറിയിപ്പ്:** മഴ സാധ്യത, താപനില, മരുന്ന് തളിക്കാൻ അനുയോജ്യമായ സമയം.\n"
                "4. 📈 **വിപണി വിലകൾ (Mandi Rates):** തത്സമയ പച്ചക്കറി, ധാന്യ മാർക്കറ്റ് നിരക്കുകൾ.\n"
                "5. 🏛️ **സർക്കാർ പദ്ധതികൾ:** പി.എം കിസാൻ, വിള ഇൻഷുറൻസ് വിവരങ്ങൾ.\n"
                "6. 🐄 **ക്ഷീരവികസനം & കന്നുകാലി പരിപാലനം.**\n\n"
                "നിങ്ങളുടെ കൃഷി സംബന്ധമായ ഏത് ചോദ്യവും ചോദിക്കാം!"
            ),
            "Tamil": (
                "🌾 **வணக்கம்! நான் ஃபார்ம்அசிஸ்ட் (FarmAssist), உங்கள் விவசாய நண்பன் (Krishi Mitra).** 🚜\n\n"
                "நான் உங்களுக்கு பின்வரும் சேவைகளை வழங்குகிறேன்:\n"
                "1. 🌿 **பயிர் சாகுபடி:** உரம் இடும் முறைகள், பாசன ஆலோசனை, விதை தேர்வு.\n"
                "2. 📸 **இலை நோய் கண்டறிதல்:** பாதிக்கப்பட்ட இலை அல்லது செடியின் புகைப்படத்தை அனுப்பினால் உடனடி தீர்வு.\n"
                "3. 🌦️ **வானிலை எச்சரிக்கை:** மழை வாய்ப்பு மற்றும் பூச்சிக்கொல்லி தெளிப்பதற்கான உகந்த நேரம்.\n"
                "4. 📈 **மண்டி சந்தை விலைகள்:** முக்கிய சந்தைகளின் தற்போதைய விலை நிலவரம்.\n"
                "5. 🏛️ **அரசு திட்டங்கள்:** PM-கிசான், பயிர் காப்பீடு பற்றிய தகவல்கள்.\n"
                "6. 🐄 **கால்நடை பராமரிப்பு.**\n\n"
                "உங்கள் கேள்விகளை தட்டச்சு செய்தோ அல்லது குரல் பதிவாகவோ அனுப்புங்கள்!"
            ),
            "Hindi": (
                "🌾 **नमस्ते! मैं फार्मअसिस्ट (FarmAssist) हूँ, आपका समर्पित कृषि मित्र (AI Krishi Mitra)।** 🚜\n\n"
                "मैं आपकी इन सभी कार्यों में सहायता कर सकता हूँ:\n"
                "1. 🌿 **फसल प्रबंधन एवं पोषण:** खाद-उर्वरक की सही मात्रा, सिंचाई और बुवाई सलाह।\n"
                "2. 📸 **पत्ती रोग पहचान:** किसी भी रोगग्रस्त पत्ती की फोटो भेजें, तुरंत जैविक व रासायनिक उपचार पाएं।\n"
                "3. 🌦️ **मौसम एवं छिड़काव परामर्श:** बारिश का पूर्वानुमान और कीटनाशक छिड़काव का सही समय।\n"
                "4. 📈 **लाइव मंडी भाव:** प्रमुख मंडियों के ताजा जिंस रेट।\n"
                "5. 🏛️ **सरकारी योजनाएं:** पीएम-किसान सम्मान निधि और फसल बीमा सहायता।\n"
                "6. 🐄 **पशुपालन एवं डेयरी विकास।**\n\n"
                "खेती से जुड़ा अपना कोई भी सवाल लिखकर या वॉइस नोट भेजकर पूछें!"
            )
        }
        return {"messages": [AIMessage(content=persona_cards.get(lang, persona_cards["English"]))]}

    # 2. Pure greeting fast path
    if is_greeting(last_human_text):
        if not user_language:
            greeting_reply = (
                "Hey there! 👋 I'm FarmAssist, your friendly farming buddy.\n\n"
                "How can I help you today? Please pick your preferred language:\n"
                "- English\n"
                "- മലയാളം (Malayalam)\n"
                "- हिन्दी (Hindi)\n"
                "- தமிழ் (Tamil)"
            )
            return {"messages": [AIMessage(content=greeting_reply)]}
        else:
            # Localized greeting if language is already known
            greeting_map = {
                "Malayalam": "നമസ്കാരം! 👋 ഞാൻ FarmAssist ആണ്. നിങ്ങളുടെ കൃഷിയെയോ കാലാവസ്ഥയെയോ കുറിച്ച് ഇന്ന് ഞാൻ എങ്ങനെയാണ് സഹായിക്കേണ്ടത്?",
                "Hindi": "नमस्ते! 👋 मैं FarmAssist हूँ। आज मैं आपकी फसल या मौसम की जानकारी में कैसे मदद कर सकता हूँ?",
                "Tamil": "வணக்கம்! 👋 நான் FarmAssist. உங்கள் விவசாயம் அல்லது வானிலை குறித்து இன்று எவ்வாறு உதவ முடியும்?",
            }
            default_greeting = "Hey there! 👋 I'm FarmAssist. How can I help you with your crops, weather, or farming advice today?"
            return {"messages": [AIMessage(content=greeting_map.get(user_language, default_greeting))]}

    # 3. Pure language selection fast path
    pure_lang = detect_language_choice_fast(last_human_text)
    if pure_lang and len(last_human_text.split()) <= 3:
        ack_map = {
            "English": "Great! I've set your preferred language to English. 🌾\n\nHow can I assist you with your farming, crops, or weather today?",
            "Malayalam": "തീർച്ചയായും! ഞാൻ നിങ്ങളുടെ ഭാഷ മലയാളമായി സജ്ജീകരിച്ചു. 🌾\n\nനിങ്ങളുടെ കൃഷിയെയോ കാലാവസ്ഥയെയോ കുറിച്ച് ഇന്ന് എന്താണ് അറിയേണ്ടത്?",
            "Hindi": "बिल्कुल! आपकी भाषा हिन्दी सेट कर दी गई है। 🌾\n\nआज मैं आपकी खेती, फसल या मौसम से जुड़ी किस बात में मदद कर सकता हूँ?",
            "Tamil": "நிச்சயமாக! உங்கள் மொழி தமிழ் என அமைக்கப்பட்டுள்ளது. 🌾\n\nஉங்கள் விவசாயம், பயிர்கள் அல்லது வானிலை குறித்து இன்று எவ்வாறு உதவ முடியும்?",
        }
        ack_msg = ack_map.get(pure_lang, ack_map["English"])
        return {"messages": [AIMessage(content=ack_msg)], "user_language": pure_lang}

    if user_language:
        language_section = (
            f"# 1. USER LANGUAGE: {user_language}\n"
            f"- The user's active language is {user_language}.\n"
            f"- Respond completely in {user_language} and in its native script.\n"
            f"- Do NOT ask the user to pick their language again.\n"
            f"- If the user explicitly switches to another language, switch instantly and acknowledge the change.\n"
        )
    else:
        language_section = (
            "# 1. GREETING & ONBOARDING\n"
            "- If this is the first message and language is not yet known, introduce yourself warmly in 1 short sentence.\n"
            "- Ask the user to pick their preferred language: English, മലയാളം (Malayalam), हिन्दी (Hindi), or தமிழ் (Tamil).\n"
        )

    # Prepend SystemMessage if not present in context window
    sys_msg = SystemMessage(
        content=(
            "You are FarmAssist, a friendly, expert agronomist AI assistant helping farmers over WhatsApp.\n"
            "CRITICAL: Always output your response directly to the farmer. Do NOT use <think> tags.\n\n"
            f"{language_section}\n"
            "# 2. STRICT AGRICULTURAL CONTEXT BOUNDARY (MANDATORY)\n"
            "- You are EXCLUSIVELY an agricultural, farming, weather, and crop advisory assistant named FarmAssist.\n"
            "- ALLOWED TOPICS:\n"
            "  1. Crop cultivation, soil health, seeds, fertilizers, organic farming, and irrigation.\n"
            "  2. Plant diseases, leaf symptoms, pests, weeds, and agricultural remedies.\n"
            "  3. Agricultural weather forecasts, spray windows, and seasonal advice.\n"
            "  4. APMC Mandi commodity rates, market trends, and agricultural marketing (via fetch_live_mandi_rates).\n"
            "  5. Government agricultural schemes (PM-KISAN, crop insurance, subsidies).\n"
            "  6. Livestock, poultry, dairy, and rural livelihoods.\n"
            "- STRICT OFF-TOPIC REFUSAL POLICY:\n"
            "  If the user asks about ANY question outside agriculture (e.g. computer coding, politics, movies, general trivia, gaming, sports, romance, non-farm finance, or human medicine):\n"
            "  YOU MUST POLITELY DECLINE. Do NOT attempt to answer off-topic questions.\n"
            "  Politely explain that FarmAssist is dedicated strictly to agriculture, farming, crops, weather, and mandi prices, and kindly invite them to ask an agricultural question.\n\n"
            "# 3. ADVISORY STYLE & FARMER SIMPLICITY\n"
            "- Tone: Warm, practical, and empathetic. Strictly avoid complex academic or chemical jargon.\n"
            "- First-Response Rule: Keep initial responses simple and focused ONLY on basic essential needs: 1) What it is / what to use it for, 2) How much to use (exact simple dose), and 3) When/how to apply. Do NOT overwhelm the farmer with excessive paragraphs.\n"
            "- Follow-up Depth: If the farmer asks follow-up questions (such as safety precautions, harvest waiting time / PHI, chemical toxicity, or detailed scientific reasons), then provide full, accurate, in-depth details referencing CIBRC/PPQS/ICAR standards.\n"
            "- Format: Keep replies concise (short bullet points). Use bold text for key dosages and critical warnings.\n"
            "- Clean WhatsApp Formatting: NEVER output HTML tags (such as <br>, <p>, <b>). Use standard line breaks. For bullet points, use clean dashes ('- ') or bullet dots. Never leave stray, dangling asterisks or unclosed markdown.\n"
            "- Direct Action Answers: For action or permission questions (e.g. 'Can I spray?', 'Should I irrigate today?'), start with a direct 'Yes / No / Delay' before explaining why. For open-ended crop recommendations or market price questions, answer directly with the crop advice and expected mandi rates without saying Yes/No.\n\n"
            "# 4. WEATHER & LOCATION\n"
            f"{location_context}\n"
            "- WEATHER INQUIRIES: When the user asks specifically about current weather, rain, temperature, or spraying windows, CHECK if they provided a specific place name or if you have their saved GPS location. If no location is mentioned and none is saved, politely ask for their town or to share location via WhatsApp.\n"
            "- CROP PLANNING, PROFITABILITY & MARKET DEMAND:\n"
            "  * When asked broad questions like 'which crop will have more sale in the coming days', 'which crops have high demand', 'what should I plant for profit', or 'best crops to grow':\n"
            "  * DO NOT interrogate the farmer in repetitive loops demanding specific crop names, soil, or water before providing an answer!\n"
            "  * IMMEDIATELY answer with top high-demand seasonal crops (e.g., commercial vegetables like tomatoes, green chillies, onions, garlic; seasonal pulses and oilseeds; cash crops).\n"
            "  * If the user gave a location (e.g. Varanasi, UP, Punjab, Tamil Nadu) or you have their saved location, TAILOR the crop recommendations and mandi demand directly to that region's agro-climatic zone and wholesale mandi demand.\n"
            "  * You may use `search_duckduckgo` or `fetch_live_mandi_rates` to check current market trends.\n"
            "  * Recommend 2-3 specific lucrative crops, their sowing/harvest window, and expected market price range.\n"
            "- **PROFESSIONAL WEATHER ADVISORY FORMAT**:\n"
            "  When reporting weather, you MUST organize your response with these clear, structured sections:\n"
            "  * Header: \"Here is the current weather update for **[Location Name]**:\"\n"
            "  * **Current Conditions:**\n"
            "    - **Temperature:** [X]°C (with contextual descriptor, e.g. \"Comfortable evening\", \"Warm afternoon\")\n"
            "    - **Humidity:** [X]%\n"
            "    - **Rain:** None currently / ongoing\n"
            "    - **Wind:** [Speed] km/h\n"
            "  * **Forecast for the Next Few Days:**\n"
            "    - Multi-day breakdown with temperature highs, rain chance %, and expected rainfall.\n"
            "  * **Soil Status:**\n"
            "    - Surface soil moisture % and practical agricultural interpretation.\n"
            "  * **Advice:**\n"
            "    - **Irrigation:** Direct recommendation (delay or irrigate based on upcoming rain).\n"
            "    - **Spraying:** Safe spray window based on rain and wind conditions.\n"
            "  * Source tag: `[Source: Open-Meteo Forecast]`\n\n"
            "# 5. APMC MANDI MARKET RATES & PRICES\n"
            "- When asked about a specific commodity price (e.g. 'tomato price in Kolar', 'wheat rate today'), ALWAYS use `fetch_live_mandi_rates`.\n"
            "- When asked broad market questions (e.g. 'which crop is selling well / high demand'), use `fetch_live_mandi_rates(commodity='crops', state_or_market=...)` or `search_duckduckgo`.\n"
            "- Report the modal (average) price and the range in ₹/Quintal and ₹/kg.\n"
            "- Append `[Source: APMC Mandi Rates]` or `[Source: APMC Mandi / Agmarknet Market Intelligence]`.\n\n"
            "# 6. AGRICULTURAL ACCURACY & GROUNDING\n"
            "- Ground all advice in established ICAR agronomy, seasonal crop calendars (Kharif, Rabi, Zaid), and genuine market economics.\n"
            "- If neither web search nor database returns information, provide sound agronomic principles rather than repetitive loops.\n"
            "- Safe Fallback: Advise them to consult the local Krishi Vigyan Kendra (KVK) or Kisan Call Center (1800-180-1551).\n\n"
            "# 7. MANDATORY SOURCE CITATIONS\n"
            "- Append exactly one of the following tags if a tool was used:\n"
            "  * If retrieved via `fetch_live_mandi_rates`: `[Source: APMC Mandi Rates]`\n"
            "  * If retrieved via `search_duckduckgo`: `[Source: DuckDuckGo - <Domain>]`\n"
            "  * If retrieved via `query_agri_knowledge_base`: `[Source: ICAR Advisory / Govt Scheme Database]`\n"
            "  * If based purely on weather telemetry: `[Source: Open-Meteo Forecast]`"
        )
    )
    
    # Filter out existing system messages to avoid duplication
    filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    
    # Cap tool calls per turn to 2. Count ONLY ToolMessages executed in the current turn.
    current_turn_tool_msgs = []
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            break
        if isinstance(m, ToolMessage):
            current_turn_tool_msgs.append(m)

    allow_tools = len(current_turn_tool_msgs) < 2
    active_groq_caller = llm_with_tools if allow_tools else llm
    
    # Check circuit breaker before attempting Groq
    can_use_groq = not is_groq_rate_limited()
    
    if can_use_groq:
        try:
            response = await asyncio.wait_for(active_groq_caller.ainvoke([sys_msg] + filtered_messages), timeout=20.0)
            return {"messages": [response]}
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = any(term in err_str for term in ["429", "rate_limit", "rate limit", "tokens", "limit", "quota", "too large", "tpm", "rpm"])
            
            if is_rate_limit or isinstance(e, asyncio.TimeoutError):
                mark_groq_rate_limited(600.0)
                logger.warning(f"Groq API rate limit or timeout ({e}). Switching to NVIDIA NIM immediately.")
            else:
                logger.warning(f"Groq invocation error ({e}). Switching to NVIDIA NIM immediately.")

    # Silent, seamless fallback to NVIDIA NIM API
    nvidia_caller = get_nvidia_llm_with_tools(bind_tools=allow_tools)
    if nvidia_caller:
        try:
            response = await asyncio.wait_for(nvidia_caller.ainvoke([sys_msg] + filtered_messages), timeout=20.0)
            return {"messages": [response]}
        except Exception as nve:
            logger.warning(f"NVIDIA NIM primary error: {nve}. Retrying backup...")
            backup_caller = get_nvidia_llm_with_tools("meta/llama-3.2-11b-vision-instruct", bind_tools=allow_tools)
            if backup_caller:
                try:
                    response = await asyncio.wait_for(backup_caller.ainvoke([sys_msg] + filtered_messages), timeout=20.0)
                    return {"messages": [response]}
                except Exception as be:
                    logger.warning(f"NVIDIA NIM backup error: {be}")

    # Graceful user-friendly fallback response instead of hanging or crashing
    logger.warning("All LLM providers (Groq and NVIDIA) failed or timed out. Returning friendly fallback.")
    fallback_replies = {
        "Malayalam": "ക്ഷമിക്കണം, ഞങ്ങളുടെ കാർഷിക സെർവറുകളുമായി കണക്റ്റുചെയ്യുന്നതിൽ ഒരു ചെറിയ തടസ്സം നേരിടുന്നു. ദയവായി അല്പം കഴിഞ്ഞ് നിങ്ങളുടെ ചോദ്യം വീണ്ടും ചോദിക്കാമോ?",
        "Hindi": "क्षमा करें, हमारे कृषि सर्वर से जुड़ने में कुछ देरी हो रही है। कृपया कुछ क्षण बाद अपना प्रश्न दोबारा पूछें।",
        "Tamil": "மன்னிக்கவும், எங்கள் சேவையகங்களை இணைப்பதில் சிறிய தாமதம் ஏற்பட்டுள்ளது. தயவுசெய்து சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்.",
        "English": "I'm experiencing a brief connection delay with our agronomy servers. Please send your question again in a moment!"
    }
    safe_reply = fallback_replies.get(user_language, fallback_replies["English"])
    return {"messages": [AIMessage(content=safe_reply)]}

# Define Routing Logic
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    # If the last message requested tool calls, route to tools only if current turn allows
    if getattr(last_message, "tool_calls", None):
        current_turn_tool_msgs = []
        for m in reversed(messages):
            if isinstance(m, HumanMessage):
                break
            if isinstance(m, ToolMessage):
                current_turn_tool_msgs.append(m)
        if len(current_turn_tool_msgs) < 2:
            return "tools"
            
    return END

# Build the Graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", agent_node)
workflow.add_node("tools", ToolNode(tools))

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

# We don't compile with checkpointer here; it will be compiled per request in main.py
