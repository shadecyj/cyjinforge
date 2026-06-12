#!/usr/bin/env python3
"""
AI Radar — 每日 AI 前沿资讯自动采集脚本
采集 10 个数据源，去重，关键词标记，输出 data.json
"""

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from collections import OrderedDict
from typing import Any
from urllib.parse import urljoin

import requests
import feedparser

# ============================================================
# 配置
# ============================================================

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "data.json")
ARCHIVE_DIR = os.path.join(OUTPUT_DIR, "archive")
REQUEST_TIMEOUT = 30
USER_AGENT = "AI-Radar/1.0 (bot; daily academic/news aggregator)"

# 伴侣聚焦关键词
COMPANION_KEYWORDS = [
    # 中文 — 伴侣
    "情感计算", "对话系统", "个性化", "人机交互", "情感识别", "情感分析",
    "情绪感知", "共情", "陪伴", "社交机器人", "人格", "性格",
    # English — companion
    "empathy", "dialogue system", "dialogue", "dialog system", "dialog",
    "companion", "personalization", "personalisation",
    "affective computing", "affective",
    "conversational AI", "conversational agent",
    "multimodal interaction", "multimodal",
    "human-robot interaction", "social robot",
    "emotional AI", "emotional",
    "personality", "rapport", "trust", "relationship",
    "human-computer interaction", "human-agent interaction",
    # consciousness / self
    "AI意识", "自我进化", "自我思考", "自我反省", "机器意识",
    "意识涌现", "自我意识", "反思", "内省",
    "emergence", "self-awareness", "self-aware",
    "self-evolution", "self-evolving", "self-evolve",
    "self-reflection", "self-reflective", "self-reflect",
    "introspection", "introspective",
    "metacognition", "metacognitive",
    "consciousness", "conscious",
    "sentience", "sentient",
    "autonomous agent", "autonomous",
    "agency",
    "self-improving", "self-improvement",
    "recursive self-improvement",
    "theory of mind",
    "self-model", "self model",
    "self-play", "self play",
    "intrinsic motivation", "curiosity-driven", "curiosity driven",
    "free energy principle",
    "active inference",
    "predictive processing",
    "global workspace",
    "integrated information",
]

GENERAL_FRONTIER_KEYWORDS = [
    "LLM", "large language model", "large language models",
    "AGI", "artificial general intelligence",
    "reasoning", "chain-of-thought", "chain of thought",
    "alignment", "RLHF", "RL" "reinforcement learning",
    "agent", "multi-agent", "tool use", "function calling",
    "multimodal", "foundation model", "transformer",
    "RAG", "retrieval augmented",
    "world model", "planning",
    "diffusion", "generative",
    "fine-tuning", "fine tuning", "instruction tuning",
    "zero-shot", "few-shot", "in-context learning",
    "scaling law", "emergent ability",
    "knowledge distillation", "pruning", "quantization",
    "mixture of experts",
    "long context", "long-context",
    "safety", "hallucination", "factuality",
    "watermark", "detection",
    " embodied", "robot",
]


def make_id(title: str, url: str) -> str:
    return hashlib.sha256(f"{title}|{url}".encode()).hexdigest()[:12]


def tag_entry(title: str, summary: str, categories_str: str = "") -> dict:
    """Return tags and spotlight boolean for an entry."""
    text = f"{title} {summary} {categories_str}".lower()
    tags = set()
    spotlight = False
    for kw in COMPANION_KEYWORDS:
        if kw.lower() in text:
            spotlight = True
            tags.add("spotlight")
            break
    for kw in GENERAL_FRONTIER_KEYWORDS:
        if kw.lower() in text:
            tags.add(kw.lower())
    return {"tags": sorted(tags), "spotlight": spotlight}


def safe_get(url: str, **kwargs) -> requests.Response | None:
    """GET with retries, return None on failure."""
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT,
                                headers={"User-Agent": USER_AGENT}, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt == 2:
                print(f"  [WARN] Failed to fetch {url}: {e}")
                return None
            time.sleep(2 ** attempt)
    return None


# ============================================================
# 数据源采集函数
# ============================================================

