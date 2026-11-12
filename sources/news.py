from urllib.parse import quote_plus

import feedparser
import yfinance as yf

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"


def _fetch_rss(query, limit):
    feed = feedparser.parse(GOOGLE_NEWS_RSS.format(query=quote_plus(query)))
    articles = []
    for entry in feed.entries[:limit]:
        articles.append(
            {
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": entry.get("source", {}).get("title", "Google News"),
            }
        )
    return articles


def _yfinance_news(ticker, limit):
    articles = []
    try:
        for item in yf.Ticker(ticker).news or []:
            content = item.get("content", item)
            title = (content.get("title") or "").strip()
            if not title:
                continue
            link = (content.get("canonicalUrl") or {}).get("url") or content.get("link", "")
            provider = (content.get("provider") or {}).get("displayName", "Yahoo Finance")
            published = content.get("pubDate") or content.get("displayTime", "")
            articles.append({"title": title, "link": link, "published": published, "source": provider})
            if len(articles) >= limit:
                break
    except Exception:
        pass
    return articles


def fetch_company_news(ticker, name, limit=12):
    """Recent headlines for a company, combining Yahoo Finance with a Google News search fallback."""
    articles = _yfinance_news(ticker, limit)
    if len(articles) < limit:
        seen = {article["title"] for article in articles}
        for article in _fetch_rss(f"{name} stock", limit - len(articles)):
            if article["title"] not in seen:
                articles.append(article)
    return articles[:limit]


def fetch_macro_news(topics, limit_per_topic=6):
    """Broad market, policy and geopolitical headlines, independent of any single company."""
    articles = []
    for topic in topics:
        articles.extend(_fetch_rss(topic, limit_per_topic))
    return articles
