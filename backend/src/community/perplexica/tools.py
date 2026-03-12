"""
Perplexica Headless Search Tools (Option B)

Uses Perplexica's proven search backend in headless mode without 
summarization pipeline. Integrates with local LLM for metadata extraction.
"""

import os
import re
import json
from typing import Optional
import requests
from urllib.parse import quote_plus

# Configuration from environment
PERPLEXICA_URL = os.getenv("PERPLEXICA_URL", "http://perplexica:3000")
LM_BASE_URL = os.getenv("LM_BASE_URL", "http://100.92.121.111:1234/v1")
LM_API_KEY = os.getenv("LM_API_KEY", "lm-studio")
REQUEST_TIMEOUT = 30


def _extract_search_results(html_content: str) -> list[dict]:
    """
    Extract search results from Perplexica's HTML response.
    Parses raw HTML to find article results.
    
    Returns:
        List of dicts with keys: title, url, snippet
    """
    results = []
    
    # Pattern to match search result items
    # Look for links with href and title attributes
    pattern = r'<a\s+[^>]*href="([^"]+)"[^>]*>\s*([^<]+)\s*</a>(?:\s*<[^>]*>)*\s*([^<]*)'
    
    matches = re.finditer(pattern, html_content, re.IGNORECASE | re.DOTALL)
    seen_urls = set()
    
    for match in matches:
        url = match.group(1)
        title = match.group(2).strip()
        snippet = match.group(3).strip() if match.group(3) else ""
        
        # Filter out internal links and duplicates
        if (url and 
            not url.startswith('#') and 
            not url.startswith('javascript:') and
            not url.startswith('/') and
            url not in seen_urls and
            len(title) > 3):
            
            results.append({
                "title": title,
                "url": url,
                "snippet": snippet[:200] if snippet else ""
            })
            seen_urls.add(url)
    
    return results[:10]  # Return top 10 results


async def web_search_tool(query: str, max_results: int = 5) -> dict:
    """
    Search the web using Perplexica's headless search backend.
    
    Uses Perplexica's proven search mechanism (/search endpoint) in headless mode.
    Local LLM support for future metadata extraction if needed.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)
    
    Returns:
        Dict with keys:
        - results: List of search results with title, url, snippet
        - count: Number of results returned
        - query: The original search query
        - source: "perplexica-headless"
    """
    try:
        # Use Perplexica's /search endpoint with format=json for structured output
        search_url = f"{PERPLEXICA_URL}/search"
        params = {
            "q": query,
            "format": "json"  # Request JSON format for easier parsing
        }
        
        print(f"[web_search_tool] Searching: {query} at {search_url}")
        
        response = requests.get(
            search_url,
            params=params,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Try parsing as JSON first
        try:
            data = response.json()
            if isinstance(data, dict) and 'results' in data:
                results = data['results'][:max_results]
                return {
                    "results": results,
                    "count": len(results),
                    "query": query,
                    "source": "perplexica-headless"
                }
        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, fall back to HTML parsing
            pass
        
        # Fall back to HTML parsing if JSON unavailable
        html_content = response.text
        results = _extract_search_results(html_content)[:max_results]
        
        return {
            "results": results,
            "count": len(results),
            "query": query,
            "source": "perplexica-headless"
        }
    
    except requests.exceptions.Timeout:
        return {
            "results": [],
            "count": 0,
            "query": query,
            "error": f"Search timeout: Perplexica not responding after {REQUEST_TIMEOUT}s",
            "source": "perplexica-headless"
        }
    except requests.exceptions.ConnectionError:
        return {
            "results": [],
            "count": 0,
            "query": query,
            "error": f"Search failed: Cannot connect to Perplexica at {PERPLEXICA_URL}",
            "source": "perplexica-headless"
        }
    except Exception as e:
        return {
            "results": [],
            "count": 0,
            "query": query,
            "error": f"Search failed: {str(e)}",
            "source": "perplexica-headless"
        }


async def web_fetch_tool(url: str) -> dict:
    """
    Fetch and parse content from a URL.
    
    Args:
        url: URL to fetch
    
    Returns:
        Dict with keys:
        - content: Extracted text content
        - title: Page title if available
        - url: The URL that was fetched
        - status_code: HTTP status code
    """
    try:
        print(f"[web_fetch_tool] Fetching: {url}")
        
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        
        # Extract basic content
        content = response.text[:5000]  # First 5000 chars
        
        # Try to extract title
        title_match = re.search(r'<title[^>]*>([^<]+)</title>', content, re.IGNORECASE)
        title = title_match.group(1) if title_match else "No title"
        
        # Remove HTML tags for cleaner content
        text_content = re.sub(r'<[^>]+>', '', content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        return {
            "content": text_content[:3000],
            "title": title,
            "url": url,
            "status_code": response.status_code,
            "source": "perplexica-headless"
        }
    
    except requests.exceptions.Timeout:
        return {
            "content": "",
            "url": url,
            "error": "Fetch timeout",
            "status_code": 0,
            "source": "perplexica-headless"
        }
    except Exception as e:
        return {
            "content": "",
            "url": url,
            "error": f"Fetch failed: {str(e)}",
            "status_code": 0,
            "source": "perplexica-headless"
        }


# Export tools for configuration
__all__ = ["web_search_tool", "web_fetch_tool"]
