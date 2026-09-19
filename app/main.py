from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from contextlib import asynccontextmanager
import base64
import logging
import os
import re
import asyncio
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agent.graph import workflow
from app.services.stt import transcribe_audio_groq
from app.services.tts import synthesize_speech, detect_voice
from app.services.guardrails import check_nvidia_guardrail
from app.services.vision_service import diagnose_plant_disease
from app.tools.rag_tool import query_agri_knowledge_base
from app.services.openwa_client import (
    send_text_message,
    send_voice_message,
    is_bot_own_message,
    is_bot_own_audio,
    download_message_media,
    ensure_session_started,
    register_webhook_if_needed,
)
from app.services.session_manager import (
    get_or_create_thread_id,
    update_user_location,
    get_user_location,
    update_user_language,
    get_user_language,
)
from app.services.text_cleaner import clean_response_text, make_short_audio_summary
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ensure data directories exist across Windows / Linux environments
os.makedirs(os.path.dirname(os.path.abspath(settings.DB_PATH)), exist_ok=True)
os.makedirs(os.path.dirname(os.path.abspath(settings.LOCATIONS_DB_PATH)), exist_ok=True)

static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

SUPPORTED_LANGUAGES = {
    "english": "English",
    "malayalam": "Malayalam",
    "മലയാളം": "Malayalam",
    "hindi": "Hindi",
    "हिन्दी": "Hindi",
    "tamil": "Tamil",
    "தமிழ்": "Tamil",
}

def detect_language_choice(text: str) -> str | None:
    """Detect if the incoming text is a language selection choice."""
    if not text:
        return None
    cleaned = text.strip().lower().rstrip(".!,")
    if cleaned in SUPPORTED_LANGUAGES:
        return SUPPORTED_LANGUAGES[cleaned]
    words = cleaned.split()
    for kw, lang in SUPPORTED_LANGUAGES.items():
        if kw in words:
            return lang
    return None

def is_whatsapp_group_message(msg_data: dict, from_phone: str) -> bool:
    """
    Detects if an incoming WhatsApp message originates from a group chat.
    Checks OpenWA group flags, chat object properties, and WhatsApp '@g.us' JID suffix.
    """
    if msg_data.get("isGroupMsg"):
        return True
    chat_obj = msg_data.get("chat")
    if isinstance(chat_obj, dict) and chat_obj.get("isGroup"):
        return True
    for field in [from_phone, msg_data.get("chatId"), msg_data.get("from")]:
        if field and isinstance(field, str) and field.strip().endswith("@g.us"):
            return True
    return False

def extract_and_clean_final_message(state_messages: list) -> str:
    """Extracts and sanitizes the final LLM response from LangGraph state messages."""
    if not state_messages:
        return "I'm sorry, I encountered an unexpected error processing your request. Please try again."
        
    # Search backwards for the most recent assistant response that has valid human text content
    for msg in reversed(state_messages):
        if isinstance(msg, AIMessage) or getattr(msg, "type", "") == "ai":
            # Intermediate tool-calling messages are NOT final user responses
            if getattr(msg, "tool_calls", None):
                continue
            content = getattr(msg, "content", "")
            if isinstance(content, list):
                # Handle multimodal or structured content blocks
                text_parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                content = " ".join(text_parts)
            if content and isinstance(content, str) and content.strip():
                stripped = clean_response_text(content)
                if stripped:
                    return stripped

    return "I'm sorry, I couldn't generate a complete response. Please try again."


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages startup and shutdown lifecycle:
    Initializes the SQLite checkpointer and compiles the LangGraph agent once,
    avoiding expensive per-request recompilation and SQLite lock contention.
    """
    logger.info(f"Initializing Checkpointer at {settings.DB_PATH}...")
    saver_cm = AsyncSqliteSaver.from_conn_string(settings.DB_PATH)
    checkpointer = await saver_cm.__aenter__()
    app.state.checkpointer_cm = saver_cm
    app.state.graph = workflow.compile(checkpointer=checkpointer)
    logger.info("FarmAssist agent graph compiled successfully.")
    
    # Pre-warm FAISS RAG knowledge base in background thread to avoid first-query latency spike
    try:
        asyncio.create_task(asyncio.to_thread(query_agri_knowledge_base.invoke, {"query": "rice cultivation"}))
        logger.info("Pre-warming agricultural RAG knowledge base in background...")
    except Exception as e:
        logger.debug(f"RAG pre-warm initialization: {e}")

    # Auto-start OpenWA session engine and verify webhook
    try:
        await ensure_session_started()
        await register_webhook_if_needed()
    except Exception as e:
        logger.warning(f"Could not auto-verify OpenWA session/webhook on startup: {e}")
    
    yield
    
    logger.info("Closing FarmAssist Checkpointer...")
    try:
        await saver_cm.__aexit__(None, None, None)
    except Exception as e:
        logger.error(f"Error closing checkpointer: {e}")
    logger.info("Shutdown complete.")

app = FastAPI(title="WhatsApp Agricultural Bot (FarmAssist)", lifespan=lifespan)

# Mount Static Files for Web Sandbox
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    """Serves the FarmAssist interactive web sandbox UI."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "FarmAssist API is running. Access /health or /static/index.html"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

