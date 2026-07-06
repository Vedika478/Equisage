"""
Indian stock news from RSS feeds + NSE official announcements.
No API key required. No paid service. Real-time data.
"""

import feedparser
import requests
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Optional
import re
import time

# ── RSS Feed Registry ─────────────────────────────────────────────────────────

INDIAN_RSS_FEEDS = [
    {
        "name": "Economic Times Markets",
        "url": "https://economictimes.indiatimes.com/markets/rss.cms",
        "weight": 3,  # Higher weight = more trusted source
    },
    {
        "name": "Moneycontrol",
        "url": "https://www.moneycontrol.com/rss/latestnews.xml",
        "weight": 3,
    },
    {
        "name": "Business Standard Markets",
        "url": "https://www.business-standard.com/rss/markets-106.rss",
        "weight": 3,
    },
    {
        "name": "Mint Markets",
        "url": "https://www.livemint.com/rss/markets",
        "weight": 2,
    },
    {
        "name": "Financial Express Markets",
        "url": "https://www.financialexpress.com/market/feed/",
        "weight": 2,
    },
    {
        "name": "Hindu Business Line",
        "url": "https://www.thehindubusinessline.com/markets/?service=rss",
        "weight": 2,
    },
]

# ── Company Name Aliases ──────────────────────────────────────────────────────
# RSS news uses company names, not ticker symbols. Map both.

COMPANY_ALIASES = {
    "HDFCBANK":    ["hdfc bank", "hdfc bank ltd", "hdfc banking"],
    "ICICIBANK":   ["icici bank", "icici bank ltd"],
    "SBIN":        ["state bank", "sbi", "state bank of india"],
    "KOTAKBANK":   ["kotak bank", "kotak mahindra bank", "kotak"],
    "AXISBANK":    ["axis bank", "axis bank ltd"],
    "TCS":         ["tcs", "tata consultancy", "tata consultancy services"],
    "INFY":        ["infosys", "infy", "infosys ltd"],
    "WIPRO":       ["wipro", "wipro ltd", "wipro technologies"],
    "HCLTECH":     ["hcl tech", "hcl technologies", "hcltech"],
    "TECHM":       ["tech mahindra", "techm"],
    "RELIANCE":    ["reliance", "reliance industries", "ril", "jio"],
    "CHOLAFIN":    ["chola", "cholamandalam", "cholafin"],
    "BAJFINANCE":  ["bajaj finance", "bajaj fin", "bajfinance"],
    "HINDUNILVR":  ["hindustan unilever", "hul", "unilever india"],
    "ITC":         ["itc ltd", "itc limited", "itc"],
    "SUNPHARMA":   ["sun pharma", "sun pharmaceutical", "sunpharma"],
    "DRREDDY":     ["dr reddy", "dr. reddy", "drreddys"],
    "TATAMOTORS":  ["tata motors", "tatamotors", "tata motor"],
    "MARUTI":      ["maruti", "maruti suzuki", "maruti udyog"],
    "ZOMATO":      ["zomato", "zomato ltd"],
    "ADANIENT":    ["adani enterprises", "adani group", "adanient"],
    "LTIM":        ["ltimindtree", "lti mindtree", "larsen toubro infotech"],
    "ONGC":        ["ongc", "oil and natural gas", "oil & natural gas"],
    "BAJAJFINSV":  ["bajaj finserv", "bajaj financial services"],
    "NESTLEIND":   ["nestle india", "nestle", "nestlé india"],
    "BRITANNIA":   ["britannia", "britannia industries"],
    "DABUR":       ["dabur", "dabur india"],
    "CIPLA":       ["cipla", "cipla ltd"],
    "DIVISLAB":    ["divi's", "divis lab", "divi laboratories"],
}

# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class NewsArticle:
    title: str
    source: str
    published_raw: str
    summary: str = ""
    url: str = ""
    relevance_score: float = 0.0  # Higher = more relevant to the stock
    is_nse_announcement: bool = False

@dataclass
class NewsBundle:
    articles: list[NewsArticle] = field(default_factory=list)
    total_found: int = 0
    sources_checked: int = 0
    has_nse_announcement: bool = False
    fetch_error: Optional[str] = None

# ── Core Fetchers ─────────────────────────────────────────────────────────────

def _get_search_terms(symbol: str) -> list[str]:
    """Get all search terms for a symbol including aliases."""
    base = symbol.upper().replace(".NS", "").replace(".BO", "")
    terms = [base.lower()]
    
    if base in COMPANY_ALIASES:
        terms.extend(COMPANY_ALIASES[base])
    
    return terms

def _score_relevance(title: str, summary: str, search_terms: list[str]) -> float:
    """
    Score how relevant an article is to the stock.
    Title match = higher score than body match.
    Exact symbol/name match = higher than partial.
    """
    title_lower = title.lower()
    summary_lower = summary.lower()
    score = 0.0
    
    for term in search_terms:
        if term in title_lower:
            # Title match is 3x more valuable than summary match
            score += 3.0
            # Bonus for exact word boundary match (not just substring)
            if re.search(r'\b' + re.escape(term) + r'\b', title_lower):
                score += 1.0
        if term in summary_lower:
            score += 1.0
    
    return score

