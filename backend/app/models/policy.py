# ==============================================================================
# MNR Law Crawler Online - 政策数据模型
# ==============================================================================
#
# 项目名称: MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)
# 项目地址: https://github.com/ViVi141/MNR-Law-Crawler-Online
# 作者: ViVi141
# 许可证: MIT License
#
# 描述: 定义政策数据的SQLAlchemy模型，包含字段定义和关系映射
#
# ==============================================================================

"""
政策模型
"""

from sqlalchemy import (
    Column,
    BigInteger,
    Integer,
    String,
    Text,
    Date,
    Boolean,
    DateTime,
    Index,
    ForeignKey,
)
from sqlalchemy.sql import func
from ..database import Base


class Policy(Base):
    """政策主表"""

    __tablename__ = "policies"

    id = Column(BigInteger, primary_key=True, index=True)

    # 基本信息
    title = Column(String(500), nullable=False, index=True)
    doc_number = Column(String(200), index=True)
    pub_date = Column(Date, index=True)
    effective_date = Column(Date)

    # 分类信息
    category = Column(String(200), index=True)
    category_code = Column(String(50))
    level = Column(String(100), index=True)  # 效力级别
    validity = Column(
        String(100)
    )  # 有效性（如：部门规范性文件、行政法规等）- 从50增加到100

    # 来源信息
    source_url = Column(Text, nullable=False)
    source_name = Column(String(200), index=True)

    # 内容
    content = Column(Text, nullable=False)  # 全文内容
    content_summary = Column(Text)  # 摘要

    # 元数据
    publisher = Column(String(200))  # 发布机构
    keywords = Column(Text)  # JSON数组字符串

    # S3文件路径
    json_s3_key = Column(String(500))
    markdown_s3_key = Column(String(500))
    docx_s3_key = Column(String(500))
    attachments_s3_keys = Column(Text)  # JSON数组字符串

    # 本地文件路径（可选，用于缓存）
    json_local_path = Column(String(500))
    markdown_local_path = Column(String(500))
    docx_local_path = Column(String(500))
    attachments_local_path = Column(Text)

    # 存储模式
    storage_mode = Column(String(20), default="local")  # s3/local/both
    s3_bucket = Column(String(100))
    s3_region = Column(String(50))

    # 统计
    word_count = Column(BigInteger, default=0)
    attachment_count = Column(Integer, default=0)

    # 索引标记
    is_indexed = Column(Boolean, default=False)

    # 时间戳
    crawl_time = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 任务关联（新增：每个任务的数据独立）
    task_id = Column(
        BigInteger,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # 唯一约束
    # 注意：PostgreSQL不支持部分唯一索引，所以使用应用层逻辑检查唯一性
    # 对于task_id不为NULL的情况：(title, source_url, pub_date, task_id)唯一
    # 对于task_id为NULL的情况：(title, source_url, pub_date)唯一（兼容旧数据）
    __table_args__ = (
        Index("idx_policy_unique", "title", "source_url", "pub_date"),
        Index("idx_policy_task", "task_id"),
        # 注意：全文搜索应该使用PostgreSQL的GIN索引和tsvector，而不是普通的btree索引
        # 这里只对title建立索引，content字段太大无法用btree索引
        # 全文搜索功能在search_service中使用tsvector实现
    )
