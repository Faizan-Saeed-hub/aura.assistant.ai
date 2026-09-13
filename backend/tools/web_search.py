import json
from typing import List, Dict, Any

import json
import httpx
from typing import List, Dict, Any

def web_search(query: str, max_results: int = 4) -> str:
    """Perform a free real-time web search using DuckDuckGo or Wikipedia fallback (No API key needed)."""
    # 1. Try DuckDuckGo official package
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            if results:
                output = []
                for i, r in enumerate(results, 1):
                    title = r.get("title", "")
                    snippet = r.get("body", "")
                    url = r.get("href", "")
                    output.append(f"{i}. **{title}**\n   {snippet}\n   URL: {url}")
                return "\n\n".join(output)
    except Exception:
        pass

    # 2. Try DuckDuckGo Instant Answer API (Free JSON endpoint)
    try:
        resp = httpx.get("https://api.duckduckgo.com/", params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}, timeout=6.0)
        if resp.status_code == 200:
            data = resp.json()
            abstract = data.get("AbstractText", "")
            source_url = data.get("AbstractURL", "")
            heading = data.get("Heading", query)
            related = [t.get("Text") for t in data.get("RelatedTopics", []) if isinstance(t, dict) and t.get("Text")]
            
            if abstract:
                res = [f"**{heading}**\n{abstract}\nSource: {source_url}"]
                if related:
                    res.append("\n**Related Info:**")
                    for r in related[:3]:
                        res.append(f"- {r}")
                return "\n".join(res)
    except Exception:
        pass

    # 3. Fallback to Wikipedia summary if general topic
    try:
        from backend.tools.wikipedia import wikipedia_lookup
        wiki_res = wikipedia_lookup(query)
        if wiki_res and "No Wikipedia article" not in wiki_res:
            return wiki_res
    except Exception:
        pass

    return f"Search for '{query}': No live results found. Please check internet connection or query terms."
