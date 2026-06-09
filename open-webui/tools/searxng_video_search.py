"""
title: SearXNG Video Search
author: local
description: Search for videos via the local SearXNG instance (YouTube, Google Videos). Use this when the user asks for video content, documentaries, lectures, or talks on a topic.
version: 0.1.0
"""

import requests


class Tools:
    def __init__(self):
        self.searxng_url = "http://searxng:8080/search"

    def search_videos(self, query: str) -> str:
        """
        Search for videos on a topic using local SearXNG.
        Use this when the user asks for video content, documentaries, lectures or talks.
        Sources include YouTube and Google Videos.
        :param query: The video search query
        :return: Formatted list of videos with titles, descriptions and links
        """
        try:
            response = requests.get(
                self.searxng_url,
                params={
                    "q": query,
                    "format": "json",
                    "categories": "videos",
                    "language": "en"
                },
                timeout=8
            )
            data = response.json()
            results = data.get("results", [])[:6]

            if not results:
                return f"No video results found for: {query}"

            lines = [f"## Video results for: {query}\n"]
            for r in results:
                title = r.get("title", "No title")
                content = r.get("content", "").strip()
                url = r.get("url", "")
                engine = r.get("engine", "")
                length = r.get("length", "")

                lines.append(f"**{title}**")
                meta = filter(None, [engine, length])
                lines.append(f"*{' — '.join(meta)}*")
                if content:
                    lines.append(content)
                lines.append(f"Link: {url}\n")

            return "\n".join(lines)

        except Exception as e:
            return f"Video search failed: {e}"
