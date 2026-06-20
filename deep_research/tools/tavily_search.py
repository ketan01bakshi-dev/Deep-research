"""Tavily-powered web search for research literature."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import urlparse

from cursor_sdk import CustomTool, CustomToolContext

# Credible academic and health-research sources (Tavily include_domains limit: 300).
CREDIBLE_RESEARCH_DOMAINS = [
    "pubmed.ncbi.nlm.nih.gov",
    "ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "nih.gov",
    "who.int",
    "cdc.gov",
    "nature.com",
    "sciencedirect.com",
    "springer.com",
    "bmj.com",
    "nejm.org",
    "thelancet.com",
    "jamanetwork.com",
    "cochranelibrary.com",
    "arxiv.org",
    "academic.oup.com",
    "wiley.com",
    "cell.com",
    "nutrition.org",
    "ahajournals.org",
    "frontiersin.org",
    "mdpi.com",
    "biomedcentral.com",
    "plos.org",
    "cambridge.org",
    "tandfonline.com",
    "karger.com",
    "europepmc.org",
]

_PDF_URL_RE = re.compile(r"\.pdf(?:$|[?#])", re.IGNORECASE)


def _is_pdf_url(url: str) -> bool:
    return bool(_PDF_URL_RE.search(url))


def _classify_source(url: str) -> str:
    if _is_pdf_url(url):
        return "pdf"
    host = urlparse(url).netloc.lower()
    if any(domain in host for domain in ("pubmed", "pmc", "arxiv", "ncbi")):
        return "paper"
    if any(domain in host for domain in ("nih.gov", "who.int", "cdc.gov")):
        return "government"
    return "article"


def _normalize_result(item: dict[str, Any]) -> dict[str, Any]:
    url = str(item.get("url") or "")
    source_type = _classify_source(url)
    normalized: dict[str, Any] = {
        "title": item.get("title") or "",
        "url": url,
        "source_type": source_type,
        "score": item.get("score"),
        "published_date": item.get("published_date"),
        "snippet": (item.get("content") or "")[:500],
    }
    if source_type == "pdf":
        normalized["pdf_url"] = url
    return normalized


def search_research_literature(
    args: dict[str, Any],
    _ctx: CustomToolContext,
) -> str:
    """Execute Tavily search tuned for papers, PDFs, and credible articles."""
    query = str(args.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")

    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "TAVILY_API_KEY is not set. Add it to .env (see .env.example)."
        )

    from deep_research.tools.search_support import (
        check_tavily_quota,
        extract_citations_from_results,
        load_cached_search,
        record_tavily_call,
        save_cached_search,
        save_sources_artifact,
    )

    max_results = int(args.get("max_results") or 10)
    max_results = max(1, min(max_results, 20))
    time_range = str(args.get("time_range") or "year")
    source_mode = str(args.get("source_mode") or "academic").strip().lower()
    if source_mode not in {"academic", "general", "news"}:
        raise ValueError("source_mode must be academic, general, or news")

    allowed, remaining = check_tavily_quota()
    if not allowed:
        raise ValueError("Daily Tavily search quota exceeded. Try again tomorrow.")

    cached = load_cached_search(
        query,
        source_mode=source_mode,
        max_results=max_results,
        time_range=time_range,
    )
    if cached is not None:
        cached["cache_hit"] = True
        return json.dumps(cached, indent=2)

    from tavily import TavilyClient

    search_depth = str(args.get("search_depth") or "advanced").strip().lower()
    if search_depth not in {"basic", "advanced"}:
        search_depth = "advanced"

    search_kwargs: dict[str, Any] = {
        "query": query,
        "search_depth": search_depth,
        "max_results": max_results,
        "time_range": time_range,
        "include_answer": False,
        "include_raw_content": False,
    }

    if source_mode == "news":
        search_kwargs["topic"] = "news"
    else:
        search_kwargs["topic"] = "general"
        if source_mode == "academic":
            search_kwargs["include_domains"] = CREDIBLE_RESEARCH_DOMAINS

    client = TavilyClient(api_key=api_key)
    response = client.search(**search_kwargs)
    record_tavily_call()

    results = [_normalize_result(item) for item in response.get("results", [])]
    pdf_urls = [r["pdf_url"] for r in results if r.get("pdf_url")]
    citations = extract_citations_from_results(results)
    sources_path = save_sources_artifact(citations)

    payload = {
        "query": query,
        "source_mode": source_mode,
        "search_depth": search_depth,
        "answer": response.get("answer"),
        "result_count": len(results),
        "pdf_urls": pdf_urls,
        "results": results,
        "citations_count": len(citations),
        "sources_path": sources_path,
        "quota_remaining": max(0, remaining - 1),
        "cache_hit": False,
        "usage_note": (
            "Use download_research_pdfs with pdf_urls (or direct PDF links from "
            "results) to save papers locally. Call verify_sources to check link health."
        ),
    }
    save_cached_search(
        query,
        source_mode=source_mode,
        max_results=max_results,
        time_range=time_range,
        payload=payload,
    )
    return json.dumps(payload, indent=2)


SEARCH_RESEARCH_LITERATURE_TOOL = CustomTool(
    execute=search_research_literature,
    description=(
        "Search for credible sources on any research topic using the Tavily API. "
        "Use source_mode=academic for papers/institutions, general for any field, "
        "news for current events. Returns pdf_urls when direct PDF links are found."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Research question or topic to search for.",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum results to return (1-20, default 10).",
                "minimum": 1,
                "maximum": 20,
            },
            "time_range": {
                "type": "string",
                "description": "Recency filter: day, week, month, or year (default year).",
                "enum": ["day", "week", "month", "year"],
            },
            "source_mode": {
                "type": "string",
                "enum": ["academic", "general", "news"],
                "description": (
                    "academic=peer-reviewed/gov domains; general=any field; news=current events"
                ),
            },
            "search_depth": {
                "type": "string",
                "enum": ["basic", "advanced"],
                "description": "Tavily search depth (default advanced).",
            },
        },
        "required": ["query"],
    },
)