def fetch_arxiv(query: str = "cat:cs.AI OR cat:cs.CL OR cat:cs.HC",
                max_results: int = 50) -> list[dict]:
    """Fetch recent papers from arXiv API."""
    entries = []
    url = "http://export.arxiv.org/api/query"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    resp = safe_get(url, params=params)
    if not resp:
        return entries

    feed = feedparser.parse(resp.text)
    for item in feed.entries:
        title = item.title.strip().replace("\n", " ")
        summary = item.summary.strip().replace("\n", " ")[:500]
        link = item.link
        published = item.published
        authors = [a.name for a in item.authors] if hasattr(item, "authors") else []
        cats = [t.term for t in item.tags] if hasattr(item, "tags") else []
        tid = make_id(title, link)
        meta = tag_entry(title, summary, " ".join(cats))
        entries.append({
            "id": tid,
            "title": title,
            "url": link,
            "source": "arxiv",
            "category": "paper",
            "date": published[:10],
            "summary": summary[:300],
            "authors": authors[:5],
            "tags": meta["tags"],
            "spotlight": meta["spotlight"],
        })
    print(f"  arXiv: {len(entries)} papers")
    return entries


def fetch_semantic_scholar(query: str = "artificial intelligence",
                           limit: int = 30) -> list[dict]:
    """Fetch recent papers from Semantic Scholar API (no key needed for basic)."""
    entries = []
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": limit,
        "sort": "publicationDate:desc",
        "fields": "title,url,abstract,publicationDate,authors,year",
    }
    resp = safe_get(url, params=params)
    if not resp:
        return entries
    data = resp.json()
    for paper in data.get("data", []):
        title = paper.get("title", "").strip()
        p_url = paper.get("url", "")
        if not title or not p_url:
            continue
        summary = paper.get("abstract", "") or ""
        date_str = paper.get("publicationDate", "") or ""
        authors = [a.get("name", "") for a in paper.get("authors", [])]
        tid = make_id(title, p_url)
        meta = tag_entry(title, summary)
        entries.append({
            "id": tid,
            "title": title,
            "url": p_url,
            "source": "semantic-scholar",
            "category": "paper",
            "date": date_str,
            "summary": summary[:300],
            "authors": authors[:5],
            "tags": meta["tags"],
            "spotlight": meta["spotlight"],
        })
    print(f"  Semantic Scholar: {len(entries)} papers")
    return entries


def fetch_hn(query: str = "AI|LLM|GPT|agent|artificial intelligence",
             max_items: int = 40) -> list[dict]:
    """Fetch Hacker News recent AI-related items via Algolia search."""
    entries = []
    today = datetime.now(timezone.utc)
    cutoff = (today - timedelta(days=2)).strftime("%Y-%m-%d")

    # Search HN for AI topics
    url = "https://hn.algolia.com/api/v1/search_by_date"
    for q in ["AI", "LLM", "GPT", "agent", "artificial intelligence", "machine learning",
              "consciousness", "self-improving"]:
        params = {
            "query": q,
            "tags": "story",
            "hitsPerPage": 10,
            "numericFilters": f"created_at_i>{int(time.time()) - 172800}",
        }
        resp = safe_get(url, params=params)
        if not resp:
            continue
        data = resp.json()
        for hit in data.get("hits", []):
            title = hit.get("title", "").strip()
            link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            if not title:
                continue
            tid = make_id(title, link)
            meta = tag_entry(title, "")
            entries.append({
                "id": tid,
                "title": title,
                "url": link,
                "source": "hacker-news",
                "category": "discussion",
                "date": hit.get("created_at", "")[:10],
                "summary": f"Points: {hit.get('points', 0)}, Comments: {hit.get('num_comments', 0)}",
                "authors": [],
                "tags": meta["tags"],
                "spotlight": meta["spotlight"],
            })
    print(f"  Hacker News: {len(entries)} items")
    return entries


