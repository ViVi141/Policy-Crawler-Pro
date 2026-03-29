"""尝试从 gi 首页解析 gkml 链接并请求第一页（调试用）。"""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import urljoin

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)
os.chdir(BACKEND_ROOT)

import requests  # noqa: E402
from bs4 import BeautifulSoup  # noqa: E402


def main() -> int:
    base = "https://gi.mnr.gov.cn/"
    index_url = urljoin(base, "index.html")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        )
    }
    session = requests.Session()
    session.headers.update(headers)
    r = session.get(index_url, timeout=45)
    print(f"[index] status={r.status_code} len={len(r.text)}")
    if r.status_code != 200:
        return 1

    soup = BeautifulSoup(r.text, "html.parser")
    hrefs = []
    for a in soup.find_all("a", href=True):
        h = a.get("href", "").strip()
        if "gkml2018" in h and "index_" in h:
            full = urljoin(index_url, h)
            if full not in hrefs:
                hrefs.append(full)

    print(f"[parse] unique gkml list links: {len(hrefs)}")
    for u in hrefs[:5]:
        print(f"  sample: {u}")

    if not hrefs:
        return 1

    test_url = hrefs[0]
    session.headers["Referer"] = index_url
    session.headers["Accept"] = (
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    )
    r2 = session.get(test_url, timeout=45)
    print(f"[list] GET {test_url}")
    print(f"[list] status={r2.status_code} len={len(r2.text)}")
    if r2.status_code == 200 and len(r2.text) > 500:
        print("[list] OK (looks like HTML)")
        return 0

    print("[list] failed or empty")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
