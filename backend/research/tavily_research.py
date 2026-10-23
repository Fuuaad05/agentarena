import hashlib
import json
import os
import re
import threading
import time
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


CACHE_SCHEMA_VERSION = 3
_CALLBACK_SIGNATURE = r"(?:urllib\.parse\.)?parse(?:\\)?_qsl(?:[\s*`\[\]]){0,12}\("


def callback_documentation_excerpt(raw):
    """Find the function section in plain text or escaped Tavily Markdown.

    Return the original contiguous text, with whitespace collapsed only.
    Never replace an absent parse_qsl section with parse_qs documentation.
    """
    for signature in re.finditer(_CALLBACK_SIGNATURE, raw, re.I):
        section = raw[signature.start():]
        next_function = re.search(r"(?:urllib\.parse\.)?urlunparse(?:[\s*`\[\]]){0,12}\(", section, re.I)
        if next_function:
            section = section[:next_function.start()]
        section = re.sub(r"\s+", " ", section).strip()[:1800]
        if "blank values" in section.lower() or "blanks should" in section.lower():
            return section
    return None


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
            "callback": "Python 3.11 urllib.parse.parse_qsl application/x-www-form-urlencoded parameters",
            "redirect": "Python 3.11 urllib.parse urljoin reference absolute URL security warning",
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

            if cached.get("schema_version") != CACHE_SCHEMA_VERSION:
                return None
            if time.time() - cached.get("fetched_at", 0) > 86400:
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
        Execute one search, plus at most one exact-page extraction for redirect fallback.

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
            "max_results": 5 if scenario_id in ("redirect", "callback") else MAX_RESULTS,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }

        # For the documentation-led use case, use primary Python documentation.
        if scenario_id in ("redirect", "callback"):
            payload["include_domains"] = ["docs.python.org"]
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

            if scenario_id == "callback":
                content = callback_documentation_excerpt(content) or ""

            # Bound the size of external text sent to Nemotron.
            content = re.sub(
                r"\s+",
                " ",
                content,
            )[:1000]

            if scenario_id in ("redirect", "callback"):
                from urllib.parse import urlparse
                parsed = urlparse(url)
                if parsed.hostname != "docs.python.org" or parsed.path != "/3.11/library/urllib.parse.html" or not content:
                    continue
            if scenario_id == "callback" and "blank" not in content.lower():
                continue
            sources.append({
                "id": f"S{len(sources) + 1}",
                "title": title[:200],
                "url": url,
                "content": content,
            })

        extraction_error = None
        if scenario_id in ("redirect", "callback") and not sources:
            # Search indexes may omit older documentation versions. Use the
            # requested primary page, never silently substitute another version.
            sources, extraction_error = self._extract_python_documentation(scenario_id)

        context_parts = []

        for index, source in enumerate(
            sources,
            start=1,
        ):

            context_parts.append(
                f"[SOURCE S{index}]\n"
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
            "schema_version": CACHE_SCHEMA_VERSION,
            "fetched_at": time.time(),
            "error": extraction_error,
        }

        # An empty/filtered search must not suppress the next real attempt for 24 hours.
        if sources:
            self._write_cache(query, result)

        return result

    def _extract_python_documentation(self, topic="redirect"):
        url = "https://docs.python.org/3.11/library/urllib.parse.html"
        request = urllib.request.Request(
            "https://api.tavily.com/extract",
            data=json.dumps({"urls": [url], "extract_depth": "basic", "include_images": False}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))
            matching_pages = 0
            extracted_chars = 0
            signature_count = 0
            for item in data.get("results", []):
                if item.get("url", "").split("#")[0] != url:
                    continue
                matching_pages += 1
                raw = str(item.get("raw_content") or "").strip()
                extracted_chars = max(extracted_chars, len(raw))
                signature_count += len(re.findall(_CALLBACK_SIGNATURE, raw, re.I))
                if not raw:
                    continue
                # Use a contiguous passage from the actual retrieved document.
                # The topic selector is curated; it is not a blind research agent.
                if topic == "callback":
                    excerpt = callback_documentation_excerpt(raw)
                    if not excerpt:
                        continue
                else:
                    raw = re.sub(r"\s+", " ", raw)
                    focus = raw.lower().find("not secure")
                    if focus < 0:
                        focus = raw.lower().find("absolute url")
                    if focus < 0:
                        focus = raw.lower().find("urllib.parse.urljoin")
                    excerpt = raw[max(0, focus - 350):max(0, focus - 350) + 1600]
                return [{"id": "S1", "title": "Python 3.11 urllib.parse (Tavily Extract)",
                         "url": url + ("#urllib.parse.parse_qsl" if topic == "callback" else ""), "content": excerpt}], None
            return [], (f"Tavily did not return a parse_qsl section with blank-value documentation; no substitute section was used. Matching pages: {matching_pages}; extracted characters: {extracted_chars}; function markers: {signature_count}."
                        if topic == "callback" else "Tavily search and exact-page extraction returned no usable Python 3.11 documentation.")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
            return [], f"Tavily exact-page extraction failed: {error}"
