from typing import TypedDict, Annotated, List, Any
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode
from app.config import settings
from app.tools.weather import get_weather
from app.tools.rag_tool import query_agri_knowledge_base
from app.tools.web_search import search_live_web
import json

# Define the State
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    sender_phone: str
    user_lat: float
    user_lon: float

# Define Tools
@tool
async def fetch_weather_tool(location_name: str = "", lat: float = None, lon: float = None) -> str:
    """
    Fetches agricultural weather data including temperature, precipitation, wind, and soil moisture.
    Provide a `location_name` (e.g. 'Bangalore', 'Delhi') if the user asks for a specific place.
    If the user has a saved GPS location, pass it via `lat` and `lon`.
    """
    data = await get_weather(location_name if location_name else None, lat, lon)
    return json.dumps(data)

tools = [fetch_weather_tool, query_agri_knowledge_base, search_live_web]

# Initialize LLM
llm = ChatGroq(
    model="qwen/qwen3.6-27b",
    api_key=settings.GROQ_API_KEY,
    temperature=0.2
)
llm_with_tools = llm.bind_tools(tools)

# Define Nodes
async def agent_node(state: AgentState):
    messages = state["messages"]
    
    user_lat = state.get("user_lat")
    user_lon = state.get("user_lon")
    location_context = f"\nThe user's saved GPS location is Lat: {user_lat}, Lon: {user_lon}." if user_lat and user_lon else "\nThe user HAS NOT provided their location yet."

    # Prepend SystemMessage if not present in context window
    sys_msg = SystemMessage(
        content=(
            "You are FarmAssist, a friendly, expert agronomist AI assistant helping farmers over WhatsApp.\n\n"
            "# 1. GREETING & ONBOARDING\n"
            "- If this is the first message, introduce yourself warmly in 1-2 short sentences.\n"
            "- Ask the user to pick their preferred language: English, മലയാളം (Malayalam), हिन्दी (Hindi), or தமிழ் (Tamil).\n\n"
            "# 2. LANGUAGE RULES\n"
            "- Once a language is selected or detected, respond completely in that native language and script.\n"
            "- Speak naturally in rural colloquial phrasing. Avoid mixing languages (e.g. no 'Manglish').\n"
            "- If the user switches languages, switch instantly and acknowledge the change in that new language.\n\n"
            "# 3. ADVISORY STYLE\n"
            "- Tone: Warm, practical, and clear. No heavy jargon.\n"
            "- Format: Keep replies concise (under 3-4 short paragraphs or bullet points). Use bold text for key warnings.\n"
            "- Direct Answers: Start with a direct 'Yes / No / Delay' before explaining why.\n\n"
            "# 4. WEATHER, TOOLS & LOCATION\n"
            f"{location_context}\n"
            "- If the user asks about weather, planting, or spraying, CHECK if they provided a specific place name or if you have their saved GPS location.\n"
            "- If you DO NOT have a saved location and they didn't specify a town/village, DO NOT call the weather tool. Politely ask them to type their village/town name OR tap the WhatsApp Paperclip/Plus (+) icon -> Location -> 'Send your current location'.\n"
            "- If you HAVE their saved location (or they specified a town), ALWAYS call the fetch_weather_tool before answering.\n"
            "- Translate technical weather metrics into everyday farming terms.\n\n"
            "# 5. ZERO HALLUCINATION POLICY ('I DON'T KNOW')\n"
            "- If you are asked about agricultural practices, schemes, or live market prices, you MUST use `query_agri_knowledge_base` or `search_live_web`.\n"
            "- If neither tool returns verified information, DO NOT GUESS. You MUST explicitly state that you do not have verified information on that topic.\n"
            "- Safe Fallback: Advise them to consult the local Krishi Vigyan Kendra (KVK) or call the Kisan Call Center (1800-180-1551).\n\n"
            "# 6. MANDATORY SOURCE CITATIONS\n"
            "- You must append exactly one of the following tags (localized into the user's language) if you used a tool:\n"
            "  * If retrieved via `query_agri_knowledge_base`: `[Source: ICAR Advisory / Govt Scheme Database]`\n"
            "  * If retrieved via `search_live_web`: `[Source: Web Search - <Domain>]`\n"
            "  * If based purely on weather telemetry: `[Source: Open-Meteo Forecast]`"
        )
    )
    
    # Filter out existing system messages to avoid duplication
    filtered_messages = [m for m in messages if not isinstance(m, SystemMessage)]
    
    response = await llm_with_tools.ainvoke([sys_msg] + filtered_messages)
    return {"messages": [response]}

# Define Routing Logic
def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    
    if last_message.tool_calls:
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
