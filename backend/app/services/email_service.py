"""
邮件服务（基于aiosmtplib）
"""

import logging
from typing import Optional, List, Dict, Any
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta

from ..config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务（支持实时配置更新）"""

    def __init__(self):
        """初始化邮件服务"""
        self._load_config()

    def _load_config(self, db: Optional[Any] = None):
        """从数据库或settings加载配置（实时更新）"""
        # 尝试从数据库加载配置
        if db is None:
            # 如果没有传入db，自己创建会话
            should_close_db = True
            try:
                from ..database import SessionLocal

                db = SessionLocal()
            except Exception as e:
                logger.warning(f"无法连接数据库加载邮件配置，使用默认配置: {e}")
                # 从settings加载默认配置
                self.enabled = settings.email_enabled
                self.smtp_host = settings.email_smtp_host
                self.smtp_port = settings.email_smtp_port
                self.smtp_user = settings.email_smtp_user
                self.smtp_password = settings.email_smtp_password
                self.from_address = settings.email_from_address
                self.to_addresses = settings.email_to_addresses_list
                return
        else:
            # 如果传入了db，不要关闭它
            should_close_db = False

        try:
            from .config_service import ConfigService

            config_service = ConfigService()
            email_config = config_service.get_email_config(db, include_password=True)

            self.enabled = email_config.get("enabled", settings.email_enabled)
            self.smtp_host = email_config.get("smtp_host") or settings.email_smtp_host
            self.smtp_port = email_config.get("smtp_port") or settings.email_smtp_port
            self.smtp_user = email_config.get("smtp_user") or settings.email_smtp_user
            self.smtp_password = (
                email_config.get("smtp_password") or settings.email_smtp_password
            )
            self.from_address = (
                email_config.get("from_address") or settings.email_from_address
            )
            to_addresses_str = email_config.get("to_addresses", "[]")
            if isinstance(to_addresses_str, str):
                import json

                try:
                    self.to_addresses = json.loads(to_addresses_str)
                except Exception:
                    self.to_addresses = settings.email_to_addresses_list
            else:
                self.to_addresses = to_addresses_str or settings.email_to_addresses_list

            if should_close_db:
                db.close()

        except Exception as e:
            logger.warning(f"从数据库加载邮件配置失败，使用默认配置: {e}")
            if should_close_db:
                db.close()

            # 从settings加载默认配置
            self.enabled = settings.email_enabled
            self.smtp_host = settings.email_smtp_host
            self.smtp_port = settings.email_smtp_port
            self.smtp_user = settings.email_smtp_user
            self.smtp_password = settings.email_smtp_password
            self.from_address = settings.email_from_address
            self.to_addresses = settings.email_to_addresses_list

    def reload_config(self, db: Optional[Any] = None):
        """重新加载配置（用于配置更新后）"""
        self._load_config(db)
        logger.info("邮件服务配置已重新加载")

    def is_enabled(self, db: Optional[Any] = None) -> bool:
        """检查邮件服务是否启用且有收件人（实时检查配置）"""
        # 如果提供了db，重新加载配置
        if db is not None:
            self._load_config(db)

        return self.enabled and all(
            [
                self.smtp_host,
                self.smtp_user,
                self.smtp_password,
                self.from_address,
                self.to_addresses,  # 必须有收件人地址
            ]
        )

    async def send_email(
        self,
        subject: str,
        body: str,
        to_addresses: Optional[List[str]] = None,
        body_html: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """发送邮件（支持实时配置更新）

        Args:
            subject: 邮件主题
            body: 邮件正文（纯文本）
            to_addresses: 收件人地址列表（如果为None，使用配置中的默认收件人）
            body_html: 邮件正文（HTML格式，可选）
            db: 数据库会话（可选，如果提供则实时加载配置）

        Returns:
            发送结果字典
        """
        # 如果提供了db，重新加载配置以确保使用最新配置
        if db is not None:
            self._load_config(db)

        if not self.is_enabled(db):
            return {"success": False, "message": "邮件服务未启用或配置不完整"}

        to_list = to_addresses or self.to_addresses
        if not to_list:
            return {"success": False, "message": "未指定收件人地址"}

        try:
            # 创建邮件消息
            if body_html:
                msg = MIMEMultipart("alternative")
                msg.attach(MIMEText(body, "plain", "utf-8"))
                msg.attach(MIMEText(body_html, "html", "utf-8"))
            else:
                msg = MIMEText(body, "plain", "utf-8")

            msg["Subject"] = subject
            msg["From"] = self.from_address
            msg["To"] = ", ".join(to_list)

            # 发送邮件
            # 端口587使用STARTTLS（先建立普通连接，然后升级到TLS）
            # 端口465使用SSL/TLS（直接建立TLS连接）
            use_tls = self.smtp_port == 465
            start_tls = self.smtp_port == 587

            smtp = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                use_tls=use_tls,
                start_tls=start_tls,  # 如果为True，connect()会自动处理STARTTLS，无需手动调用
            )

            await smtp.connect()
            # 注意：如果start_tls=True，connect()已经自动处理了STARTTLS升级
            # 不要再手动调用 starttls()，否则会报错 "Connection already using TLS"
            await smtp.login(self.smtp_user, self.smtp_password)
            await smtp.send_message(msg)
            # 某些SMTP服务器在发送完成后会立即关闭连接，导致quit()失败
            # 如果邮件已成功发送，忽略quit()的错误
            try:
                await smtp.quit()
            except Exception:
                # 邮件已成功发送，quit()失败不影响整体结果
                pass

            logger.info(f"邮件发送成功: {subject} -> {', '.join(to_list)}")
            return {
                "success": True,
                "message": f"邮件已发送到 {', '.join(to_list)}",
                "to": to_list,
            }
        except Exception as e:
            logger.error(f"发送邮件失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"发送邮件失败: {str(e)}",
                "error": str(e),
            }

    async def send_task_start_notification(
        self,
        task_name: str,
        task_type: str,
        data_sources: List[str],
        keywords: Optional[str] = None,
        date_range: Optional[str] = None,
        max_pages: Optional[int] = None,
        to_addresses: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """发送任务开始通知

        Args:
            task_name: 任务名称
            task_type: 任务类型
            data_sources: 数据源列表
            keywords: 关键词（如果有）
            date_range: 日期范围（如果有）
            max_pages: 最大页数（如果有）
            to_addresses: 收件人地址列表
            start_time: 开始时间
            db: 数据库会话（可选，如果提供则实时加载配置）
        """
        if not self.is_enabled(db):
            return {"success": False, "message": "邮件服务未启用或未配置收件人"}

        start_time_str = (
            start_time.strftime("%Y-%m-%d %H:%M:%S")
            if start_time
            else datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        )

        subject = f"[MNR Law Crawler] 任务开始: {task_name}"

        body = f"""
