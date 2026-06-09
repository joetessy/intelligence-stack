"""
title: SearXNG News Search
author: local
description: Search recent news articles via the local SearXNG instance. Use this when the user asks about current events, breaking news, recent developments, or anything time-sensitive.
version: 0.1.0
"""

import requests


class Tools:
    def __init__(self):
        self.searxng_url = "http://searxng:8080/search"

    def search_news(self, query: str) -> str:
        """
        Search for recent news articles on a topic using local SearXNG.
        Use this for current events, breaking news, or anything recent.
        :param query: The news search query
        :return: Formatted list of recent news articles with titles, summaries and sources
        """
        try:
            response = requests.get(
                self.searxng_url,
                params={
                    "q": query,
                    "format": "json",
                    "categories": "news",
                    "language": "en"
                },
                timeout=8
            )
            data = response.json()
            results = data.get("results", [])[:6]

            if not results:
                return f"No news results found for: {query}"

            lines = [f"## News results for: {query}\n"]
            for r in results:
                title = r.get("title", "No title")
                content = r.get("content", "").strip()
                url = r.get("url", "")
                published = r.get("publishedDate", "")
                engine = r.get("engine", "")

                lines.append(f"**{title}**")
                if published:
                    lines.append(f"*{published} — via {engine}*")
                if content:
                    lines.append(content)
                lines.append(f"Source: {url}\n")

            return "\n".join(lines)

        except Exception as e:
            return f"News search failed: {e}"
