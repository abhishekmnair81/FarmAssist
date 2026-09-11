import asyncio
import os
import uuid
import re
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.agent.graph import workflow
from app.services.session_manager import update_user_location, get_user_location

async def main():
    # Use the same SQLite path the container uses
    db_path = "/app/data/checkpoints.sqlite"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    print("=========================================")
    print("🌾 FarmAssist Local CLI Testing Mode 🌾")
    print("=========================================")
    print("Type 'location <lat> <lon>' to mock sending a WhatsApp GPS ping.")
    print("Example: location 13.0827 80.2707")
    print("Type 'quit' to exit.")
    print("=========================================\n")
    
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
                
                # Mock native WhatsApp location sharing
                if user_input.lower().startswith("location "):
                    parts = user_input.split()
                    if len(parts) == 3:
                        lat, lon = parts[1], parts[2]
                        update_user_location(phone, float(lat), float(lon))
                        user_input = f"I have sent my location (Lat: {lat}, Lon: {lon}). Please provide the current weather and agronomy recommendations for this location."
                        print(f"[System: GPS Location intercepted and saved!]")
                    else:
                        print("Invalid location format. Use: location <lat> <lon>")
                        continue
                    
                state_dict = {
                    "messages": [HumanMessage(content=user_input)],
                    "sender_phone": phone
                }
                
                # Inject persistent location into state (mirroring main.py)
                user_loc = get_user_location(phone)
                if user_loc:
                    state_dict["user_lat"] = user_loc.get("lat")
                    state_dict["user_lon"] = user_loc.get("lon")
                    
                print("FarmAssist: (Thinking...)")
                
                # Run the agent
                state = await graph.ainvoke(state_dict, config=config)
                final_message = state["messages"][-1].content
                
                # Handle reasoning tags and fallback logic
                stripped = re.sub(r'<think>.*?</think>', '', final_message, flags=re.DOTALL).strip()
                if not stripped:
                    reasoning = state["messages"][-1].additional_kwargs.get("reasoning_content")
                    if reasoning:
                        stripped = "[Fallback] I was thinking too deeply about your question and ran out of time! Could you please ask me again simply?"
                    else:
                        stripped = final_message.strip()
                        
                print(f"\nFarmAssist: {stripped}\n")
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\n[Error]: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