任务开始执行通知

任务名称: {task_name}
任务类型: {task_type}
开始时间: {start_time_str}

配置信息:
- 数据源: {', '.join(data_sources)}
{f"- 关键词: {keywords}" if keywords else ""}
{f"- 日期范围: {date_range}" if date_range else ""}
{f"- 最大页数: {max_pages}" if max_pages else ""}

任务已开始执行，您将收到完成通知。
"""

        body_html = f"""
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
        <h2 style="color: #007acc; border-bottom: 2px solid #007acc; padding-bottom: 10px;">
            ▶ 任务开始执行
        </h2>

        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 5px 0;"><strong>任务名称:</strong> {task_name}</p>
            <p style="margin: 5px 0;"><strong>任务类型:</strong> {task_type}</p>
            <p style="margin: 5px 0;"><strong>开始时间:</strong> {start_time_str}</p>
        </div>

        <h3 style="color: #555; border-bottom: 1px solid #eee; padding-bottom: 5px;">配置信息</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>数据源</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{', '.join(data_sources)}</td>
            </tr>
            {"<tr><td style='padding: 8px; border: 1px solid #ddd;'><strong>关键词</strong></td><td style='padding: 8px; border: 1px solid #ddd;'>" + keywords + "</td></tr>" if keywords else ""}
            {"<tr style='background-color: #f0f0f0;'><td style='padding: 8px; border: 1px solid #ddd;'><strong>日期范围</strong></td><td style='padding: 8px; border: 1px solid #ddd;'>" + date_range + "</td></tr>" if date_range else ""}
            {"<tr><td style='padding: 8px; border: 1px solid #ddd;'><strong>最大页数</strong></td><td style='padding: 8px; border: 1px solid #ddd;'>" + str(max_pages) + "</td></tr>" if max_pages else ""}
        </table>

        <p style="color: #666; font-style: italic;">
            任务已开始执行，您将收到完成通知。
        </p>
    </div>
