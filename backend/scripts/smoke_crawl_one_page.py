"""
随机选一个关键词，用与线上一致的 APIClient.search_policies 请求第 1 页。

用法（在 backend 目录下）:
    python scripts/smoke_crawl_one_page.py
"""

from __future__ import annotations

import os
import random
import sys

BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

os.chdir(BACKEND_ROOT)

from app.core.api_client import APIClient  # noqa: E402
from app.core.config import Config  # noqa: E402

KEYWORD_POOL = [
    "土地",
    "规划",
    "矿业",
    "海洋",
    "测绘",
    "耕地",
    "生态修复",
    "确权",
]


def main() -> int:
    config_path = os.path.join(BACKEND_ROOT, "config.json")
    config = Config(config_path)
    # 冒烟：缩短重试与超时，避免长时间挂死（与线上任务配置无关，仅本脚本内覆盖）
    config.config["max_retries"] = 2
    config.config["retry_delay"] = 3
    if config.get("timeout", 90) > 60:
        config.config["timeout"] = 60
    config.config.setdefault("connect_timeout", 15)

    keyword = random.choice(KEYWORD_POOL)
    print(f"[smoke] 随机关键词: {keyword}", flush=True)
    print(
        f"[smoke] 本脚本超时/重试: timeout={config.get('timeout')}, "
        f"connect_timeout={config.get('connect_timeout')}, max_retries={config.get('max_retries')}",
        flush=True,
    )

    client = APIClient(config)

    data_source = None
    for ds in config.get("data_sources", []):
        if ds.get("enabled", True) and ds.get("type") != "gd":
            data_source = {
                "base_url": ds.get("base_url", "https://gi.mnr.gov.cn/"),
                "search_api": ds.get(
                    "search_api", "https://search.mnr.gov.cn/was5/web/search"
                ),
                "channel_id": str(ds.get("channel_id", "216640")),
            }
            if "search_portal_url" in ds:
                data_source["search_portal_url"] = ds.get("search_portal_url")
            else:
                data_source["search_portal_url"] = config.get(
                    "search_portal_url", "https://search.mnr.gov.cn/g2018/"
                )
            print(f"[smoke] 数据源: {ds.get('name', 'default')}")
            break

    if not data_source:
        data_source = {
            "base_url": config.get("base_url", "https://gi.mnr.gov.cn/"),
            "search_api": config.get(
                "search_api", "https://search.mnr.gov.cn/was5/web/search"
            ),
            "channel_id": str(config.get("channel_id", "216640")),
            "search_portal_url": config.get(
                "search_portal_url", "https://search.mnr.gov.cn/g2018/"
            ),
        }

    result = client.search_policies(
        [keyword],
        1,
        None,
        None,
        data_source=data_source,
    )

    if not result:
        print("[smoke] 失败: 无返回（超时/连接错误/重试用尽）")
        return 1

    print(f"[smoke] 成功: type={result['type']}")
    payload = result.get("data")
    if result["type"] == "json":
        text = str(payload)
    else:
        text = payload if isinstance(payload, str) else str(payload)
    preview = text[:2000]
    if len(text) > 2000:
        preview += "\n... (截断)"
    print("[smoke] 内容预览:\n", preview)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
