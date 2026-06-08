import json
import re
from typing import Optional

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

TIMEOUT = 15
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def fetch_page(url: str) -> Optional[str]:
    try:
        resp = httpx.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def extract_price(html: str, url: str = "") -> Optional[float]:
    if not html:
        return None
    return (
        _try_jsonld(html)
        or _try_meta(html)
        or _try_common_selectors(html)
        or _try_regex(html)
    )


def extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        return re.sub(r"\s+", " ", title)[:200]
    return ""


def _try_jsonld(html: str) -> Optional[float]:
    for m in re.finditer(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.IGNORECASE | re.DOTALL,
    ):
        try:
            data = json.loads(m.group(1))
            for item in data if isinstance(data, list) else [data]:
                off = item.get("offers", item)
                if isinstance(off, list):
                    off = off[0]
                price = off.get("price")
                if price:
                    return float(price)
        except (json.JSONDecodeError, (ValueError, TypeError)):
            continue
    return None


def _try_meta(html: str) -> Optional[float]:
    patterns = [
        r'<meta[^>]+property="(?:product:)?price:amount"[^>]+content="([^"]+)"',
        r'<meta[^>]+itemprop="price"[^>]+content="([^"]+)"',
        r'<meta[^>]+name="(?:twitter:data1|price)"[^>]+content="([^"]+)"',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            try:
                return _clean_price(m.group(1))
            except ValueError:
                continue
    return None


def _try_common_selectors(html: str) -> Optional[float]:
    patterns = [
        r'class="[^"]*price[^"]*"[^>]*>[^<]*\$?([0-9,]+\.?[0-9]{0,2})',
        r'class="[^"]*price[^"]*"[^>]*>\s*<[^>]+>\s*\$?([0-9,]+\.?[0-9]{0,2})',
        r'id="[^"]*price[^"]*"[^>]*>\$?([0-9,]+\.?[0-9]{0,2})',
        r'itemprop="price"[^>]*>\$?([0-9,]+\.?[0-9]{0,2})',
        r'data-price="([0-9,]+\.?[0-9]{0,2})"',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            try:
                return _clean_price(m.group(1))
            except ValueError:
                continue
    return None


def _try_regex(html: str) -> Optional[float]:
    pat = r'\$?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)'
    candidates = re.findall(pat, html)
    for c in candidates[:30]:
        try:
            val = _clean_price(c)
            if 0.5 < val < 999999:
                return val
        except ValueError:
            continue
    return None


def _clean_price(s: str) -> float:
    return float(s.replace(",", "").replace("$", "").strip())


def scrape(url: str) -> Optional[dict]:
    html = fetch_page(url)
    if not html:
        return None
    price = extract_price(html, url)
    if price is None:
        return None
    return {
        "url": url,
        "title": extract_title(html) or url,
        "price": price,
        "currency": "USD",
    }
