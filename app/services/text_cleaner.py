import re
import html

def clean_response_text(text: str) -> str:
    """
    Cleans LLM response text for WhatsApp and Web text display:
    1. Strips <think>...</think> reasoning blocks (complete or unclosed).
    2. Decodes HTML entities (&nbsp;, &amp;, &#39;, &quot;, &lt;, &gt;).
    3. Converts HTML line breaks (<br>, <br/>, <p>) to clean newlines.
    4. Strips any lingering HTML tags.
    5. Removes escaped markdown backslashes (\\*, \\_).
    6. Formats bullet points cleanly (converts '* ' to '• ') to avoid WhatsApp bold collisions.
    7. Collapses 3+ asterisks and removes standalone/dangling asterisks.
    8. Normalizes repeated punctuation and excessive blank lines.
    """
    if not text:
        return ""

    # 1. Strip complete <think>...</think> blocks
    cleaned = re.sub(r'(?is)<think>.*?</think>', '', text).strip()

    # 2. If stripping complete blocks left an empty string but text started with <think>,
    # try to extract content after </think> or remove the <think> opening tag
    if not cleaned:
        if "</think>" in text:
            cleaned = text.split("</think>", 1)[-1].strip()
        else:
            cleaned = re.sub(r'(?is)^\s*<think>\s*', '', text).strip()

    # 3. Strip any stray <think> or </think> tags
    cleaned = re.sub(r'(?is)</?think>', '', cleaned)

    # 4. Decode HTML entities and replace non-breaking spaces
    cleaned = html.unescape(cleaned)
    cleaned = cleaned.replace('\xa0', ' ').replace('\u200b', '')

    # 5. Convert HTML line breaks and paragraphs to natural newlines
    cleaned = re.sub(r'(?i)<br\s*/?>', '\n', cleaned)
    cleaned = re.sub(r'(?i)</?(?:p|div|hr|tr|li)\s*/?>', '\n', cleaned)
    # Strip any remaining HTML tags (like <b>, </b>, <span>, <i>, etc.)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)

    # 6. Remove escaped markdown backslashes like \* or \_
    cleaned = re.sub(r'\\([*_~`])', r'\1', cleaned)

    # 7. Normalize WhatsApp bullet points: Convert leading '* ' or '+ ' to '• '
    # This prevents WhatsApp from mistaking bullet asterisks for unclosed bold text
    cleaned = re.sub(r'(?m)^(\s*)[*+]\s+', r'\1• ', cleaned)

    # 8. Clean up stray and broken asterisks
    cleaned = re.sub(r'\*{3,}', '', cleaned)                 # Collapse 3+ asterisks to empty
    cleaned = re.sub(r'(?m)^\s*\*+\s*$', '', cleaned)        # Remove lines containing only asterisks and whitespace
    cleaned = re.sub(r'(?<=\s)\*(?=\s)', '', cleaned)        # Remove standalone asterisks surrounded by whitespace

    # 9. Collapse 3+ repeated special characters (e.g. ####, ----, ....., !!!!!, ????)
    cleaned = re.sub(r'#{3,}', '', cleaned)
    cleaned = re.sub(r'-{4,}', '---', cleaned)
    cleaned = re.sub(r'\.{4,}', '...', cleaned)
    cleaned = re.sub(r'!{3,}', '!', cleaned)
    cleaned = re.sub(r'\?{3,}', '?', cleaned)

    # 10. Collapse multiple horizontal spaces and clean excessive blank lines
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    cleaned = re.sub(r' ?\n ?', '\n', cleaned)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()

