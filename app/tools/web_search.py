import asyncio
import logging
import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from langchain_core.tools import tool

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

import httpx
import lxml.html

logger = logging.getLogger(__name__)

def clean_search_snippet(text: str) -> str:
    """Sanitizes raw search snippets by removing HTML tags, entities, non-breaking spaces, and broken asterisks."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'(?i)<br\s*/?>', ' ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('\xa0', ' ').replace('\u200b', '')
    text = re.sub(r'^\d+\.\s*', '', text)
    text = re.sub(r'\*{2,}', '', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

def _search_lite_ddg(query: str) -> List[Dict[str, Any]]:
    """Ultra-fast, lightweight DuckDuckGo Lite search with HTML sanitization."""
    url = "https://lite.duckduckgo.com/lite/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://lite.duckduckgo.com/",
    }
    try:
        r = httpx.post(url, data={"q": query}, headers=headers, follow_redirects=True, timeout=5.0)
        if r.status_code != 200:
            return []
        doc = lxml.html.fromstring(r.text)
        links = doc.xpath('//a[contains(@class, "result-link")]')
        snippets = doc.xpath('//td[contains(@class, "result-snippet")]')
        results = []
        for a, s in zip(links[:4], snippets[:4]):
            title = clean_search_snippet(a.text_content())
            url_href = a.get("href", "").strip()
            body = clean_search_snippet(s.text_content())
            if title and body:
                results.append({
                    "title": title,
                    "body": body,
                    "url": url_href,
                    "source": "DuckDuckGo"
                })
        return results
    except Exception as e:
        logger.debug(f"Lite DDG search failed: {e}")
        return []

def _search_html_ddg(query: str) -> List[Dict[str, Any]]:
    """Direct HTML search fallback using lxml parsing."""
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://html.duckduckgo.com/",
    }
    try:
        r = httpx.post(url, data={"q": query}, headers=headers, follow_redirects=True, timeout=5.0)
        if r.status_code != 200:
            return []
        doc = lxml.html.fromstring(r.text)
        items = []
        for res in doc.xpath('//div[contains(@class, "result__body")]')[:4]:
            t_nodes = res.xpath('.//h2//text()')
            s_nodes = res.xpath('.//a[contains(@class, "result__snippet")]//text()')
            u_nodes = res.xpath('.//a[contains(@class, "result__url")]/@href')
            title = clean_search_snippet(' '.join(''.join(t_nodes).split()))
            snippet = clean_search_snippet(' '.join(''.join(s_nodes).split()))
            url_href = u_nodes[0].strip() if u_nodes else ""
            if title and snippet:
                items.append({
                    "title": title,
                    "body": snippet,
                    "url": url_href,
                    "source": "DuckDuckGo"
                })
        return items
    except Exception as e:
        logger.debug(f"Direct HTML DDG search failed: {e}")
        return []

def _search_google_news_rss(query: str) -> List[Dict[str, Any]]:
    """High-reliability Indian news & agricultural advisory RSS fallback (zero rate limits, <300ms)."""
    try:
        encoded_q = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_q}&hl=en-IN&gl=IN&ceid=IN:en"
        r = httpx.get(url, timeout=5.0, follow_redirects=True)
        if r.status_code != 200:
            return []
        root = ET.fromstring(r.content)
        items = root.findall('.//item')
        results = []
        for it in items[:4]:
            title_elem = it.find('title')
            link_elem = it.find('link')
            desc_elem = it.find('description')
            source_elem = it.find('source')
            
            raw_title = title_elem.text if title_elem is not None else ""
            raw_link = link_elem.text if link_elem is not None else ""
            raw_desc = desc_elem.text if desc_elem is not None else ""
            source_name = source_elem.text if source_elem is not None else "AgriNews"
            
            title = clean_search_snippet(raw_title)
            body = clean_search_snippet(raw_desc)
            if title:
                results.append({
                    "title": title,
                    "body": body or title,
                    "url": raw_link,
                    "source": source_name
                })
        return results
    except Exception as e:
        logger.debug(f"Google News RSS fallback search failed: {e}")
        return []

def _sync_ddgs_search(query: str) -> List[Dict[str, Any]]:
    """
    Executes agricultural web search across 4 resilient tiers:
    1. Lite DDG (fastest, clean text)
    2. HTML DDG
    3. Google News RSS (official Indian agricultural & scheme news)
    4. DDGS API fallback
    """
    enhanced_query = query.strip()
    lower_q = enhanced_query.lower()
    
    # Context biasing: If query lacks agricultural terms, append context
    agri_terms = ["india", "kisan", "krishi", "mandi", "farmer", "agriculture", "farming", "crop", "crops", "harvest", "fertilizer", "pesticide"]
    if not any(k in lower_q for k in agri_terms):
        enhanced_query = f"{enhanced_query} agriculture India"
    elif "india" not in lower_q and not any(st in lower_q for st in ["up", "punjab", "haryana", "bihar", "tamil nadu", "kerala", "karnataka", "maharashtra", "delhi"]):
        enhanced_query = f"{enhanced_query} India"

    # Tier 1: DuckDuckGo Lite
    lite_items = _search_lite_ddg(enhanced_query)
    if lite_items:
        return lite_items

    # Tier 2: DuckDuckGo HTML
    html_items = _search_html_ddg(enhanced_query)
    if html_items:
        return html_items

    # Tier 3: Google News RSS Indian Agricultural Feed
    rss_items = _search_google_news_rss(enhanced_query)
    if rss_items:
        return rss_items

    # Tier 4: DDGS API with tight timeout
    try:
        ddg = DDGS()
        text_items = list(ddg.text(enhanced_query, region="in-en", max_results=3))
        if text_items:
            results = []
            for item in text_items:
                title = clean_search_snippet(item.get("title", ""))
                body = clean_search_snippet(item.get("body", ""))
                if title and body:
                    results.append({
                        "title": title,
                        "body": body,
                        "url": item.get("href", ""),
                        "source": "Web"
                    })
            if results:
                return results
    except Exception as e:
        logger.debug(f"DDGS text search failed: {e}")

    return []

@tool
async def search_duckduckgo(query: str) -> str:
    """
    Searches the live web via DuckDuckGo for recent agricultural news, government schemes (e.g. PM-KISAN),
    weather anomalies, pest alerts, and current crop market trends.
    Use this if the user asks about recent developments, current government programs, or queries requiring real-time web verification.
    """
    logger.info(f"Executing DuckDuckGo search for: {query}")
    try:
        results = await asyncio.wait_for(asyncio.to_thread(_sync_ddgs_search, query), timeout=12.0)
        if not results:
            return "No recent web articles found for this query. Proceeding with agronomic database advisory."
            
        formatted_results = []
        for r in results:
            url = r.get("url", "")
            domain = r.get("source", "Web")
            if "//" in url:
                try:
                    domain = url.split("/")[2].replace("www.", "")
                except Exception:
                    pass
            title = r.get("title", "")
            body = r.get("body", "")
            formatted_results.append(
                f"• {title}\n  Summary: {body}\n  [Source: {domain}]"
            )
        
        return "\n\n".join(formatted_results)
    except asyncio.TimeoutError:
        logger.warning(f"DuckDuckGo search timed out for query: {query}")
        return "DuckDuckGo search timed out. Proceeding with agronomy knowledge base."
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        return f"DuckDuckGo search encountered a temporary issue: {e}"

# Backward compatibility alias
search_live_web = search_duckduckgo
