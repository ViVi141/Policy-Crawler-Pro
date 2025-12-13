"""
数据模型定义 - 适配自然资源部API
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone


@dataclass
class Policy:
    """政策基本信息 - 适配自然资源部API"""

    title: str
    pub_date: str  # 发布日期 YYYY-MM-DD
    doc_number: str = ""  # 发文字号
    source: str = ""  # 来源URL
    link: str = ""  # 链接（兼容字段）
    url: str = ""  # URL（兼容字段）
    content: str = ""  # 正文内容
    category: str = ""  # 分类
    level: str = "自然资源部"  # 机构级别
    validity: str = ""  # 有效性
    effective_date: str = ""  # 生效日期
    publisher: str = ""  # 发布机构
    crawl_time: str = ""  # 爬取时间
    _data_source: Optional[Dict[str, Any]] = None  # 数据源信息（内部使用）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "title": self.title,
            "pub_date": self.pub_date,
            "doc_number": self.doc_number,
            "source": self.source,
            "link": self.link or self.source,
            "url": self.url or self.source,
            "content": self.content,
            "category": self.category,
            "level": self.level,
            "validity": self.validity,
            "effective_date": self.effective_date,
            "publisher": self.publisher,
            "crawl_time": self.crawl_time,
        }
        # 如果存在_data_source，也包含在字典中
        if self._data_source:
            result["_data_source"] = self._data_source
            # 如果有name字段，也作为source_name传递
            if "name" in self._data_source:
                result["source_name"] = self._data_source["name"]
        # 如果存在文件路径属性，也包含在字典中
        if hasattr(self, "markdown_path"):
            result["markdown_path"] = getattr(self, "markdown_path", None)
        if hasattr(self, "docx_path"):
            result["docx_path"] = getattr(self, "docx_path", None)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Policy":
        """从字典创建"""
        return cls(
            title=data.get("title", ""),
            pub_date=data.get("pub_date", ""),
            doc_number=data.get("doc_number", ""),
            source=data.get("source", data.get("url", data.get("link", ""))),
            link=data.get("link", data.get("url", data.get("source", ""))),
            url=data.get("url", data.get("link", data.get("source", ""))),
            content=data.get("content", ""),
            category=data.get("category", ""),
            level=data.get("level", "自然资源部"),
            validity=data.get("validity", ""),
            effective_date=data.get("effective_date", ""),
            publisher=data.get("publisher", ""),
            crawl_time=data.get(
                "crawl_time", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            ),
        )

    @property
    def id(self) -> str:
        """获取政策ID（使用标题和链接的组合）"""
        return f"{self.title}|{self.link or self.source}"


@dataclass
class FileAttachment:
    """附件信息"""

    file_name: str
    file_url: str
    file_ext: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "file_name": self.file_name,
            "file_url": self.file_url,
            "file_ext": self.file_ext,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileAttachment":
        """从字典创建"""
        return cls(
            file_name=data.get("file_name", ""),
            file_url=data.get("file_url", ""),
            file_ext=data.get("file_ext", ""),
        )


@dataclass
class PolicyDetail:
    """政策详细信息"""

    policy: Policy
    attachments: List[FileAttachment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "policy": self.policy.to_dict(),
            "attachments": [att.to_dict() for att in self.attachments],
        }


@dataclass
class CrawlStage:
    """爬取阶段信息"""

    name: str  # 阶段名称，如 "search_policies", "crawl_details"
    description: str  # 阶段描述，如 "搜索政策列表", "爬取政策详情"
    total_count: int = 0  # 该阶段总项目数
    completed_count: int = 0  # 该阶段已完成项目数
    failed_count: int = 0  # 该阶段失败项目数
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    message: str = ""  # 当前阶段状态消息

    @property
    def progress_percentage(self) -> float:
        """阶段进度百分比"""
        if self.total_count == 0:
            return 0.0
        return ((self.completed_count + self.failed_count) / self.total_count) * 100

    @property
    def success_rate(self) -> float:
        """阶段成功率"""
        if self.completed_count + self.failed_count == 0:
            return 0.0
        return (self.completed_count / (self.completed_count + self.failed_count)) * 100


@dataclass
class CrawlProgress:
    """爬取进度"""

    # 总体进度
    total_count: int = 0  # 预估总政策数
    completed_count: int = 0  # 已完成政策数
    failed_count: int = 0  # 失败政策数

    # 当前处理信息
    current_policy_id: str = ""
    current_policy_title: str = ""

    # 时间信息
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # 历史记录
    completed_policies: List[str] = field(default_factory=list)
    failed_policies: List[Dict[str, str]] = field(default_factory=list)

    # 多阶段进度支持
    stages: Dict[str, CrawlStage] = field(default_factory=dict)
    current_stage: str = ""  # 当前阶段名称

    # 兼容性字段（已废弃，保留向后兼容）
    estimated_total: Optional[int] = None  # 预估总数（现在通过total_count表示）

    def get_current_stage(self) -> Optional[CrawlStage]:
        """获取当前阶段"""
        return self.stages.get(self.current_stage)

    def set_stage(self, stage_name: str, description: str = "", total_count: int = 0):
        """设置当前阶段"""
        if stage_name not in self.stages:
            self.stages[stage_name] = CrawlStage(
                name=stage_name, description=description, total_count=total_count
            )

        self.current_stage = stage_name
        stage = self.stages[stage_name]
        if stage.status == "pending":
            stage.status = "running"
            stage.start_time = datetime.now(timezone.utc)

    def update_stage_progress(
        self,
        stage_name: str = None,
        completed: int = 0,
        failed: int = 0,
        message: str = "",
    ):
        """更新阶段进度"""
        stage_name = stage_name or self.current_stage
        if stage_name and stage_name in self.stages:
            stage = self.stages[stage_name]
            stage.completed_count += completed
            stage.failed_count += failed
            if message:
                stage.message = message

            # 更新总体进度
            self._update_overall_progress()

    def complete_stage(self, stage_name: str = None, success: bool = True):
        """完成阶段"""
        stage_name = stage_name or self.current_stage
        if stage_name and stage_name in self.stages:
            stage = self.stages[stage_name]
            stage.status = "completed" if success else "failed"
            stage.end_time = datetime.now(timezone.utc)

    @property
    def success_rate(self) -> float:
        """总体成功率"""
        total_processed = self.completed_count + self.failed_count
        if total_processed == 0:
            return 0.0
        return (self.completed_count / total_processed) * 100

    @property
    def progress_percentage(self) -> float:
        """总体进度百分比"""
        if self.total_count == 0:
            return 0.0
        return ((self.completed_count + self.failed_count) / self.total_count) * 100

    @property
    def current_stage_progress(self) -> float:
        """当前阶段进度百分比"""
        stage = self.get_current_stage()
        return stage.progress_percentage if stage else 0.0

    @property
    def elapsed_time(self) -> Optional[float]:
        """已用时间（秒）"""
        if not self.start_time:
            return None
        end = self.end_time or datetime.now(timezone.utc)
        return (end - self.start_time).total_seconds()

    def _update_overall_progress(self):
        """更新总体进度（基于各阶段进度）"""
        # 如果有明确的阶段，基于当前阶段更新总体进度
        current_stage = self.get_current_stage()
        if current_stage and current_stage.total_count > 0:
            # 对于详情爬取阶段，completed_count就是实际完成的政策数
            if self.current_stage == "crawl_details":
                self.completed_count = current_stage.completed_count
                self.failed_count = current_stage.failed_count
            # 对于搜索阶段，total_count就是预估的政策数
            elif self.current_stage == "search_policies":
                self.total_count = max(self.total_count, current_stage.total_count)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            # 总体进度
            "total_count": self.total_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "success_rate": self.success_rate,
            "progress_percentage": self.progress_percentage,
            # 当前处理信息
            "current_policy_id": self.current_policy_id,
            "current_policy_title": self.current_policy_title,
            "current_stage": self.current_stage,
            # 时间信息
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "elapsed_time": self.elapsed_time,
            # 历史记录
            "completed_policies": self.completed_policies,
            "failed_policies": self.failed_policies,
            # 多阶段进度
            "stages": {
                name: {
                    "name": stage.name,
                    "description": stage.description,
                    "total_count": stage.total_count,
                    "completed_count": stage.completed_count,
                    "failed_count": stage.failed_count,
                    "progress_percentage": stage.progress_percentage,
                    "success_rate": stage.success_rate,
                    "status": stage.status,
                    "message": stage.message,
                    "start_time": (
                        stage.start_time.isoformat() if stage.start_time else None
                    ),
                    "end_time": stage.end_time.isoformat() if stage.end_time else None,
                }
                for name, stage in self.stages.items()
            },
            # 当前阶段进度
            "current_stage_progress": self.current_stage_progress,
        }