class ChatRequest(BaseModel):
    type: str # "text", "location", "audio"
    body: str = ""
    lat: float = None
    lng: float = None
    audio_b64: str = ""

@app.post("/api/chat")
async def web_sandbox_chat(req: ChatRequest):
    """Dedicated endpoint for the Web Sandbox UI."""
    from_phone = "WEB_SANDBOX_USER"
    input_text = ""
    
    if req.type == "text":
        input_text = req.body.strip()
    elif req.type == "location":
        if req.lat is not None and req.lng is not None:
            update_user_location(from_phone, float(req.lat), float(req.lng))
            input_text = f"I have sent my location (Lat: {req.lat}, Lon: {req.lng}). Please provide the current weather and agronomy recommendations for this location."
        else:
            return JSONResponse({"error": "Missing coordinates"}, status_code=400)
    elif req.type == "audio":
        if req.audio_b64:
            try:
                audio_bytes = base64.b64decode(req.audio_b64)
                input_text = await transcribe_audio_groq(audio_bytes)
                logger.info(f"Web UI Transcribed text: {input_text}")
            except Exception as e:
                logger.error(f"Audio transcription failed: {e}")
                return JSONResponse({"error": f"Audio transcription failed: {e}"}, status_code=400)
        else:
            return JSONResponse({"error": "Missing audio data"}, status_code=400)
    else:
        return JSONResponse({"error": "Unsupported message type"}, status_code=400)

    if not input_text:
        return JSONResponse({"error": "Empty input text"}, status_code=400)

    try:
        # Retrieve pre-compiled graph from app state or compile on-demand
        graph = getattr(app.state, "graph", None)
        if graph is None:
            saver_cm = AsyncSqliteSaver.from_conn_string(settings.DB_PATH)
            checkpointer = await saver_cm.__aenter__()
            graph = workflow.compile(checkpointer=checkpointer)

        # Check if user is selecting/updating language
        chosen_lang = detect_language_choice(input_text)
        if chosen_lang:
            update_user_language(from_phone, chosen_lang)
        elif not get_user_language(from_phone):
            if re.search(r"[\u0900-\u097F]", input_text):
                update_user_language(from_phone, "Hindi")
            elif re.search(r"[\u0B80-\u0BFF]", input_text):
                update_user_language(from_phone, "Tamil")
            elif re.search(r"[\u0D00-\u0D7F]", input_text):
                update_user_language(from_phone, "Malayalam")

        thread_id = await get_or_create_thread_id(from_phone, timeout_seconds=settings.SESSION_TTL_SECONDS)
        config = {"configurable": {"thread_id": thread_id}}
        
        state_dict = {
            "messages": [HumanMessage(content=input_text)],
            "sender_phone": from_phone
        }
        
        user_lang = get_user_language(from_phone)
        if user_lang:
            state_dict["user_language"] = user_lang
            
        user_loc = get_user_location(from_phone)
        if user_loc:
            state_dict["user_lat"] = user_loc.get("lat")
            state_dict["user_lon"] = user_loc.get("lon")
            
        state = await graph.ainvoke(state_dict, config=config)
        final_message = extract_and_clean_final_message(state.get("messages", []))
                
        # Optional: Generate Voice Response
        audio_b64_out = None
        if req.type == "audio":
            try:
                detected_lang = detect_voice(final_message)
                audio_content = await synthesize_speech(final_message, detected_lang)
                if audio_content:
                    audio_b64_out = base64.b64encode(audio_content).decode("utf-8")
            except Exception as e:
                logger.error(f"TTS failed for Web UI: {e}")

        return {
            "text": final_message,
            "audio_b64": audio_b64_out,
            "transcribed_text": input_text if req.type == "audio" else None
        }
    except Exception as e:
        logger.error(f"Error in /api/chat: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)

async def process_whatsapp_message(payload: dict, graph = None):
    """
    Background task to process incoming webhook events from WhatsApp.
    Supports both OpenWA wrapped {'event': ..., 'data': {...}} and flat payload structures.
    """
    try:
        event = payload.get("event")
        logger.info(f"Processing WhatsApp webhook event: {event}")
        # If event is specified, ignore events other than message.received
        if event and event not in ["message.received", "message", "message.create"]:
            logger.info(f"Ignoring non-message event: {event}")
            return
            
        # Extract message data: unwrapped or wrapped
        if "data" in payload and isinstance(payload.get("data"), dict):
            msg_data = payload["data"]
        elif "payload" in payload and isinstance(payload.get("payload"), dict):
            msg_data = payload["payload"]
        else:
            msg_data = payload

        from_phone = msg_data.get("chatId") or msg_data.get("from")
        to_phone = msg_data.get("to")
        if not from_phone:
            logger.warning(f"No 'from' or 'chatId' field in message payload: {list(msg_data.keys())}")
            return
            
        # Ignore only WhatsApp status/story broadcasts
        if from_phone.startswith("status@") or msg_data.get("isStatusBroadcast") or msg_data.get("kind") == "status":
            logger.info("Ignoring status broadcast.")
            return

        # Ignore WhatsApp group messages unless explicitly allowed (respond strictly to DMs)
        if is_whatsapp_group_message(msg_data, from_phone) and not getattr(settings, "ALLOW_GROUP_MESSAGES", False):
            logger.info(f"Ignoring message from WhatsApp group: {from_phone} (sender: {msg_data.get('author')})")
            return

        sender_id = msg_data.get("author") or from_phone
        from_me = msg_data.get("fromMe", False)
        message_type = msg_data.get("type", "text")
        input_text = ""
        is_audio = False

        if message_type in ["chat", "text"]:
            input_text = msg_data.get("body", "")
        elif message_type in ["ptt", "audio", "voice"]:
            is_audio = True
            audio_bytes = None
            media_obj = msg_data.get("media") or msg_data.get("mediaData") or {}
            media_data = None
            if isinstance(media_obj, dict):
                media_data = media_obj.get("data")
            elif isinstance(media_obj, str):
                media_data = media_obj
            if not media_data and isinstance(msg_data.get("body"), str) and msg_data.get("body").startswith("data:audio"):
                media_data = msg_data.get("body")
                
            if media_data:
                if "," in media_data:
                    media_data = media_data.split(",", 1)[1]
                try:
                    audio_bytes = base64.b64decode(media_data)
                except Exception as e:
                    logger.warning(f"Failed to b64decode audio media: {e}")

            # If media was omitted in webhook, download it directly from OpenWA
            if not audio_bytes:
                msg_id = msg_data.get("id")
                if msg_id:
                    logger.info(f"Audio omitted from webhook payload, fetching from OpenWA API for msg {msg_id}...")
                    audio_bytes = await download_message_media(from_phone, msg_id)

            if audio_bytes:
                # Check if this voice note is the bot's own outbound audio echoing back
                if from_me and is_bot_own_audio(audio_bytes):
                    logger.info("Ignoring echo of bot's own outbound voice note.")
                    return

                try:
                    user_lang = get_user_language(sender_id)
                    input_text = await transcribe_audio_groq(audio_bytes, language=user_lang)
                    logger.info(f"Transcribed audio text: {repr(input_text)}")
                except Exception as e:
                    logger.error(f"STT transcription failed: {e}")
                    input_text = ""
            else:
                logger.warning("Could not obtain audio bytes for voice note.")
                input_text = ""

        elif message_type == "location":
            loc_obj = msg_data.get("location") if isinstance(msg_data.get("location"), dict) else {}
            lat = msg_data.get("lat") or loc_obj.get("latitude") or loc_obj.get("lat")
            lon = msg_data.get("lng") or loc_obj.get("longitude") or loc_obj.get("lng") or loc_obj.get("lon")
            if lat is not None and lon is not None:
                update_user_location(sender_id, float(lat), float(lon))
                input_text = f"I have sent my location (Lat: {lat}, Lon: {lon}). Please provide the current weather and agronomy recommendations for this location."
            else:
                input_text = "I tried to send my location but the coordinates were missing."
        elif message_type in ["image", "photo"] or (isinstance(msg_data.get("mimetype"), str) and msg_data.get("mimetype").startswith("image/")):
            image_bytes = None
            media_obj = msg_data.get("media") or msg_data.get("mediaData") or {}
            media_data = None
            if isinstance(media_obj, dict):
                media_data = media_obj.get("data")
            elif isinstance(media_obj, str):
                media_data = media_obj
            if not media_data and isinstance(msg_data.get("body"), str) and msg_data.get("body").startswith("data:image"):
                media_data = msg_data.get("body")

            if media_data:
                if "," in media_data:
                    media_data = media_data.split(",", 1)[1]
                try:
                    image_bytes = base64.b64decode(media_data)
                except Exception as e:
                    logger.warning(f"Failed to b64decode image media: {e}")

            if not image_bytes:
                msg_id = msg_data.get("id")
                if msg_id:
                    logger.info(f"Image omitted from payload, downloading from OpenWA API for msg {msg_id}...")
                    image_bytes = await download_message_media(from_phone, msg_id)

            if image_bytes:
                caption = msg_data.get("caption") or msg_data.get("body") or ""
                if isinstance(caption, str) and caption.startswith("data:image"):
                    caption = ""
                user_lang = get_user_language(sender_id)
                if not user_lang and caption:
                    if re.search(r"[\u0D00-\u0D7F]", caption):
                        user_lang = "Malayalam"
                    elif re.search(r"[\u0B80-\u0BFF]", caption):
                        user_lang = "Tamil"
                    elif re.search(r"[\u0900-\u097F]", caption):
                        user_lang = "Hindi"
                user_lang = user_lang or "English"
                logger.info(f"Diagnosing agricultural image for {from_phone} in {user_lang} (caption: {caption})...")
                diagnosis = await diagnose_plant_disease(image_bytes, caption=caption, language=user_lang)
                await send_text_message(from_phone, diagnosis)
                return
            else:
                logger.warning(f"Could not extract image bytes from {from_phone}")
                return
        else:
            logger.info(f"Unsupported message type: {message_type}")
            return

        # Check fromMe / self-messages
        if from_me:
            # Check if this is the bot's own outbound text response echoing back
            if not is_audio and is_bot_own_message(input_text):
                logger.info("Ignoring echo of bot's own response message.")
                return
            # Allow self-chat (Message yourself) testing, but ignore outbound chats to other external contacts
            is_self_chat = bool(to_phone and from_phone and to_phone.split("@")[0] == from_phone.split("@")[0])
            if not is_self_chat:
                logger.info("Ignoring fromMe message")
                return
            logger.info(f"Processing self-chat test message from {from_phone}: {input_text}")

        # If audio could not be heard, inform the user rather than staying silent
        if not input_text or not input_text.strip():
            if is_audio:
                user_lang = get_user_language(sender_id) or "English"
                if user_lang == "Malayalam":
                    unheard_msg = "ക്ഷമിക്കണം, നിങ്ങളുടെ ശബ്ദ സന്ദേശം വ്യക്തമായി കേൾക്കാൻ കഴിഞ്ഞില്ല. ദയവായി മൈക്രോഫോണിനടുത്ത് സംസാരിച്ച് വീണ്ടും അയക്കുക, അല്ലെങ്കിൽ സന്ദേശം ടൈപ്പ് ചെയ്യുക."
                elif user_lang == "Hindi":
                    unheard_msg = "क्षमा करें, आपकी आवाज़ स्पष्ट नहीं सुनाई दी। कृपया माइक के पास बोलकर पुनः भेजें या लिखकर बताएं।"
                elif user_lang == "Tamil":
                    unheard_msg = "மன்னிக்கவும், உங்கள் குரல் பதிவு தெளிவாக கேட்கவில்லை. தயவுசெய்து மீண்டும் பேசவும் அல்லது தட்டச்சு செய்யவும்."
                else:
                    unheard_msg = "Sorry, I couldn't clearly hear any speech in your voice note. Please try speaking closer to the microphone, or type your query."
                logger.info(f"Sending inaudible audio prompt to {from_phone}")
                await send_text_message(from_phone, unheard_msg)
            return

        logger.info(f"Processing message from {from_phone} (sender: {sender_id}): {input_text}")

        # Check NVIDIA Security Guardrails on user query
        user_lang = get_user_language(sender_id) or "English"
        is_safe, refusal = await check_nvidia_guardrail(input_text, user_lang)
        if not is_safe and refusal:
            logger.warning(f"Query from {from_phone} blocked by NVIDIA Security Guardrails.")
            await send_text_message(from_phone, refusal)
            return

        if graph is None:
            graph = getattr(app.state, "graph", None)
            
        if graph is None:
            saver_cm = AsyncSqliteSaver.from_conn_string(settings.DB_PATH)
            checkpointer = await saver_cm.__aenter__()
            graph = workflow.compile(checkpointer=checkpointer)

        # Check if user is selecting/updating language
        chosen_lang = detect_language_choice(input_text)
        if chosen_lang:
            update_user_language(sender_id, chosen_lang)
        elif not get_user_language(sender_id):
            if re.search(r"[\u0900-\u097F]", input_text):
                update_user_language(sender_id, "Hindi")
            elif re.search(r"[\u0B80-\u0BFF]", input_text):
                update_user_language(sender_id, "Tamil")
            elif re.search(r"[\u0D00-\u0D7F]", input_text):
                update_user_language(sender_id, "Malayalam")

        thread_id = await get_or_create_thread_id(sender_id, timeout_seconds=settings.SESSION_TTL_SECONDS)
        config = {"configurable": {"thread_id": thread_id}}
        
        state_dict = {
            "messages": [HumanMessage(content=input_text)],
            "sender_phone": sender_id
        }
        
        user_lang = get_user_language(sender_id)
        if user_lang:
            state_dict["user_language"] = user_lang

        user_loc = get_user_location(sender_id)
        if user_loc:
            state_dict["user_lat"] = user_loc.get("lat")
            state_dict["user_lon"] = user_loc.get("lon")
        
        state = await graph.ainvoke(state_dict, config=config)
        final_message = extract_and_clean_final_message(state.get("messages", []))
            
        if is_audio:
            try:
                # 1. Generate short, punchy audio summary (under 25-30s) instead of reading 2-minute text
                spoken_summary = make_short_audio_summary(final_message, max_words=45)
                voice = detect_voice(spoken_summary or final_message)
                audio_reply = await synthesize_speech(spoken_summary or final_message, voice)
                await send_voice_message(from_phone, audio_reply)
                
                # 2. Also send the full detailed text for complete farmer reference
                await send_text_message(from_phone, final_message)
            except Exception as e:
                logger.error(f"TTS conversion failed: {e}. Falling back to text.")
                await send_text_message(from_phone, final_message)
        else:
            await send_text_message(from_phone, final_message)
            
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        graph = getattr(request.app.state, "graph", None)
        background_tasks.add_task(process_whatsapp_message, payload, graph)
        return JSONResponse(content={"status": "processing"})
    except Exception as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
