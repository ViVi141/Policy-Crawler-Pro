"""
系统配置管理服务
"""

import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from ..models.system_config import SystemConfig
from ..config import settings

logger = logging.getLogger(__name__)


class ConfigService:
    """系统配置管理服务"""

    @staticmethod
    def _parse_json_value(value: str) -> Any:
        """解析JSON值，如果不是JSON则返回原值"""
        if not value:
            return value
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    @staticmethod
    def _serialize_value(value: Any) -> str:
        """序列化值为JSON字符串"""
        if isinstance(value, str):
            # 检查是否已经是有效的JSON字符串
            try:
                json.loads(value)
                return value  # 已经是JSON字符串，直接返回
            except json.JSONDecodeError:
                return json.dumps(value)  # 普通字符串，需要序列化
        else:
            return json.dumps(value)

    def get_config(
        self, db: Session, config_key: str, category: str = "general"
    ) -> Optional[SystemConfig]:
        """获取配置项"""
        return (
            db.query(SystemConfig)
            .filter(SystemConfig.key == config_key, SystemConfig.category == category)
            .first()
        )

    def get_config_value(
        self,
        db: Session,
        config_key: str,
        default: Any = None,
        category: str = "general",
    ) -> Any:
        """获取配置值"""
        config = self.get_config(db, config_key, category)
        if config:
            return self._parse_json_value(config.value)
        return default

    def set_config(
        self,
        db: Session,
        config_key: str,
        config_value: Any,
        category: str = "general",
        description: Optional[str] = None,
        is_encrypted: bool = False,
    ) -> SystemConfig:
        """设置配置项"""
        # 将值转换为JSON字符串
        value_str = self._serialize_value(config_value)

        config = self.get_config(db, config_key, category)
        if config:
            config.value = value_str
            if description:
                config.description = description
            config.is_encrypted = is_encrypted
            db.commit()
            db.refresh(config)
            logger.info(f"更新配置: {config_key} (category: {category})")
        else:
            config = SystemConfig(
                key=config_key,
                value=value_str,
                category=category,
                description=description or "",
                is_encrypted=is_encrypted,
            )
            db.add(config)
            db.commit()
            db.refresh(config)
            logger.info(f"创建配置: {config_key} (category: {category})")

        return config

    def delete_config(
        self, db: Session, config_key: str, category: str = "general"
    ) -> bool:
        """删除配置项"""
        config = self.get_config(db, config_key, category)
        if config:
            db.delete(config)
            db.commit()
            logger.info(f"删除配置: {config_key} (category: {category})")
            return True
        return False

    def get_all_configs(
        self, db: Session, category: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取所有配置（返回字典）"""
        query = db.query(SystemConfig)
        if category:
            query = query.filter(SystemConfig.category == category)

        configs = query.all()
        result = {}
        for config in configs:
            result[config.key] = self._parse_json_value(config.value)
        return result

    def get_feature_flags(self, db: Session) -> Dict[str, bool]:
        """获取功能开关配置"""
        flags = {
            "s3_enabled": settings.s3_enabled,
            "scheduler_enabled": settings.scheduler_enabled,
            "email_enabled": settings.email_enabled,
            "cache_enabled": settings.cache_enabled,
        }

        # 从数据库读取覆盖值（如果存在）
        for key in flags.keys():
            db_value = self.get_config_value(db, key, category="feature")
            if db_value is not None:
                flags[key] = bool(db_value)

        return flags

    def set_feature_flag(self, db: Session, flag_name: str, enabled: bool) -> bool:
        """设置功能开关"""
        valid_flags = [
            "s3_enabled",
            "scheduler_enabled",
            "email_enabled",
            "cache_enabled",
        ]
        if flag_name not in valid_flags:
            raise ValueError(f"无效的功能开关名称: {flag_name}")

        self.set_config(
            db,
            flag_name,
            enabled,
            category="feature",
            description=f"功能开关: {flag_name}",
        )

        # 注意：这只是在数据库中保存配置，实际生效需要重启应用或动态重载配置
        logger.warning(f"功能开关 {flag_name} 已设置为 {enabled}，需要重启应用才能生效")
        return True

    def get_s3_config(self, db: Session) -> Dict[str, Any]:
        """获取S3配置"""
        return {
            "enabled": self.get_config_value(
                db, "s3_enabled", settings.s3_enabled, category="feature"
            ),
            "bucket_name": self.get_config_value(
                db, "bucket_name", settings.s3_bucket_name, category="s3"
            ),
            "region": self.get_config_value(
                db, "region", settings.s3_region, category="s3"
            ),
            "endpoint_url": self.get_config_value(
                db, "endpoint_url", settings.s3_endpoint_url, category="s3"
            ),
            "access_key_id": self.get_config_value(
                db, "access_key_id", settings.s3_access_key_id, category="s3"
            ),
            "secret_access_key": (
                "***" if settings.s3_secret_access_key else None
            ),  # 不返回真实密钥
        }

    def update_s3_config(self, db: Session, config: Dict[str, Any]) -> Dict[str, Any]:
        """更新S3配置"""
        if "enabled" in config:
            self.set_config(
                db,
                "s3_enabled",
                config["enabled"],
                category="feature",
                description="S3功能开关",
            )
        if "bucket_name" in config:
            self.set_config(
                db,
                "bucket_name",
                config["bucket_name"],
                category="s3",
                description="S3存储桶名称",
            )
        if "region" in config:
            self.set_config(
                db, "region", config["region"], category="s3", description="S3区域"
            )
        if "endpoint_url" in config:
            self.set_config(
                db,
                "endpoint_url",
                config["endpoint_url"],
                category="s3",
                description="S3端点URL",
            )
        if "access_key_id" in config:
            self.set_config(
                db,
                "access_key_id",
                config["access_key_id"],
                category="s3",
                description="S3访问密钥ID",
                is_encrypted=True,
            )
        if "secret_access_key" in config:
            self.set_config(
                db,
                "secret_access_key",
                config["secret_access_key"],
                category="s3",
                description="S3秘密访问密钥",
                is_encrypted=True,
            )

        # 更新环境变量（从数据库读取最新的配置值）
        from ..config import settings
        from .s3_service import reinitialize_s3_service

        # 更新settings中的S3配置
        if "enabled" in config:
            settings.s3_enabled = config["enabled"]
        if "bucket_name" in config:
            settings.s3_bucket_name = config["bucket_name"]
        if "region" in config:
            settings.s3_region = config["region"]
        if "endpoint_url" in config:
            settings.s3_endpoint_url = config["endpoint_url"]
        if "access_key_id" in config:
            settings.s3_access_key_id = config["access_key_id"]
        if "secret_access_key" in config:
            settings.s3_secret_access_key = config["secret_access_key"]

        # 重新初始化S3服务（无需重启）
        reinitialize_s3_service()

        return self.get_s3_config(db)

    def test_s3_connection(
        self, db: Session, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """测试S3连接"""
        try:
            import boto3
            from botocore.exceptions import ClientError

            # 使用提供的配置或从数据库读取
            if config:
                test_config = config.copy()
                # 从config中获取密钥，如果提供了secret_access_key则使用
                secret_key = (
                    config.get("secret_access_key") or settings.s3_secret_access_key
                )
            else:
                s3_config = self.get_s3_config(db)
                test_config = {
                    "bucket_name": s3_config.get("bucket_name")
                    or settings.s3_bucket_name,
                    "region": s3_config.get("region") or settings.s3_region,
                    "endpoint_url": s3_config.get("endpoint_url")
                    or settings.s3_endpoint_url,
                    "access_key_id": s3_config.get("access_key_id")
                    or settings.s3_access_key_id,
                }
                secret_key = settings.s3_secret_access_key

            # 验证必需字段
            if (
                not test_config.get("bucket_name")
                or not test_config.get("access_key_id")
                or not secret_key
            ):
                return {
                    "success": False,
                    "message": "S3配置不完整，缺少必需字段（bucket_name, access_key_id, secret_access_key）",
                }

            # 创建临时S3客户端进行测试
            s3_client = boto3.client(
                "s3",
                endpoint_url=test_config.get("endpoint_url"),
                aws_access_key_id=test_config.get("access_key_id"),
                aws_secret_access_key=secret_key,
                region_name=test_config.get("region", "us-east-1"),
            )

            # 测试连接（尝试列出bucket或获取bucket信息）
            try:
                s3_client.head_bucket(Bucket=test_config["bucket_name"])
                success = True
                message = "S3连接测试成功"
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "404":
                    success = False
                    message = f"Bucket不存在: {test_config['bucket_name']}"
                elif error_code == "403":
                    success = False
                    message = "无权限访问Bucket"
                else:
                    success = False
                    message = f"S3连接测试失败: {str(e)}"
            except Exception as e:
                success = False
                message = f"S3连接测试失败: {str(e)}"

            return {
                "success": success,
                "message": message,
                "config": {
                    "bucket_name": test_config.get("bucket_name"),
                    "region": test_config.get("region"),
                    "endpoint_url": test_config.get("endpoint_url"),
                },
            }
        except Exception as e:
            logger.error(f"S3连接测试失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"S3连接测试失败: {str(e)}",
                "error": str(e),
            }

    def get_email_config(
        self, db: Session, include_password: bool = False
    ) -> Dict[str, Any]:
        """获取邮件配置

        Args:
            include_password: 是否包含密码（用于内部操作，如发送邮件）
        """
        result = {
            "enabled": self.get_config_value(
                db, "email_enabled", settings.email_enabled, category="feature"
            ),
            "smtp_host": self.get_config_value(
                db, "smtp_host", settings.email_smtp_host, category="email"
            ),
            "smtp_port": self.get_config_value(
                db, "smtp_port", settings.email_smtp_port, category="email"
            ),
            "smtp_user": self.get_config_value(
                db, "smtp_user", settings.email_smtp_user, category="email"
            ),
            "from_address": self.get_config_value(
                db, "from_address", settings.email_from_address, category="email"
            ),
            "to_addresses": self.get_config_value(
                db, "to_addresses", settings.email_to_addresses_list, category="email"
            ),
        }

        if include_password:
            # 获取真实密码（用于内部操作）
            smtp_password_config = self.get_config(
                db, "smtp_password", category="email"
            )
            if smtp_password_config:
                result["smtp_password"] = self._parse_json_value(
                    smtp_password_config.value
                )
            else:
                result["smtp_password"] = settings.email_smtp_password
        else:
            result["smtp_password"] = (
                "***" if settings.email_smtp_password else None
            )  # 不返回真实密码

        return result

    def update_email_config(
        self, db: Session, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新邮件配置

        注意：如果启用邮件服务，必须配置收件人地址
        """
        # 更新配置
        if "enabled" in config:
            self.set_config(
                db,
                "email_enabled",
                config["enabled"],
                category="feature",
                description="邮件功能开关",
            )
        if "smtp_host" in config:
            self.set_config(
                db,
                "smtp_host",
                config["smtp_host"],
                category="email",
                description="SMTP服务器地址",
            )
        if "smtp_port" in config:
            self.set_config(
                db,
                "smtp_port",
                config["smtp_port"],
                category="email",
                description="SMTP端口",
            )
        if "smtp_user" in config:
            self.set_config(
                db,
                "smtp_user",
                config["smtp_user"],
                category="email",
                description="SMTP用户名",
            )
        if "smtp_password" in config:
            self.set_config(
                db,
                "smtp_password",
                config["smtp_password"],
                category="email",
                description="SMTP密码",
                is_encrypted=True,
            )
        if "from_address" in config:
            self.set_config(
                db,
                "from_address",
                config["from_address"],
                category="email",
                description="发件人地址",
            )
        if "to_addresses" in config:
            # 确保是列表
            addresses = config["to_addresses"]
            if isinstance(addresses, str):
                # 尝试解析为JSON，如果不是JSON则按逗号分割
                parsed = self._parse_json_value(addresses)
                if isinstance(parsed, list):
                    addresses = parsed
                elif parsed == addresses:  # 不是JSON，是普通字符串
                    addresses = [
                        addr.strip() for addr in addresses.split(",") if addr.strip()
                    ]
                else:
                    addresses = parsed if isinstance(parsed, list) else [parsed]
            elif isinstance(addresses, list):
                addresses = [
                    addr.strip() if isinstance(addr, str) else str(addr)
                    for addr in addresses
                    if addr
                ]
            # 过滤空值
            addresses = [addr for addr in addresses if addr and addr.strip()]
            self.set_config(
                db,
                "to_addresses",
                json.dumps(addresses),
                category="email",
                description="收件人地址列表",
            )

        # 获取更新后的配置
        updated_config = self.get_email_config(db)

        # 验证：如果启用邮件服务，必须配置收件人地址
        enabled = updated_config.get("enabled", False)
        to_addresses = updated_config.get("to_addresses", [])

        if enabled:
            if not to_addresses or len(to_addresses) == 0:
                raise ValueError("启用邮件服务时，必须至少配置一个收件人地址")
            # 验证收件人地址格式
            import re

            email_pattern = re.compile(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            )
            for addr in to_addresses:
                if not email_pattern.match(addr):
                    raise ValueError(f"无效的收件人邮箱地址格式: {addr}")

        return updated_config

    def test_email_connection(
        self, db: Session, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """测试邮件连接"""
        try:
            import aiosmtplib
            import asyncio

            # 使用提供的配置或从数据库读取
            if config:
                test_config = config.copy()
                # 如果config中没有密码，从数据库读取（包含密码）
                if "smtp_password" not in test_config or not test_config.get(
                    "smtp_password"
                ):
                    email_config_with_pwd = self.get_email_config(
                        db, include_password=True
                    )
                    test_config["smtp_password"] = (
                        email_config_with_pwd.get("smtp_password")
                        or settings.email_smtp_password
                    )
            else:
                # 从数据库读取配置（包含密码）
                email_config = self.get_email_config(db, include_password=True)
                test_config = {
                    "smtp_host": email_config.get("smtp_host")
                    or settings.email_smtp_host,
                    "smtp_port": email_config.get("smtp_port")
                    or settings.email_smtp_port,
                    "smtp_user": email_config.get("smtp_user")
                    or settings.email_smtp_user,
                    "smtp_password": email_config.get("smtp_password")
                    or settings.email_smtp_password,
                    "from_address": email_config.get("from_address")
                    or settings.email_from_address,
                }

            # 验证必需字段
            required_fields = [
                "smtp_host",
                "smtp_port",
                "smtp_user",
                "smtp_password",
                "from_address",
            ]
            missing_fields = [f for f in required_fields if not test_config.get(f)]
            if missing_fields:
                return {
                    "success": False,
                    "message": f"缺少必需字段: {', '.join(missing_fields)}",
                    "missing_fields": missing_fields,
                }

            # 异步测试连接
            async def test_smtp():
                try:
                    # 确保所有必需字段都是正确的类型
                    smtp_host = (
                        str(test_config["smtp_host"])
                        if test_config["smtp_host"]
                        else None
                    )
                    smtp_port = (
                        int(test_config["smtp_port"])
                        if test_config["smtp_port"]
                        else None
                    )
                    smtp_user = (
                        str(test_config["smtp_user"])
                        if test_config["smtp_user"]
                        else None
                    )
                    smtp_password = (
                        str(test_config["smtp_password"])
                        if test_config["smtp_password"]
                        else None
                    )

                    if not all([smtp_host, smtp_port, smtp_user, smtp_password]):
                        return False, "邮件配置不完整"

                    # 端口587使用STARTTLS，端口465使用SSL/TLS
                    use_tls = smtp_port == 465
                    start_tls = smtp_port == 587

                    smtp = aiosmtplib.SMTP(
                        hostname=smtp_host,
                        port=smtp_port,
                        use_tls=use_tls,
                        start_tls=start_tls,  # 如果为True，connect()会自动处理STARTTLS
                    )
                    await smtp.connect()
                    # 注意：如果start_tls=True，connect()已经自动处理了STARTTLS升级
                    # 不要再手动调用 starttls()，否则会报错 "Connection already using TLS"
                    await smtp.login(smtp_user, smtp_password)
                    # 某些SMTP服务器可能会立即关闭连接，导致quit()失败
                    # 如果连接测试成功，忽略quit()的错误
                    try:
                        await smtp.quit()
                    except Exception:
                        # 连接测试已成功，quit()失败不影响整体结果
                        pass
                    return True, None
                except Exception as e:
                    return False, str(e)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success, error = loop.run_until_complete(test_smtp())
            finally:
                loop.close()

            if success:
                return {
                    "success": True,
                    "message": "邮件服务器连接测试成功",
                    "config": {
                        "smtp_host": test_config["smtp_host"],
                        "smtp_port": test_config["smtp_port"],
                        "from_address": test_config["from_address"],
                    },
                }
            else:
                return {
                    "success": False,
                    "message": f"邮件服务器连接测试失败: {error}",
                    "error": error,
                }
        except Exception as e:
            logger.error(f"邮件连接测试失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"邮件连接测试失败: {str(e)}",
                "error": str(e),
            }

    def send_test_email(
        self, db: Session, to_address: str, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发送测试邮件"""
        try:
            import aiosmtplib
            import asyncio
            from email.mime.text import MIMEText
            from datetime import datetime

            # 使用提供的配置或从数据库读取
            if config:
                test_config = config.copy()
                # 如果config中没有密码，从数据库读取（包含密码）
                if "smtp_password" not in test_config or not test_config.get(
                    "smtp_password"
                ):
                    email_config_with_pwd = self.get_email_config(
                        db, include_password=True
                    )
                    test_config["smtp_password"] = (
                        email_config_with_pwd.get("smtp_password")
                        or settings.email_smtp_password
                    )
            else:
                # 从数据库读取配置（包含密码）
                email_config = self.get_email_config(db, include_password=True)
                test_config = {
                    "smtp_host": email_config.get("smtp_host")
                    or settings.email_smtp_host,
                    "smtp_port": email_config.get("smtp_port")
                    or settings.email_smtp_port,
                    "smtp_user": email_config.get("smtp_user")
                    or settings.email_smtp_user,
                    "smtp_password": email_config.get("smtp_password")
                    or settings.email_smtp_password,
                    "from_address": email_config.get("from_address")
                    or settings.email_from_address,
                }

            # 验证必需字段
            required_fields = [
                "smtp_host",
                "smtp_port",
                "smtp_user",
                "smtp_password",
                "from_address",
            ]
            missing_fields = [f for f in required_fields if not test_config.get(f)]
            if missing_fields:
                return {
                    "success": False,
                    "message": f"缺少必需字段: {', '.join(missing_fields)}",
                    "missing_fields": missing_fields,
                }

            # 创建测试邮件
            msg = MIMEText(
                f"这是一封测试邮件，发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            msg["Subject"] = "MNR Law Crawler - 测试邮件"
            msg["From"] = test_config["from_address"]
            msg["To"] = to_address

            # 异步发送邮件
            async def send_email():
                try:
                    # 确保所有必需字段都是正确的类型
                    smtp_host = (
                        str(test_config["smtp_host"])
                        if test_config["smtp_host"]
                        else None
                    )
                    smtp_port = (
                        int(test_config["smtp_port"])
                        if test_config["smtp_port"]
                        else None
                    )
                    smtp_user = (
                        str(test_config["smtp_user"])
                        if test_config["smtp_user"]
                        else None
                    )
                    smtp_password = (
                        str(test_config["smtp_password"])
                        if test_config["smtp_password"]
                        else None
                    )

                    if not all([smtp_host, smtp_port, smtp_user, smtp_password]):
                        return False, "邮件配置不完整"

                    # 端口587使用STARTTLS，端口465使用SSL/TLS
                    use_tls = smtp_port == 465
                    start_tls = smtp_port == 587

                    smtp = aiosmtplib.SMTP(
                        hostname=smtp_host,
                        port=smtp_port,
                        use_tls=use_tls,
                        start_tls=start_tls,  # 如果为True，connect()会自动处理STARTTLS
                    )
                    await smtp.connect()
                    # 注意：如果start_tls=True，connect()已经自动处理了STARTTLS升级
                    # 不要再手动调用 starttls()，否则会报错 "Connection already using TLS"
                    await smtp.login(smtp_user, smtp_password)
                    await smtp.send_message(msg)
                    # 某些SMTP服务器在发送完成后会立即关闭连接，导致quit()失败
                    # 如果邮件已成功发送，忽略quit()的错误
                    try:
                        await smtp.quit()
                    except Exception:
                        # 邮件已成功发送，quit()失败不影响整体结果
                        pass
                    return True, None
                except Exception as e:
                    return False, str(e)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success, error = loop.run_until_complete(send_email())
            finally:
                loop.close()

            if success:
                return {
                    "success": True,
                    "message": f"测试邮件已发送到 {to_address}",
                    "to": to_address,
                }
            else:
                return {
                    "success": False,
                    "message": f"发送测试邮件失败: {error}",
                    "error": error,
                }
        except Exception as e:
            logger.error(f"发送测试邮件失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"发送测试邮件失败: {str(e)}",
                "error": str(e),
            }

    def get_crawler_config(self, db: Session) -> Dict[str, Any]:
        """获取爬虫配置"""
        # 默认值
        default_delay = 0.5
        default_use_proxy = False

        return {
            "request_delay": self.get_config_value(
                db, "request_delay", default_delay, category="crawler"
            ),
            "use_proxy": self.get_config_value(
                db, "use_proxy", default_use_proxy, category="crawler"
            ),
        }

    def update_crawler_config(
        self, db: Session, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """更新爬虫配置"""
        if "request_delay" in config:
            delay = float(config["request_delay"])
            if delay < 0:
                raise ValueError("爬取延迟不能小于0")
            self.set_config(
                db,
                "request_delay",
                delay,
                category="crawler",
                description="爬取延迟（秒）",
            )

        if "use_proxy" in config:
            self.set_config(
                db,
                "use_proxy",
                bool(config["use_proxy"]),
                category="crawler",
                description="是否使用代理",
            )

        return self.get_crawler_config(db)
