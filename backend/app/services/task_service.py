"""
任务服务 - 管理爬虫任务
"""

import logging
import threading
import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..models.task import Task, TaskPolicy
from ..models.policy import Policy
from .policy_service import PolicyService

logger = logging.getLogger(__name__)


class TaskService:
    """任务服务"""

    def __init__(self):
        """初始化任务服务"""
        self.policy_service = PolicyService()
        self._running_tasks: Dict[int, threading.Thread] = {}
        self._crawler_instances: Dict[int, Any] = {}  # 保存爬虫实例用于停止操作
        self._crawler_lock = threading.Lock()  # 线程安全锁

    def create_task(
        self,
        db: Session,
        task_name: str,
        task_type: str,
        config: Dict[str, Any],
        user_id: int,
    ) -> Task:
        """创建任务

        Args:
            db: 数据库会话
            task_name: 任务名称
            task_type: 任务类型 (crawl_task/backup_task)
            config: 任务配置
            user_id: 创建者ID

        Returns:
            Task对象

        Raises:
            ValueError: 如果爬取任务未指定数据源
        """
        # 验证爬取任务必须指定数据源
        if task_type == "crawl_task":
            data_sources = config.get("data_sources", [])
            if not data_sources or len(data_sources) == 0:
                raise ValueError("创建爬取任务时必须至少指定一个数据源")
            # 验证数据源配置完整性
            for ds in data_sources:
                if not isinstance(ds, dict):
                    raise ValueError(f"数据源配置格式错误: {ds}")
                required_fields = ["name", "base_url", "search_api", "ajax_api"]
                missing_fields = [
                    f for f in required_fields if f not in ds or not ds.get(f)
                ]
                if missing_fields:
                    raise ValueError(
                        f"数据源 '{ds.get('name', 'unknown')}' 缺少必需字段: {', '.join(missing_fields)}"
                    )

        task = Task(
            task_name=task_name,
            task_type=task_type,
            status="pending",
            config_json=config,
            created_by=user_id,
        )
        db.add(task)
        try:
            db.commit()
            db.refresh(task)
            logger.info(f"创建任务: {task.task_name} (ID: {task.id})")
            return task
        except Exception as e:
            db.rollback()
            logger.error(f"创建任务失败: {e}", exc_info=True)
            raise

    def start_task(self, db: Session, task_id: int, background: bool = True) -> Task:
        """启动任务

        Args:
            db: 数据库会话
            task_id: 任务ID
            background: 是否在后台执行

        Returns:
            Task对象
        """
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        if task.status == "running":
            raise ValueError(f"任务已在运行中: {task_id}")

        if task.status in ["completed", "cancelled"]:
            raise ValueError(f"任务已完成或已取消: {task_id}")

        # 更新任务状态
        task.status = "running"
        task.start_time = datetime.now(timezone.utc)
        db.commit()

        # 发送任务开始邮件通知（如果启用且有收件人）
        try:
            from .email_service import get_email_service

            email_service = get_email_service()
            # 传入db以实时加载配置
            if email_service.is_enabled(db):
                import asyncio

                # 准备任务配置信息
                config = task.config_json or {}
                data_sources = []
                if "data_sources" in config:
                    for ds in config["data_sources"]:
                        if isinstance(ds, dict) and "name" in ds:
                            data_sources.append(ds["name"])
                        elif isinstance(ds, str):
                            data_sources.append(ds)

                keywords = config.get("keywords")
                date_range = None
                if config.get("start_date") and config.get("end_date"):
                    date_range = f"{config['start_date']} ~ {config['end_date']}"
                elif config.get("start_date"):
                    date_range = f"从 {config['start_date']} 开始"
                elif config.get("end_date"):
                    date_range = f"至 {config['end_date']}"

                max_pages = config.get("max_pages")

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        email_service.send_task_start_notification(
                            task_name=task.task_name,
                            task_type=task.task_type,
                            data_sources=data_sources,
                            keywords=keywords,
                            date_range=date_range,
                            max_pages=max_pages,
                            start_time=task.start_time,
                            db=db,  # 传入db以实时加载配置
                        )
                    )

                    if result["success"]:
                        logger.info(f"✅ 任务开始邮件通知发送成功: {task.task_name}")
                    else:
                        logger.warning(
                            f"❌ 任务开始邮件通知发送失败: {result.get('message', '未知错误')}"
                        )

                except Exception as email_error:
                    logger.error(
                        f"❌ 发送任务开始邮件通知时发生异常: {email_error}",
                        exc_info=True,
                    )
                finally:
                    loop.close()
            else:
                logger.debug(f"邮件服务未启用，跳过任务开始通知: {task.task_name}")
        except Exception as e:
            logger.error(f"❌ 任务开始邮件通知流程异常: {e}", exc_info=True)

        if background:
            # 在后台线程执行
            thread = threading.Thread(
                target=self._execute_task, args=(task_id,), daemon=True
            )
            thread.start()
            self._running_tasks[task_id] = thread
        else:
            # 同步执行
            self._execute_task(task_id)

        return task

    def stop_task(self, db: Session, task_id: int) -> bool:
        """停止任务

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            是否成功停止
        """
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False

        if task.status != "running":
            return False

        # 更新任务状态
        task.status = "cancelled"
        task.end_time = datetime.now(timezone.utc)
        db.commit()

        # 停止爬虫（如果正在运行）- 线程安全
        with self._crawler_lock:
            crawler = self._crawler_instances.get(task_id)
            if crawler and hasattr(crawler, "stop_requested"):
                crawler.stop_requested = True
                logger.info(f"已设置爬虫停止标志: {task_id}")
            # 立即删除弱引用，让爬虫实例可以被垃圾回收
            if task_id in self._crawler_instances:
                del self._crawler_instances[task_id]

        logger.info(f"任务已停止: {task_id}")
        return True

    def pause_task(self, db: Session, task_id: int) -> bool:
        """暂停任务

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            是否成功暂停
        """
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False

        if task.status != "running":
            return False

        # 更新任务状态为暂停
        task.status = "paused"
        task.end_time = datetime.now(timezone.utc)
        db.commit()

        # 停止爬虫（如果正在运行）- 线程安全
        with self._crawler_lock:
            crawler = self._crawler_instances.get(task_id)
            if crawler and hasattr(crawler, "stop_requested"):
                crawler.stop_requested = True
                logger.info(f"已设置爬虫停止标志（暂停）: {task_id}")

        logger.info(f"任务已暂停: {task_id}")
        return True

    def resume_task(self, db: Session, task_id: int) -> bool:
        """恢复暂停的任务

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            是否成功恢复
        """
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False

        if task.status != "paused":
            return False

        # 恢复任务状态为待执行，然后启动
        task.status = "pending"
        db.commit()

        # 启动任务
        try:
            self.start_task(db, task_id, background=True)
            logger.info(f"任务已恢复: {task_id}")
            return True
        except Exception as e:
            logger.error(f"恢复任务失败: {e}", exc_info=True)
            task.status = "paused"
            db.commit()
            return False

    def get_task(self, db: Session, task_id: int) -> Optional[Task]:
        """获取任务"""
        return db.query(Task).filter(Task.id == task_id).first()

    def delete_task(self, db: Session, task_id: int) -> bool:
        """删除任务（包括关联的数据和文件）

        Args:
            db: 数据库会话
            task_id: 任务ID

        Returns:
            是否成功删除

        Raises:
            ValueError: 如果任务不存在或正在运行
        """
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"任务不存在: {task_id}")

        # 检查任务状态，如果正在运行，不允许删除
        if task.status == "running":
            raise ValueError("无法删除正在运行的任务，请先停止任务")

        # 1. 查找任务关联的所有政策（通过task_id直接查找，更高效）
        policies = db.query(Policy).filter(Policy.task_id == task_id).all()

        deleted_policies_count = 0
        deleted_files_count = 0

        # 2. 对每个政策进行处理（因为policy.task_id == task_id，这些政策只属于该任务）
        from .storage_service import StorageService

        storage_service = StorageService()

        for policy in policies:
            policy_id = policy.id

            # 删除政策的所有文件（文件路径包含task_id，确保独立）
            file_types = ["markdown", "docx"]
            for file_type in file_types:
                try:
                    if storage_service.delete_policy_file(
                        policy_id, file_type, task_id=task_id
                    ):
                        deleted_files_count += 1
                except Exception as e:
                    logger.warning(f"删除政策 {policy_id} 的 {file_type} 文件失败: {e}")

            # 删除附件
            from ..models.attachment import Attachment

            attachments = (
                db.query(Attachment).filter(Attachment.policy_id == policy_id).all()
            )
            for attachment in attachments:
                # 删除附件文件
                if attachment.file_path and os.path.exists(attachment.file_path):
                    try:
                        os.remove(attachment.file_path)
                        deleted_files_count += 1
                    except Exception as e:
                        logger.warning(
                            f"删除附件文件失败: {attachment.file_path} - {e}"
                        )
                # 删除S3附件（如果有）
                if attachment.file_s3_key and storage_service.s3_service.is_enabled():
                    try:
                        storage_service.s3_service.delete_file(attachment.file_s3_key)
                    except Exception as e:
                        logger.warning(
                            f"删除S3附件失败: {attachment.file_s3_key} - {e}"
                        )
                # 删除附件记录
                db.delete(attachment)

            # 删除政策记录
            db.delete(policy)
            deleted_policies_count += 1

        # 3. 删除TaskPolicy关联记录（虽然policy.task_id已经关联，但为了数据一致性，也删除关联记录）
        task_policies = db.query(TaskPolicy).filter(TaskPolicy.task_id == task_id).all()
        for task_policy in task_policies:
            db.delete(task_policy)

        # 4. 更新关联的备份记录（不删除备份）
        from ..models.system_config import BackupRecord

        backups = (
            db.query(BackupRecord)
            .filter(
                BackupRecord.source_type == "task",
                BackupRecord.source_id == str(task_id),
            )
            .all()
        )

        for backup in backups:
            backup.source_deleted = True
            # 如果还没有保存任务名称，现在保存
            if not backup.source_name:
                backup.source_name = task.task_name

        # 5. 删除任务记录
        db.delete(task)
        db.commit()

        logger.info(
            f"已删除任务: {task.task_name} (ID: {task_id}), "
            f"删除了 {deleted_policies_count} 个政策, {deleted_files_count} 个文件, "
            f"更新了 {len(backups)} 个备份记录（备份已保留）"
        )
        return True

    def get_tasks(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 20,
        task_type: Optional[str] = None,
        status: Optional[str] = None,
        completed_only: bool = False,
    ) -> tuple:
        """获取任务列表

        Returns:
            (任务列表, 总数)
        """
        query = db.query(Task)

        if task_type:
            query = query.filter(Task.task_type == task_type)
        if status:
            query = query.filter(Task.status == status)

        total = query.count()
        tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()

        return tasks, total

    def _execute_task(self, task_id: int):
        """执行任务（内部方法）"""
        from ..database import SessionLocal

        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return

            config = task.config_json or {}

            # 创建进度回调，将进度消息保存到数据库
            def progress_callback(message: str):
                logger.info(f"[任务 {task_id}] {message}")
                try:
                    # 更新任务进度消息（追加模式，保留最近的进度信息）
                    task = db.query(Task).filter(Task.id == task_id).first()
                    if task:
                        # 保留最近的进度消息（最多保留最后100行，约5000字符）
                        current_msg = task.progress_message or ""
                        lines = current_msg.split("\n") if current_msg else []
                        # 限制单行消息长度
                        max_line_length = 500
                        if len(message) > max_line_length:
                            message = message[:max_line_length] + "..."
                        # 添加新消息
                        lines.append(
                            f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}"
                        )
                        # 只保留最后100行
                        if len(lines) > 100:
                            lines = lines[-100:]
                        # 限制总长度
                        max_total_length = 10000
                        task.progress_message = "\n".join(lines)
                        if len(task.progress_message) > max_total_length:
                            task.progress_message = task.progress_message[
                                -max_total_length:
                            ]
                        db.commit()
                except Exception as e:
                    logger.warning(f"保存进度消息失败: {e}")
                    db.rollback()

            # 执行爬虫任务
            try:
                # 导入爬虫模块
                from ..core.config import Config
                from ..core.crawler import PolicyCrawler

                # 创建配置对象（会加载默认配置）
                crawler_config = Config()

                # 从数据库读取爬虫配置（延迟等），先应用系统配置
                from ..services.config_service import ConfigService

                config_service = ConfigService()
                crawler_db_config = config_service.get_crawler_config(db)
                if crawler_db_config.get("request_delay"):
                    crawler_config.config["request_delay"] = crawler_db_config[
                        "request_delay"
                    ]
                if crawler_db_config.get("use_proxy") is not None:
                    crawler_config.config["use_proxy"] = crawler_db_config["use_proxy"]

                # 处理任务配置：合并到默认配置中（而不是直接覆盖）
                # 需要保留默认配置中的重要字段（如 output_dir、log_dir 等）
                task_config = config.copy()

                # 如果配置中指定了data_sources，使用指定的数据源
                if "data_sources" in task_config and task_config["data_sources"]:
                    # 验证数据源配置完整性，确保包含所有必需字段
                    validated_data_sources = []
                    for ds in task_config["data_sources"]:
                        # 确保数据源配置包含所有必需字段
                        validated_ds = {
                            "name": ds.get("name", ""),
                            "base_url": ds.get("base_url", ""),
                            "search_api": ds.get("search_api", ""),
                            "ajax_api": ds.get(
                                "ajax_api", ds.get("search_api", "")
                            ),  # 如果没有ajax_api，使用search_api
                            "channel_id": ds.get("channel_id", ""),
                            "enabled": ds.get("enabled", True),
                        }
                        # 验证必需字段
                        required_fields = [
                            "name",
                            "base_url",
                            "search_api",
                            "channel_id",
                        ]
                        missing_fields = [
                            f for f in required_fields if not validated_ds.get(f)
                        ]
                        if missing_fields:
                            logger.warning(
                                f"[任务 {task_id}] 数据源 '{validated_ds.get('name')}' 缺少必需字段: {missing_fields}，跳过该数据源"
                            )
                            continue
                        validated_data_sources.append(validated_ds)

                    if not validated_data_sources:
                        raise ValueError(
                            "没有有效的数据源配置，请检查数据源配置是否完整"
                        )

                    task_config["data_sources"] = validated_data_sources
                    logger.info(
                        f"[任务 {task_id}] 使用任务配置的数据源: {[ds.get('name') for ds in validated_data_sources]}"
                    )
                else:
                    # 使用默认配置中的数据源（启用状态的）
                    logger.info(f"[任务 {task_id}] 使用默认配置的数据源")

                # 将任务配置合并到爬虫配置中（保留默认配置的其他字段）
                crawler_config.config.update(task_config)

                # 检查任务状态（可能在执行前已被停止或暂停）
                task = db.query(Task).filter(Task.id == task_id).first()
                if not task or task.status != "running":
                    logger.info(
                        f"任务状态已改变，停止执行: {task_id}, status={task.status if task else 'None'}"
                    )
                    return

                # 创建爬虫实例
                crawler = PolicyCrawler(crawler_config, progress_callback)

                # 存储爬虫实例引用（用于停止操作）- 线程安全
                with self._crawler_lock:
                    self._crawler_instances[task_id] = crawler

                # 执行爬取
                # 处理关键词：空列表或None表示全量爬取
                keywords = config.get("keywords", [])
                if keywords and isinstance(keywords, list):
                    # 过滤空字符串
                    keywords = [kw for kw in keywords if kw and kw.strip()]
                    if not keywords:  # 如果过滤后为空，表示全量爬取
                        keywords = None
                elif not keywords or (
                    isinstance(keywords, str) and not keywords.strip()
                ):
                    keywords = None

                # 支持 date_range 格式和 start_date/end_date 格式
                date_range = config.get("date_range", {})
                start_date = config.get("start_date") or (
                    date_range.get("start") if date_range else None
                )
                end_date = config.get("end_date") or (
                    date_range.get("end") if date_range else None
                )

                # 清理空字符串
                if (
                    start_date
                    and isinstance(start_date, str)
                    and not start_date.strip()
                ):
                    start_date = None
                if end_date and isinstance(end_date, str) and not end_date.strip():
                    end_date = None

                # 记录爬取模式
                if not keywords and not start_date and not end_date:
                    logger.info(
                        f"[任务 {task_id}] 全量爬取模式：无关键词、无时间范围限制"
                    )
                    if progress_callback:
                        progress_callback(
                            "全量爬取模式：将爬取所有政策（无关键词和时间范围限制）"
                        )
                elif not keywords:
                    logger.info(
                        f"[任务 {task_id}] 全量关键词爬取模式：无关键词，时间范围: {start_date} 至 {end_date}"
                    )
                    if progress_callback:
                        progress_callback(
                            f"全量关键词爬取模式：时间范围 {start_date} 至 {end_date}"
                        )
                elif not start_date and not end_date:
                    logger.info(
                        f"[任务 {task_id}] 关键词爬取模式：关键词={keywords}，无时间范围限制"
                    )
                    if progress_callback:
                        progress_callback(
                            f"关键词爬取模式：关键词={keywords}，无时间范围限制"
                        )

                policies = crawler.search_all_policies(
                    keywords=keywords if keywords else None,
                    start_date=start_date,
                    end_date=end_date,
                    callback=progress_callback,
                    limit_pages=config.get("limit_pages"),
                )

                # 保存政策到数据库
                saved_count = 0
                skipped_count = 0
                failed_count = 0

                # 记录已保存文件的原始路径，用于后续清理
                saved_file_paths = set()

                # 任务运行中邮件通知检查
                email_notified = False  # 标记是否已发送运行中邮件通知

                # 在循环中检查停止标志
                for i, policy in enumerate(policies):
                    # 检查是否请求停止 - 线程安全
                    with self._crawler_lock:
                        crawler = self._crawler_instances.get(task_id)
                        if (
                            crawler
                            and hasattr(crawler, "stop_requested")
                            and crawler.stop_requested
                        ):
                            logger.info(
                                f"[任务 {task_id}] 检测到停止请求，停止处理政策"
                            )
                            # 重新查询任务状态
                            task = db.query(Task).filter(Task.id == task_id).first()
                            if task and task.status == "paused":
                                task.status = "paused"
                            else:
                                task.status = "cancelled"
                            task.end_time = datetime.now(timezone.utc)
                            db.commit()
                            break

                    try:
                        # 对政策进行详细爬取（包括文件生成）
                        logger.info(f"开始详细爬取政策: {policy.title[:50]}...")
                        try:
                            detailed_policy = crawler.crawl_single_policy(
                                policy, callback=progress_callback
                            )
                            if detailed_policy:
                                policy = detailed_policy  # 使用详细爬取的结果
                                logger.info(f"详细爬取完成: {policy.title[:50]}")
                            else:
                                logger.warning(
                                    f"详细爬取失败，使用原始数据: {policy.title[:50]}"
                                )
                        except Exception as e:
                            logger.error(f"详细爬取出错: {e}，使用原始数据继续")

                        # 转换为字典
                        if hasattr(policy, "to_dict"):
                            policy_data = policy.to_dict()
                        elif isinstance(policy, dict):
                            policy_data = policy
                        else:
                            policy_data = {
                                "title": getattr(policy, "title", ""),
                                "pub_date": getattr(policy, "pub_date", ""),
                                "doc_number": getattr(policy, "doc_number", ""),
                                "source": getattr(
                                    policy, "source", getattr(policy, "url", "")
                                ),
                                "content": getattr(policy, "content", ""),
                                "category": getattr(policy, "category", ""),
                                "level": getattr(policy, "level", ""),
                                "validity": getattr(policy, "validity", ""),
                                "effective_date": getattr(policy, "effective_date", ""),
                            }
                            # 尝试获取_data_source（如果policy对象有这个属性）
                            if hasattr(policy, "_data_source") and policy._data_source:
                                policy_data["_data_source"] = policy._data_source

                        # 保存政策（传入task_id，确保每个任务的数据独立）
                        db_policy = self.policy_service.save_policy(
                            db, policy_data, task_id
                        )

                        if db_policy:
                            # 如果爬虫生成了文件，通过storage_service保存文件并更新数据库路径
                            from .storage_service import StorageService

                            storage_service = StorageService()

                            # 处理markdown文件（确保文件已保存到存储服务）
                            if (
                                "markdown_path" in policy_data
                                and policy_data["markdown_path"]
                            ):
                                markdown_path = policy_data["markdown_path"]
                                if os.path.exists(markdown_path):
                                    try:
                                        storage_result = (
                                            storage_service.save_policy_file(
                                                db_policy.id,
                                                "markdown",
                                                markdown_path,
                                                content_type="text/markdown",
                                                task_id=task_id,
                                            )
                                        )
                                        if storage_result.get("success"):
                                            # 如果之前已有本地路径，删除旧文件
                                            old_path = db_policy.markdown_local_path
                                            new_path = storage_result.get("local_path")
                                            if (
                                                old_path
                                                and old_path != new_path
                                                and os.path.exists(old_path)
                                            ):
                                                try:
                                                    os.remove(old_path)
                                                    logger.debug(
                                                        f"删除旧markdown文件: {old_path}"
                                                    )
                                                except Exception as e:
                                                    logger.warning(
                                                        f"删除旧markdown文件失败: {e}"
                                                    )
                                            db_policy.markdown_local_path = new_path
                                            db_policy.markdown_s3_key = (
                                                storage_result.get("s3_key")
                                            )
                                            # 记录原始文件路径，用于后续清理
                                            saved_file_paths.add(markdown_path)
                                            # 删除爬虫输出目录中的原始文件（已保存到存储服务）
                                            try:
                                                if (
                                                    os.path.exists(markdown_path)
                                                    and markdown_path != new_path
                                                ):
                                                    os.remove(markdown_path)
                                                    logger.debug(
                                                        f"删除爬虫输出目录中的markdown文件: {markdown_path}"
                                                    )
                                            except Exception as e:
                                                logger.warning(
                                                    f"删除爬虫输出文件失败: {e}"
                                                )
                                            logger.debug(
                                                f"政策 {db_policy.id} 的markdown文件已保存到存储服务"
                                            )
                                    except Exception as e:
                                        logger.warning(
                                            f"保存政策 {db_policy.id} 的markdown文件失败: {e}"
                                        )

                            # 处理docx文件（确保文件已保存到存储服务）
                            if "docx_path" in policy_data and policy_data["docx_path"]:
                                docx_path = policy_data["docx_path"]
                                if os.path.exists(docx_path):
                                    try:
                                        storage_result = storage_service.save_policy_file(
                                            db_policy.id,
                                            "docx",
                                            docx_path,
                                            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                            task_id=task_id,
                                        )
                                        if storage_result.get("success"):
                                            # 如果之前已有本地路径，删除旧文件
                                            old_path = db_policy.docx_local_path
                                            new_path = storage_result.get("local_path")
                                            if (
                                                old_path
                                                and old_path != new_path
                                                and os.path.exists(old_path)
                                            ):
                                                try:
                                                    os.remove(old_path)
                                                    logger.debug(
                                                        f"删除旧docx文件: {old_path}"
                                                    )
                                                except Exception as e:
                                                    logger.warning(
                                                        f"删除旧docx文件失败: {e}"
                                                    )
                                            db_policy.docx_local_path = new_path
                                            db_policy.docx_s3_key = storage_result.get(
                                                "s3_key"
                                            )
                                            # 记录原始文件路径，用于后续清理
                                            saved_file_paths.add(docx_path)
                                            # 删除爬虫输出目录中的原始文件（已保存到存储服务）
                                            try:
                                                if (
                                                    os.path.exists(docx_path)
                                                    and docx_path != new_path
                                                ):
                                                    os.remove(docx_path)
                                                    logger.debug(
                                                        f"删除爬虫输出目录中的docx文件: {docx_path}"
                                                    )
                                            except Exception as e:
                                                logger.warning(
                                                    f"删除爬虫输出文件失败: {e}"
                                                )
                                            logger.debug(
                                                f"政策 {db_policy.id} 的docx文件已保存到存储服务"
                                            )
                                    except Exception as e:
                                        logger.warning(
                                            f"保存政策 {db_policy.id} 的docx文件失败: {e}"
                                        )

                            # 处理附件（如果爬虫下载了附件）
                            if (
                                hasattr(policy, "_attachment_paths")
                                and policy._attachment_paths
                            ):
                                from ..models.attachment import Attachment

                                for att_info in policy._attachment_paths:
                                    if att_info.get("storage_path") and os.path.exists(
                                        att_info["storage_path"]
                                    ):
                                        try:
                                            # 通过存储服务保存附件（传入task_id，确保附件路径独立）
                                            storage_result = (
                                                storage_service.save_attachment(
                                                    db_policy.id,
                                                    att_info.get("file_name", ""),
                                                    att_info["storage_path"],
                                                    task_id=task_id,
                                                )
                                            )
                                            if storage_result.get("success"):
                                                # 查找或创建附件记录
                                                attachment = (
                                                    db.query(Attachment)
                                                    .filter(
                                                        Attachment.policy_id
                                                        == db_policy.id,
                                                        Attachment.file_url
                                                        == att_info.get("url", ""),
                                                    )
                                                    .first()
                                                )
                                                if not attachment:
                                                    attachment = Attachment(
                                                        policy_id=db_policy.id,
                                                        file_name=att_info.get(
                                                            "name",
                                                            att_info.get(
                                                                "file_name", ""
                                                            ),
                                                        ),
                                                        file_url=att_info.get(
                                                            "url", ""
                                                        ),
                                                        file_size=(
                                                            os.path.getsize(
                                                                att_info["storage_path"]
                                                            )
                                                            if os.path.exists(
                                                                att_info["storage_path"]
                                                            )
                                                            else 0
                                                        ),
                                                        file_type=os.path.splitext(
                                                            att_info.get(
                                                                "file_name", ""
                                                            )
                                                        )[1].lstrip("."),
                                                        file_path=storage_result.get(
                                                            "local_path"
                                                        ),  # 使用正确的字段名
                                                    )
                                                    db.add(attachment)
                                            else:
                                                attachment.file_path = (
                                                    storage_result.get("local_path")
                                                )  # 使用正确的字段名
                                                attachment.file_s3_key = (
                                                    storage_result.get("s3_key")
                                                )  # 使用正确的字段名
                                                logger.debug(
                                                    f"政策 {db_policy.id} 的附件已保存到存储服务"
                                                )
                                        except Exception as e:
                                            logger.warning(
                                                f"保存政策 {db_policy.id} 的附件失败: {e}"
                                            )

                            # 提交文件路径更新
                            db.commit()
                            # 创建任务-政策关联（虽然policy.task_id已经关联，但为了数据一致性，也创建TaskPolicy记录）
                            # 注意：由于policy.task_id已经关联到任务，TaskPolicy主要用于查询和统计
                            try:
                                task_policy = TaskPolicy(
                                    task_id=task_id, policy_id=db_policy.id
                                )
                                db.add(task_policy)
                                db.commit()  # 提交TaskPolicy关联
                            except Exception as e:
                                # 如果关联已存在，忽略错误
                                logger.debug(f"TaskPolicy关联可能已存在: {e}")
                                db.rollback()

                            # 检查是否是新创建的（简单判断：爬取时间很近）
                            # 确保时区一致：使用 timezone-aware datetime
                            now_utc = datetime.now(timezone.utc)

                            # 确保 crawl_time 是 timezone-aware
                            if db_policy.crawl_time:
                                if db_policy.crawl_time.tzinfo is None:
                                    # 假设是UTC时间，添加时区信息
                                    crawl_time_utc = db_policy.crawl_time.replace(
                                        tzinfo=timezone.utc
                                    )
                                else:
                                    crawl_time_utc = db_policy.crawl_time

                                if (now_utc - crawl_time_utc).total_seconds() < 10:
                                    saved_count += 1
                                    if saved_count % 10 == 0:  # 每保存10条更新一次进度
                                        progress_callback(
                                            f"已保存 {saved_count} 条政策..."
                                        )
                                else:
                                    skipped_count += 1
                            else:
                                # 如果没有爬取时间，可能是旧数据
                                skipped_count += 1
                            # 注意：failed_count只在except块中增加，这里不应该增加

                        # 定期更新任务统计信息（每处理20条）
                        total_processed = saved_count + skipped_count + failed_count
                        if total_processed > 0 and total_processed % 20 == 0:
                            try:
                                task = db.query(Task).filter(Task.id == task_id).first()
                                if task:
                                    task.policy_count = len(
                                        policies
                                    )  # 使用实际的政策总数
                                    task.success_count = saved_count
                                    task.failed_count = failed_count + skipped_count
                                    db.commit()

                                    # 检查是否需要发送任务运行中邮件通知（每处理50条检查一次）
                                    if total_processed % 50 == 0 and not email_notified:
                                        try:
                                            from .email_service import get_email_service

                                            email_service = get_email_service()
                                            # 传入db以实时加载配置
                                            if email_service.is_enabled(db):
                                                import asyncio

                                                logger.debug(
                                                    f"发送任务运行中邮件通知: {task.task_name}"
                                                )

                                                loop = asyncio.new_event_loop()
                                                asyncio.set_event_loop(loop)
                                                try:
                                                    result = loop.run_until_complete(
                                                        email_service.send_task_completion_notification(
                                                            task_name=task.task_name,
                                                            task_status="running",
                                                            policy_count=len(policies),
                                                            success_count=saved_count,
                                                            failed_count=failed_count
                                                            + skipped_count,
                                                            start_time=task.start_time,
                                                            end_time=None,  # 运行中没有结束时间
                                                            db=db,
                                                        )
                                                    )

                                                    if result["success"]:
                                                        email_notified = True  # 标记已发送通知，避免重复发送
                                                        logger.info(
                                                            f"✅ 已发送任务运行中邮件通知: {task.task_name}"
                                                        )
                                                    else:
                                                        logger.warning(
                                                            f"❌ 发送任务运行中邮件通知失败: {result.get('message', '未知错误')}"
                                                        )
                                                except Exception as email_error:
                                                    logger.error(
                                                        f"❌ 发送任务运行中邮件通知时发生异常: {email_error}",
                                                        exc_info=True,
                                                    )
                                                finally:
                                                    loop.close()
                                            else:
                                                logger.debug(
                                                    f"邮件服务未启用，跳过任务运行中通知: {task.task_name}"
                                                )
                                        except Exception as e:
                                            logger.warning(
                                                f"发送任务运行中邮件通知失败: {e}"
                                            )

                            except Exception as e:
                                logger.warning(f"更新任务统计失败: {e}")
                                db.rollback()

                    except Exception as e:
                        logger.error(f"保存政策失败: {e}", exc_info=True)
                        failed_count += 1

                # 检查是否是因为停止请求而退出
                task = db.query(Task).filter(Task.id == task_id).first()
                was_stopped = False
                if task_id in self._crawler_instances:
                    crawler = self._crawler_instances[task_id]
                    if hasattr(crawler, "stop_requested") and crawler.stop_requested:
                        was_stopped = True
                        # 如果任务被停止，检查当前状态决定是暂停还是取消
                        if task and task.status == "paused":
                            task.status = "paused"
                            task.error_message = "任务已暂停"
                        else:
                            task.status = "cancelled"
                            task.error_message = "任务已取消"

                if not was_stopped:
                    # 正常完成
                    task.status = "completed"
                    task.policy_count = len(policies)
                    task.success_count = saved_count
                    task.failed_count = failed_count + skipped_count

                task.end_time = datetime.now(timezone.utc)
                db.commit()

                # 清理爬虫实例引用
                if task_id in self._crawler_instances:
                    del self._crawler_instances[task_id]

                logger.info(
                    f"任务完成: {task_id}, 爬取: {len(policies)}, 保存: {saved_count}, 跳过: {skipped_count}, 失败: {failed_count}"
                )

                # 任务完成后自动备份（如果启用）
                if not was_stopped and task.status == "completed":
                    task_config = task.config_json or {}
                    backup_config = task_config.get("backup", {})

                    # 兼容旧的auto_backup配置
                    if task_config.get("auto_backup", False) and not backup_config:
                        backup_config = {"enabled": True, "strategy": "always"}

                    # 检查是否启用备份
                    if backup_config.get("enabled", False):
                        backup_strategy = backup_config.get("strategy", "always")
                        should_backup = False

                        if backup_strategy == "always":
                            should_backup = True
                        elif backup_strategy == "on_success":
                            should_backup = task.status == "completed"
                        elif backup_strategy == "on_new_policies":
                            # 检查是否有新政策
                            new_policies_count = saved_count
                            min_policies = backup_config.get("min_policies", 0)
                            should_backup = new_policies_count >= min_policies

                        if should_backup:
                            try:
                                from .backup_service import BackupService

                                backup_service = BackupService()
                                # 优化备份名称：包含任务名称
                                safe_task_name = "".join(
                                    c
                                    for c in task.task_name
                                    if c.isalnum() or c in (" ", "-", "_")
                                ).strip()[:50]
                                backup_name = f"task_{task_id}_{safe_task_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
                                backup_record = backup_service.create_backup(
                                    db=db,
                                    backup_type="full",
                                    backup_name=backup_name,
                                    source_type="task",
                                    source_id=str(task_id),
                                    backup_strategy=backup_strategy,
                                    source_name=task.task_name,
                                )
                                logger.info(
                                    f"任务 {task_id} 完成后自动备份已创建: {backup_record.id} (策略: {backup_strategy})"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"任务 {task_id} 完成后自动备份失败: {e}"
                                )

                # 如果启用了S3，确保所有已保存的文件都上传到S3
                # 注意：文件在保存政策时已经通过storage_service保存，这里只需要处理可能遗漏的文件
                try:
                    from .storage_service import StorageService

                    storage_service = StorageService()
                    if storage_service.s3_service.is_enabled():
                        logger.info(f"检查任务 {task_id} 的文件是否已上传到S3...")
                        uploaded_count = 0
                        failed_upload_count = 0

                        # 获取任务关联的所有政策
                        task_policies = (
                            db.query(TaskPolicy)
                            .filter(TaskPolicy.task_id == task_id)
                            .all()
                        )
                        policy_ids = [tp.policy_id for tp in task_policies]
                        policies_to_check = (
                            db.query(Policy).filter(Policy.id.in_(policy_ids)).all()
                        )

                        # 检查每个政策的文件，如果本地有但S3没有，则上传
                        for policy in policies_to_check:
                            # 检查markdown文件
                            if (
                                policy.markdown_local_path
                                and os.path.exists(policy.markdown_local_path)
                                and not policy.markdown_s3_key
                            ):
                                try:
                                    # 使用包含task_id的路径，确保与保存时一致
                                    if policy.task_id:
                                        s3_key = f"policies/{policy.task_id}/{policy.id}/{policy.id}.md"
                                    else:
                                        s3_key = f"policies/{policy.id}/{policy.id}.md"
                                    if storage_service.s3_service.upload_file(
                                        policy.markdown_local_path,
                                        s3_key,
                                        content_type="text/markdown",
                                    ):
                                        policy.markdown_s3_key = s3_key
                                        # 删除本地文件（如果配置了只保留S3）
                                        if storage_service.storage_mode == "s3":
                                            os.remove(policy.markdown_local_path)
                                            policy.markdown_local_path = None
                                        db.commit()
                                        uploaded_count += 1
                                        logger.debug(
                                            f"政策 {policy.id} 的markdown文件已上传到S3"
                                        )
                                except Exception as e:
                                    logger.warning(
                                        f"上传政策 {policy.id} 的markdown文件失败: {e}"
                                    )
                                    failed_upload_count += 1

                            # 检查docx文件
                            if (
                                policy.docx_local_path
                                and os.path.exists(policy.docx_local_path)
                                and not policy.docx_s3_key
                            ):
                                try:
                                    # 使用包含task_id的路径，确保与保存时一致
                                    if policy.task_id:
                                        s3_key = f"policies/{policy.task_id}/{policy.id}/{policy.id}.docx"
                                    else:
                                        s3_key = (
                                            f"policies/{policy.id}/{policy.id}.docx"
                                        )
                                    if storage_service.s3_service.upload_file(
                                        policy.docx_local_path,
                                        s3_key,
                                        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                    ):
                                        policy.docx_s3_key = s3_key
                                        # 删除本地文件（如果配置了只保留S3）
                                        if storage_service.storage_mode == "s3":
                                            os.remove(policy.docx_local_path)
                                            policy.docx_local_path = None
                                        db.commit()
                                        uploaded_count += 1
                                        logger.debug(
                                            f"政策 {policy.id} 的docx文件已上传到S3"
                                        )
                                except Exception as e:
                                    logger.warning(
                                        f"上传政策 {policy.id} 的docx文件失败: {e}"
                                    )
                                    failed_upload_count += 1

                        # 清理爬虫输出目录中的残留文件（如果文件已经保存到storage_service）
                        # 注意：只删除已经保存到storage_service的文件，避免误删
                        try:
                            output_dir = crawler_config.config.get(
                                "output_dir", "crawled_data"
                            )
                            markdown_dir = os.path.join(output_dir, "markdown")
                            docx_dir = os.path.join(output_dir, "docx")

                            # 清理markdown目录（只删除已保存的文件）
                            if os.path.exists(markdown_dir):
                                for filename in os.listdir(markdown_dir):
                                    if filename.endswith(".md"):
                                        file_path = os.path.join(markdown_dir, filename)
                                        # 使用记录的原始文件路径来匹配，而不是通过文件名提取ID
                                        # 因为文件名中的数字是markdown_number，不是policy.id
                                        if file_path in saved_file_paths:
                                            try:
                                                os.remove(file_path)
                                                logger.debug(
                                                    f"清理已保存的markdown文件: {filename}"
                                                )
                                            except Exception as e:
                                                logger.warning(
                                                    f"删除文件失败 {file_path}: {e}"
                                                )

                            # 清理docx目录（只删除已保存的文件）
                            if os.path.exists(docx_dir):
                                for filename in os.listdir(docx_dir):
                                    if filename.endswith(".docx"):
                                        file_path = os.path.join(docx_dir, filename)
                                        # 使用记录的原始文件路径来匹配，而不是通过文件名提取ID
                                        # 因为文件名中的数字是markdown_number，不是policy.id
                                        if file_path in saved_file_paths:
                                            try:
                                                os.remove(file_path)
                                                logger.debug(
                                                    f"清理已保存的docx文件: {filename}"
                                                )
                                            except Exception as e:
                                                logger.warning(
                                                    f"删除文件失败 {file_path}: {e}"
                                                )
                        except Exception as e:
                            logger.warning(f"清理输出目录失败: {e}")

                        if uploaded_count > 0 or failed_upload_count > 0:
                            logger.info(
                                f"文件检查完成: 新上传 {uploaded_count} 个, 失败 {failed_upload_count} 个"
                            )
                        else:
                            logger.debug("所有文件已正确保存到存储服务")
                except Exception as e:
                    logger.error(f"上传文件到S3失败: {e}", exc_info=True)
                    db.rollback()

                # 发送邮件通知（如果启用且有收件人）
                try:
                    from .email_service import get_email_service

                    email_service = get_email_service()
                    # 传入db以实时加载配置，确保使用最新配置
                    if email_service.is_enabled(db):
                        import asyncio

                        # 记录邮件通知尝试
                        logger.info(
                            f"尝试发送任务完成邮件通知: {task.task_name} (状态: completed)"
                        )

                        # 创建新的时间循环来发送异步邮件
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(
                                email_service.send_task_completion_notification(
                                    task_name=task.task_name,
                                    task_status="completed",
                                    policy_count=len(policies),
                                    success_count=saved_count,
                                    failed_count=failed_count + skipped_count,
                                    start_time=task.start_time,
                                    end_time=datetime.now(timezone.utc),
                                    db=db,  # 传入db以实时加载配置
                                )
                            )

                            if result["success"]:
                                logger.info(
                                    f"✅ 任务完成邮件通知发送成功: {task.task_name}"
                                )
                            else:
                                logger.error(
                                    f"❌ 任务完成邮件通知发送失败: {result.get('message', '未知错误')}"
                                )

                        except Exception as email_error:
                            logger.error(
                                f"❌ 发送任务完成邮件通知时发生异常: {email_error}",
                                exc_info=True,
                            )
                        finally:
                            loop.close()
                    else:
                        logger.debug(
                            f"邮件服务未启用或未配置，跳过任务完成通知: {task.task_name}"
                        )
                except Exception as e:
                    logger.error(f"❌ 任务完成邮件通知流程异常: {e}", exc_info=True)

            except Exception as e:
                logger.error(f"任务执行失败: {e}", exc_info=True)

                # 检查是否是因为停止请求而退出 - 线程安全
                task = db.query(Task).filter(Task.id == task_id).first()
                was_stopped = False
                with self._crawler_lock:
                    crawler = self._crawler_instances.get(task_id)
                    if (
                        crawler
                        and hasattr(crawler, "stop_requested")
                        and crawler.stop_requested
                    ):
                        was_stopped = True
                        # 如果任务被停止，检查当前状态决定是暂停还是取消
                        if task and task.status == "paused":
                            task.status = "paused"
                            task.error_message = "任务已暂停"
                        else:
                            task.status = "cancelled"
                            task.error_message = "任务已取消"

                if not was_stopped:
                    task.status = "failed"
                    # 清理错误消息中的敏感信息
                    try:
                        from .utils import sanitize_error_message

                        task.error_message = sanitize_error_message(e)
                    except ImportError:
                        # 如果utils模块不存在，使用简单的错误消息
                        task.error_message = f"任务执行失败: {type(e).__name__}"

                task.end_time = datetime.now(timezone.utc)
                db.commit()

                # 清理爬虫实例引用 - 线程安全
                with self._crawler_lock:
                    if task_id in self._crawler_instances:
                        del self._crawler_instances[task_id]

                # 发送邮件通知（如果启用且有收件人）
                try:
                    from .email_service import get_email_service

                    email_service = get_email_service()
                    # 传入db以实时加载配置，确保使用最新配置
                    if email_service.is_enabled(db):
                        import asyncio

                        # 记录邮件通知尝试
                        logger.info(f"尝试发送任务失败邮件通知: {task.task_name}")

                        # 创建新的时间循环来发送异步邮件
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            result = loop.run_until_complete(
                                email_service.send_task_completion_notification(
                                    task_name=task.task_name,
                                    task_status="failed",
                                    policy_count=(
                                        len(policies) if "policies" in locals() else 0
                                    ),
                                    success_count=(
                                        saved_count if "saved_count" in locals() else 0
                                    ),
                                    failed_count=(
                                        failed_count
                                        if "failed_count" in locals()
                                        else 0
                                    ),
                                    error_message=str(e),
                                    start_time=task.start_time,
                                    end_time=datetime.now(timezone.utc),
                                    db=db,  # 传入db以实时加载配置
                                )
                            )

                            if result["success"]:
                                logger.info(
                                    f"✅ 任务失败邮件通知发送成功: {task.task_name}"
                                )
                            else:
                                logger.error(
                                    f"❌ 任务失败邮件通知发送失败: {result.get('message', '未知错误')}"
                                )

                        except Exception as email_error:
                            logger.error(
                                f"❌ 发送任务失败邮件通知时发生异常: {email_error}",
                                exc_info=True,
                            )
                        finally:
                            loop.close()
                    else:
                        logger.debug(
                            f"邮件服务未启用或未配置，跳过任务失败通知: {task.task_name}"
                        )
                except Exception as notify_error:
                    logger.error(
                        f"❌ 任务失败邮件通知流程异常: {notify_error}", exc_info=True
                    )
                except Exception as email_error:
                    logger.warning(f"发送任务失败通知邮件失败: {email_error}")

        except Exception as e:
            logger.error(f"执行任务异常: {e}", exc_info=True)
            # 清理爬虫实例引用 - 线程安全
            with self._crawler_lock:
                if task_id in self._crawler_instances:
                    del self._crawler_instances[task_id]
        finally:
            # 清理运行中的任务记录
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
            # 确保清理爬虫实例引用 - 线程安全
            with self._crawler_lock:
                if task_id in self._crawler_instances:
                    del self._crawler_instances[task_id]
            # 确保总是关闭数据库会话
            try:
                db.close()
            except Exception as e:
                logger.error(f"关闭数据库会话失败: {e}")
