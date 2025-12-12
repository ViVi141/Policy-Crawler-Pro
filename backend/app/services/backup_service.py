"""
备份服务（数据库备份）
"""

import os
import subprocess
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session
from ..models.system_config import BackupRecord
from ..database import SessionLocal
from ..config import settings
from .storage_service import StorageService
from .s3_service import S3Service

logger = logging.getLogger(__name__)


class BackupService:
    """备份服务"""

    def __init__(self):
        """初始化备份服务"""
        self.storage_service = StorageService()
        self.backup_dir = Path(settings.storage_local_dir) / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"备份服务初始化完成，备份目录: {self.backup_dir}")

    def create_backup(
        self,
        db: Session,
        backup_type: str = "full",
        backup_name: Optional[str] = None,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        backup_strategy: Optional[str] = None,
        source_name: Optional[str] = None,
    ) -> BackupRecord:
        """创建数据库备份

        Args:
            db: 数据库会话
            backup_type: 备份类型 (full/incremental)
            backup_name: 备份名称（可选，默认自动生成）

        Returns:
            BackupRecord对象
        """
        from urllib.parse import urlparse

        # 解析数据库URL
        db_url = urlparse(settings.database_url)
        db_name = db_url.path.lstrip("/")
        db_host = db_url.hostname or "localhost"
        db_port = db_url.port or 5432
        db_user = db_url.username
        db_password = db_url.password

        # 生成备份文件名
        if not backup_name:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_name = f"{db_name}_{backup_type}_{timestamp}"

        backup_id = str(uuid.uuid4())
        backup_file = f"{backup_name}.sql"
        backup_path = self.backup_dir / backup_file

        # 创建备份记录
        backup_record = BackupRecord(
            id=backup_id,
            backup_type=backup_type,
            status="pending",
            start_time=datetime.now(timezone.utc),
            local_path=str(backup_path),
            source_type=source_type,
            source_id=str(source_id) if source_id else None,
            backup_strategy=backup_strategy,
            source_name=source_name,
            source_deleted=False,
        )
        db.add(backup_record)
        db.commit()
        db.refresh(backup_record)

        try:
            # 使用pg_dump执行备份
            logger.info(f"开始创建数据库备份: {backup_name}")

            # 设置环境变量（用于pg_dump）
            env = os.environ.copy()
            if db_password:
                env["PGPASSWORD"] = db_password

            # 构建pg_dump命令
            cmd = [
                "pg_dump",
                "-h",
                db_host,
                "-p",
                str(db_port),
                "-U",
                db_user,
                "-d",
                db_name,
                "-F",
                "c",  # 自定义格式
                "-f",
                str(backup_path),
            ]

            # 备份策略说明：
            # 1. pg_dump不支持真正的增量备份（只备份变更的数据）
            # 2. 可以实现基于时间的差异备份策略：
            #    - 使用--schema-only和--data-only分离模式和数据
            #    - 结合备份时间戳，可以实现差异备份
            # 3. 真正的增量备份需要：
            #    - PostgreSQL的WAL归档（Write-Ahead Logging）
            #    - 使用pg_basebackup进行基础备份
            #    - 使用pg_receivewal接收WAL流
            # 4. 当前实现为完整备份，适合中小型数据库
            #    对于大型数据库，建议：
            #    - 使用表级备份（--table选项）
            #    - 配置WAL归档实现连续备份
            #    - 使用pgBackRest或Barman等专业备份工具

            # 可选：基于时间的备份优化
            # 如果backup_type为"incremental"，可以只备份最近N天的数据
            # 这里保持完整备份以确保数据一致性

            # 执行备份
            result = subprocess.run(
                cmd, env=env, capture_output=True, text=True, timeout=3600  # 1小时超时
            )

            if result.returncode != 0:
                raise Exception(f"pg_dump执行失败: {result.stderr}")

            # 获取文件大小
            file_size = os.path.getsize(backup_path)
            file_size_str = self._format_file_size(file_size)

            # 更新备份记录
            backup_record.status = "completed"
            backup_record.end_time = datetime.now(timezone.utc)
            backup_record.file_size = file_size_str
            backup_record.local_path = str(backup_path)

            # 如果启用S3，上传到S3
            if settings.s3_enabled:
                try:
                    s3_service = S3Service()
                    if s3_service.is_enabled():
                        s3_key = f"backups/{backup_file}"
                        s3_service.upload_file(str(backup_path), s3_key)
                        backup_record.s3_key = s3_key
                        logger.info(f"备份已上传到S3: {s3_key}")
                except Exception as e:
                    logger.warning(f"上传备份到S3失败: {e}")

            db.commit()
            logger.info(f"数据库备份创建成功: {backup_name}, 大小: {file_size_str}")

            # 发送邮件通知（如果启用且有收件人）
            try:
                from .email_service import get_email_service

                email_service = get_email_service()
                # 传入db以实时加载配置
                if email_service.is_enabled(db) and email_service.to_addresses:
                    import asyncio
                    from datetime import datetime

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(
                            email_service.send_backup_notification(
                                backup_type=backup_type,
                                backup_path=str(backup_path),
                                file_size=file_size_str,
                                status="completed",
                                start_time=backup_record.start_time,
                                end_time=backup_record.end_time,
                                db=db,  # 传入db以实时加载配置
                            )
                        )
                    finally:
                        loop.close()
            except Exception as email_error:
                logger.warning(f"发送备份通知邮件失败: {email_error}")

            return backup_record

        except Exception as e:
            # 更新备份记录为失败
            backup_record.status = "failed"
            backup_record.end_time = datetime.now(timezone.utc)
            backup_record.error_message = str(e)
            db.commit()

            logger.error(f"创建数据库备份失败: {backup_name} - {e}", exc_info=True)

            # 发送邮件通知（如果启用且有收件人）
            try:
                from .email_service import get_email_service

                email_service = get_email_service()
                # 传入db以实时加载配置
                if email_service.is_enabled(db) and email_service.to_addresses:
                    import asyncio
                    from datetime import datetime

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(
                            email_service.send_backup_notification(
                                backup_type=backup_type,
                                backup_path=(
                                    str(backup_path) if backup_path.exists() else "N/A"
                                ),
                                file_size="0",
                                status="failed",
                                error_message=str(e),
                                start_time=backup_record.start_time,
                                end_time=backup_record.end_time,
                                db=db,  # 传入db以实时加载配置
                            )
                        )
                    finally:
                        loop.close()
            except Exception as email_error:
                logger.warning(f"发送备份失败通知邮件失败: {email_error}")

            raise

    def restore_backup(
        self, backup_record_id: str, target_database: Optional[str] = None
    ) -> Dict[str, Any]:
        """恢复数据库备份

        Args:
            backup_record_id: 备份记录ID
            target_database: 目标数据库名称（如果为None，使用原数据库）

        Returns:
            恢复结果字典
        """
        db = SessionLocal()
        try:
            backup_record = (
                db.query(BackupRecord)
                .filter(BackupRecord.id == backup_record_id)
                .first()
            )

            if not backup_record:
                raise ValueError(f"备份记录不存在: {backup_record_id}")

            if backup_record.status != "completed":
                raise ValueError(f"备份记录状态无效: {backup_record.status}")

            # 获取备份文件路径
            backup_path = None
            if backup_record.local_path and Path(backup_record.local_path).exists():
                backup_path = backup_record.local_path
            elif backup_record.s3_key:
                # 从S3下载备份文件
                try:
                    s3_service = S3Service()
                    if s3_service.is_enabled():
                        backup_path = s3_service.download_file_to_temp(
                            backup_record.s3_key
                        )
                except Exception as e:
                    raise Exception(f"从S3下载备份文件失败: {e}")
            else:
                raise ValueError("找不到备份文件")

            if not backup_path or not Path(backup_path).exists():
                raise ValueError(f"备份文件不存在: {backup_path}")

            # 解析数据库URL
            from urllib.parse import urlparse

            db_url = urlparse(settings.database_url)
            db_name = target_database or db_url.path.lstrip("/")
            db_host = db_url.hostname or "localhost"
            db_port = db_url.port or 5432
            db_user = db_url.username
            db_password = db_url.password

            # 使用pg_restore恢复备份
            logger.warning(f"开始恢复数据库备份: {backup_record_id} -> {db_name}")
            logger.warning("⚠️  注意：这将覆盖目标数据库的所有数据！")

            # 设置环境变量
            env = os.environ.copy()
            if db_password:
                env["PGPASSWORD"] = db_password

            # 构建pg_restore命令
            cmd = [
                "pg_restore",
                "-h",
                db_host,
                "-p",
                str(db_port),
                "-U",
                db_user,
                "-d",
                db_name,
                "--clean",  # 清理现有对象
                "--if-exists",  # 如果对象不存在则不报错
                str(backup_path),
            ]

            # 执行恢复
            result = subprocess.run(
                cmd, env=env, capture_output=True, text=True, timeout=3600  # 1小时超时
            )

            if result.returncode != 0:
                raise Exception(f"pg_restore执行失败: {result.stderr}")

            logger.info(f"数据库备份恢复成功: {backup_record_id} -> {db_name}")

            return {
                "success": True,
                "message": f"备份已恢复到数据库: {db_name}",
                "backup_id": backup_record_id,
                "target_database": db_name,
            }

        except Exception as e:
            logger.error(f"恢复数据库备份失败: {backup_record_id} - {e}", exc_info=True)
            return {
                "success": False,
                "message": f"恢复备份失败: {str(e)}",
                "error": str(e),
            }
        finally:
            db.close()

    def get_backup_records(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 20,
        backup_type: Optional[str] = None,
        status: Optional[str] = None,
        source_type: Optional[str] = None,
        source_deleted: Optional[bool] = None,
    ) -> tuple[List[BackupRecord], int]:
        """获取备份记录列表"""
        query = db.query(BackupRecord)

        if backup_type:
            query = query.filter(BackupRecord.backup_type == backup_type)
        if status:
            query = query.filter(BackupRecord.status == status)
        if source_type:
            query = query.filter(BackupRecord.source_type == source_type)
        if source_deleted is not None:
            query = query.filter(BackupRecord.source_deleted == source_deleted)

        total = query.count()
        records = (
            query.order_by(BackupRecord.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return records, total

    def get_backup_record(self, db: Session, backup_id: str) -> Optional[BackupRecord]:
        """获取备份记录"""
        return db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()

    def delete_backup(self, db: Session, backup_id: str) -> bool:
        """删除备份记录和文件"""
        backup_record = (
            db.query(BackupRecord).filter(BackupRecord.id == backup_id).first()
        )

        if not backup_record:
            return False

        # 删除本地文件
        if backup_record.local_path and Path(backup_record.local_path).exists():
            try:
                os.remove(backup_record.local_path)
                logger.info(f"已删除本地备份文件: {backup_record.local_path}")
            except Exception as e:
                logger.warning(f"删除本地备份文件失败: {e}")

        # 删除S3文件
        if backup_record.s3_key:
            try:
                s3_service = S3Service()
                if s3_service.is_enabled():
                    s3_service.delete_file(backup_record.s3_key)
                    logger.info(f"已删除S3备份文件: {backup_record.s3_key}")
            except Exception as e:
                logger.warning(f"删除S3备份文件失败: {e}")

        # 删除记录
        db.delete(backup_record)
        db.commit()
        logger.info(f"已删除备份记录: {backup_id}")
        return True

    def cleanup_old_backups(self, db: Session, keep_count: int = 10) -> Dict[str, Any]:
        """清理旧备份，保留最新的N个

        Args:
            db: 数据库会话
            keep_count: 保留的备份数量

        Returns:
            清理结果
        """
        try:
            # 获取所有已完成的备份，按创建时间排序
            all_backups = (
                db.query(BackupRecord)
                .filter(BackupRecord.status == "completed")
                .order_by(BackupRecord.created_at.desc())
                .all()
            )

            if len(all_backups) <= keep_count:
                return {
                    "success": True,
                    "message": f"备份数量 ({len(all_backups)}) 未超过保留数量 ({keep_count})，无需清理",
                    "deleted_count": 0,
                    "kept_count": len(all_backups),
                }

            # 删除超过保留数量的备份
            backups_to_delete = all_backups[keep_count:]
            deleted_count = 0

            for backup in backups_to_delete:
                if self.delete_backup(db, backup.id):
                    deleted_count += 1

            return {
                "success": True,
                "message": f"已清理 {deleted_count} 个旧备份，保留 {keep_count} 个最新备份",
                "deleted_count": deleted_count,
                "kept_count": keep_count,
            }
        except Exception as e:
            logger.error(f"清理旧备份失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"清理旧备份失败: {str(e)}",
                "error": str(e),
            }

    def _format_file_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
