import hashlib
import json
import os
import re
import threading
import urllib.error
import urllib.request

from pathlib import Path
from typing import Any
from dotenv import load_dotenv

load_dotenv(
    Path(__file__).resolve().parents[2] / ".env"
)


TAVILY_ENDPOINT = "https://api.tavily.com/search"

CACHE_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / ".cache"
    / "tavily"
)

MAX_RESULTS = 3
REQUEST_TIMEOUT = 15

_cache_lock = threading.Lock()


class TavilyResearch:
    """
    Research service for AgentArena.

    Responsibilities:
    - Build focused research queries.
    - Search documentation and technical references.
    - Cache repeated queries.
    - Return concise, structured research context.
    - Fail gracefully when Tavily is unavailable.

    The service never sends repository source code
    to Tavily.
    """

    def __init__(self):
        self.api_key = os.getenv(
            "TAVILY_API_KEY", ""
        ).strip()

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _build_query(
        self,
        scenario_id: str,
        bug_report: str,
    ) -> str:
        """
        Build a research query using known scenario context.

        Queries describe the domain rather than exposing
        repository source code.
        """

        scenario_queries = {
            "discount": (
                "percentage discount calculation "
                "zero percent edge cases "
                "financial software unit testing"
            ),
            "auth": (
                "authentication session expiration "
                "timestamp boundary conditions "
                "security testing"
            ),
            "authentication": (
                "authentication session expiration "
                "timestamp boundary conditions "
                "security testing"
            ),
            "inventory": (
                "inventory stock reservation "
                "exact available quantity "
                "boundary condition testing"
            ),
            "shipping": (
                "shipping weight tier boundaries "
                "inclusive exclusive thresholds "
                "unit testing"
            ),
        }

        if scenario_id in scenario_queries:
            return scenario_queries[scenario_id]

        # Generic fallback. Never forward arbitrary bug reports
        # or repository contents to a third-party search API.
        return (
            "software engineering boundary value "
            "analysis regression testing pytest "
            "edge case testing best practices"
        )

    def _cache_path(
        self,
        query: str,
    ) -> Path:

        fingerprint = hashlib.sha256(
            query.encode("utf-8")
        ).hexdigest()

        return (
            CACHE_DIRECTORY
            / f"{fingerprint}.json"
        )

    def _read_cache(
        self,
        query: str,
    ) -> dict | None:

        path = self._cache_path(query)

        if not path.is_file():
            return None

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                cached = json.load(file)

            if not isinstance(cached, dict):
                return None

            cached["cached"] = True

            return cached

        except (OSError, json.JSONDecodeError):
            return None

    def _write_cache(
        self,
        query: str,
        result: dict,
    ):

        try:
            with _cache_lock:
                CACHE_DIRECTORY.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                path = self._cache_path(query)

                temporary_path = path.with_suffix(
                    ".tmp"
                )

                temporary_path.write_text(
                    json.dumps(
                        result,
                        indent=2,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

                temporary_path.replace(path)

        except OSError as error:
            print(
                f"Tavily cache warning: {error}"
            )

    def search(
        self,
        scenario_id: str,
        bug_report: str,
    ) -> dict:
        """
        Execute at most one Tavily search.

        Returns a consistent dictionary whether research
        succeeds, is disabled, or fails.
        """

        query = self._build_query(
            scenario_id,
            bug_report,
        )

        base_result = {
            "enabled": bool(self.api_key),
            "status": "unavailable",
            "query": query,
            "sources": [],
            "context": "",
            "cached": False,
            "error": None,
        }

        if not self.api_key:
            base_result["status"] = "disabled"
            base_result["error"] = (
                "TAVILY_API_KEY is not configured."
            )

            return base_result

        cached = self._read_cache(query)

        if cached is not None:
            return cached

        payload = {
            "query": query,
            "search_depth": "basic",
            "topic": "general",
            "max_results": MAX_RESULTS,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }

        request = urllib.request.Request(
            TAVILY_ENDPOINT,
            data=json.dumps(payload).encode(
                "utf-8"
            ),
            headers={
                "Content-Type": "application/json",
                "Authorization": (
                    f"Bearer {self.api_key}"
                ),
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=REQUEST_TIMEOUT,
            ) as response:

                data = json.loads(
                    response.read().decode(
                        "utf-8"
                    )
                )

        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            OSError,
            ValueError,
        ) as error:

            base_result["status"] = "failed"
            base_result["error"] = str(error)

            print(
                f"Tavily research failed: {error}"
            )

            return base_result

        sources = []

        for item in data.get("results", []):

            if not isinstance(item, dict):
                continue

            title = str(
                item.get("title") or ""
            ).strip()

            url = str(
                item.get("url") or ""
            ).strip()

            content = str(
                item.get("content") or ""
            ).strip()

            if not url.startswith(
                ("https://", "http://")
            ):
                continue

            # Bound the size of external text sent to Nemotron.
            content = re.sub(
                r"\s+",
                " ",
                content,
            )[:1000]

            sources.append({
                "title": title[:200],
                "url": url,
                "content": content,
            })

        context_parts = []

        for index, source in enumerate(
            sources,
            start=1,
        ):

            context_parts.append(
                f"[SOURCE {index}]\n"
                f"Title: {source['title']}\n"
                f"URL: {source['url']}\n"
                f"Excerpt: {source['content']}"
            )

        result = {
            "enabled": True,
            "status": (
                "completed"
                if sources
                else "no_results"
            ),
            "query": query,
            "sources": sources,
            "context": "\n\n".join(
                context_parts
            ),
            "cached": False,
            "error": None,
        }

        self._write_cache(
            query,
            result,
        )

        return result