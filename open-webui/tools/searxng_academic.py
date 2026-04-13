"""
title: SearXNG Academic Search
author: local
description: Search academic papers, journals and scientific literature via the local SearXNG instance (arXiv, Semantic Scholar, Google Scholar). Use this when the user asks about research, papers, studies, or academic topics.
version: 0.1.0
"""

import requests


class Tools:
    def __init__(self):
        self.searxng_url = "http://searxng:8080/search"

    def search_academic(self, query: str) -> str:
        """
        Search academic papers and scientific literature using local SearXNG.
        Use this for research papers, studies, journal articles, or scholarly topics.
        Sources include arXiv, Semantic Scholar and Google Scholar.
        :param query: The academic search query
        :return: Formatted list of academic papers and articles with abstracts and sources
        """
        try:
            response = requests.get(
                self.searxng_url,
                params={
                    "q": query,
                    "format": "json",
                    "categories": "science",
                    "language": "en"
                },
                timeout=8
            )
            data = response.json()
            results = data.get("results", [])[:6]

            if not results:
                return f"No academic results found for: {query}"

            lines = [f"## Academic results for: {query}\n"]
            for r in results:
                title = r.get("title", "No title")
                content = r.get("content", "").strip()
                url = r.get("url", "")
                engine = r.get("engine", "")

                lines.append(f"**{title}**")
                lines.append(f"*via {engine}*")
                if content:
                    lines.append(content)
                lines.append(f"Source: {url}\n")

            return "\n".join(lines)

        except Exception as e:
            return f"Academic search failed: {e}"
