import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.main import app
import base64
import json

client = TestClient(app)

@pytest.fixture
def mock_httpx_post():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        yield mock_post

@pytest.fixture
def mock_httpx_get():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        yield mock_get

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
@patch("app.main.logger")
async def test_webhook_loop_prevention(mock_logger):
    # Test that fromMe=True messages are ignored
    from app.main import process_whatsapp_message
    payload = {
        "from": "12345@c.us",
        "type": "chat",
        "body": "test",
        "fromMe": True
    }
    await process_whatsapp_message(payload)
    mock_logger.info.assert_called_with("Ignoring fromMe message")

@pytest.mark.asyncio
@patch("app.main.transcribe_audio_groq", new_callable=AsyncMock)
@patch("app.agent.graph.workflow.compile")
@patch("app.main.send_voice_message", new_callable=AsyncMock)
async def test_audio_payload_decoding_and_stt(mock_send_voice, mock_compile, mock_stt):
    # Test audio payload ingestion, base64 decoding, and STT mock
    from app.main import process_whatsapp_message
    
    mock_stt.return_value = "What is the weather?"
    
    # Mock LangGraph output
    mock_graph = AsyncMock()
    mock_graph.ainvoke.return_value = {
        "messages": [AsyncMock(content="The weather is fine.")]
    }
    mock_compile.return_value = mock_graph
    
    sample_audio_bytes = b"fake_audio_content"
    base64_audio = base64.b64encode(sample_audio_bytes).decode("utf-8")
    
    payload = {
        "from": "12345@c.us",
        "type": "ptt",
        "mediaData": {
            "data": f"data:audio/ogg;base64,{base64_audio}"
        },
        "fromMe": False
    }
    
    await process_whatsapp_message(payload)
    
    # Verify STT was called with decoded bytes
    mock_stt.assert_called_once_with(sample_audio_bytes)
    # Verify voice response was sent
    mock_send_voice.assert_called_once()

@pytest.mark.asyncio
@patch("app.tools.weather.get_weather", new_callable=AsyncMock)
async def test_langgraph_decision_routing_and_tool(mock_get_weather):
    # Test LangGraph decision routing to tool node
    from app.agent.graph import agent_node, should_continue, fetch_weather_tool, AgentState
    from langchain_core.messages import HumanMessage, AIMessage, ToolCall
    from langchain_core.messages.tool import ToolMessage

    mock_get_weather.return_value = {"current": {"temperature_2m": 25.0}}
    
    # 1. Test fetch_weather_tool directly
    tool_result_json = await fetch_weather_tool.ainvoke({"location": "Bangalore"})
    result_dict = json.loads(tool_result_json)
    assert result_dict["current"]["temperature_2m"] == 25.0

    # 2. Test routing logic
    # If the LLM generates a tool call, should_continue should route to "tools"
    state = {
        "messages": [AIMessage(content="", tool_calls=[{"name": "fetch_weather_tool", "args": {"location": "Bangalore"}, "id": "call_123"}])],
        "sender_phone": "123"
    }
    assert should_continue(state) == "tools"
    
    # If the LLM generates a final response, should_continue should route to END
    state = {
        "messages": [AIMessage(content="Here is your weather.")],
        "sender_phone": "123"
    }
    from langgraph.graph import END
    assert should_continue(state) == END

def test_detect_voice():
    from app.services.tts import detect_voice
    
    assert detect_voice("ನಮಸ್ಕಾರ") == "kn-IN-GaganNeural"
    assert detect_voice("नमस्ते") == "hi-IN-SwaraNeural"
    assert detect_voice("നമസ്കാരം") == "ml-IN-SobhanaNeural"
    assert detect_voice("Hello") == "en-IN-NeerjaNeural"
