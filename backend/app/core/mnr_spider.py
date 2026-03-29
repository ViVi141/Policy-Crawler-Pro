"""
自然资源部政府信息公开平台爬虫
适配 https://gi.mnr.gov.cn/
"""

from bs4 import BeautifulSoup
from collections import deque
from datetime import datetime, timezone
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .api_client import APIClient
from .config import Config
from .models import Policy
from .html_parsers import get_parser_for_data_source
from .mnr_gi_article import extract_gi_article_urls
from .mnr_gi_list import (
    build_category_list_url,
    find_next_list_page_url,
    same_gi_list_page,
)

logger = logging.getLogger(__name__)

# 自然资源部分类配置（政府信息公开平台）
MNR_CATEGORIES = {
    "自然资源调查监测": {"code": "1318", "name": "自然资源调查监测"},
    "自然资源确权登记": {"code": "1319", "name": "自然资源确权登记"},
    "自然资源合理开发利用": {"code": "1320", "name": "自然资源合理开发利用"},
    "自然资源有偿使用": {"code": "1321", "name": "自然资源有偿使用"},
    "国土空间规划": {"code": "1322", "name": "国土空间规划"},
    "国土空间用途管制": {"code": "1663", "name": "国土空间用途管制"},
    "国土空间生态修复": {"code": "1324", "name": "国土空间生态修复"},
    "耕地保护": {"code": "1325", "name": "耕地保护"},
    "地质勘查": {"code": "1326", "name": "地质勘查"},
    "矿产勘查": {"code": "1327", "name": "矿产勘查"},
    "矿产保护": {"code": "1328", "name": "矿产保护"},
    "矿产开发": {"code": "1329", "name": "矿产开发"},
    "地质环境保护": {"code": "1330", "name": "地质环境保护"},
    "海洋资源": {"code": "1331", "name": "海洋资源"},
    "测绘地理信息": {"code": "1332", "name": "测绘地理信息"},
    "地质灾害防治": {"code": "1334", "name": "地质灾害防治"},
    "地质公园": {"code": "1335", "name": "地质公园"},
    "地质遗迹保护": {"code": "1336", "name": "地质遗迹保护"},
    "矿业权评估": {"code": "1338", "name": "矿业权评估"},
    "机构建设": {"code": "1339", "name": "机构建设"},
    "综合管理": {"code": "1340", "name": "综合管理"},
    "其他": {"code": "1341", "name": "其他"},
}


