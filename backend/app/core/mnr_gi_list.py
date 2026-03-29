"""
自然资源部 gi.mnr.gov.cn 公开目录列表直爬：按分类 URL 逐页抓取，不依赖 search.mnr.gov.cn。
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# 主题分类下列表页常见路径（与站点公开目录 iframe 一致）
GI_LIST_PATH_PREFIX = "gkml2018/1285"


def build_category_list_url(
    base_url: str,
    category_code: str,
    index_file: str = "index_4724.html",
) -> str:
    """生成分类下第一页列表 URL。"""
    root = base_url.rstrip("/") + "/"
    path = f"{GI_LIST_PATH_PREFIX}/{category_code}/{index_file}"
    return urljoin(root, path)


def _normalize_url(url: str) -> str:
    """用于比较是否同一页（忽略 fragment）。"""
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, p.path, p.params, p.query, ""))


def same_gi_list_page(a: str, b: str) -> bool:
    """判断两个列表页 URL 是否视为同一页。"""
    return _normalize_url(a) == _normalize_url(b)


def find_next_list_page_url(soup: BeautifulSoup, current_url: str) -> Optional[str]:
    """从列表页 HTML 中解析「下一页」链接。

    政务站点常见：文字「下一页」、class、或 index_xxx_N.html 递增。
    """
    current_norm = _normalize_url(current_url)

    # 1) 明确「下一页」
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).replace(" ", "")
        title = (a.get("title") or "").strip()
        if "下一页" in text or "下一页" in title:
            href = (a.get("href") or "").strip()
            if not href:
                continue
            low = href.lower()
            if low.startswith("javascript") or low.startswith("#"):
                continue
            nxt = urljoin(current_url, href)
            if _normalize_url(nxt) != current_norm:
                return nxt

    # 2) 分页区域常见 class
    for sel in ("page", "page_div", "pagebox", "fenye", "flip"):
        box = soup.find(class_=re.compile(sel, re.I))
        if not box:
            continue
        for a in box.find_all("a", href=True):
            text = a.get_text(strip=True).replace(" ", "")
            if "下一" in text or text in ("下页", "后页"):
                href = (a.get("href") or "").strip()
                if not href:
                    continue
                low = href.lower()
                if low.startswith("javascript") or low.startswith("#"):
                    continue
                nxt = urljoin(current_url, href)
                if _normalize_url(nxt) != current_norm:
                    return nxt

    # 3) 同目录 index_数字_页码.html 尝试 +1（部分模板第二页起带后缀）
    path = urlparse(current_url).path
    m = re.search(r"(index_\d+)_(\d+)(\.html?)$", path, re.I)
    if m:
        prefix, num_s, suf = m.group(1), m.group(2), m.group(3)
        nxt_num = int(num_s) + 1
        new_path = re.sub(
            r"(index_\d+)_(\d+)(\.html?)$",
            f"{prefix}_{nxt_num}{suf}",
            path,
            count=1,
            flags=re.I,
        )
        p = urlparse(current_url)
        guess = urlunparse((p.scheme, p.netloc, new_path, "", "", ""))
        if guess != current_url:
            return guess

    # 4) 第一页 index_4724.html（无 _页码 后缀）-> index_4724_2.html
    if re.search(r"index_\d+\.html?$", path, re.I) and not re.search(
        r"index_\d+_\d+\.html?$", path, re.I
    ):
        new_path2 = re.sub(
            r"(index_\d+)(\.html?)$",
            r"\1_2\2",
            path,
            flags=re.I,
        )
        if new_path2 != path:
            p2 = urlparse(current_url)
            guess2 = urlunparse((p2.scheme, p2.netloc, new_path2, "", "", ""))
            if _normalize_url(guess2) != current_norm:
                return guess2

    return None