def fetch_rss_news(symbol: str, max_articles: int = 8) -> list[NewsArticle]:
    """
    Fetch relevant news for a stock from multiple Indian RSS feeds.
    Filters by relevance, deduplicates, returns top articles.
    """
    search_terms = _get_search_terms(symbol)
    all_articles = []
    seen_hashes = set()
    sources_fetched = 0

    for feed_info in INDIAN_RSS_FEEDS:
        try:
            # feedparser handles encoding, redirects, and malformed XML gracefully
            feed = feedparser.parse(
                feed_info["url"],
                agent="EquiSage/1.0 (Research Platform; +https://equisage.app)"
            )

            if feed.bozo and not feed.entries:
                continue  # Completely broken feed, skip

            sources_fetched += 1

            for entry in feed.entries[:50]:  # Check top 50 from each feed
                title = entry.get("title", "").strip()
                summary = (
                    entry.get("summary", "") or
                    entry.get("description", "") or
                    entry.get("content", [{}])[0].get("value", "") if entry.get("content") else ""
                ).strip()

                if not title:
                    continue

                # Deduplicate by title hash
                title_hash = hashlib.md5(title.lower().encode()).hexdigest()
                if title_hash in seen_hashes:
                    continue
                seen_hashes.add(title_hash)

                # Score relevance
                relevance = _score_relevance(title, summary, search_terms)
                if relevance == 0:
                    continue  # Not relevant to this stock at all

                # Parse published date
                published = (
                    entry.get("published", "") or
                    entry.get("updated", "") or
                    entry.get("created", "") or
                    "Recent"
                )

                all_articles.append(NewsArticle(
                    title=title,
                    source=feed_info["name"],
                    published_raw=published,
                    summary=summary[:400] if summary else "",
                    url=entry.get("link", ""),
                    relevance_score=relevance * feed_info["weight"],
                ))

        except Exception:
            continue  # Never crash on a single bad feed

    # Sort by relevance score descending, return top N
    all_articles.sort(key=lambda a: a.relevance_score, reverse=True)
    return all_articles[:max_articles]


def fetch_nse_announcements(symbol: str, max_items: int = 3) -> list[NewsArticle]:
    """
    Fetch official corporate announcements from NSE.
    Free, no API key, authoritative source.
    Returns recent company announcements (results, dividends, board meetings, etc.)
    """
    base_symbol = symbol.upper().replace(".NS", "").replace(".BO", "")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
    }

    articles = []

    try:
        # NSE requires a session cookie — get it first
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=8)
        time.sleep(0.5)  # Respect NSE servers

        # Fetch corporate announcements
        url = f"https://www.nseindia.com/api/corp-info?symbol={base_symbol}&corpType=announcements&market=equities"
        response = session.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            announcements = data.get("data", [])

            for ann in announcements[:max_items]:
                subject = ann.get("subject", "") or ann.get("desc", "")
                date = ann.get("date", "") or ann.get("bm_date", "")
                attachment = ann.get("attchmntFile", "")
                pdf_url = f"https://nsearchives.nseindia.com/corporate/{attachment}" if attachment else ""

                if subject:
                    articles.append(NewsArticle(
                        title=f"[NSE Official] {subject}",
                        source="NSE Corporate Announcements",
                        published_raw=date,
                        summary=f"Official NSE corporate announcement for {base_symbol}.",
                        url=pdf_url,
                        relevance_score=10.0,  # Always maximally relevant
                        is_nse_announcement=True,
                    ))

    except Exception:
        pass  # NSE API is optional — RSS feeds are the primary source

    return articles


def fetch_news_for_stock(symbol: str) -> NewsBundle:
    """
    Master news fetch function. Call this from your data pipeline.
    Combines RSS feeds + NSE announcements.
    Returns NewsBundle with ranked, deduplicated articles.
    """
    try:
        # Run both fetches
        rss_articles = fetch_rss_news(symbol, max_articles=8)
        nse_articles = fetch_nse_announcements(symbol, max_items=3)

        # NSE announcements go first (highest relevance), then RSS
        all_articles = nse_articles + rss_articles

        # Final deduplication pass
        seen = set()
        unique_articles = []
        for article in all_articles:
            key = hashlib.md5(article.title.lower().encode()).hexdigest()
            if key not in seen:
                seen.add(key)
                unique_articles.append(article)

        return NewsBundle(
            articles=unique_articles[:10],
            total_found=len(unique_articles),
            sources_checked=len(INDIAN_RSS_FEEDS),
            has_nse_announcement=len(nse_articles) > 0,
        )

    except Exception as e:
        return NewsBundle(fetch_error=str(e))


# ── Format for LLM Prompt ─────────────────────────────────────────────────────

def format_news_for_prompt(bundle: NewsBundle) -> str:
    """Format news bundle into clean text for the master analysis prompt."""
    if not bundle.articles:
        return "No recent news found in Indian business press for this stock."

    lines = [f"Recent news ({bundle.total_found} articles found across {bundle.sources_checked} Indian sources):"]

    for i, article in enumerate(bundle.articles[:8], 1):
        lines.append(f"\n{i}. [{article.source}] {article.title}")
        if article.published_raw and article.published_raw != "Recent":
            lines.append(f"   Published: {article.published_raw}")
        if article.summary:
            lines.append(f"   {article.summary[:300]}")
        if article.is_nse_announcement:
            lines.append(f"   ⚡ OFFICIAL NSE ANNOUNCEMENT")

    return "\n".join(lines)
