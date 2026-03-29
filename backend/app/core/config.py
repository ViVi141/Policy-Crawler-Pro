"""
配置管理模块
"""

import os
import json
from typing import Any


class Config:
    """配置管理类"""

    # 默认配置
    DEFAULT_CONFIG = {
        # 数据源配置（支持多个网站）
        "data_sources": [
            {
                "name": "政府信息公开平台",
                "base_url": "https://gi.mnr.gov.cn/",
                "search_api": "https://search.mnr.gov.cn/was5/web/search",
                "ajax_api": "https://search.mnr.gov.cn/was5/web/ajaxdata.jsp",
                "search_portal_url": "https://search.mnr.gov.cn/g2018/",
                "mnr_crawl_mode": "gi_article",
                "gi_article_seed_urls": [
                    "https://gi.mnr.gov.cn/202603/t20260327_2917437.html"
                ],
                "gi_list_index_file": "index_4724.html",
                "channel_id": "216640",
                "enabled": True,
            },
            {
                "name": "政策法规库",
                "base_url": "https://f.mnr.gov.cn/",
                "search_api": "https://search.mnr.gov.cn/was5/web/search",
                "ajax_api": "https://search.mnr.gov.cn/was5/web/ajaxdata.jsp",
                "search_portal_url": "https://search.mnr.gov.cn/g2018/",
                "mnr_crawl_mode": "gi_article",
                "gi_article_seed_urls": [
                    "https://f.mnr.gov.cn/index_3553.html"
                ],
                "channel_id": "174757",
                "enabled": False,
            },
            {
                "name": "广东省法规",
                "type": "gd",
                "api_base_url": "https://www.gdpc.gov.cn:443/bascdata",
                "law_rule_types": [1, 2, 3],  # 1=地方性法规, 2=政府规章, 3=规范性文件
                "enabled": False,
            },
        ],
        # 兼容旧配置（向后兼容，默认使用政府信息公开平台）
        "base_url": "https://gi.mnr.gov.cn/",
        "search_api": "https://search.mnr.gov.cn/was5/web/search",
        "ajax_api": "https://search.mnr.gov.cn/was5/web/ajaxdata.jsp",
        "search_portal_url": "https://search.mnr.gov.cn/g2018/",
        "mnr_crawl_mode": "gi_article",
        "gi_article_seed_urls": [
            "https://gi.mnr.gov.cn/202603/t20260327_2917437.html"
        ],
        "gi_list_index_file": "index_4724.html",
        "channel_id": "216640",  # 政府信息公开平台的频道ID
        # 请求配置
        "request_delay": 0.5,  # 爬取延迟（秒），默认0.5秒
        "retry_delay": 5,
        "max_retries": 3,
        "rate_limit_delay": 30,
        "session_rotate_interval": 50,
        # 政务搜索接口常较慢：读取超时默认 90s；连接阶段单独限制避免长时间卡在握手
        "connect_timeout": 15,
        "timeout": 90,
        # 政策重试配置
        "max_policy_retries": 0,  # 政策爬取失败时的最大重试次数（0表示不重试）
        "policy_retry_delay": 5,  # 政策重试前的等待时间（秒）
        # 爬取配置
        "page_size": 20,
        "perpage": 20,  # 每页数量
        "max_pages": 999999,  # 最大翻页数
        "max_empty_pages": 3,  # 最大连续空页数
        "categories": [],  # 分类列表，空列表表示搜索全部分类
        # 输出配置
        "output_dir": "crawled_data",
        "save_json": True,
        "save_markdown": True,
        "save_docx": True,  # 是否保存DOCX格式
        "save_files": True,
        # 搜索配置
        "keywords": [],  # 关键词列表
        "start_date": "",  # 起始日期 yyyy-MM-dd
        "end_date": "",  # 结束日期 yyyy-MM-dd
        # 文件下载配置
        "download_docx": True,
        "download_doc": True,
        # 政务站点附件多为 PDF；默认关闭会导致仅 PDF 的页面无法下载与合并正文
        "download_pdf": True,
        "download_all_files": False,  # 下载所有形式的附件（忽略文件类型）
        # 代理配置
        "use_proxy": False,
        "kuaidaili_api_key": "",
        # 日志配置
        "log_level": "INFO",
        "log_file": "crawler.log",
        # GUI配置
        "window_width": 1200,
        "window_height": 1000,
        "theme": "light",
    }

    def __init__(self, config_file: str = "config.json"):
        """初始化配置

        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> bool:
        """从文件加载配置

        Returns:
            加载是否成功
        """
        if not os.path.exists(self.config_file):
            self.save()
            return False

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                user_config = json.load(f)

            # 特殊处理：如果用户配置中没有data_sources，使用默认的
            # 如果用户配置中有data_sources但只有一个，检查是否需要补充默认的第二个数据源
            if "data_sources" not in user_config or not user_config.get("data_sources"):
                # 用户配置中没有data_sources，保持默认配置
                pass
            else:
                # 用户配置中有data_sources，检查是否需要补充
                user_data_sources = user_config.get("data_sources", [])
                default_data_sources = self.DEFAULT_CONFIG.get("data_sources", [])

                # 如果用户配置中只有一个数据源，且默认配置中有两个，检查是否需要补充
                if len(user_data_sources) == 1 and len(default_data_sources) == 2:
                    user_source_names = {ds.get("name") for ds in user_data_sources}
                    default_source_names = {
                        ds.get("name") for ds in default_data_sources
                    }

                    # 如果用户配置中缺少某个默认数据源，补充它
                    missing_sources = default_source_names - user_source_names
                    if missing_sources:
                        for default_ds in default_data_sources:
                            if default_ds.get("name") in missing_sources:
                                # 添加缺失的数据源，默认禁用
                                user_data_sources.append(
                                    {**default_ds, "enabled": False}
                                )
                        user_config["data_sources"] = user_data_sources

            # 更新配置
            self.config.update(user_config)
            return True
        except Exception as e:
            print(f"配置加载失败: {e}")
            return False

    def save(self) -> bool:
        """保存配置到文件

        Returns:
            保存是否成功
        """
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"配置保存失败: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """设置配置项

        Args:
            key: 配置键
            value: 配置值

        Returns:
            是否成功
        """
        self.config[key] = value
        return self.save()

    def reset(self) -> bool:
        """重置为默认配置

        Returns:
            是否成功
        """
        self.config = self.DEFAULT_CONFIG.copy()
        return self.save()

    @property
    def output_dir(self) -> str:
        """输出目录"""
        return self.get("output_dir", "crawled_data")

    @property
    def use_proxy(self) -> bool:
        """是否使用代理"""
        return self.get("use_proxy", False)

    @property
    def kuaidaili_api_key(self) -> str:
        """快代理API密钥（兼容旧格式）"""
        # 优先使用新格式
        secret_id = self.get("kuaidaili_secret_id", "")
        secret_key = self.get("kuaidaili_secret_key", "")
        if secret_id and secret_key:
            return f"{secret_id}:{secret_key}"
        # 兼容旧格式
        return self.get("kuaidaili_api_key", "")