</body>
</html>
"""

        return await self.send_email(
            subject=subject,
            body=body,
            body_html=body_html,
            to_addresses=to_addresses,
            db=db,
        )

    async def send_task_completion_notification(
        self,
        task_name: str,
        task_status: str,
        policy_count: int = 0,
        success_count: int = 0,
        failed_count: int = 0,
        error_message: Optional[str] = None,
        to_addresses: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """发送任务完成通知（支持实时配置更新）

        Args:
            task_name: 任务名称
            task_status: 任务状态 (completed/failed/paused)
            policy_count: 政策总数
            success_count: 成功数量
            failed_count: 失败数量
            error_message: 错误消息（如果失败）
            to_addresses: 收件人地址列表
            start_time: 开始时间
            end_time: 结束时间
            db: 数据库会话（可选，如果提供则实时加载配置）
        """
        if not self.is_enabled(db):
            return {"success": False, "message": "邮件服务未启用或未配置收件人"}

        status_map = {
            "completed": ("成功", "green", "✓"),
            "failed": ("失败", "red", "✗"),
            "paused": ("已暂停", "orange", "⏸"),
        }
        status_text, status_color, status_icon = status_map.get(
            task_status, ("未知", "gray", "?")
        )

        # 将UTC时间转换为北京时间 (UTC+8)
        def utc_to_beijing(utc_time: datetime) -> str:
            """将UTC时间转换为北京时间字符串"""
            if utc_time.tzinfo is None:
                # 如果时间没有时区信息，假设是UTC
                utc_time = utc_time.replace(tzinfo=timezone.utc)

            # 转换为北京时间 (UTC+8)
            beijing_time = utc_time + timedelta(hours=8)
            return beijing_time.strftime("%Y-%m-%d %H:%M:%S")

        current_time = datetime.now(timezone.utc)
        end_time_str = utc_to_beijing(end_time or current_time)
        start_time_str = utc_to_beijing(start_time) if start_time else "N/A"

        subject = f"[MNR Law Crawler] 任务{status_text}: {task_name}"

        body = f"""
任务执行通知

任务名称: {task_name}
状态: {status_icon} {status_text}
开始时间: {start_time_str}
完成时间: {end_time_str}

统计信息:
- 政策总数: {policy_count}
- 成功数量: {success_count}
- 失败数量: {failed_count}
"""

        if error_message:
            body += f"\n错误信息:\n{error_message}\n"

        body_html = f"""
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
        <h2 style="color: {status_color}; border-bottom: 2px solid {status_color}; padding-bottom: 10px;">
            {status_icon} 任务执行通知
        </h2>
        
        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 5px 0;"><strong>任务名称:</strong> {task_name}</p>
            <p style="margin: 5px 0;"><strong>状态:</strong> <span style="color: {status_color}; font-weight: bold;">{status_text}</span></p>
            <p style="margin: 5px 0;"><strong>开始时间:</strong> {start_time_str}</p>
            <p style="margin: 5px 0;"><strong>完成时间:</strong> {end_time_str}</p>
        </div>
        
        <h3 style="color: #555; border-bottom: 1px solid #eee; padding-bottom: 5px;">统计信息</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>政策总数</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{policy_count}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>成功数量</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd; color: green;">{success_count}</td>
            </tr>
            <tr style="background-color: #f0f0f0;">
                <td style="padding: 8px; border: 1px solid #ddd;"><strong>失败数量</strong></td>
                <td style="padding: 8px; border: 1px solid #ddd; color: red;">{failed_count}</td>
            </tr>
        </table>
"""

        if error_message:
            body_html += f"""
        <h3 style="color: #d32f2f; border-bottom: 1px solid #eee; padding-bottom: 5px;">错误信息</h3>
        <div style="background-color: #ffebee; padding: 15px; border-left: 4px solid #d32f2f; margin: 15px 0;">
            <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;">{error_message}</pre>
        </div>
"""

        body_html += """
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            此邮件由 MNR Law Crawler 系统自动发送
        </p>
    </div>
