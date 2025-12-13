"""
API客户端模块 - 处理所有HTTP请求
适配自然资源部政府信息公开平台API
"""

import requests
import time
import random
import json
import logging
import warnings
from typing import Dict, Optional, Any, List
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# 禁用 urllib3 的 HeaderParsingError 警告
try:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.HeaderParsingError)
except (ImportError, AttributeError):
    pass

from .config import Config

# 使用模块级logger
logger = logging.getLogger(__name__)


# User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


class APIClient:
    """API客户端类 - 适配自然资源部API"""

    def __init__(self, config: Config):
        """初始化API客户端

        Args:
            config: 配置对象
        """
        self.config = config
        self.session = self._create_session()
        self.request_count = 0
        self.current_proxy = None

        # 初始化代理（如果启用）
        self._init_proxy()

    def _create_session(self) -> requests.Session:
        """创建新的会话"""
        session = requests.Session()

        # 随机选择User-Agent
        user_agent = random.choice(USER_AGENTS)

        # 设置请求头（自然资源部API）
        session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": self.config.get("base_url", "https://gi.mnr.gov.cn/"),
                "X-Requested-With": "XMLHttpRequest",
            }
        )

        return session

    def _init_proxy(self):
        """初始化代理"""
        if not self.config.use_proxy:
            return

        api_key = self.config.kuaidaili_api_key
        if not api_key:
            return

        try:
            # 尝试导入快代理SDK
            import kdl

            if ":" in api_key:
                secret_id, secret_key = api_key.split(":", 1)
                auth = kdl.Auth(secret_id, secret_key)
                self.kuaidaili_client = kdl.Client(auth, timeout=(8, 12), max_retries=3)
                print("[信息] 快代理已启用")
            else:
                print("[警告] 快代理API密钥格式错误，需要 secret_id:secret_key")
        except ImportError:
            print("[警告] 快代理SDK未安装: pip install kdl")
        except Exception as e:
            print(f"[警告] 快代理初始化失败: {e}")

    def _get_proxy(self, force_new: bool = False) -> Optional[Dict[str, str]]:
        """获取代理IP

        Args:
            force_new: 是否强制获取新代理

        Returns:
            代理配置字典
        """
        if not self.config.use_proxy:
            return None

        if force_new or self.current_proxy is None:
            try:
                if hasattr(self, "kuaidaili_client"):
                    proxy_list = self.kuaidaili_client.get_dps(1, format="json")
                    if proxy_list and len(proxy_list) > 0:
                        self.current_proxy = proxy_list[0]
                        print(f"  [代理] 获取新代理: {self.current_proxy[:50]}...")
            except Exception as e:
                if force_new:
                    print(f"  [警告] 获取代理失败: {e}")
                self.current_proxy = None

        if self.current_proxy:
            return {
                "http": f"http://{self.current_proxy}",
                "https": f"http://{self.current_proxy}",
            }

        return None

    def _rotate_session(self):
        """轮换会话"""
        if hasattr(self.session, "close"):
            try:
                self.session.close()
            except Exception:
                pass

        self.session = self._create_session()
        self.request_count = 0
        print("  [会话轮换] 已创建新会话")

    def _check_and_rotate_session(self):
        """检查并轮换会话"""
        self.request_count += 1
        if self.request_count >= self.config.get("session_rotate_interval", 50):
            self._rotate_session()

    def search_policies(
        self,
        keywords: List[str] = None,
        page: int = 1,
        start_date: str = None,
        end_date: str = None,
        data_source: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """搜索政策列表（自然资源部API）

        Args:
            keywords: 关键词列表
            page: 页码
            start_date: 起始日期 yyyy-MM-dd
            end_date: 结束日期 yyyy-MM-dd
            data_source: 数据源配置（如果为None，使用默认配置）

        Returns:
            搜索结果（可能是JSON或HTML）
        """
        if keywords is None:
            keywords = []

        # 如果提供了数据源配置，使用它；否则使用默认配置
        if data_source:
            search_api = data_source.get(
                "search_api", "https://search.mnr.gov.cn/was5/web/search"
            )
            channel_id = data_source.get("channel_id", "216640")
            base_url = data_source.get("base_url", "https://gi.mnr.gov.cn/")
            # 更新Referer
            self.session.headers.update({"Referer": base_url})
        else:
            search_api = self.config.get(
                "search_api", "https://search.mnr.gov.cn/was5/web/search"
            )
            channel_id = self.config.get("channel_id", "216640")
            base_url = self.config.get("base_url", "https://gi.mnr.gov.cn/")

        perpage = self.config.get("perpage", 20)

        # 构建搜索关键词
        search_word = " ".join(keywords) if keywords else ""

        params = {
            "channelid": channel_id,
            "searchword": search_word,
            "page": page,
            "perpage": perpage,
            "searchtype": "title",  # 搜索标题
            "orderby": "RELEVANCE",  # 按相关性排序
        }

        # 添加时间过滤
        if start_date:
            params["starttime"] = start_date
        if end_date:
            params["endtime"] = end_date

        self._check_and_rotate_session()

        max_retries = self.config.get("max_retries", 3)
        timeout = self.config.get("timeout", 30)

        for retry in range(max_retries):
            try:
                proxies = self._get_proxy(force_new=(retry > 0))

                # 添加详细日志
                if retry > 0:
                    print(f"  [重试 {retry}/{max_retries}] 请求: {search_api}")
                    print(
                        f"  参数: channelid={params.get('channelid')}, page={params.get('page')}, searchword={params.get('searchword')[:50] if params.get('searchword') else ''}"
                    )

                response = self.session.get(
                    search_api, params=params, timeout=timeout, proxies=proxies
                )
                response.raise_for_status()

                # 设置编码
                if response.encoding is None or response.encoding.lower() in [
                    "iso-8859-1",
                    "windows-1252",
                ]:
                    response.encoding = response.apparent_encoding or "utf-8"

                # 尝试解析为JSON
                try:
                    result = response.json()
                    return {"type": "json", "data": result}
                except json.JSONDecodeError:
                    # 如果不是JSON，返回HTML文本
                    return {"type": "html", "data": response.text}

            except requests.exceptions.Timeout as e:
                print(f"[X] 请求超时 (timeout={timeout}s): {e}")
                if retry < max_retries - 1:
                    wait_time = self.config.get("retry_delay", 5) * (retry + 1)
                    print(f"  [重试 {retry + 1}/{max_retries}] 等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                else:
                    return None
            except requests.exceptions.ConnectionError as e:
                print(f"[X] 连接错误: {e}")
                if retry < max_retries - 1:
                    wait_time = self.config.get("retry_delay", 5) * (retry + 1)
                    print(f"  [重试 {retry + 1}/{max_retries}] 等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                else:
                    return None
            except Exception as e:
                print(f"[X] 搜索请求异常: {type(e).__name__}: {e}")

                if retry < max_retries - 1:
                    wait_time = self.config.get("retry_delay", 5) * (retry + 1)
                    print(f"  [重试 {retry + 1}/{max_retries}] 等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                else:
                    return None

        return None

    def get_policy_detail(
        self, url: str, data_source: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """获取政策详情页正文和附件（自然资源部API）

        Args:
            url: 政策详情页URL
            data_source: 数据源配置（如果为None，根据URL自动判断）

        Returns:
            包含content和attachments的字典
            {
                'content': str,  # 正文内容
                'attachments': List[Dict]  # 附件列表，每个附件包含 {'url': str, 'name': str}
            }
        """
        # 如果没有提供数据源，根据URL自动判断
        if not data_source:
            data_sources = self.config.get("data_sources", [])
            for ds in data_sources:
                if ds.get("base_url", "") in url:
                    data_source = ds
                    break

        # 如果找到数据源，更新Referer
        if data_source:
            base_url = data_source.get("base_url", "https://gi.mnr.gov.cn/")
            self.session.headers.update({"Referer": base_url})

        self._check_and_rotate_session()

        max_retries = self.config.get("max_retries", 3)
        for retry in range(max_retries):
            try:
                proxies = self._get_proxy(force_new=(retry > 0))
                response = self.session.get(
                    url, timeout=self.config.get("timeout", 30), proxies=proxies
                )
                response.raise_for_status()
                response.encoding = response.apparent_encoding

                soup = BeautifulSoup(response.text, "html.parser")

                # 针对自然资源部网站的特定结构：正文在 <div id="content"> 或 <div class="TRS_Editor"> 中
                # 优先查找 id="content" 的div（这是真正的正文容器）
                # gi.mnr.gov.cn 和 f.mnr.gov.cn 都使用类似的结构
                content_div = soup.find("div", id="content")

                if not content_div:
                    # 如果没找到，尝试其他常见的正文容器
                    content_div = soup.find("div", class_="TRS_Editor")
                if not content_div:
                    content_div = soup.find("div", class_="Custom_UnionStyle")
                if not content_div:
                    content_div = soup.find("div", class_="content")
                if not content_div:
                    content_div = soup.find("div", class_="article-content")
                if not content_div:
                    content_div = soup.find("div", class_="main-content")
                if not content_div:
                    content_div = soup.find("div", class_="article")

                # 提取正文内容
                content = ""
                if content_div:
                    # 如果是外层content容器，需要移除不需要的部分
                    if content_div.get("class") and "content" in content_div.get(
                        "class"
                    ):
                        # 移除搜索框
                        search_box = content_div.find("div", class_="search-box")
                        if search_box:
                            search_box.decompose()

                        # 移除元信息表格（dtl-top和dtl-middle）
                        dtl_top = content_div.find("div", class_="dtl-top")
                        if dtl_top:
                            dtl_top.decompose()

                        dtl_middle = content_div.find("div", class_="dtl-middle")
                        if dtl_middle:
                            dtl_middle.decompose()

                        # 查找真正的正文容器（id="content"）
                        real_content = content_div.find("div", id="content")
                        if real_content:
                            content_div = real_content

                    # 清洗内容：移除不需要的元素
                    # 移除脚本、样式、导航等元素
                    for element in content_div.find_all(
                        ["script", "style", "nav", "header", "footer"]
                    ):
                        element.decompose()

                    # 移除页面操作元素（打印、分享等）- 更保守的策略
                    for element in content_div.find_all(
                        ["div", "span", "p", "a", "button"]
                    ):
                        text = element.get_text(strip=True)
                        # 只移除明确的页面操作元素，且必须是完整的短语，不能是正文的一部分
                        if len(text) < 15 and text in [
                            "打印",
                            "分享",
                            "字号",
                            "关闭",
                            "下载",
                            "仅内容打印",
                            "【字号：大中小】",
                            "【打印】",
                            "【关闭】",
                            "【下载】",
                            "大",
                            "中",
                            "小",
                            "分享到",
                            "收藏",
                            "返回顶部",
                        ]:
                            # 检查父元素是否有其他重要内容，如果没有才删除
                            parent_text = (
                                element.parent.get_text() if element.parent else ""
                            )
                            if len(parent_text.replace(text, "").strip()) < 10:
                                element.decompose()

                    # 不移除空的元素（可能包含有用的空格或换行），只移除明显的空白元素
                    # 注释掉原来的激进删除逻辑，改为在文本清理阶段处理

                    # 优先提取 Custom_UnionStyle 中的内容（这是真正的正文）
                    custom_style = content_div.find("div", class_="Custom_UnionStyle")
                    if custom_style:
                        # 不再移除第一个段落，因为可能是正文的一部分，避免缺字
                        # 使用strip=False保留原始文本结构，避免丢失内容
                        content = custom_style.get_text(separator="\n", strip=False)
                        # 手动清理每行的首尾空白，但保留换行结构
                        lines = content.split("\n")
                        content = "\n".join(
                            [
                                line.strip()
                                for line in lines
                                if line.strip() or line == ""
                            ]
                        )
                    else:
                        # 否则使用整个content_div的内容
                        # 使用strip=False保留原始文本结构，避免丢失内容
                        content = content_div.get_text(separator="\n", strip=False)
                        # 手动清理每行的首尾空白，但保留换行结构
                        lines = content.split("\n")
                        content = "\n".join(
                            [
                                line.strip()
                                for line in lines
                                if line.strip() or line == ""
                            ]
                        )

                    # 进一步清洗文本内容
                    content = self._clean_content(content)
                else:
                    # 兜底：返回全页文本，但也要清洗
                    content = soup.get_text(separator="\n", strip=True)
                    content = self._clean_content(content)

                # 提取附件链接
                attachments = self._extract_attachments(soup, url)

                # 提取元信息（从详情页）
                metadata = self._extract_metadata(soup)

                return {
                    "content": content,
                    "attachments": attachments,
                    "metadata": metadata,  # 返回元信息
                }

            except Exception as e:
                print(f"[X] 获取详情失败: {e}")

                if retry < max_retries - 1:
                    wait_time = self.config.get("retry_delay", 5) * (retry + 1)
                    time.sleep(wait_time)
                else:
                    return {"content": "", "attachments": []}

        return {"content": "", "attachments": []}

    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """从详情页提取元信息（针对自然资源部网站的特定结构，支持 gi.mnr.gov.cn 和 f.mnr.gov.cn）

        Args:
            soup: BeautifulSoup对象

        Returns:
            包含元信息的字典
        """
        metadata = {}

        # 自然资源部网站使用div结构存储元信息，在dtl-middle中（gi.mnr.gov.cn 和 f.mnr.gov.cn 都使用）
        # 查找dtl-middle容器
        dtl_middle = soup.find("div", class_="dtl-middle")
        if dtl_middle:
            # 查找mid-1到mid-4的div，它们包含标签和值
            # mid-1和mid-3是标签行，mid-2和mid-4是值行
            mid_1 = dtl_middle.find("div", class_="mid-1")
            mid_2 = dtl_middle.find("div", class_="mid-2")
            mid_3 = dtl_middle.find("div", class_="mid-3")
            mid_4 = dtl_middle.find("div", class_="mid-4")

            # 按列匹配：mid-1和mid-2是一组，mid-3和mid-4是一组
            # 第一组：mid-1（标签）和mid-2（值）
            if mid_1 and mid_2:
                labels_1 = [
                    span.get_text(strip=True).replace("\xa0", "").replace("\u00a0", "")
                    for span in mid_1.find_all("span")
                ]
                values_1 = [
                    span.get_text(strip=True).replace("\xa0", "").replace("\u00a0", "")
                    for span in mid_2.find_all("span")
                ]
                # 移除HTML注释标记
                labels_1 = [
                    text.replace("<!--", "").replace("-->", "")
                    for text in labels_1
                    if text
                ]
                values_1 = [
                    text.replace("<!--", "").replace("-->", "")
                    for text in values_1
                    if text
                ]

                # 匹配第一组的标签和值
                for i, label in enumerate(labels_1):
                    if i < len(values_1):
                        value = values_1[i]
                        label_clean = (
                            label.replace("\xa0", "")
                            .replace("\u00a0", "")
                            .replace(" ", "")
                        )

                        # 提取各种元信息
                        if "发文字号" in label_clean or "文号" in label_clean:
                            if "doc_number" not in metadata or not metadata.get(
                                "doc_number"
                            ):
                                metadata["doc_number"] = value
                        elif "发布机构" in label_clean or (
                            "机构" in label_clean and "发布" in label_clean
                        ):
                            # 发布机构应该存储到publisher字段，而不是level
                            if "publisher" not in metadata or not metadata.get(
                                "publisher"
                            ):
                                metadata["publisher"] = value
                            # 如果level字段还未设置，也可以设置（向后兼容）
                            if "level" not in metadata or not metadata.get("level"):
                                metadata["level"] = value
                        elif "业务类型" in label_clean or "分类" in label_clean:
                            if "category" not in metadata or not metadata.get(
                                "category"
                            ):
                                metadata["category"] = value

            # 第二组：mid-3（标签）和mid-4（值）
            if mid_3 and mid_4:
                labels_3 = [
                    span.get_text(strip=True).replace("\xa0", "").replace("\u00a0", "")
                    for span in mid_3.find_all("span")
                ]
                values_3 = [
                    span.get_text(strip=True).replace("\xa0", "").replace("\u00a0", "")
                    for span in mid_4.find_all("span")
                ]
                # 移除HTML注释标记
                labels_3 = [
                    text.replace("<!--", "").replace("-->", "")
                    for text in labels_3
                    if text
                ]
                values_3 = [
                    text.replace("<!--", "").replace("-->", "")
                    for text in values_3
                    if text
                ]

                # 匹配第二组的标签和值
                for i, label in enumerate(labels_3):
                    if i < len(values_3):
                        value = values_3[i]
                        label_clean = (
                            label.replace("\xa0", "")
                            .replace("\u00a0", "")
                            .replace(" ", "")
                        )

                        # 提取各种元信息
                        # 发布日期：必须是日期格式，不能是效力级别
                        if (
                            (
                                "成文时间" in label_clean
                                or "生成日期" in label_clean
                                or "发布日期" in label_clean
                            )
                            and "效力" not in label_clean
                            and "级别" not in label_clean
                        ):
                            # 验证值是否是日期格式（包含年月日或长度>=8）
                            if (
                                any(keyword in value for keyword in ["年", "月", "日"])
                                or len(value) >= 8
                            ):
                                if "pub_date" not in metadata or not metadata.get(
                                    "pub_date"
                                ):
                                    metadata["pub_date"] = value
                        elif "效力级别" in label_clean or (
                            "级别" in label_clean and "效力" in label_clean
                        ):
                            if "validity" not in metadata or not metadata.get(
                                "validity"
                            ):
                                metadata["validity"] = value
                        elif "生效日期" in label_clean or "实施日期" in label_clean:
                            if "effective_date" not in metadata or not metadata.get(
                                "effective_date"
                            ):
                                metadata["effective_date"] = value
                        elif "时效状态" in label_clean or (
                            "状态" in label_clean and "时效" in label_clean
                        ):
                            if "validity" not in metadata or not metadata.get(
                                "validity"
                            ):
                                metadata["validity"] = value

        # 如果从dtl-middle没提取到，尝试从表格中提取（兼容其他结构）
        if not metadata:
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) >= 2:
                        label = (
                            cells[0]
                            .get_text(strip=True)
                            .replace("\xa0", "")
                            .replace("\u00a0", "")
                        )
                        value = cells[1].get_text(strip=True)

                        # 提取各种元信息
                        # 发布日期：必须是日期格式，不能是效力级别
                        if (
                            (
                                "成文时间" in label
                                or "生成日期" in label
                                or "发布日期" in label
                            )
                            and "效力" not in label
                            and "级别" not in label
                        ):
                            # 验证值是否是日期格式（包含年月日或长度>=8）
                            if (
                                any(keyword in value for keyword in ["年", "月", "日"])
                                or len(value) >= 8
                            ):
                                if (
                                    "pub_date" not in metadata
                                    or not metadata["pub_date"]
                                ):
                                    metadata["pub_date"] = value
                        elif "发布机构" in label or (
                            "机构" in label and "发布" in label
                        ):
                            # 发布机构应该存储到publisher字段
                            if "publisher" not in metadata or not metadata.get(
                                "publisher"
                            ):
                                metadata["publisher"] = value
                            # 如果level字段还未设置，也可以设置（向后兼容）
                            if "level" not in metadata or not metadata["level"]:
                                metadata["level"] = value
                        elif "效力级别" in label or "级别" in label:
                            if "validity" not in metadata or not metadata["validity"]:
                                metadata["validity"] = value
                        elif "业务类型" in label or "分类" in label:
                            if "category" not in metadata or not metadata["category"]:
                                metadata["category"] = value
                        elif "生效日期" in label or "实施日期" in label:
                            if (
                                "effective_date" not in metadata
                                or not metadata["effective_date"]
                            ):
                                metadata["effective_date"] = value

        # 后备逻辑：根据文号推断发布机构（针对自然资源部网站）
        # 检查是否已经有文号，如果有则尝试推断发布机构
        existing_doc_number = metadata.get("doc_number", "")
        if existing_doc_number and not metadata.get("publisher"):
            if existing_doc_number.startswith("自然资发"):
                metadata["publisher"] = "自然资源部"
                metadata["level"] = "自然资源部"
                logger.debug(
                    f"根据文号推断发布机构: {existing_doc_number} -> 自然资源部"
                )
            elif existing_doc_number.startswith(
                "国土资发"
            ) or existing_doc_number.startswith("国土调查办发"):
                metadata["publisher"] = "国土资源部"
                metadata["level"] = "国土资源部"
                logger.debug(
                    f"根据文号推断发布机构: {existing_doc_number} -> 国土资源部"
                )
            elif existing_doc_number.startswith("国土资源部"):
                metadata["publisher"] = "国土资源部"
                metadata["level"] = "国土资源部"
                logger.debug(
                    f"根据文号推断发布机构: {existing_doc_number} -> 国土资源部"
                )

        return metadata

    def _clean_content(self, content: str) -> str:
        """清洗正文内容，移除不需要的元素，修复被错误拆分的文本

        Args:
            content: 原始内容

        Returns:
            清洗后的内容
        """
        if not content:
            return content

        # 第一步：修复被错误拆分的数字和文字（使用更精确的模式，避免误删）
        import re

        # 修复被换行符拆分的年份数字（如 \n2022\n 或 \n2022 \n）- 只修复4位数字，且前后是文字或标点
        content = re.sub(r"([^\d])\s*\n+(\d{4})\s*\n+([^\d])", r"\1\2\3", content)
        # 修复被换行符拆分的编号（如 \n2号 或 \n第2条 或 \n2项）- 确保前面有文字
        content = re.sub(r"([^0-9\n])\s*\n+(\d+[号条款项])", r"\1\2", content)
        # 修复被拆分的括号内容（如 〔\n内容\n〕 或 （\n内容\n））- 确保括号完整
        content = re.sub(
            r"〔\s*\n+([^〕\n]{1,100}?)\s*\n+〕", r"〔\1〕", content, flags=re.DOTALL
        )
        content = re.sub(
            r"（\s*\n+([^）\n]{1,100}?)\s*\n+）", r"（\1）", content, flags=re.DOTALL
        )
        # 修复被拆分的书名号内容（如 《\n内容\n》）
        content = re.sub(
            r"《\s*\n+([^》\n]{1,100}?)\s*\n+》", r"《\1》", content, flags=re.DOTALL
        )
        # 修复被拆分的引号内容（如 "\n内容\n"）- 更保守，确保引号匹配
        content = re.sub(
            r'"\s*\n+([^"\n]{1,100}?)\s*\n+"', r'"\1"', content, flags=re.DOTALL
        )
        # 修复被拆分的连续数字（如 "第\n1\n条" 应该合并为 "第1条"）
        content = re.sub(r"第\s*\n+(\d+)\s*\n+条", r"第\1条", content)
        # 修复被拆分的编号格式（如 "(\n1\n)" 应该合并为 "(1)"）- 确保括号匹配
        content = re.sub(r"\(\s*\n+(\d+)\s*\n+\)", r"(\1)", content)

        # 修复被拆分的常见词汇（如 "你\n公\n司" -> "你公司"）
        # 但要注意不能过度替换，只在明确的情况下替换
        # 修复"公司"被拆分（使用非贪婪匹配，避免过度替换）
        content = re.sub(r"([^\n\d])\n+公\n+司([^\n\d])", r"\1公司\2", content)
        # 修复"部门"被拆分
        content = re.sub(r"([^\n\d])\n+部\n+门([^\n\d])", r"\1部门\2", content)
        # 修复"规定"被拆分
        content = re.sub(r"([^\n\d])\n+规\n+定([^\n\d])", r"\1规定\2", content)
        # 修复"决定"被拆分
        content = re.sub(r"([^\n\d])\n+决\n+定([^\n\d])", r"\1决定\2", content)
        # 修复"申请"被拆分
        content = re.sub(r"([^\n\d])\n+申\n+请([^\n\d])", r"\1申请\2", content)
        # 修复"资质"被拆分
        content = re.sub(r"([^\n\d])\n+资\n+质([^\n\d])", r"\1资质\2", content)
        # 修复"证书"被拆分
        content = re.sub(r"([^\n\d])\n+证\n+书([^\n\d])", r"\1证书\2", content)

        lines = content.split("\n")
        cleaned_lines = []

        # 定义需要完全匹配的短行关键词（这些通常是页面元素）
        exact_match_keywords = [
            "【字号：大中小】",
            "【打印】",
            "【仅内容打印】",
            "【关闭】",
            "【下载】",
            "打印",
            "分享到",
            "字号",
            "关闭",
            "下载",
            "仅内容打印",
            "分享",
            "收藏",
            "返回顶部",
            "大",
            "中",
            "小",
        ]

        # 定义需要过滤的完整短语（通常是导航或页面元素）
        full_phrase_keywords = ["标题文号机构正文全部高级检索", "高级检索"]

        # 定义元信息标签（这些单独成行时应该被移除）
        metadata_labels = [
            "名称",
            "文号",
            "发布机构",
            "业务类型",
            "废止记录",
            "成文时间",
            "效力级别",
            "来源",
            "时效状态",
            "标题",
        ]

        # 用于检测重复的元信息块
        in_metadata_block = False
        metadata_block_start = -1
        consecutive_metadata_lines = 0

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 跳过空行（后面会统一处理）
            if not line:
                cleaned_lines.append("")
                i += 1
                continue

            # 检测元信息块：如果连续多行都是元信息标签或值，可能是重复的元信息表格
            is_metadata_label = line in metadata_labels or any(
                label in line for label in ["来", "一一", "源"]
            )
            is_metadata_value = False

            # 检查是否是元信息值（通常是日期、机构名、文号等格式）
            if any(
                keyword in line
                for keyword in [
                    "年",
                    "月",
                    "日",
                    "部门",
                    "规范性文件",
                    "现行有效",
                    "废止",
                ]
            ):
                is_metadata_value = True

            # 如果检测到元信息块
            if is_metadata_label or is_metadata_value:
                if not in_metadata_block:
                    in_metadata_block = True
                    metadata_block_start = len(cleaned_lines)
                    consecutive_metadata_lines = 0
                consecutive_metadata_lines += 1

                # 如果连续超过5行都是元信息，可能是重复的元信息表格，跳过
                if consecutive_metadata_lines > 5:
                    # 回退到元信息块开始位置，移除这些行
                    cleaned_lines = cleaned_lines[:metadata_block_start]
                    # 跳过这个元信息块
                    while i < len(lines) and (
                        lines[i].strip() in metadata_labels
                        or any(label in lines[i].strip() for label in metadata_labels)
                        or any(
                            keyword in lines[i].strip()
                            for keyword in ["年", "月", "日", "部门", "规范性文件"]
                        )
                    ):
                        i += 1
                    in_metadata_block = False
                    consecutive_metadata_lines = 0
                    continue
            else:
                # 如果不是元信息，重置状态
                if in_metadata_block and consecutive_metadata_lines <= 5:
                    # 如果元信息块很短，保留（可能是正常的元信息）
                    in_metadata_block = False
                    consecutive_metadata_lines = 0
                elif in_metadata_block:
                    # 如果元信息块很长，已经在上面的逻辑中处理了
                    in_metadata_block = False
                    consecutive_metadata_lines = 0

            # 跳过完全匹配的短行关键词
            if len(line) < 10:
                if line in exact_match_keywords:
                    i += 1
                    continue
                # 检查是否是只包含这些关键词的短行
                if any(
                    line == kw
                    or (len(kw) < 10 and (line.startswith(kw) or line.endswith(kw)))
                    for kw in exact_match_keywords
                ):
                    # 但如果是包含其他内容的行，保留
                    if len(line) > 15:
                        pass  # 保留
                    else:
                        i += 1
                        continue

            # 跳过包含完整短语的行
            if any(phrase in line for phrase in full_phrase_keywords):
                if len(line) > 50:
                    pass  # 保留长行
                else:
                    i += 1
                    continue

            # 跳过只包含特殊字符的极短行（但保留可能有意义的单字符，如"年"、"月"等）
            if len(line) <= 1 and all(c in " \t\n\r" for c in line):
                i += 1
                continue

            # 不再跳过单个常见页面元素词，因为它们可能是正文的一部分
            # 例如"你公"后面可能跟着"司"，不应该删除"公"行
            # 原来的逻辑过于激进，导致缺字

            # 跳过被拆分的页面元素（如"大"、"中"、"小"单独成行）
            if line in ["大", "中", "小"]:
                # 检查前后行是否是页面元素的一部分
                if i > 0 and i < len(lines) - 1:
                    prev_line = lines[i - 1].strip() if i > 0 else ""
                    next_line = lines[i + 1].strip() if i < len(lines) - 1 else ""
                    if "字号" in prev_line or "】" in next_line:
                        i += 1
                        continue

            # 跳过空的【】标签
            if (
                line == "【"
                or line == "】"
                or line.startswith("【")
                and line.endswith("】")
                and len(line) <= 5
            ):
                i += 1
                continue

            # 修复被拆分的文本（如"来一一源"应该是"来源"）
            if line == "来" or line == "一一" or line == "源":
                # 检查是否是"来源"被拆分
                if i < len(lines) - 2:
                    if (
                        line == "来"
                        and lines[i + 1].strip() == "一一"
                        and lines[i + 2].strip() == "源"
                    ):
                        # 跳过这三行
                        i += 3
                        continue

            # 保留这一行
            cleaned_lines.append(line)
            i += 1

        # 移除正文开头的重复元信息
        # 如果开头有很多短行和元信息标签，可能是重复的元信息表格
        result = []
        skip_initial_metadata = True
        initial_metadata_count = 0
        found_real_content = False

        for line in cleaned_lines:
            if not line.strip():
                if found_real_content:
                    result.append(line)
                continue

            # 检查是否是元信息标签或值（更保守的判断）
            # 只对明确的元信息标签或格式化的元信息值进行判断
            is_metadata = False
            if line in metadata_labels:
                is_metadata = True
            elif len(line) <= 3 and line in metadata_labels:
                is_metadata = True
            elif len(line) < 20 and any(
                keyword in line for keyword in ["年", "月", "日"]
            ):
                # 只对明确的日期格式或包含多个元信息关键词的行判断为元信息
                metadata_keywords_count = sum(
                    1
                    for keyword in [
                        "部门",
                        "规范性文件",
                        "现行有效",
                        "废止",
                        "机构",
                        "文号",
                    ]
                    if keyword in line
                )
                if metadata_keywords_count >= 2:
                    is_metadata = True

            # 检查是否是真正的正文内容（长行且不是元信息）
            is_real_content = len(line) > 20 and not is_metadata

            if skip_initial_metadata:
                if is_metadata:
                    initial_metadata_count += 1
                    # 如果连续超过8行都是元信息，跳过（提高阈值，避免误删）
                    if initial_metadata_count > 8:
                        continue
                    # 如果元信息块很短（<=3行），保留（可能是正常的正文开头）
                    elif initial_metadata_count <= 3:
                        result.append(line)
                        found_real_content = True  # 认为已经找到内容了
                        skip_initial_metadata = False
                elif is_real_content:
                    # 找到真正的正文内容，停止跳过
                    found_real_content = True
                    skip_initial_metadata = False
                    result.append(line)
                else:
                    # 不确定的行，更保守：如果已经有较多元信息（>5行），继续跳过；否则保留
                    if initial_metadata_count > 5:
                        continue
                    else:
                        result.append(line)
                        # 如果这行看起来像正文（长度>10），认为找到内容了
                        if len(line) > 10:
                            found_real_content = True
                            skip_initial_metadata = False
            else:
                result.append(line)

        # 合并连续的空行（最多保留一个空行）
        final_result = []
        prev_empty = False
        for line in result:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue
            final_result.append(line)
            prev_empty = is_empty

        # 移除开头和结尾的空行
        while final_result and not final_result[0].strip():
            final_result.pop(0)
        while final_result and not final_result[-1].strip():
            final_result.pop()

        # 移除末尾的页面元素
        while final_result and any(
            keyword in final_result[-1]
            for keyword in ["【", "】", "字号", "打印", "关闭", "下载"]
        ):
            final_result.pop()
            # 如果移除后末尾是空行，也移除
            while final_result and not final_result[-1].strip():
                final_result.pop()

        return "\n".join(final_result)

    def _extract_attachments(
        self, soup: BeautifulSoup, base_url: str
    ) -> List[Dict[str, str]]:
        """从HTML中提取附件链接

        Args:
            soup: BeautifulSoup对象
            base_url: 基础URL，用于拼接相对链接

        Returns:
            附件列表，每个附件包含 {'url': str, 'name': str}
        """
        attachments = []

        # 常见的附件文件扩展名（按长度从长到短排序，优先匹配长扩展名如.tar.gz）
        attachment_extensions = [
            ".tar.gz",
            ".tar.bz2",
            ".tar.xz",
            ".zip",
            ".tar",
            ".rar",
            ".7z",
            ".gz",
            ".bz2",
            ".doc",
            ".docx",
            ".pdf",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".txt",
            ".csv",
            ".xml",
            ".json",
        ]

        # 查找所有链接
        links = soup.find_all("a", href=True)

        for link in links:
            href = link.get("href", "").strip()
            if not href:
                continue

            # 过滤无效链接
            href_lower = href.lower()

            # 跳过无效链接
            if (
                href_lower.startswith("javascript:")
                or href_lower.startswith("mailto:")
                or href_lower.startswith("#")
            ):
                continue

            # 跳过空链接或只有#的链接
            if href == "#" or href == "javascript:;" or href == "javascript:void(0)":
                continue

            # 检查是否是附件链接
            is_attachment = False

            # 方法1: 检查文件扩展名（优先匹配长扩展名）
            for ext in attachment_extensions:
                if href_lower.endswith(ext):
                    is_attachment = True
                    break

            # 方法2: 检查链接文本是否包含"下载"、"附件"等关键词
            link_text = link.get_text(strip=True).lower()
            if any(
                keyword in link_text
                for keyword in ["下载", "附件", "download", "attachment"]
            ):
                # 但需要确保链接本身是有效的（不是javascript:）
                if not href_lower.startswith("javascript:"):
                    is_attachment = True

            # 方法3: 检查链接是否指向常见的附件路径
            if any(
                keyword in href_lower
                for keyword in ["/attach/", "/attachment/", "/file/", "/download/"]
            ):
                is_attachment = True

            if is_attachment:
                # 构建完整URL
                full_url = None
                if not href.startswith("http://") and not href.startswith("https://"):
                    if href.startswith("/"):
                        # 绝对路径
                        from urllib.parse import urlparse

                        parsed = urlparse(base_url)
                        full_url = f"{parsed.scheme}://{parsed.netloc}{href}"
                    else:
                        # 相对路径
                        full_url = urljoin(base_url, href)
                else:
                    full_url = href

                # 再次验证URL是否有效（避免javascript:等无效链接）
                if not full_url or full_url.lower().startswith(
                    ("javascript:", "mailto:", "#")
                ):
                    continue

                # 验证URL格式（必须包含协议）
                if not full_url.startswith("http://") and not full_url.startswith(
                    "https://"
                ):
                    continue

                # 获取附件名称
                attachment_name = link.get_text(strip=True)
                if not attachment_name or len(attachment_name) < 2:
                    # 如果没有文本，尝试从URL中提取文件名
                    attachment_name = href.split("/")[-1].split("?")[0]
                    # 如果还是没有，使用URL的一部分
                    if not attachment_name or len(attachment_name) < 2:
                        attachment_name = f"附件_{len(attachments) + 1}"

                # 避免重复
                if not any(att["url"] == full_url for att in attachments):
                    attachments.append({"url": full_url, "name": attachment_name})

        return attachments

    def download_file(
        self, file_path: str, save_path: str, chunk_size: int = 8192
    ) -> bool:
        """下载文件

        Args:
            file_path: 文件URL或路径
            save_path: 保存路径（本地）
            chunk_size: 分块大小

        Returns:
            是否下载成功
        """
        # 如果是完整URL，直接使用；否则拼接base_url
        if file_path.startswith("http://") or file_path.startswith("https://"):
            url = file_path
        else:
            base_url = self.config.get("base_url", "https://gi.mnr.gov.cn/")
            url = urljoin(base_url, file_path)

        self._check_and_rotate_session()

        max_retries = self.config.get("max_retries", 3)
        for retry in range(max_retries):
            try:
                proxies = self._get_proxy(force_new=(retry > 0))

                # 禁用 urllib3 的 HeaderParsingError 警告
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    try:
                        import urllib3

                        urllib3.disable_warnings(urllib3.exceptions.HeaderParsingError)
                    except (ImportError, AttributeError):
                        pass

                    response = self.session.get(
                        url, stream=True, timeout=60, proxies=proxies
                    )
                    response.raise_for_status()

                # 下载文件
                import os

                try:
                    with open(save_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                f.write(chunk)

                    # 检查文件是否成功下载
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        return True
                    else:
                        print("  [X] 下载失败：文件为空或不存在")
                        return False

                except Exception as download_error:
                    # 即使下载过程中出错，也检查文件是否已部分下载
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        # 文件已部分下载，可能是 HeaderParsingError 导致的
                        error_str = str(download_error)
                        if (
                            "HeaderParsingError" in error_str
                            or "NoBoundaryInMultipartDefect" in error_str
                        ):
                            # 忽略这个解析错误，文件已成功下载
                            return True
                    raise  # 重新抛出异常

            except Exception as e:
                # 检查是否是 HeaderParsingError（文件可能已成功下载）
                import os

                error_str = str(e)
                error_type = type(e).__name__

                if (
                    "HeaderParsingError" in error_type
                    or "NoBoundaryInMultipartDefect" in error_str
                ):
                    # 检查文件是否已成功下载
                    if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                        # 文件已成功下载，忽略这个解析错误
                        return True

                print(f"  [X] 下载失败: {e}")

                if retry < max_retries - 1:
                    wait_time = self.config.get("retry_delay", 5) * (retry + 1)
                    print(f"  [重试 {retry + 1}/{max_retries}] 等待 {wait_time} 秒...")
                    time.sleep(wait_time)
                else:
                    return False

        return False

    def close(self):
        """关闭客户端"""
        if hasattr(self.session, "close"):
            try:
                self.session.close()
            except Exception:
                pass
