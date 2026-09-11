from langchain_core.tools import tool
from duckduckgo_search import DDGS
import logging

logger = logging.getLogger(__name__)

@tool
def search_live_web(query: str) -> str:
    """
    Searches the live web for recent agricultural news, live APMC mandi market rates, or current events.
    Use this if the user asks about live prices, breaking news, or topics outside standard farming knowledge.
    """
    logger.info(f"Executing web search for: {query}")
    try:
        results = DDGS().text(query, max_results=3)
        if not results:
            return "No relevant live information found."
            
        formatted_results = []
        for r in results:
            href = r.get("href", "")
            domain = href.split("/")[2] if "//" in href else "Web"
            formatted_results.append(
                f"Snippet: {r.get('body')}\n[Source: Web Search - {domain}]"
            )
        
        return "\n\n".join(formatted_results)
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return f"Web search failed due to an error."