def clean_text_for_speech(text: str) -> str:
    """
    Sanitizes response text specifically for Text-to-Speech (TTS) voice generation:
    1. Strips all markdown formatting (bold, italics, headers, backticks, tildes).
    2. Strips citations like [Source: Open-Meteo Forecast] and URLs.
    3. Expands units (°C, %, km/h, mm) into natural spoken words in Malayalam, Tamil, Hindi, or English.
    4. Strips parentheses, brackets, and braces while keeping inner content.
    5. Replaces colons and semicolons with natural commas (speech pauses).
    6. Replaces slashes and ampersands with words.
    7. Completely eliminates all remaining special characters (*, #, _, -, ~, quotes, math symbols).
    8. Removes all emojis and dingbats.
    9. Normalizes pauses and whitespace so Edge-TTS never speaks punctuation names.
    """
    if not text:
        return ""

    # 1. First run general cleaning
    cleaned = clean_response_text(text)

    # 2. Strip URLs and source citations like [Source: ...] or [source: ...]
    cleaned = re.sub(r'https?://\S+|www\.\S+', '', cleaned)
    cleaned = re.sub(r'(?i)\[Source:[^\]]*\]', '', cleaned)
    cleaned = re.sub(r'\[.*?\]', '', cleaned)

    # 3. Detect Indic language context for localized unit expansion
    is_ml = bool(re.search(r'[\u0D00-\u0D7F]', cleaned))
    is_ta = bool(re.search(r'[\u0B80-\u0BFF]', cleaned))
    is_hi = bool(re.search(r'[\u0900-\u097F]', cleaned))

    if is_ml:
        cleaned = re.sub(r'(\d+)\s*°\s*C\b', r'\1 ഡിഗ്രി സെൽഷ്യസ്', cleaned)
        cleaned = re.sub(r'°C\b', ' ഡിഗ്രി സെൽഷ്യസ്', cleaned)
        cleaned = re.sub(r'(\d+)\s*%', r'\1 ശതമാനം', cleaned)
        cleaned = re.sub(r'(\d+)\s*km/h\b', r'\1 കിലോമീറ്റർ', cleaned)
        cleaned = re.sub(r'\bkm/h\b', 'കിലോമീറ്റർ', cleaned)
        cleaned = re.sub(r'(\d+)\s*mm\b', r'\1 മില്ലിമീറ്റർ', cleaned)
    elif is_ta:
        cleaned = re.sub(r'(\d+)\s*°\s*C\b', r'\1 டிகிரி செல்சியஸ்', cleaned)
        cleaned = re.sub(r'°C\b', ' டிகிரி செல்சியஸ்', cleaned)
        cleaned = re.sub(r'(\d+)\s*%', r'\1 சதவீதம்', cleaned)
        cleaned = re.sub(r'(\d+)\s*km/h\b', r'\1 கிலோமீட்டர்', cleaned)
        cleaned = re.sub(r'\bkm/h\b', 'கிலோமீட்டர்', cleaned)
        cleaned = re.sub(r'(\d+)\s*mm\b', r'\1 மில்லிமீட்டர்', cleaned)
    elif is_hi:
        cleaned = re.sub(r'(\d+)\s*°\s*C\b', r'\1 डिग्री सेल्सियस', cleaned)
        cleaned = re.sub(r'°C\b', ' डिग्री सेल्सियस', cleaned)
        cleaned = re.sub(r'(\d+)\s*%', r'\1 प्रतिशत', cleaned)
        cleaned = re.sub(r'(\d+)\s*km/h\b', r'\1 किलोमीटर प्रति घंटा', cleaned)
        cleaned = re.sub(r'\bkm/h\b', 'किलोमीटर प्रति घंटा', cleaned)
        cleaned = re.sub(r'(\d+)\s*mm\b', r'\1 मिलीमीटर', cleaned)
    else:
        cleaned = re.sub(r'(\d+)\s*°\s*C\b', r'\1 degrees Celsius', cleaned)
        cleaned = re.sub(r'°C\b', ' degrees Celsius', cleaned)
        cleaned = re.sub(r'(\d+)\s*%', r'\1 percent', cleaned)
        cleaned = re.sub(r'\bkm/h\b', 'kilometers per hour', cleaned)
        cleaned = re.sub(r'(\d+)\s*mm\b', r'\1 millimeters', cleaned)

    # 4. Strip markdown bold/italics across newlines
    cleaned = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'_{1,3}(.*?)_{1,3}', r'\1', cleaned, flags=re.DOTALL)

    # 5. Remove all brackets and parentheses while keeping the words inside
    cleaned = re.sub(r'[()\[\]{}<>]', ' ', cleaned)

    # 6. Replace colons and semicolons with gentle pauses (commas) so TTS never speaks 'colon'
    cleaned = re.sub(r'[:;]', ', ', cleaned)

    # 7. Convert slashes and ampersands into natural connective words
    or_word = ' അല്ലെങ്കിൽ ' if is_ml else (' அல்லது ' if is_ta else (' या ' if is_hi else ' or '))
    and_word = ' and '
    cleaned = re.sub(r'/', or_word, cleaned)
    cleaned = re.sub(r'&', and_word, cleaned)

    # 8. Convert bullet lines to natural pauses
    cleaned = re.sub(r'^\s*[-*•▪▫+]\s+', ', ', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\s*\d+\.\s+', ', ', cleaned, flags=re.MULTILINE)

    # 9. Strip ALL remaining special characters that TTS would read aloud
    # Specifically: * # ` ~ _ + = ^ | \ " ' “ ” ‘ ’ « » – —
    cleaned = re.sub(r'[\"*#`~_+=^|\\\'"“”‘’«»–—]', ' ', cleaned)
    cleaned = re.sub(r'-', ' ', cleaned)

    # 10. Remove all emojis and miscellaneous Unicode symbols
    emoji_pattern = re.compile(
        "["
        "\U00010000-\U0010FFFF"  # Supplemental symbols, pictographs, emojis
        "\u2600-\u27BF"          # Misc symbols & dingbats
        "\u2300-\u23FF"          # Misc technical
        "\u2B50-\u2B55"          # Stars & shapes
        "\uFE00-\uFE0F"          # Variation selectors
        "\u200B-\u200D"          # Zero-width spaces & joiners
        "\uFEFF"                 # Zero-width no-break space
        "]+",
        flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub('', cleaned)

    # 11. Normalize commas, periods, and whitespace into natural cadence
    cleaned = re.sub(r'\s*,\s*', ', ', cleaned)
    cleaned = re.sub(r'(,\s*)+', ', ', cleaned)
    cleaned = re.sub(r'\s*\.\s*', '. ', cleaned)
    cleaned = re.sub(r'(\.\s*)+', '. ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = re.sub(r'\s+([.,!?])', r'\1', cleaned)
    cleaned = re.sub(r'^[,.\s]+', '', cleaned)

    return cleaned.strip()

def make_short_audio_summary(text: str, max_words: int = 45) -> str:
    """
    Extracts a concise, punchy executive summary of 1-3 sentences (under ~45 words / 20-30 seconds audio)
    specifically for WhatsApp voice messages, avoiding 2-minute long audio files.
    """
    if not text:
        return ""
        
    cleaned = clean_response_text(text)
    
    # Strip markdown headers, horizontal rules, and source tags
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    meaningful_lines = []
    
    for line in lines:
        if line.startswith("#") or line.startswith("---") or line.startswith("[Source:"):
            continue
        if line.lower().startswith("header:") or line.lower().startswith("source tag:"):
            continue
        meaningful_lines.append(line)
        
    unified_text = " ".join(meaningful_lines)
    
    # Split into sentences using punctuation boundaries
    sentences = re.split(r'(?<=[.!?।])\s+', unified_text)
    
    chosen_sentences = []
    total_words = 0
    
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        words = s_clean.split()
        if not words:
            continue
            
        if total_words + len(words) <= max_words or not chosen_sentences:
            chosen_sentences.append(s_clean)
            total_words += len(words)
            if len(chosen_sentences) >= 3:
                break
        else:
            break
            
    summary = " ".join(chosen_sentences)
    return clean_text_for_speech(summary)


