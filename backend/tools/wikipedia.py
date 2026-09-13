import httpx
from typing import Optional

def wikipedia_lookup(query: str) -> str:
    """Lookup a summary of any topic, person, or historical event on Wikipedia (100% Free, no API key)."""
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{httpx.URL(query)}"
        headers = {"User-Agent": "AIPersonalAssistant/1.0 (contact@example.com)"}
        res = httpx.get(url, headers=headers, follow_redirects=True, timeout=6.0)
        if res.status_code == 200:
            data = res.json()
            title = data.get("title", query)
            extract = data.get("extract", "")
            page_url = data.get("content_urls", {}).get("desktop", {}).get("page", "")
            return f"**Wikipedia: {title}**\n{extract}\nSource: {page_url}"
        elif res.status_code == 404:
            # Try search endpoint
            search_url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "opensearch",
                "search": query,
                "limit": 1,
                "namespace": 0,
                "format": "json"
            }
            s_res = httpx.get(search_url, params=params, headers=headers, timeout=6.0)
            if s_res.status_code == 200:
                s_data = s_res.json()
                if len(s_data) > 2 and s_data[1]:
                    first_title = s_data[1][0]
                    first_desc = s_data[2][0] if s_data[2] else ""
                    first_link = s_data[3][0] if s_data[3] else ""
                    return f"**Wikipedia: {first_title}**\n{first_desc}\nSource: {first_link}"
            return f"No Wikipedia article found for '{query}'."
        else:
            return f"Wikipedia lookup error ({res.status_code})"
    except Exception as e:
        return f"Could not query Wikipedia: {str(e)}"
