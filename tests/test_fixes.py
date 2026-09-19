import pytest
from app.services.text_cleaner import clean_text_for_speech, clean_response_text
from app.services.session_manager import update_user_language, get_user_language
from app.main import detect_language_choice, extract_and_clean_final_message, is_whatsapp_group_message
from app.tools.web_search import clean_search_snippet
from app.config import settings
from langchain_core.messages import AIMessage

def test_clean_text_for_speech_units_and_markdown():
    input_text = (
        "Here is the weather for **Jayanagar**:\n"
        "* **Temperature:** 27.7°C (Warm afternoon)\n"
        "* **Humidity:** 74%\n"
        "* **Rain:** 7mm expected\n"
        "* **Wind:** 9.3 km/h\n"
        "Soil moisture is ~8-9%. 🌱🚜\n"
        "[Source: Open-Meteo Forecast]"
    )
    spoken = clean_text_for_speech(input_text)
    
    # Verify markdown asterisks are stripped
    assert "**" not in spoken
    assert "*" not in spoken
    
    # Verify emojis are removed
    assert "🌱" not in spoken
    assert "🚜" not in spoken
    
    # Verify source citation is removed
    assert "[Source:" not in spoken
    assert "Open-Meteo" not in spoken
    
    # Verify units are expanded to words
    assert "degrees Celsius" in spoken
    assert "percent" in spoken
    assert "kilometers per hour" in spoken
    assert "millimeters" in spoken

def test_session_ttl_is_24_hours():
    assert settings.SESSION_TTL_SECONDS == 86400

def test_language_detection_and_persistence():
    # Detect language choice
    assert detect_language_choice("English") == "English"
    assert detect_language_choice("english") == "English"
    assert detect_language_choice("മലയാളം") == "Malayalam"
    assert detect_language_choice("malayalam") == "Malayalam"
    assert detect_language_choice("हिन्दी") == "Hindi"
    assert detect_language_choice("hindi") == "Hindi"
    assert detect_language_choice("தமிழ்") == "Tamil"
    assert detect_language_choice("tamil") == "Tamil"
    assert detect_language_choice("I want Hindi please") == "Hindi"
    assert detect_language_choice("What is the weather today?") is None

    # Test persistence
    test_user = "TEST_USER_LANG_999"
    update_user_language(test_user, "Malayalam")
    assert get_user_language(test_user) == "Malayalam"
    
    update_user_language(test_user, "English")
    assert get_user_language(test_user) == "English"

def test_clean_response_text_unclosed_think_tags():
    # Regular completed think tag
    text1 = "<think>Let me calculate weather</think>The weather is 25°C."
    assert clean_response_text(text1) == "The weather is 25°C."

    # Unclosed think tag with response
    text2 = "<think>I should advise the farmer to wait for rain. Here is the answer: delay spraying."
    cleaned2 = clean_response_text(text2)
    assert "delay spraying" in cleaned2
    assert "<think>" not in cleaned2

    # Repeated special characters
    text3 = "Attention!!!!! The wind is high *********"
    cleaned3 = clean_response_text(text3)
    assert "!!!!!" not in cleaned3
    assert "*********" not in cleaned3

def test_extract_and_clean_final_message_no_fallback_on_reasoning():
    # Normal message
    msg = AIMessage(content="Today is sunny.")
    assert extract_and_clean_final_message([msg]) == "Today is sunny."

    # When content is empty and only reasoning_content exists, reasoning_content must NOT be leaked
    msg_reasoning = AIMessage(
        content="",
        additional_kwargs={"reasoning_content": "We need to answer about good crops to grow in Thrissur..."}
    )
    result = extract_and_clean_final_message([msg_reasoning])
    assert "Thrissur" not in result
    assert "We need to answer" not in result
    assert "couldn't generate a complete response" in result

    # When intermediate tool call message is followed by final text response
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[{"name": "fetch_live_mandi_rates", "args": {"commodity": "banana"}, "id": "1", "type": "tool_call"}],
        additional_kwargs={"reasoning_content": "Fetch banana mandi rates first."}
    )
    final_msg = AIMessage(content="**Banana** is a great crop to grow in Thrissur.")
    assert extract_and_clean_final_message([tool_call_msg, final_msg]) == "**Banana** is a great crop to grow in Thrissur."

def test_is_whatsapp_group_message():
    # Direct Messages (DMs)
    dm_payload_1 = {"chatId": "919072906348@c.us", "isGroupMsg": False}
    assert is_whatsapp_group_message(dm_payload_1, "919072906348@c.us") is False

    dm_payload_2 = {"chatId": "87780608733192@lid", "isGroupMsg": False}
    assert is_whatsapp_group_message(dm_payload_2, "87780608733192@lid") is False

    # Group Messages (@g.us or isGroupMsg flag)
    group_payload_1 = {"chatId": "120363025123456789@g.us", "isGroupMsg": True, "author": "919072906348@c.us"}
    assert is_whatsapp_group_message(group_payload_1, "120363025123456789@g.us") is True

    group_payload_2 = {"chatId": "120363025123456789@g.us", "author": "919072906348@c.us"}
    assert is_whatsapp_group_message(group_payload_2, "120363025123456789@g.us") is True

    group_payload_3 = {"chat": {"isGroup": True}, "from": "120363025123456789@g.us"}
    assert is_whatsapp_group_message(group_payload_3, "120363025123456789@g.us") is True

    # Config default is False (DMs only)
    assert settings.ALLOW_GROUP_MESSAGES is False

def test_clean_response_text_html_and_asterisks():
    # Test <br> and <br/> tags converted to newlines
    raw_html = "**Tomato:** ₹25/kg<br>* **Potato:** ₹18/kg<br />* **Onion:** ₹22/kg"
    cleaned = clean_response_text(raw_html)
    assert "<br>" not in cleaned
    assert "<br/>" not in cleaned
    assert "<br />" not in cleaned
    assert "\n" in cleaned
    # Leading asterisks converted to clean bullet points
    assert "• **Potato:**" in cleaned
    assert "• **Onion:**" in cleaned

    # Test HTML tags and entities decoded
    entity_text = "<p>Soil is wet &amp; &nbsp; cold.</p><b>Note:</b> Delay spray."
    cleaned_entities = clean_response_text(entity_text)
    assert "<p>" not in cleaned_entities
    assert "<b>" not in cleaned_entities
    assert "&amp;" not in cleaned_entities
    assert "&" in cleaned_entities
    assert "Soil is wet & cold." in cleaned_entities

    # Test broken asterisks and lines with only asterisks
    broken_stars = "Header\n***\n* \n• Item 1\nFooter *"
    cleaned_stars = clean_response_text(broken_stars)
    assert "***" not in cleaned_stars
    assert "\n* \n" not in cleaned_stars

def test_clean_search_snippet():
    raw_snippet = "1.&nbsp;Latest Tomato price in Kerala<br><b>Market rate:</b> ₹3,200/Qtl.&#39;s"
    clean = clean_search_snippet(raw_snippet)
    assert "<br>" not in clean
    assert "<b>" not in clean
    assert "&nbsp;" not in clean
    assert "&#39;" not in clean
    assert "1." not in clean
    assert "Latest Tomato price in Kerala Market rate: ₹3,200/Qtl.'s" in clean