def fetch_github_trending(languages: list[str] | None = None,
                          since: str = "daily") -> list[dict]:
    """Fetch GitHub Trending repos by scraping the page (no API key needed)."""
    entries = []
    if languages is None:
        languages = ["", "python", "jupyter-notebook", "rust"]

    for lang in languages:
        lang_param = f"/{lang}" if lang else ""
        url = f"https://github.com/trending{lang_param}?since={since}"
        resp = safe_get(url)
        if not resp:
            continue

        # Simple regex-based extraction (robust enough for trending page)
        html = resp.text
        # Extract repo blocks
        blocks = re.split(r'<article\s+class="Box-row"', html)[1:]
        for block in blocks:
            # Repo name: /owner/repo
            repo_match = re.search(r'href="(/([^/]+)/([^"]+))"', block)
            if not repo_match:
                continue
            owner = repo_match.group(2)
            name = repo_match.group(3)
            full_name = f"{owner}/{name}"
            link = f"https://github.com{repo_match.group(1)}"

            # Description
            desc_match = re.search(r'<p\s+class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', block, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ""
            description = re.sub(r'<[^>]+>', '', description)

            # Language
            lang_match = re.search(r'programmingLanguage">([^<]+)<', block)
            repo_language = lang_match.group(1) if lang_match else ""

            # Stars
            stars_match = re.search(r'(\d[\d,]*)\s*stars today', block)
            stars_today = stars_match.group(1) if stars_match else "0"

            tid = make_id(full_name, link)
            meta = tag_entry(f"{full_name} {description}", repo_language)

            entries.append({
                "id": tid,
                "title": full_name,
                "url": link,
                "source": "github-trending",
                "category": "project",
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "summary": description[:300],
                "authors": [owner],
                "tags": meta["tags"] + ([repo_language] if repo_language else []),
                "spotlight": meta["spotlight"],
                "stars_today": stars_today,
            })
        if lang:
            print(f"  GitHub Trending/{lang}: {len(entries)} repos (cumulative)")

    print(f"  GitHub Trending: {len(entries)} repos total")
    return entries


def fetch_huggingface_papers(limit: int = 30) -> list[dict]:
    """Fetch daily papers from Hugging Face."""
    entries = []
    url = "https://huggingface.co/api/daily_papers"
    resp = safe_get(url)
    if not resp:
        return entries

    papers = resp.json()
    for paper in papers[:limit]:
        title = paper.get("title", "").strip()
        paper_url = f"https://huggingface.co/papers/{paper.get('paper', {}).get('id', '')}"
        if not title:
            continue
        summary = paper.get("paper", {}).get("summary", "") or ""
        upvotes = paper.get("upvotes", 0)
        tid = make_id(title, paper_url)
        meta = tag_entry(title, summary)
        entries.append({
            "id": tid,
            "title": title,
            "url": paper_url,
            "source": "huggingface",
            "category": "paper",
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "summary": summary[:300],
            "authors": [],
            "tags": meta["tags"],
            "spotlight": meta["spotlight"],
            "upvotes": upvotes,
        })
    print(f"  Hugging Face: {len(entries)} papers")
    return entries


def fetch_paperswithcode() -> list[dict]:
    """Fetch trending papers from Papers With Code."""
    entries = []
    url = "https://paperswithcode.com/api/v1/papers/"
    params = {"ordering": "-pub_date", "items_per_page": 30}
    resp = safe_get(url, params=params)
    if not resp:
        return entries
    data = resp.json()
    for paper in data.get("results", []):
        title = paper.get("title", "").strip()
        p_url = paper.get("url_abs", "") or paper.get("url_pdf", "")
        if not title or not p_url:
            continue
        summary = paper.get("abstract", "") or ""
        pub_date = paper.get("pub_date", "") or ""
        tid = make_id(title, p_url)
        meta = tag_entry(title, summary)
        entries.append({
            "id": tid,
            "title": title,
            "url": p_url,
            "source": "paperswithcode",
            "category": "paper",
            "date": pub_date,
            "summary": summary[:300],
            "authors": [],
            "tags": meta["tags"],
            "spotlight": meta["spotlight"],
        })
    print(f"  Papers With Code: {len(entries)} papers")
    return entries


def fetch_rss_feeds() -> list[dict]:
    """Fetch from RSS feeds: tech blogs and Chinese AI media."""
    entries = []
    feeds = [
        ("MIT Tech Review AI", "https://www.technologyreview.com/feed/"),
        ("TechCrunch AI", "https://techcrunch.com/tag/artificial-intelligence/feed/"),
        ("机器之心", "https://www.jiqizhixin.com/rss"),
        ("量子位", "https://www.qbitai.com/feed"),
        ("Reddit ML", "https://www.reddit.com/r/MachineLearning/.rss"),
        ("Reddit AI", "https://www.reddit.com/r/artificial/.rss"),
    ]

    for feed_name, feed_url in feeds:
        resp = safe_get(feed_url)
        if not resp:
            print(f"  RSS {feed_name}: failed")
            continue
        feed = feedparser.parse(resp.text)
        count = 0
        for item in feed.entries[:15]:
            title = item.title.strip()
            link = item.link
            if not title or not link:
                continue
            summary = item.get("summary", "") or item.get("description", "") or ""
            summary = re.sub(r'<[^>]+>', '', summary).strip()[:300]
            published = ""
            if hasattr(item, "published_parsed") and item.published_parsed:
                try:
                    published = f"{item.published_parsed[0]:04d}-{item.published_parsed[1]:02d}-{item.published_parsed[2]:02d}"
                except Exception:
                    published = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            else:
                published = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            tid = make_id(title, link)
            meta = tag_entry(title, summary)
            entries.append({
                "id": tid,
                "title": title,
                "url": link,
                "source": f"rss-{feed_name.lower().replace(' ', '-')}",
                "category": "news",
                "date": published,
                "summary": summary,
                "authors": [],
                "tags": meta["tags"],
                "spotlight": meta["spotlight"],
            })
            count += 1
        print(f"  RSS {feed_name}: {count} items")

    print(f"  RSS total: {len(entries)} items")
    return entries


# ============================================================
# 主流程
# ============================================================

def deduplicate(entries: list[dict]) -> list[dict]:
    """Remove duplicates by id, keep first occurrence."""
    seen = OrderedDict()
    for e in entries:
        eid = e.get("id", make_id(e["title"], e["url"]))
        if eid not in seen:
            e["id"] = eid
            seen[eid] = e
    return list(seen.values())


def main():
    print("=" * 50)
    print(f"AI Radar Fetch — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 50)

    all_entries = []

    # Run all fetchers (fail gracefully per source)
    fetchers = [
        ("arXiv", fetch_arxiv),
        ("Semantic Scholar", fetch_semantic_scholar),
        ("Hugging Face", fetch_huggingface_papers),
        ("Papers With Code", fetch_paperswithcode),
        ("GitHub Trending", fetch_github_trending),
        ("Hacker News", fetch_hn),
        ("RSS Feeds", fetch_rss_feeds),
    ]

    for name, func in fetchers:
        print(f"\n[{name}]")
        try:
            entries = func()
            all_entries.extend(entries)
        except Exception as e:
            print(f"  [ERROR] {name} failed: {e}")

    # Deduplicate
    print(f"\n{'=' * 50}")
    print(f"Total before dedup: {len(all_entries)}")
    all_entries = deduplicate(all_entries)
    print(f"Total after dedup: {len(all_entries)}")

    # Sort by date desc, spotlight first
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    all_entries.sort(key=lambda e: (
        not e.get("spotlight", False),
        e.get("date", today_str),
        e.get("title", ""),
    ), reverse=False)

    # Stats
    papers = [e for e in all_entries if e["category"] == "paper"]
    projects = [e for e in all_entries if e["category"] == "project"]
    news = [e for e in all_entries if e["category"] == "news"]
    discussions = [e for e in all_entries if e["category"] == "discussion"]
    spotlight = [e for e in all_entries if e["spotlight"]]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "total": len(all_entries),
            "papers": len(papers),
            "projects": len(projects),
            "news": len(news),
            "discussions": len(discussions),
            "spotlight": len(spotlight),
        },
        "entries": all_entries,
    }

    # Write data.json
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Written {len(all_entries)} entries to {OUTPUT_FILE}")
    print(f"   Stats: {output['stats']}")

    # Archive daily snapshot
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    archive_file = os.path.join(ARCHIVE_DIR, f"{today_str}.json")
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"📦 Archived to {archive_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
