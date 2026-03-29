"""
自然资源部政务站点正文页 URL：/YYYYMM/tYYYYMMDD_<id>.html（如 /202603/t20260327_2917437.html）。

适用于 gi.mnr.gov.cn（政府信息公开）与 f.mnr.gov.cn（政策法规库）。详情页内常含「相关文章」等相对链接，可据此做链接发现。
"""

from __future__ import annotations

import re
from typing import List, Tuple
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

# 路径形如 /202603/t20260327_2917437.html
GI_ARTICLE_PATH_RE = re.compile(
    r"/\d{6}/t\d{8}_\d+\.html?$",
    re.IGNORECASE,
)

# 使用相同正文路径模式的 MNR 子站（hostname 不含端口）
_MNR_ARTICLE_HOSTS: Tuple[str, ...] = ("gi.mnr.gov.cn", "f.mnr.gov.cn")


def _mnr_article_hostname(netloc: str) -> str:
    h = (netloc or "").lower()
    if ":" in h:
        h = h.split(":", 1)[0]
    if h.startswith("www."):
        h = h[4:]
    return h


def is_gi_article_url(url: str) -> bool:
    """是否为 gi / f 站点常见的正文页路径（与公开库相同 URL 模式）。"""
    parsed = urlparse(url)
    if _mnr_article_hostname(parsed.netloc) not in _MNR_ARTICLE_HOSTS:
        return False
    path = parsed.path
    return GI_ARTICLE_PATH_RE.search(path) is not None


def extract_gi_article_urls(html: str, page_url: str) -> List[str]:
    """从 HTML 中解析正文链接并规范为绝对 URL（去重）。"""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    out: List[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()
        if not href:
            continue
        low = href.lower()
        if low.startswith("javascript") or low.startswith("#"):
            continue
        full = urljoin(page_url, href)
        if not is_gi_article_url(full):
            continue
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out
