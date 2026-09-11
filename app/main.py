from fastapi import FastAPI, BackgroundTasks, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import base64
import logging
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
import os

from app.agent.graph import workflow
from app.services.stt import transcribe_audio_groq
from app.services.tts import synthesize_speech, detect_voice
from app.services.openwa_client import send_text_message, send_voice_message
from app.services.session_manager import get_or_create_thread_id, update_user_location, get_user_location
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Agricultural Bot")

DB_PATH = "/app/data/checkpoints.sqlite"
# Ensure directory exists for local testing
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Mount Static Files for Web Sandbox
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

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
        input_text = req.body
    elif req.type == "location":
        if req.lat and req.lng:
            update_user_location(from_phone, req.lat, req.lng)
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
                return JSONResponse({"error": f"Audio transcription failed: {e}"}, status_code=400)
        else:
            return JSONResponse({"error": "Missing audio data"}, status_code=400)
    else:
        return JSONResponse({"error": "Unsupported message type"}, status_code=400)

    if not input_text:
        return JSONResponse({"error": "Empty input text"}, status_code=400)

    # Agent Processing
    async with AsyncSqliteSaver.from_conn_string(DB_PATH) as checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
        thread_id = await get_or_create_thread_id(from_phone, timeout_seconds=180)
        config = {"configurable": {"thread_id": thread_id}}
        
        state_dict = {
            "messages": [HumanMessage(content=input_text)],
            "sender_phone": from_phone
        }
        
        user_loc = get_user_location(from_phone)
        if user_loc:
            state_dict["user_lat"] = user_loc.get("lat")
            state_dict["user_lon"] = user_loc.get("lon")
            
        state = await graph.ainvoke(state_dict, config=config)
        final_message = state["messages"][-1].content
        
        # Cleanup Reasoning
        import re
        stripped_message = re.sub(r'<think>.*?</think>', '', final_message, flags=re.DOTALL).strip()
        if not stripped_message:
            reasoning = state["messages"][-1].additional_kwargs.get("reasoning_content")
            if reasoning:
                stripped_message = "I'm sorry, I was thinking too deeply about your question and ran out of time! Could you please ask me again simply?"
            else:
                stripped_message = final_message.strip()
                
        # Optional: Generate Voice Response
        audio_b64_out = None
        if req.type == "audio":
            try:
                detected_lang = detect_voice(stripped_message)
                audio_content = await synthesize_speech(stripped_message, detected_lang)
                if audio_content:
                    audio_b64_out = base64.b64encode(audio_content).decode('utf-8')
            except Exception as e:
                logger.error(f"TTS failed for Web UI: {e}")

        return {
            "text": stripped_message,
            "audio_b64": audio_b64_out,
            "transcribed_text": input_text if req.type == "audio" else None
        }

async def process_whatsapp_message(payload: dict):
    """
    Background task to process incoming webhook.
    """
    try:
        event = payload.get("event")
        if event != "message.received":
            return
            
        msg_data = payload.get("data", {})
        from_phone = msg_data.get("from")
        if not from_phone:
            logger.error("No 'from' field in payload")
            return
            
        # Ignore messages sent by the bot itself
        if msg_data.get("fromMe", False):
            logger.info("Ignoring fromMe message")
            return

        # Open Access: Allow all users, but ignore group chats to prevent spam
        is_group = msg_data.get("isGroupMsg", False)
        if is_group or from_phone.endswith("@g.us"):
            logger.info("Ignoring group message.")
            return

        message_type = msg_data.get("type")
        input_text = ""
        is_audio = False

        if message_type in ["chat", "text"]:
            input_text = msg_data.get("body", "")
        elif message_type in ["ptt", "audio", "voice"]:
            is_audio = True
            # Extract base64 audio
            media_obj = msg_data.get("media") or msg_data.get("mediaData") or {}
            media_data = media_obj.get("data")
            if media_data:
                # Remove data URI prefix if present
                if "," in media_data:
                    media_data = media_data.split(",", 1)[1]
                
                audio_bytes = base64.b64decode(media_data)
                input_text = await transcribe_audio_groq(audio_bytes)
                logger.info(f"Transcribed text: {input_text}")
            else:
                input_text = "Sorry, I could not process the audio."
        elif message_type == "location":
            lat = msg_data.get("lat")
            lon = msg_data.get("lng")
            if lat and lon:
                update_user_location(from_phone, float(lat), float(lon))
                input_text = f"I have sent my location (Lat: {lat}, Lon: {lon}). Please provide the current weather and agronomy recommendations for this location."
            else:
                input_text = "I tried to send my location but the coordinates were missing."
        else:
            logger.info(f"Unsupported message type: {message_type}")
            return

        if not input_text:
            return

        # Initialize SQLite Saver and compile graph
        async with AsyncSqliteSaver.from_conn_string(DB_PATH) as checkpointer:
            graph = workflow.compile(checkpointer=checkpointer)
            
            thread_id = await get_or_create_thread_id(from_phone, timeout_seconds=180)
            config = {"configurable": {"thread_id": thread_id}}
            
            # Prepare state
            state_dict = {
                "messages": [HumanMessage(content=input_text)],
                "sender_phone": from_phone
            }
            
            user_loc = get_user_location(from_phone)
            if user_loc:
                state_dict["user_lat"] = user_loc.get("lat")
                state_dict["user_lon"] = user_loc.get("lon")
            
            # Invoke the graph
            state = await graph.ainvoke(
                state_dict,
                config=config
            )
            
            final_message = state["messages"][-1].content
            
            logger.info(f"STATE MESSAGES DUMP:")
            for m in state["messages"]:
                logger.info(f"Role: {m.__class__.__name__} | Content: {repr(m.content)} | Additional: {m.additional_kwargs}")
            
            # Strip <think> tags often generated by reasoning models like Qwen
            import re
            stripped_message = re.sub(r'<think>.*?</think>', '', final_message, flags=re.DOTALL).strip()
            
            if not stripped_message:
                # Check if it's a reasoning model that put everything in additional_kwargs
                reasoning = state["messages"][-1].additional_kwargs.get("reasoning_content")
                if reasoning:
                    logger.warning("LLM got stuck in reasoning mode and did not output a final answer (likely hit max tokens).")
                    stripped_message = "I'm sorry, I was thinking too deeply about your question and ran out of time! Could you please ask me again simply?"
                else:
                    # Legacy <think> tag extraction fallback
                    think_match = re.search(r'<think>(.*?)</think>', final_message, flags=re.DOTALL)
                    if think_match:
                        stripped_message = think_match.group(1).strip()
                    else:
                        stripped_message = final_message.strip()
                    
            final_message = stripped_message
            
            if not final_message:
                logger.error("LLM returned an empty string!")
                final_message = "I'm sorry, I encountered an unexpected error processing your request. Please try again."
                
            if is_audio:
                # Reply with voice memo
                voice = detect_voice(final_message)
                audio_reply = await synthesize_speech(final_message, voice)
                await send_voice_message(from_phone, audio_reply)
            else:
                # Reply with text
                await send_text_message(from_phone, final_message)
                
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
        logger.info(f"Received webhook payload: {payload}")
        background_tasks.add_task(process_whatsapp_message, payload)
        return JSONResponse(content={"status": "processing"})
    except Exception as e:
        logger.error(f"Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
