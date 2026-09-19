import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from langchain_core.messages import HumanMessage, AIMessage
from app.agent.graph import agent_node

@pytest.mark.asyncio
async def test_nvidia_fallback_on_groq_429():
    """Verify that when Groq raises 429 rate limit, agent_node falls back to NVIDIA NIM seamlessly."""
    state = {
        "messages": [HumanMessage(content="What crop should I grow?")],
        "sender_phone": "12345",
        "user_language": "English",
        "user_lat": None,
        "user_lon": None
    }
    
    mock_groq_error = Exception("Error code: 429 - {'error': {'message': 'Rate limit reached', 'type': 'rate_limit_exceeded'}}")
    mock_nvidia_reply = AIMessage(content="Recommended crop for Karnataka in winter is Chickpea.")
    
    mock_groq_binding = MagicMock()
    mock_groq_binding.ainvoke = AsyncMock(side_effect=mock_groq_error)
    
    with patch("app.agent.graph.llm_with_tools", mock_groq_binding), \
         patch("app.agent.graph.get_nvidia_llm_with_tools") as mock_get_nvidia:
        
        # NVIDIA caller returns reply
        mock_nvidia_caller = AsyncMock()
        mock_nvidia_caller.ainvoke.return_value = mock_nvidia_reply
        mock_get_nvidia.return_value = mock_nvidia_caller
        
        result = await agent_node(state)
        
        # Verify fallback was invoked
        mock_get_nvidia.assert_called_once()
        mock_nvidia_caller.ainvoke.assert_called_once()
        assert result["messages"][0].content == "Recommended crop for Karnataka in winter is Chickpea."

@pytest.mark.asyncio
async def test_groq_normal_path():
    """Verify that when Groq works normally, NVIDIA is not invoked."""
    state = {
        "messages": [HumanMessage(content="Tell me about tomato farming.")],
        "sender_phone": "12345",
        "user_language": "English",
        "user_lat": None,
        "user_lon": None
    }
    
    mock_groq_reply = AIMessage(content="Tomatoes require well-draining soil and regular watering.")
    
    mock_groq_binding = MagicMock()
    mock_groq_binding.ainvoke = AsyncMock(return_value=mock_groq_reply)
    
    with patch("app.agent.graph.llm_with_tools", mock_groq_binding), \
         patch("app.agent.graph.get_nvidia_llm_with_tools") as mock_get_nvidia, \
         patch("app.agent.graph.is_groq_rate_limited", return_value=False):
        
        result = await agent_node(state)
        
        mock_groq_binding.ainvoke.assert_called_once()
        mock_get_nvidia.assert_not_called()
        assert "Tomatoes" in result["messages"][0].content

@pytest.mark.asyncio
async def test_greeting_fast_path_never_calls_tools():
    """Verify that greetings (e.g. 'hey', 'hy', 'hyy', 'namaste') return onboarding greeting without calling LLM or tools."""
    for greeting in ["hey", "hy", "hyy", "hy bro", "namaste", "vanakkam", "yo"]:
        state = {
            "messages": [HumanMessage(content=greeting)],
            "sender_phone": "12345",
            "user_language": None,
            "user_lat": None,
            "user_lon": None
        }
        
        mock_groq_binding = MagicMock()
        
        with patch("app.agent.graph.llm_with_tools", mock_groq_binding), \
             patch("app.agent.graph.get_nvidia_llm_with_tools") as mock_get_nvidia:
            
            result = await agent_node(state)
            
            mock_groq_binding.ainvoke.assert_not_called()
            mock_get_nvidia.assert_not_called()
            content = result["messages"][0].content
            assert "FarmAssist" in content
            assert "preferred language" in content

@pytest.mark.asyncio
async def test_language_selection_fast_path():
    """Verify that language selection (e.g. 'English', 'Hindi') returns immediate confirmation without calling LLM."""
    for lang in ["English", "Hindi", "Malayalam", "Tamil"]:
        state = {
            "messages": [HumanMessage(content=lang)],
            "sender_phone": "12345",
            "user_language": None,
            "user_lat": None,
            "user_lon": None
        }
        
        mock_groq_binding = MagicMock()
        with patch("app.agent.graph.llm_with_tools", mock_groq_binding), \
             patch("app.agent.graph.get_nvidia_llm_with_tools") as mock_get_nvidia:
            
            result = await agent_node(state)
            mock_groq_binding.ainvoke.assert_not_called()
            mock_get_nvidia.assert_not_called()
            assert result.get("user_language") == lang
            assert len(result["messages"][0].content) > 0

@pytest.mark.asyncio
async def test_known_language_greeting():
    """Verify that greeting with language already known returns localized greeting without LLM call."""
    state = {
        "messages": [HumanMessage(content="hy")],
        "sender_phone": "12345",
        "user_language": "Malayalam",
        "user_lat": None,
        "user_lon": None
    }
    mock_groq_binding = MagicMock()
    with patch("app.agent.graph.llm_with_tools", mock_groq_binding), \
         patch("app.agent.graph.get_nvidia_llm_with_tools") as mock_get_nvidia:
        result = await agent_node(state)
        mock_groq_binding.ainvoke.assert_not_called()
        mock_get_nvidia.assert_not_called()
        assert "നമസ്കാരം" in result["messages"][0].content