</body>
</html>
"""

        return await self.send_email(subject, body, to_addresses, body_html, db)

    async def send_backup_notification(
        self,
        backup_type: str,
        backup_path: str,
        file_size: str,
        status: str,
        error_message: Optional[str] = None,
        to_addresses: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """发送备份完成通知（支持实时配置更新）

        Args:
            backup_type: 备份类型 (full/incremental)
            backup_path: 备份文件路径
            file_size: 文件大小
            status: 备份状态 (completed/failed)
            error_message: 错误消息（如果失败）
            to_addresses: 收件人地址列表
            start_time: 开始时间
            end_time: 结束时间
            db: 数据库会话（可选，如果提供则实时加载配置）
        """
        if not self.is_enabled(db):
            return {"success": False, "message": "邮件服务未启用或未配置收件人"}

        status_text = "成功" if status == "completed" else "失败"
        status_color = "green" if status == "completed" else "red"
        status_icon = "✓" if status == "completed" else "✗"

        backup_time = (end_time or datetime.now(timezone.utc)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        start_time_str = (
            start_time.strftime("%Y-%m-%d %H:%M:%S") if start_time else "N/A"
        )
        backup_type_text = "完整备份" if backup_type == "full" else "增量备份"

        subject = f"[MNR Law Crawler] 备份{status_text}: {backup_type_text}"

        body = f"""
数据库备份通知

备份类型: {backup_type_text}
状态: {status_icon} {status_text}
开始时间: {start_time_str}
备份时间: {backup_time}
文件路径: {backup_path}
文件大小: {file_size}
"""

        if error_message:
            body += f"\n错误信息:\n{error_message}\n"

        body_html = f"""
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
        <h2 style="color: {status_color}; border-bottom: 2px solid {status_color}; padding-bottom: 10px;">
            {status_icon} 数据库备份通知
        </h2>
        
        <div style="background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <p style="margin: 5px 0;"><strong>备份类型:</strong> {backup_type_text}</p>
            <p style="margin: 5px 0;"><strong>状态:</strong> <span style="color: {status_color}; font-weight: bold;">{status_text}</span></p>
            <p style="margin: 5px 0;"><strong>开始时间:</strong> {start_time_str}</p>
            <p style="margin: 5px 0;"><strong>备份时间:</strong> {backup_time}</p>
            <p style="margin: 5px 0;"><strong>文件路径:</strong> <code style="background-color: #f0f0f0; padding: 2px 6px; border-radius: 3px;">{backup_path}</code></p>
            <p style="margin: 5px 0;"><strong>文件大小:</strong> <strong>{file_size}</strong></p>
        </div>
"""

        if error_message:
            body_html += f"""
        <h3 style="color: #d32f2f; border-bottom: 1px solid #eee; padding-bottom: 5px;">错误信息</h3>
        <div style="background-color: #ffebee; padding: 15px; border-left: 4px solid #d32f2f; margin: 15px 0;">
            <pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;">{error_message}</pre>
        </div>
"""

        body_html += """
        <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
        <p style="color: #999; font-size: 12px; text-align: center;">
            此邮件由 MNR Law Crawler 系统自动发送
        </p>
    </div>
</body>
</html>
"""

        return await self.send_email(subject, body, to_addresses, body_html, db)

    async def send_system_notification(
        self,
        title: str,
        message: str,
        level: str = "info",  # info/warning/error
        to_addresses: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """发送系统通知

        Args:
            title: 通知标题
            message: 通知消息
            level: 通知级别 (info/warning/error)
            to_addresses: 收件人地址列表
        """
        level_text = {"info": "信息", "warning": "警告", "error": "错误"}.get(
            level, "信息"
        )

        subject = f"[MNR Law Crawler] {level_text}: {title}"

        body = f"""
系统通知

级别: {level_text}
标题: {title}
时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}

{message}
"""

        color_map = {"info": "blue", "warning": "orange", "error": "red"}
        color = color_map.get(level, "blue")

        body_html = f"""
<html>
<head><meta charset="utf-8"></head>
<body>
    <h2 style="color: {color}">系统通知</h2>
    <p><strong>级别:</strong> {level_text}</p>
    <p><strong>标题:</strong> {title}</p>
    <p><strong>时间:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}</p>
    <hr>
    <pre>{message}</pre>
</body>
</html>
"""

        return await self.send_email(subject, body, to_addresses, body_html)


# 全局邮件服务实例
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """获取邮件服务单例"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