class MNRSpider:
    """
    自然资源部政府信息公开平台爬虫
    适配 https://gi.mnr.gov.cn/
    """

    def __init__(self, config: Config, api_client: Optional[APIClient] = None):
        """初始化爬虫

        Args:
            config: 配置对象
            api_client: API客户端（可选，如果不提供则创建新的）
        """
        self.config = config
        self.api_client = api_client or APIClient(config)

        # 从配置获取参数（优先使用数据源配置）
        data_sources = config.get("data_sources", [])
        enabled_source = next(
            (ds for ds in data_sources if ds.get("enabled", True)), None
        )

        if enabled_source:
            self.base_url = enabled_source.get("base_url", "https://gi.mnr.gov.cn/")
            self.search_api = enabled_source.get(
                "search_api", "https://search.mnr.gov.cn/was5/web/search"
            )
            self.ajax_api = enabled_source.get(
                "ajax_api", "https://search.mnr.gov.cn/was5/web/ajaxdata.jsp"
            )
            self.channel_id = enabled_source.get("channel_id", "216640")
            self.data_source = enabled_source  # 保存数据源配置
        else:
            # 使用默认配置
            self.base_url = config.get("base_url", "https://gi.mnr.gov.cn/")
            self.search_api = config.get(
                "search_api", "https://search.mnr.gov.cn/was5/web/search"
            )
            self.ajax_api = config.get(
                "ajax_api", "https://search.mnr.gov.cn/was5/web/ajaxdata.jsp"
            )
            self.channel_id = config.get("channel_id", "216640")
            self.data_source = {"base_url": self.base_url, "level": "自然资源部"}

        self.level = "自然资源部"
        self.categories = MNR_CATEGORIES.copy()
        self.max_pages = config.get("max_pages", 999999)

        # 根据数据源获取对应的HTML解析器
        self.html_parser = get_parser_for_data_source(self.data_source)

        # 更新 API 客户端的 Referer
        if hasattr(self.api_client, "session"):
            self.api_client.session.headers.update({"Referer": self.base_url})

    def _mnr_portal_uses_article_crawl(self) -> bool:
        """gi / f 子站可使用与正文链相同的爬取方式（/YYYYMM/t...html）。"""
        u = (self.base_url or "").lower()
        if "gi.mnr.gov.cn" in u:
            return True
        if "f.mnr.gov.cn" in u:
            return True
        return False

    def _mnr_crawl_mode(self) -> str:
        """自然资源部数据源爬取方式：search_api | gi_list | gi_article。"""
        if not self._mnr_portal_uses_article_crawl():
            return "search_api"
        m = None
        if "mnr_crawl_mode" in self.data_source:
            m = self.data_source.get("mnr_crawl_mode")
        if m is None:
            m = self.config.get("mnr_crawl_mode", "gi_article")
        s = str(m or "").strip().lower()
        if s in ("search_api", "gi_list", "gi_article"):
            if s == "gi_list" and "f.mnr.gov.cn" in (self.base_url or "").lower():
                return "gi_article"
            return s
        return "gi_article"

    def _should_use_gi_list_crawl(self) -> bool:
        """是否使用 gi.mnr.gov.cn 公开目录直爬（不调用 search.mnr.gov.cn）。"""
        return self._mnr_crawl_mode() == "gi_list"

    def _gi_article_seed_urls(self) -> List[str]:
        """正文页直爬种子 URL 列表（/YYYYMM/tYYYYMMDD_id.html）。"""
        raw = None
        if "gi_article_seed_urls" in self.data_source:
            raw = self.data_source.get("gi_article_seed_urls")
        if raw is None:
            raw = self.config.get("gi_article_seed_urls")
        if raw is None:
            return []
        if isinstance(raw, str):
            raw = [raw]
        out: List[str] = []
        for u in raw:
            if u and str(u).strip():
                out.append(str(u).strip())
        return out

    def _policy_from_gi_article_detail(
        self, url: str, detail_result: Dict[str, Any]
    ) -> Policy:
        """由详情解析结果构建 Policy（政务公开表格「名称」等已写入 metadata）。"""
        md = detail_result.get("metadata") or {}
        title = md.get("title") or ""
        if not title:
            part = url.rsplit("/", 1)[-1]
            title = part.replace(".html", "").replace(".htm", "")

        pub_raw = md.get("pub_date") or ""
        pub_date = ""
        if pub_raw:
            parsed = self._parse_date(pub_raw)
            if parsed:
                pub_date = parsed.strftime("%Y-%m-%d")
            else:
                pub_date = pub_raw.strip()

        eff = md.get("effective_date") or ""
        if eff:
            pe = self._parse_date(eff)
            if pe:
                eff = pe.strftime("%Y-%m-%d")

        return Policy(
            title=title,
            pub_date=pub_date,
            doc_number=md.get("doc_number") or "",
            source=url,
            link=url,
            url=url,
            content=detail_result.get("content") or "",
            category=md.get("category") or "",
            level=md.get("level") or self.level,
            validity=md.get("validity") or "",
            effective_date=eff,
            publisher=md.get("publisher") or "",
            crawl_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _gi_list_index_file(self) -> str:
        """列表页文件名（如 index_4724.html），部分子类站点使用其它模板时可配置。"""
        if "gi_list_index_file" in self.data_source:
            v = self.data_source.get("gi_list_index_file")
            if v:
                return str(v).strip()
        v2 = self.config.get("gi_list_index_file", "index_4724.html")
        if v2:
            return str(v2).strip()
        return "index_4724.html"

    def _build_gi_list_entries(self, category: Optional[str]) -> List[Tuple[str, str]]:
        """返回 [(分类显示名, 列表第一页 URL), ...]。"""
        index_file = self._gi_list_index_file()
        out: List[Tuple[str, str]] = []
        if category:
            if category in self.categories:
                info = self.categories[category]
                u = build_category_list_url(self.base_url, info["code"], index_file)
                out.append((info["name"], u))
                return out
            logger.warning("分类「%s」不在预置列表中，将爬取全部分类目录", category)

        for _n, info in self.categories.items():
            u = build_category_list_url(self.base_url, info["code"], index_file)
            out.append((info["name"], u))
        return out

    def _merge_page_policies_into_results(
        self,
        page_policies: List,
        results: List[Policy],
        seen_ids: set,
        keywords: List[str],
        dt_start: Optional[datetime],
        dt_end: Optional[datetime],
        callback: Optional[Callable],
        policy_callback: Optional[Callable],
        page_desc: str,
    ) -> int:
        """将一页解析结果合并进 results，返回本页新增条数。"""
        new_policies_count = 0
        for policy_data in page_policies:
            if isinstance(policy_data, dict):
                policy = Policy(
                    title=policy_data.get("title", ""),
                    pub_date=policy_data.get("pub_date", ""),
                    doc_number=policy_data.get("doc_number", ""),
                    source=policy_data.get("link", "")
                    or policy_data.get("source", ""),
                    link=policy_data.get("link", "")
                    or policy_data.get("source", ""),
                    url=policy_data.get("link", "")
                    or policy_data.get("source", ""),
                    content=policy_data.get("content", ""),
                    category=policy_data.get("category", ""),
                    level=policy_data.get("level", ""),
                    validity=policy_data.get("validity", ""),
                    effective_date=policy_data.get("effective_date", ""),
                    publisher=policy_data.get("publisher", ""),
                    crawl_time=policy_data.get(
                        "crawl_time",
                        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
            else:
                policy = policy_data

            policy_id = policy.id
            if policy_id in seen_ids:
                if callback:
                    callback(f"跳过重复政策: {policy.title}")
                continue

            if keywords and not any(kw in policy.title for kw in keywords):
                continue

            need_detail_for_dates = bool((dt_start or dt_end) and policy.link)
            if policy.link and (not policy.content or need_detail_for_dates):
                if callback:
                    callback(f"获取详情: {policy.title[:30]}...")
                logger.debug(f"获取政策详情: {policy.title[:50]}...")
                detail_result = self.api_client.get_policy_detail(
                    policy.link, data_source={"base_url": self.base_url}
                )
                policy.content = detail_result.get("content", "")

                metadata = detail_result.get("metadata", {})
                if metadata:
                    if metadata.get("pub_date"):
                        parsed_date = self._parse_date(metadata["pub_date"])
                        if parsed_date:
                            policy.pub_date = parsed_date.strftime("%Y-%m-%d")
                    if metadata.get("level"):
                        policy.level = metadata["level"]
                    if metadata.get("validity"):
                        policy.validity = metadata["validity"]
                    if metadata.get("category"):
                        policy.category = metadata["category"]
                    if metadata.get("publisher"):
                        policy.publisher = metadata["publisher"]
                    if metadata.get("effective_date"):
                        parsed_eff_date = self._parse_date(metadata["effective_date"])
                        if parsed_eff_date:
                            policy.effective_date = parsed_eff_date.strftime("%Y-%m-%d")
                    if metadata.get("doc_number") and not policy.doc_number:
                        policy.doc_number = metadata["doc_number"]

            if dt_start or dt_end:
                pub_date_fmt = (
                    self._parse_date(policy.pub_date) if policy.pub_date else None
                )
                if pub_date_fmt:
                    if dt_start and pub_date_fmt < dt_start:
                        continue
                    if dt_end and pub_date_fmt > dt_end:
                        continue
                else:
                    logger.debug(
                        "任务设定了日期范围但本条无有效发布日期，仍保留: %s",
                        policy.title[:80] if policy.title else "",
                    )

            seen_ids.add(policy_id)
            results.append(policy)
            new_policies_count += 1

            if policy_callback:
                try:
                    policy_callback(policy)
                except Exception as cb_error:
                    logger.warning(f"调用 policy_callback 失败: {cb_error}")

            if callback:
                callback(
                    f"POLICY_DATA:{policy.title}|{policy.pub_date}|{policy.link}||{policy.category}"
                )

        if callback:
            callback(
                f"{page_desc}获取{len(page_policies)}条政策（新增{new_policies_count}条）"
            )
        return new_policies_count

    def _crawl_policies_gi_list(
        self,
        keywords: Optional[List[str]] = None,
        callback: Optional[Callable] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        stop_callback: Optional[Callable] = None,
        policy_callback: Optional[Callable] = None,
    ) -> List[Policy]:
        """按公开目录 URL 逐页抓取（不经过 search 接口）。"""
        if keywords is None:
            keywords = []

        dt_start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        dt_end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        results: List[Policy] = []
        seen_ids = set()

        if callback:
            if keywords:
                callback(f"搜索关键词: {' '.join(keywords)}")
            else:
                callback("直爬模式: 按公开目录列表逐页抓取（无 search 接口）")
            if category:
                callback(f"指定分类: {category}")
            else:
                callback("分类范围: 预置全部分类（逐项爬取列表）")
            if start_date or end_date:
                callback(f"时间范围: {start_date or '不限'} 至 {end_date or '不限'}")
            else:
                callback("时间范围: 无限制")

        max_consecutive_empty = self.config.get("max_empty_pages", 3)
        entries = self._build_gi_list_entries(category)

        for cat_name, start_url in entries:
            if stop_callback and stop_callback():
                break

            current_url: Optional[str] = start_url
            list_page_idx = 0
            consecutive_empty = 0

            while (
                list_page_idx < self.max_pages
                and current_url
                and not (stop_callback and stop_callback())
            ):
                if callback:
                    callback(
                        f"「{cat_name}」列表第{list_page_idx + 1}页: {current_url}"
                    )

                html = self.api_client.fetch_html(
                    current_url, data_source={"base_url": self.base_url}
                )

                if not html:
                    if callback:
                        callback(f"列表页无响应: {current_url}")
                    break

                snippet = html[:1200] if len(html) > 1200 else html
                if "404 Not Found" in snippet or "<title>404" in snippet:
                    if callback:
                        callback(f"列表页 404，结束本分类: {current_url}")
                    break

                soup = BeautifulSoup(html, "html.parser")
                page_policies = self.html_parser.parse(soup, callback, cat_name)

                self._merge_page_policies_into_results(
                    page_policies,
                    results,
                    seen_ids,
                    keywords,
                    dt_start,
                    dt_end,
                    callback,
                    policy_callback,
                    f"「{cat_name}」第{list_page_idx + 1}页",
                )

                if not page_policies:
                    consecutive_empty += 1
                    if consecutive_empty >= max_consecutive_empty:
                        if callback:
                            callback(
                                f"连续{max_consecutive_empty}页无条目，结束本分类"
                            )
                        break
                else:
                    consecutive_empty = 0

                next_url = find_next_list_page_url(soup, current_url)
                if not next_url:
                    if callback:
                        callback(f"「{cat_name}」已无下一页")
                    break
                if same_gi_list_page(next_url, current_url):
                    if callback:
                        callback("下一页与当前页相同，结束本分类以防死循环")
                    break

                current_url = next_url
                list_page_idx += 1
                time.sleep(self.config.get("request_delay", 2))

        if callback:
            callback(f"爬取完成，共获取{len(results)}条政策")

        return results

    def _crawl_policies_gi_article(
        self,
        keywords: Optional[List[str]] = None,
        callback: Optional[Callable] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        stop_callback: Optional[Callable] = None,
        policy_callback: Optional[Callable] = None,
    ) -> List[Policy]:
        """从 /YYYYMM/tYYYYMMDD_<id>.html 正文页出发，沿页内链接做 BFS 扩展。"""
        if keywords is None:
            keywords = []

        dt_start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        dt_end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        results: List[Policy] = []
        seen_ids = set()
        seeds = self._gi_article_seed_urls()

        if not seeds:
            if callback:
                callback(
                    "未配置 gi_article_seed_urls，请在配置中提供至少一条种子页 URL，"
                    "例如政务公开正文 https://gi.mnr.gov.cn/202603/t20260327_2917437.html "
                    "或政策法规列表 https://f.mnr.gov.cn/index_3553.html"
                )
            return results

        if callback:
            if keywords:
                callback(f"搜索关键词: {' '.join(keywords)}")
            else:
                callback("正文页模式: 从种子 URL 沿站内文章链接扩展抓取")
            if category:
                callback(
                    "gi_article 模式暂不按界面「分类」筛选项过滤，请用关键词或日期范围"
                )
            if start_date or end_date:
                callback(f"时间范围: {start_date or '不限'} 至 {end_date or '不限'}")
            else:
                callback("时间范围: 无限制")
            callback(f"种子数: {len(seeds)}，最多入库 {self.max_pages} 条")

        queue = deque(seeds)
        visited_urls = set()
        fetched = 0

        while (
            queue
            and fetched < self.max_pages
            and not (stop_callback and stop_callback())
        ):
            url = queue.popleft()
            if url in visited_urls:
                continue
            visited_urls.add(url)

            if callback:
                callback(f"抓取正文: {url}")

            html = self.api_client.fetch_html(
                url, data_source={"base_url": self.base_url}
            )
            if not html:
                if callback:
                    callback(f"页面无响应: {url}")
                continue

            head = html[:1200] if len(html) > 1200 else html
            if "404 Not Found" in head or "<title>404" in head:
                if callback:
                    callback(f"页面 404: {url}")
                continue

            for nxt in extract_gi_article_urls(html, url):
                if nxt not in visited_urls:
                    queue.append(nxt)

            detail = self.api_client.get_policy_detail(
                url,
                data_source={"base_url": self.base_url},
                html_text=html,
            )
            policy = self._policy_from_gi_article_detail(url, detail)

            if keywords and not any(kw in policy.title for kw in keywords):
                continue

            if dt_start or dt_end:
                pub_date_fmt = (
                    self._parse_date(policy.pub_date) if policy.pub_date else None
                )
                if pub_date_fmt:
                    if dt_start and pub_date_fmt < dt_start:
                        continue
                    if dt_end and pub_date_fmt > dt_end:
                        continue
                else:
                    logger.debug(
                        "日期范围内任务但本条无有效发布日期: %s",
                        policy.title[:80] if policy.title else "",
                    )

            if policy.id in seen_ids:
                if callback:
                    callback(f"跳过重复: {policy.title[:40]}")
                continue

            seen_ids.add(policy.id)
            results.append(policy)
            fetched += 1

            if policy_callback:
                try:
                    policy_callback(policy)
                except Exception as cb_error:
                    logger.warning(f"调用 policy_callback 失败: {cb_error}")

            if callback:
                callback(
                    f"POLICY_DATA:{policy.title}|{policy.pub_date}|{policy.link}||{policy.category}"
                )

            time.sleep(self.config.get("request_delay", 2))

        if callback:
            callback(f"爬取完成，共获取{len(results)}条政策")

        return results

    def _search_data_source_payload(self) -> Dict[str, Any]:
        """传给 search_policies 的数据源字段（含 g2018 门户预热 URL）。"""
        portal = None
        if "search_portal_url" in self.data_source:
            portal = self.data_source.get("search_portal_url")
        else:
            portal = self.config.get(
                "search_portal_url", "https://search.mnr.gov.cn/g2018/"
            )
        return {
            "base_url": self.base_url,
            "search_api": self.search_api,
            "channel_id": self.channel_id,
            "search_portal_url": portal,
        }

    def crawl_policies(
        self,
        keywords: Optional[List[str]] = None,
        callback: Optional[Callable] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category: Optional[str] = None,
        stop_callback: Optional[Callable] = None,
        policy_callback: Optional[Callable] = None,
    ) -> List[Policy]:
        """
        爬取自然资源部政府信息公开平台政策

        Args:
            keywords: 关键词列表
            callback: 进度回调函数
            start_date: 起始日期 yyyy-MM-dd
            end_date: 结束日期 yyyy-MM-dd
            category: 分类名称，None表示搜索全部分类
            stop_callback: 停止回调函数
            policy_callback: 政策数据回调函数，每解析到一条政策时调用

        Returns:
            政策列表
        """
        if keywords is None:
            keywords = []

        dt_start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
        dt_end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None

        results = []
        seen_ids = set()  # 用于去重

        # 构建搜索关键词
        search_word = " ".join(keywords) if keywords else ""

        mode = self._mnr_crawl_mode()
        if mode == "gi_article":
            return self._crawl_policies_gi_article(
                keywords=keywords,
                callback=callback,
                start_date=start_date,
                end_date=end_date,
                category=category,
                stop_callback=stop_callback,
                policy_callback=policy_callback,
            )
        if mode == "gi_list":
            return self._crawl_policies_gi_list(
                keywords=keywords,
                callback=callback,
                start_date=start_date,
                end_date=end_date,
                category=category,
                stop_callback=stop_callback,
                policy_callback=policy_callback,
            )

        if callback:
            if search_word:
                callback(f"搜索关键词: {search_word}")
            else:
                callback("全量爬取模式: 无关键词限制，将爬取所有政策")
            if category:
                callback(f"指定分类: {category}")
            else:
                callback("分类范围: 全部分类")
            if start_date or end_date:
                callback(f"时间范围: {start_date or '不限'} 至 {end_date or '不限'}")
            else:
                callback("时间范围: 无限制（全量爬取）")

        # 分页获取数据
        page = 1
        max_consecutive_empty = self.config.get("max_empty_pages", 3)
        consecutive_empty_pages = 0

        while page <= self.max_pages:
            if stop_callback and stop_callback():
                break

            if callback:
                callback(f"正在抓取第{page}页...")

            try:
                # 构建搜索参数
                params = {
                    "channelid": self.channel_id,
                    "searchword": search_word,
                    "page": page,
                    "perpage": self.config.get("perpage", 20),
                    "searchtype": "title",
                    "orderby": "RELEVANCE",
                }

                # 添加时间过滤
                if start_date:
                    params["starttime"] = start_date
                if end_date:
                    params["endtime"] = end_date

                # 发送搜索请求
                result = self.api_client.search_policies(
                    keywords,
                    page,
                    start_date,
                    end_date,
                    data_source=self._search_data_source_payload(),
                )

                if not result:
                    consecutive_empty_pages += 1
                    if callback:
                        callback(f"第{page}页API请求失败或无响应")
                    if consecutive_empty_pages >= max_consecutive_empty:
                        if callback:
                            callback(f"连续{max_consecutive_empty}页无数据，停止爬取")
                        break
                    page += 1
                    continue

                # 解析响应数据
                page_policies = []
                if result["type"] == "json":
                    page_policies = self._parse_json_results(result["data"], callback)
                elif result["type"] == "html":
                    soup = BeautifulSoup(result["data"], "html.parser")
                    # 使用专门的HTML解析器
                    page_policies = self.html_parser.parse(
                        soup, callback, category or "全部"
                    )

                if not page_policies:
                    consecutive_empty_pages += 1
                    if callback:
                        callback(f"第{page}页无数据")
                    if consecutive_empty_pages >= max_consecutive_empty:
                        if callback:
                            callback(f"连续{max_consecutive_empty}页无数据，停止爬取")
                        break
                    page += 1
                    continue
                else:
                    consecutive_empty_pages = 0

                self._merge_page_policies_into_results(
                    page_policies,
                    results,
                    seen_ids,
                    keywords,
                    dt_start,
                    dt_end,
                    callback,
                    policy_callback,
                    f"第{page}页",
                )

                # 控制速度
                time.sleep(self.config.get("request_delay", 2))

                page += 1

            except Exception as e:
                if callback:
                    callback(f"第{page}页抓取失败: {e}")
                logger.error(f"第{page}页抓取异常: {e}", exc_info=True)
                break

        if callback:
            callback(f"爬取完成，共获取{len(results)}条政策")

        return results

    def _parse_json_results(
        self, data: Dict, callback: Optional[Callable] = None
    ) -> List[Dict]:
        """解析JSON格式的搜索结果"""
        policies = []

        try:
            # 根据实际返回的JSON结构解析
            if "results" in data:
                items = data["results"]
            elif "data" in data:
                items = data["data"]
            elif isinstance(data, list):
                items = data
            else:
                items = []

            for item in items:
                # 解析日期
                raw_date = item.get("pubdate", item.get("publishdate", ""))
                pub_date = ""
                if raw_date:
                    parsed_date = self._parse_date(raw_date)
                    if parsed_date:
                        pub_date = parsed_date.strftime("%Y-%m-%d")
                    else:
                        pub_date = raw_date.strip()

                policy = {
                    "level": "",
                    "title": item.get("title", "") or "",
                    "pub_date": pub_date or "",
                    "doc_number": item.get("filenum", "") or "",
                    "source": item.get("url", "") or "",
                    "link": item.get("url", "") or "",
                    "url": item.get("url", "") or "",
                    "content": item.get("content", "").strip()
                    or item.get("summary", "").strip()
                    or "",
                    "category": item.get("category", "") or "",
                    "validity": item.get("status", "") or "",
                    "effective_date": item.get("effectivedate", "") or "",
                    "publisher": "",
                    "crawl_time": datetime.now(timezone.utc).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                }
                policies.append(policy)

        except Exception as e:
            if callback:
                callback(f"解析JSON结果失败: {e}")
            logger.error(f"解析JSON结果失败: {e}", exc_info=True)

        return policies

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串为datetime对象"""
        if not date_str:
            return None
        for fmt in ("%Y年%m月%d日", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(date_str, fmt)
            except Exception:
                continue
        return None

    def get_available_categories(self) -> List[str]:
        """获取可用的分类列表"""
        return list(self.categories.keys())

    def test_search_api(self, callback: Optional[Callable] = None) -> bool:
        """测试搜索 API 或直爬列表页是否可用。"""
        if callback:
            callback("测试数据源连通性...")

        try:
            mode = self._mnr_crawl_mode()
            if mode == "gi_article":
                seeds = self._gi_article_seed_urls()
                test_u = None
                if seeds:
                    test_u = seeds[0]
                else:
                    if "f.mnr.gov.cn" in (self.base_url or "").lower():
                        test_u = "https://f.mnr.gov.cn/index_3553.html"
                    else:
                        test_u = (
                            "https://gi.mnr.gov.cn/202603/t20260327_2917437.html"
                        )
                html = self.api_client.fetch_html(
                    test_u, data_source={"base_url": self.base_url}
                )
                if html and len(html) > 200:
                    head = html[:1200] if len(html) > 1200 else html
                    if "404 Not Found" not in head and "<title>404" not in head:
                        if callback:
                            callback("正文页或种子页可访问")
                        return True
                if callback:
                    callback("正文页或种子页不可用或无内容")
                return False

            if mode == "gi_list":
                sample_code = self.categories["国土空间规划"]["code"]
                u = build_category_list_url(
                    self.base_url, sample_code, self._gi_list_index_file()
                )
                html = self.api_client.fetch_html(
                    u, data_source={"base_url": self.base_url}
                )
                if html and len(html) > 200:
                    head = html[:1200] if len(html) > 1200 else html
                    if "404 Not Found" not in head and "<title>404" not in head:
                        if callback:
                            callback("直爬列表页可访问")
                        return True
                if callback:
                    callback("直爬列表页不可用或无内容")
                return False

            result = self.api_client.search_policies(
                ["土地"],
                1,
                None,
                None,
                data_source=self._search_data_source_payload(),
            )

            if result:
                if callback:
                    callback(f"API测试成功，返回类型: {result['type']}")
                return True
            else:
                if callback:
                    callback("API测试失败: 无响应")
                return False

        except Exception as e:
            if callback:
                callback(f"API测试异常: {e}")
            logger.error(f"API测试异常: {e}", exc_info=True)
            return False
