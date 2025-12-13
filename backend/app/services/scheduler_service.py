"""
定时任务调度服务（基于APScheduler）
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from sqlalchemy.orm import Session

from ..models.scheduled_task import ScheduledTask, ScheduledTaskRun
from ..database import SessionLocal
from ..config import settings
from .task_service import TaskService

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务调度服务"""

    def __init__(self):
        """初始化调度器"""
        self.scheduler: Optional[BackgroundScheduler] = None
        self.task_service = TaskService()
        self._job_mapping: Dict[str, int] = {}  # job_id -> scheduled_task_id
        self._is_enabled: bool = False  # 动态启用状态

        # 初始状态：如果环境变量设置为true，则启动调度器
        if settings.scheduler_enabled:
            self.enable_scheduler()
        else:
            logger.info("定时任务调度服务已禁用（SCHEDULER_ENABLED=False）")

    def _init_scheduler(self):
        """初始化APScheduler"""
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": ThreadPoolExecutor(max_workers=5)}
        job_defaults = {
            "coalesce": True,  # 合并多次调度
            "max_instances": 1,  # 同一任务最多1个实例
            "misfire_grace_time": 300,  # 错过的任务5分钟内仍执行
        }

        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="Asia/Shanghai",  # 使用中国时区
        )

    def enable_scheduler(self):
        """启用调度器（动态）"""
        if self._is_enabled:
            logger.info("定时任务调度器已启用")
            return

        if self.scheduler is None:
            self._init_scheduler()

        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("定时任务调度器已启动")
            # 加载所有已启用的定时任务
            self.load_enabled_tasks()

        self._is_enabled = True
        logger.info("定时任务调度服务已动态启用")

    def disable_scheduler(self):
        """禁用调度器（动态）"""
        if not self._is_enabled:
            logger.info("定时任务调度器已禁用")
            return

        if self.scheduler and self.scheduler.running:
            # 停止所有正在运行的任务
            self.scheduler.remove_all_jobs()
            self.scheduler.shutdown(wait=True)
            logger.info("定时任务调度器已停止")

        self._job_mapping.clear()
        self._is_enabled = False
        logger.info("定时任务调度服务已动态禁用")

    def is_enabled(self) -> bool:
        """检查调度器是否启用"""
        return self._is_enabled

    def start(self):
        """启动调度器（兼容旧接口）"""
        if self._is_enabled:
            if self.scheduler and not self.scheduler.running:
                self.scheduler.start()
                logger.info("定时任务调度器已启动")
                self.load_enabled_tasks()
            else:
                logger.warning("定时任务调度器已在运行")
        else:
            logger.warning("定时任务调度器未启用，请先调用 enable_scheduler()")

    def shutdown(self):
        """关闭调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("定时任务调度器已关闭")

    def load_enabled_tasks(self):
        """从数据库加载所有已启用的定时任务"""
        if not self.scheduler or not self.scheduler.running:
            logger.warning("调度器未运行，无法加载任务")
            return

        db = SessionLocal()
        try:
            enabled_tasks = (
                db.query(ScheduledTask).filter(ScheduledTask.is_enabled == True).all()
            )

            for task in enabled_tasks:
                try:
                    self._add_job(task, db=db)
                    logger.info(f"已加载定时任务: {task.task_name} (ID: {task.id})")
                except Exception as e:
                    logger.error(
                        f"加载定时任务失败: {task.task_name} - {e}", exc_info=True
                    )
        except Exception as e:
            logger.error(f"加载定时任务列表失败: {e}", exc_info=True)
        finally:
            db.close()

    def create_scheduled_task(
        self,
        db: Session,
        task_type: str,
        task_name: str,
        cron_expression: str,
        config: Dict[str, Any],
        is_enabled: bool = False,
    ) -> ScheduledTask:
        """创建定时任务

        Args:
            db: 数据库会话
            task_type: 任务类型（crawl_task/backup_task等）
            task_name: 任务名称（唯一）
            cron_expression: Cron表达式（例如："0 2 * * *"表示每天凌晨2点）
            config: 任务配置
            is_enabled: 是否启用

        Returns:
            ScheduledTask对象
        """
        # 验证cron表达式并解析
        try:
            # Cron表达式格式: "分 时 日 月 周"
            parts = cron_expression.strip().split()
            if len(parts) != 5:
                raise ValueError("Cron表达式必须包含5个字段：分 时 日 月 周")
            trigger = CronTrigger(
                minute=parts[0],
                hour=parts[1],
                day=parts[2],
                month=parts[3],
                day_of_week=parts[4],
            )
        except Exception as e:
            raise ValueError(f"无效的Cron表达式: {cron_expression}, 错误: {e}")

        # 检查任务名称是否已存在
        existing = (
            db.query(ScheduledTask).filter(ScheduledTask.task_name == task_name).first()
        )
        if existing:
            raise ValueError(f"定时任务名称已存在: {task_name}")

        # 计算下次运行时间
        # APScheduler 需要 timezone-aware datetime，使用 UTC
        next_run_time = trigger.get_next_fire_time(None, datetime.now(timezone.utc))

        scheduled_task = ScheduledTask(
            task_type=task_type,
            task_name=task_name,
            cron_expression=cron_expression,
            config_json=config,
            is_enabled=is_enabled,
            next_run_time=next_run_time,
        )

        db.add(scheduled_task)
        db.commit()
        db.refresh(scheduled_task)

        # 如果启用，添加到调度器
        if is_enabled and self.scheduler and self.scheduler.running:
            try:
                self._add_job(scheduled_task, db=db)
                logger.info(f"已添加定时任务到调度器: {task_name}")
            except Exception as e:
                logger.error(
                    f"添加定时任务到调度器失败: {task_name} - {e}", exc_info=True
                )

        logger.info(f"创建定时任务: {task_name} (ID: {scheduled_task.id})")
        return scheduled_task

    def _add_job(self, scheduled_task: ScheduledTask, db: Optional[Session] = None):
        """添加任务到调度器（内部方法）"""
        if not self.scheduler or not self.scheduler.running:
            raise RuntimeError("调度器未运行")

        job_id = f"scheduled_task_{scheduled_task.id}"

        # 如果任务已存在，先移除
        if job_id in self._job_mapping.values():
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass

        # 创建触发器
        parts = scheduled_task.cron_expression.strip().split()
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
        )

        # 添加任务
        self.scheduler.add_job(
            func=self._execute_scheduled_task,
            trigger=trigger,
            id=job_id,
            args=(scheduled_task.id,),
            replace_existing=True,
        )

        self._job_mapping[job_id] = scheduled_task.id

        # 更新下次运行时间
        if db:
            next_run_time = trigger.get_next_fire_time(None, datetime.now(timezone.utc))
            scheduled_task.next_run_time = next_run_time
            db.commit()

    def _execute_scheduled_task(self, scheduled_task_id: int):
        """执行定时任务（内部方法）"""
        db = SessionLocal()
        try:
            scheduled_task = (
                db.query(ScheduledTask)
                .filter(ScheduledTask.id == scheduled_task_id)
                .first()
            )

            if not scheduled_task:
                logger.error(f"定时任务不存在: {scheduled_task_id}")
                return

            if not scheduled_task.is_enabled:
                logger.warning(f"定时任务已禁用，跳过执行: {scheduled_task.task_name}")
                return

            # 记录执行开始
            run_record = ScheduledTaskRun(
                task_id=scheduled_task_id,
                run_time=datetime.now(timezone.utc),
                status="running",
            )
            db.add(run_record)
            db.commit()

            start_time = datetime.now(timezone.utc)
            logger.info(
                f"开始执行定时任务: {scheduled_task.task_name} (ID: {scheduled_task_id})"
            )

            try:
                # 根据任务类型执行不同的逻辑
                if scheduled_task.task_type == "crawl_task":
                    result = self._execute_crawl_task(scheduled_task, db)
                elif scheduled_task.task_type == "backup_task":
                    result = self._execute_backup_task(scheduled_task, db)
                else:
                    raise ValueError(f"未知的任务类型: {scheduled_task.task_type}")

                # 更新执行记录
                end_time = datetime.now(timezone.utc)
                duration = int((end_time - start_time).total_seconds())
                run_record.status = "completed"
                run_record.result_json = result
                run_record.duration_seconds = duration

                # 更新定时任务状态
                scheduled_task.last_run_time = start_time
                scheduled_task.last_run_status = "success"
                scheduled_task.last_run_result = str(result)

                # 更新下次运行时间
                parts = scheduled_task.cron_expression.strip().split()
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4],
                )
                scheduled_task.next_run_time = trigger.get_next_fire_time(
                    None, datetime.now(timezone.utc)
                )

                db.commit()
                logger.info(
                    f"定时任务执行成功: {scheduled_task.task_name}, 耗时: {duration}秒"
                )

                # 检查是否需要备份（在任务完成后）
                if scheduled_task.task_type == "crawl_task":
                    self._check_scheduled_task_backup(
                        scheduled_task, result, db, start_time, end_time
                    )

                # 发送邮件通知（如果启用且有收件人）
                try:
                    from .email_service import get_email_service

                    email_service = get_email_service()
                    # 传入db以实时加载配置
                    if email_service.is_enabled(db) and email_service.to_addresses:
                        import asyncio

                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            task_info = (
                                result.get("task", {})
                                if isinstance(result, dict)
                                else {}
                            )
                            loop.run_until_complete(
                                email_service.send_task_completion_notification(
                                    task_name=scheduled_task.task_name,
                                    task_status="completed",
                                    policy_count=(
                                        task_info.get("policy_count", 0)
                                        if isinstance(task_info, dict)
                                        else 0
                                    ),
                                    success_count=(
                                        task_info.get("success_count", 0)
                                        if isinstance(task_info, dict)
                                        else 0
                                    ),
                                    failed_count=(
                                        task_info.get("failed_count", 0)
                                        if isinstance(task_info, dict)
                                        else 0
                                    ),
                                    start_time=start_time,
                                    end_time=end_time,
                                    db=db,  # 传入db以实时加载配置
                                )
                            )
                        finally:
                            loop.close()
                except Exception as email_error:
                    logger.warning(f"发送定时任务完成通知邮件失败: {email_error}")

            except Exception as e:
                # 记录错误
                end_time = datetime.now(timezone.utc)
                duration = int((end_time - start_time).total_seconds())
                error_msg = str(e)

                run_record.status = "failed"
                run_record.error_message = error_msg
                run_record.duration_seconds = duration

                scheduled_task.last_run_time = start_time
                scheduled_task.last_run_status = "failed"
                scheduled_task.last_run_result = error_msg

                db.commit()
                logger.error(
                    f"定时任务执行失败: {scheduled_task.task_name} - {error_msg}",
                    exc_info=True,
                )

                # 发送邮件通知（如果启用且有收件人）
                try:
                    from .email_service import get_email_service

                    email_service = get_email_service()
                    if email_service.is_enabled(db) and email_service.to_addresses:
                        import asyncio

                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            loop.run_until_complete(
                                email_service.send_task_completion_notification(
                                    task_name=scheduled_task.task_name,
                                    task_status="failed",
                                    policy_count=0,
                                    success_count=0,
                                    failed_count=0,
                                    error_message=error_msg,
                                    db=db,  # 传入db以实时加载配置
                                )
                            )
                        finally:
                            loop.close()
                except Exception as email_error:
                    logger.warning(f"发送定时任务失败通知邮件失败: {email_error}")

        except Exception as e:
            logger.error(f"执行定时任务异常: {scheduled_task_id} - {e}", exc_info=True)
        finally:
            db.close()

    def _check_scheduled_task_backup(
        self,
        scheduled_task: ScheduledTask,
        result: Dict[str, Any],
        db: Session,
        start_time: datetime,
        end_time: datetime,
    ):
        """检查定时任务是否需要备份"""
        backup_config = (
            scheduled_task.config_json.get("backup", {})
            if scheduled_task.config_json
            else {}
        )

        # 如果未启用备份，直接返回
        if not backup_config.get("enabled", False):
            return

        backup_strategy = backup_config.get("strategy", "never")
        should_backup = False

        # 检查备份策略
        if backup_strategy == "never":
            should_backup = False
        elif backup_strategy == "on_success":
            should_backup = result.get("status") == "completed"
        elif backup_strategy == "on_new_policies":
            new_policies_count = result.get("success_count", 0)
            min_policies = backup_config.get("min_policies", 0)
            should_backup = new_policies_count >= min_policies
        elif backup_strategy in ["daily", "weekly", "monthly"]:
            # 按时间策略备份
            should_backup = self._should_backup_by_time(
                scheduled_task.id, backup_strategy, db
            )

        if should_backup:
            try:
                from .backup_service import BackupService

                backup_service = BackupService()

                # 生成备份名称
                if backup_strategy in ["daily", "weekly", "monthly"]:
                    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
                    backup_name = (
                        f"scheduled_{scheduled_task.id}_{backup_strategy}_{date_str}"
                    )
                else:
                    safe_task_name = "".join(
                        c
                        for c in scheduled_task.task_name
                        if c.isalnum() or c in (" ", "-", "_")
                    ).strip()[:50]
                    backup_name = f"scheduled_{scheduled_task.id}_{safe_task_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

                backup_record = backup_service.create_backup(
                    db=db,
                    backup_type="full",
                    backup_name=backup_name,
                    source_type="scheduled",
                    source_id=str(scheduled_task.id),
                    backup_strategy=backup_strategy,
                    source_name=scheduled_task.task_name,
                )

                # 如果配置了最大备份数量，清理旧备份
                max_backups = backup_config.get("max_backups")
                if max_backups:
                    self._cleanup_old_backups(scheduled_task.id, max_backups, db)

                logger.info(
                    f"定时任务 {scheduled_task.id} 完成后自动备份已创建: {backup_record.id} (策略: {backup_strategy})"
                )
            except Exception as e:
                logger.warning(f"定时任务 {scheduled_task.id} 完成后自动备份失败: {e}")

    def _should_backup_by_time(
        self, scheduled_task_id: int, strategy: str, db: Session
    ) -> bool:
        """检查是否应该按时间策略备份"""
        from datetime import date, timedelta
        from sqlalchemy import func
        from ..models.system_config import BackupRecord

        today = date.today()

        if strategy == "daily":
            # 检查今天是否已备份
            existing_backup = (
                db.query(BackupRecord)
                .filter(
                    BackupRecord.source_type == "scheduled",
                    BackupRecord.source_id == str(scheduled_task_id),
                    BackupRecord.backup_strategy == "daily",
                    func.date(BackupRecord.start_time) == today,
                )
                .first()
            )
            return existing_backup is None

        elif strategy == "weekly":
            # 检查本周是否已备份
            week_start = today - timedelta(days=today.weekday())
            existing_backup = (
                db.query(BackupRecord)
                .filter(
                    BackupRecord.source_type == "scheduled",
                    BackupRecord.source_id == str(scheduled_task_id),
                    BackupRecord.backup_strategy == "weekly",
                    func.date(BackupRecord.start_time) >= week_start,
                )
                .first()
            )
            return existing_backup is None

        elif strategy == "monthly":
            # 检查本月是否已备份
            month_start = today.replace(day=1)
            existing_backup = (
                db.query(BackupRecord)
                .filter(
                    BackupRecord.source_type == "scheduled",
                    BackupRecord.source_id == str(scheduled_task_id),
                    BackupRecord.backup_strategy == "monthly",
                    func.date(BackupRecord.start_time) >= month_start,
                )
                .first()
            )
            return existing_backup is None

        return False

    def _cleanup_old_backups(
        self, scheduled_task_id: int, max_backups: int, db: Session
    ):
        """清理旧备份，只保留最新的N个"""
        import os
        from ..models.system_config import BackupRecord

        backups = (
            db.query(BackupRecord)
            .filter(
                BackupRecord.source_type == "scheduled",
                BackupRecord.source_id == str(scheduled_task_id),
            )
            .order_by(BackupRecord.start_time.desc())
            .all()
        )

        if len(backups) > max_backups:
            # 删除多余的备份
            for backup in backups[max_backups:]:
                try:
                    # 删除备份文件
                    if backup.local_path and os.path.exists(backup.local_path):
                        os.remove(backup.local_path)
                    # 删除S3备份（如果有）
                    if backup.s3_key:
                        from .storage_service import StorageService

                        storage_service = StorageService()
                        if storage_service.s3_service.is_enabled():
                            storage_service.s3_service.delete_file(backup.s3_key)
                    # 删除数据库记录
                    db.delete(backup)
                except Exception as e:
                    logger.warning(f"清理旧备份失败: {backup.id} - {e}")

            db.commit()

    def _execute_crawl_task(
        self, scheduled_task: ScheduledTask, db: Session
    ) -> Dict[str, Any]:
        """执行爬虫任务"""
        config = scheduled_task.config_json

        # 创建任务
        task = self.task_service.create_task(
            db=db,
            task_name=f"[定时]{scheduled_task.task_name}",
            task_type=scheduled_task.task_type,  # 使用定时任务的实际类型
            config=config,
            user_id=1,  # 定时任务使用系统用户ID
        )

        # 启动任务（后台执行）
        task = self.task_service.start_task(db=db, task_id=task.id, background=True)

        # 等待任务完成（最多等待5分钟）
        import time

        max_wait_time = 300  # 5分钟
        wait_interval = 2  # 每2秒检查一次
        waited_time = 0

        while waited_time < max_wait_time:
            db.refresh(task)
            if task.status in ["completed", "failed", "cancelled"]:
                break
            time.sleep(wait_interval)
            waited_time += wait_interval

        # 获取任务结果
        from ..models.task import Task

        final_task = db.query(Task).filter(Task.id == task.id).first()

        return {
            "task_id": final_task.id if final_task else task.id,
            "task_name": final_task.task_name if final_task else task.task_name,
            "status": final_task.status if final_task else task.status,
            "success_count": (
                getattr(final_task, "success_count", 0) if final_task else 0
            ),
            "failed_count": getattr(final_task, "failed_count", 0) if final_task else 0,
        }

    def _execute_backup_task(
        self, scheduled_task: ScheduledTask, db: Session
    ) -> Dict[str, Any]:
        """执行备份任务"""
        from .backup_service import BackupService

        config = scheduled_task.config_json or {}
        backup_type = config.get("backup_type", "full")
        backup_name = config.get("backup_name")

        backup_service = BackupService()
        backup_record = backup_service.create_backup(
            db=db, backup_type=backup_type, backup_name=backup_name
        )

        return {
            "backup_id": backup_record.id,
            "backup_type": backup_record.backup_type,
            "status": backup_record.status,
            "file_size": backup_record.file_size,
            "local_path": backup_record.local_path,
            "s3_key": backup_record.s3_key,
        }

    def enable_scheduled_task(
        self, db: Session, scheduled_task_id: int
    ) -> ScheduledTask:
        """启用定时任务"""
        scheduled_task = (
            db.query(ScheduledTask)
            .filter(ScheduledTask.id == scheduled_task_id)
            .first()
        )

        if not scheduled_task:
            raise ValueError(f"定时任务不存在: {scheduled_task_id}")

        if scheduled_task.is_enabled:
            logger.warning(f"定时任务已启用: {scheduled_task.task_name}")
            return scheduled_task

        scheduled_task.is_enabled = True
        db.commit()
        db.refresh(scheduled_task)

        # 添加到调度器（只有当调度器启用时才添加）
        if self._is_enabled and self.scheduler and self.scheduler.running:
            try:
                self._add_job(scheduled_task, db=db)
                logger.info(f"已启用定时任务: {scheduled_task.task_name}")
            except Exception as e:
                logger.error(
                    f"启用定时任务失败: {scheduled_task.task_name} - {e}", exc_info=True
                )
                scheduled_task.is_enabled = False
                db.commit()
                raise

        return scheduled_task

    def disable_scheduled_task(
        self, db: Session, scheduled_task_id: int
    ) -> ScheduledTask:
        """禁用定时任务"""
        scheduled_task = (
            db.query(ScheduledTask)
            .filter(ScheduledTask.id == scheduled_task_id)
            .first()
        )

        if not scheduled_task:
            raise ValueError(f"定时任务不存在: {scheduled_task_id}")

        if not scheduled_task.is_enabled:
            logger.warning(f"定时任务已禁用: {scheduled_task.task_name}")
            return scheduled_task

        scheduled_task.is_enabled = False
        db.commit()

        # 从调度器移除
        if self.scheduler and self.scheduler.running:
            job_id = f"scheduled_task_{scheduled_task_id}"
            try:
                self.scheduler.remove_job(job_id)
                if job_id in self._job_mapping:
                    del self._job_mapping[job_id]
                logger.info(f"已禁用定时任务: {scheduled_task.task_name}")
            except Exception as e:
                logger.warning(
                    f"从调度器移除任务失败: {scheduled_task.task_name} - {e}"
                )

        return scheduled_task

    def delete_scheduled_task(self, db: Session, scheduled_task_id: int) -> bool:
        """删除定时任务"""
        scheduled_task = (
            db.query(ScheduledTask)
            .filter(ScheduledTask.id == scheduled_task_id)
            .first()
        )

        if not scheduled_task:
            return False

        # 更新关联的备份记录
        from ..models.system_config import BackupRecord

        backups = (
            db.query(BackupRecord)
            .filter(
                BackupRecord.source_type == "scheduled",
                BackupRecord.source_id == str(scheduled_task_id),
            )
            .all()
        )

        for backup in backups:
            backup.source_deleted = True
            # 如果还没有保存任务名称，现在保存
            if not backup.source_name:
                backup.source_name = scheduled_task.task_name

        # 如果启用，先从调度器移除
        if scheduled_task.is_enabled and self.scheduler and self.scheduler.running:
            job_id = f"scheduled_task_{scheduled_task_id}"
            try:
                self.scheduler.remove_job(job_id)
                if job_id in self._job_mapping:
                    del self._job_mapping[job_id]
            except Exception as e:
                logger.warning(f"从调度器移除任务失败: {e}")

        # 删除定时任务
        db.delete(scheduled_task)
        db.commit()

        logger.info(
            f"已删除定时任务: {scheduled_task.task_name} (ID: {scheduled_task_id}), 更新了 {len(backups)} 个备份记录"
        )
        return True

    def get_scheduled_task(
        self, db: Session, scheduled_task_id: int
    ) -> Optional[ScheduledTask]:
        """获取定时任务"""
        return (
            db.query(ScheduledTask)
            .filter(ScheduledTask.id == scheduled_task_id)
            .first()
        )

    def get_scheduled_tasks(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 20,
        task_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
    ) -> tuple[List[ScheduledTask], int]:
        """获取定时任务列表"""
        query = db.query(ScheduledTask)

        if task_type:
            query = query.filter(ScheduledTask.task_type == task_type)
        if is_enabled is not None:
            query = query.filter(ScheduledTask.is_enabled == is_enabled)

        total = query.count()
        tasks = (
            query.order_by(ScheduledTask.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return tasks, total

    def get_task_runs(
        self, db: Session, task_id: int, skip: int = 0, limit: int = 20
    ) -> tuple[List[ScheduledTaskRun], int]:
        """获取任务执行历史"""
        query = db.query(ScheduledTaskRun).filter(ScheduledTaskRun.task_id == task_id)

        total = query.count()
        runs = (
            query.order_by(ScheduledTaskRun.run_time.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return runs, total


# 全局调度器实例
_scheduler_service: Optional[SchedulerService] = None


def get_scheduler_service() -> SchedulerService:
    """获取调度器服务单例"""
    global _scheduler_service
    if _scheduler_service is None:
        _scheduler_service = SchedulerService()
    return _scheduler_service
