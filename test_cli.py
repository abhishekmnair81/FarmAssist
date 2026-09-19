import asyncio
import os
import sys
import uuid
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.graph import workflow
from app.services.session_manager import update_user_location, get_user_location, update_user_language, get_user_language
from app.services.text_cleaner import clean_response_text

from app.config import settings

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

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def safe_print(text: str = ""):
    """Safe print that guarantees no UnicodeEncodeError on any console."""
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            sys.stdout.buffer.write((str(text) + "\n").encode("utf-8", errors="replace"))
            sys.stdout.flush()
        except Exception:
            print(str(text).encode("ascii", errors="replace").decode("ascii"))
    except Exception:
        pass

async def main():
    os.makedirs(os.path.dirname(os.path.abspath(settings.DB_PATH)), exist_ok=True)
    db_path = settings.DB_PATH
    
    safe_print("=========================================")
    safe_print("🌾 FarmAssist Local CLI Testing Mode 🌾")
    safe_print("=========================================")
    safe_print("Type 'location <lat> <lon>' to mock sending a WhatsApp GPS ping.")
    safe_print("Example: location 13.0827 80.2707")
    safe_print("Type 'quit' to exit.")
    safe_print("=========================================\n")
    
    phone = "CLI_TEST_USER"
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = workflow.compile(checkpointer=checkpointer)
        
        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ['quit', 'exit']:
                    break
                if not user_input:
                    continue

                # Check if user selected preferred language
                chosen_lang = detect_language_choice(user_input)
                if chosen_lang:
                    update_user_language(phone, chosen_lang)
                    safe_print(f"[System: Preferred language set to {chosen_lang}]")
                
                # Mock native WhatsApp location sharing
                if user_input.lower().startswith("location "):
                    parts = user_input.split()
                    if len(parts) == 3:
                        lat, lon = parts[1], parts[2]
                        update_user_location(phone, float(lat), float(lon))
                        user_input = f"I have sent my location (Lat: {lat}, Lon: {lon}). Please provide the current weather and agronomy recommendations for this location."
                        safe_print(f"[System: GPS Location intercepted and saved!]")
                    else:
                        safe_print("Invalid location format. Use: location <lat> <lon>")
                        continue
                    
                state_dict = {
                    "messages": [HumanMessage(content=user_input)],
                    "sender_phone": phone
                }

                # Inject language preference into state
                user_lang = get_user_language(phone)
                if user_lang:
                    state_dict["user_language"] = user_lang
                
                # Inject persistent location into state (mirroring main.py)
                user_loc = get_user_location(phone)
                if user_loc:
                    state_dict["user_lat"] = user_loc.get("lat")
                    state_dict["user_lon"] = user_loc.get("lon")
                    
                safe_print("FarmAssist: (Thinking...)")
                
                # Run the agent
                state = await graph.ainvoke(state_dict, config=config)
                final_message = state["messages"][-1].content
                
                # Clean up reasoning tags and repeated special characters
                stripped = clean_response_text(final_message)
                if not stripped:
                    reasoning = getattr(state["messages"][-1], "additional_kwargs", {}).get("reasoning_content")
                    if reasoning:
                        stripped_reasoning = clean_response_text(reasoning)
                        if stripped_reasoning:
                            stripped = stripped_reasoning
                    if not stripped and final_message and final_message.strip():
                        stripped = final_message.strip()
                    if not stripped:
                        stripped = "I'm sorry, I couldn't generate a complete response. Please try asking again."
                        
                safe_print(f"\nFarmAssist: {stripped}\n")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                err_str = str(e).lower()
                if "connection error" in err_str or "connect" in err_str or "timeout" in err_str:
                    safe_print(f"\n[Network Notice]: Momentary network drop detected. Automatically reconnecting...")
                    try:
                        safe_print("FarmAssist: (Re-connecting...)")
                        state = await graph.ainvoke(state_dict, config=config)
                        final_message = state["messages"][-1].content
                        stripped = clean_response_text(final_message)
                        safe_print(f"\nFarmAssist: {stripped}\n")
                        continue
                    except Exception:
                        safe_print(f"\n[Error]: Network connection timed out. Please try again.\n")
                else:
                    safe_print(f"\n[Error]: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
