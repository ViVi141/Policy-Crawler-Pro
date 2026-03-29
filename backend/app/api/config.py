"""
配置管理API路由
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from ..middleware.auth import get_current_user
from ..models.user import User
from ..schemas.config import (
    FeatureFlagsResponse,
    S3ConfigResponse,
    S3ConfigUpdate,
    S3TestRequest,
    EmailConfigResponse,
    EmailConfigUpdate,
    EmailTestRequest,
    TestEmailRequest,
    TestResponse,
    CrawlerConfigResponse,
    CrawlerConfigUpdate,
    KDLTestRequest,
)
from ..services.config_service import ConfigService

router = APIRouter(prefix="/config", tags=["配置管理"])
logger = logging.getLogger(__name__)

config_service = ConfigService()


@router.get("/feature-flags", response_model=FeatureFlagsResponse)
def get_feature_flags(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """获取功能开关"""
    try:
        flags = config_service.get_feature_flags(db)
        return FeatureFlagsResponse(**flags)
    except Exception as e:
        logger.error(f"获取功能开关失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取功能开关失败: {str(e)}")


@router.put("/feature-flags/{flag_name}", response_model=FeatureFlagsResponse)
def update_feature_flag(
    flag_name: str,
    enabled: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新功能开关"""
    try:
        config_service.set_feature_flag(db, flag_name, enabled)
        flags = config_service.get_feature_flags(db)

        # 如果是邮件功能开关，通知邮件服务重新加载配置
        if flag_name == "email_enabled":
            try:
                from ..services.email_service import get_email_service

                email_service = get_email_service()
                email_service.reload_config(db)
                logger.info("邮件服务配置已实时更新")
            except Exception as e:
                logger.warning(f"通知邮件服务重新加载配置失败: {e}")

        return FeatureFlagsResponse(**flags)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新功能开关失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新功能开关失败: {str(e)}")


@router.get("/s3", response_model=S3ConfigResponse)
def get_s3_config(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """获取S3配置"""
    try:
        config = config_service.get_s3_config(db)
        return S3ConfigResponse(**config)
    except Exception as e:
        logger.error(f"获取S3配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取S3配置失败: {str(e)}")


@router.put("/s3", response_model=S3ConfigResponse)
def update_s3_config(
    update: S3ConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新S3配置"""
    try:
        config_dict = update.model_dump(exclude_unset=True)
        config = config_service.update_s3_config(db, config_dict)
        return S3ConfigResponse(**config)
    except Exception as e:
        logger.error(f"更新S3配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新S3配置失败: {str(e)}")


@router.post("/s3/test", response_model=TestResponse)
def test_s3_connection(
    test_request: Optional[S3TestRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """测试S3连接"""
    try:
        config_dict = (
            test_request.model_dump(exclude_unset=True) if test_request else None
        )
        result = config_service.test_s3_connection(db, config_dict)
        return TestResponse(**result)
    except Exception as e:
        logger.error(f"S3连接测试失败: {e}", exc_info=True)
        return TestResponse(
            success=False, message=f"S3连接测试失败: {str(e)}", error=str(e)
        )


@router.get("/email/available")
def check_email_available(db: Session = Depends(get_db)):
    """检查邮件服务是否可用（公开端点，用于登录页面）"""
    try:
        email_config = config_service.get_email_config(db)
        # 检查邮件服务是否启用且配置完整（包括收件人地址）
        enabled = email_config.get("enabled", False)
        has_host = bool(email_config.get("smtp_host"))
        has_user = bool(email_config.get("smtp_user"))
        has_from = bool(email_config.get("from_address"))
        to_addresses = email_config.get("to_addresses", [])
        has_to = bool(to_addresses and len(to_addresses) > 0)

        # 邮件服务可用需要：启用 + 基本配置完整 + 有收件人地址
        available = enabled and has_host and has_user and has_from and has_to
        return {
            "available": available,
            "enabled": enabled,
            "configured": has_host and has_user and has_from and has_to,
        }
    except Exception as e:
        logger.error(f"检查邮件配置失败: {e}", exc_info=True)
        return {"available": False, "enabled": False, "configured": False}


@router.get("/email", response_model=EmailConfigResponse)
def get_email_config(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """获取邮件配置"""
    try:
        config = config_service.get_email_config(db)
        return EmailConfigResponse(**config)
    except Exception as e:
        logger.error(f"获取邮件配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取邮件配置失败: {str(e)}")


@router.put("/email", response_model=EmailConfigResponse)
def update_email_config(
    update: EmailConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新邮件配置

    注意：如果启用邮件服务，必须至少配置一个收件人地址
    配置更新后会自动重新加载，无需重启服务
    """
    try:
        config_dict = update.model_dump(exclude_unset=True)
        config = config_service.update_email_config(db, config_dict)

        # 通知邮件服务重新加载配置
        try:
            from ..services.email_service import get_email_service

            email_service = get_email_service()
            email_service.reload_config(db)
            logger.info("邮件服务配置已实时更新")
        except Exception as e:
            logger.warning(f"通知邮件服务重新加载配置失败: {e}")

        return EmailConfigResponse(**config)
    except HTTPException:
        raise
    except ValueError as e:
        # 验证错误（如缺少收件人地址）
        logger.warning(f"邮件配置验证失败: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新邮件配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新邮件配置失败: {str(e)}")


@router.post("/email/test", response_model=TestResponse)
def test_email_connection(
    test_request: Optional[EmailTestRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """测试邮件服务器连接"""
    try:
        config_dict = (
            test_request.model_dump(exclude_unset=True) if test_request else None
        )
        result = config_service.test_email_connection(db, config_dict)
        return TestResponse(**result)
    except Exception as e:
        logger.error(f"邮件连接测试失败: {e}", exc_info=True)
        return TestResponse(
            success=False, message=f"邮件连接测试失败: {str(e)}", error=str(e)
        )


@router.post("/email/send-test", response_model=TestResponse)
def send_test_email(
    request: TestEmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """发送测试邮件"""
    try:
        config_dict = (
            request.config.model_dump(exclude_unset=True) if request.config else None
        )
        result = config_service.send_test_email(db, request.to_address, config_dict)
        return TestResponse(**result)
    except Exception as e:
        logger.error(f"发送测试邮件失败: {e}", exc_info=True)
        return TestResponse(
            success=False, message=f"发送测试邮件失败: {str(e)}", error=str(e)
        )


@router.get("/data-sources")
def get_data_sources(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """获取可用数据源列表"""
    try:
        import json
        from pathlib import Path

        # 定义默认数据源列表
        default_data_sources = [
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
                "law_rule_types": [
                    1,
                    2,
                    3,
                ],  # 1=地方性法规, 2=政府规章, 3=规范性文件
                "enabled": False,
            },
        ]

        # 从config.json读取数据源配置
        config_file = Path("config.json")
        if not config_file.exists():
            config_file = Path("../config.json")

        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                config_data_sources = config_data.get("data_sources", [])

            # 合并配置文件和默认数据源
            # 策略：以配置文件中的数据源为主，但确保所有默认数据源都存在
            data_sources = []
            config_source_names = {ds.get("name") for ds in config_data_sources}

            # 首先添加配置文件中的数据源
            for ds in config_data_sources:
                # 对于广东省法规数据源，确保 law_rule_types 包含所有三种类型
                if ds.get("type") == "gd" or ds.get("name") == "广东省法规":
                    law_rule_types = ds.get("law_rule_types", [])
                    # 确保包含所有三种类型：1=地方性法规, 2=政府规章, 3=规范性文件
                    if not isinstance(law_rule_types, list):
                        law_rule_types = [1, 2, 3]
                    else:
                        # 合并，确保包含所有类型
                        all_types = {1, 2, 3}
                        current_types = set(law_rule_types)
                        if not all_types.issubset(current_types):
                            # 补充缺失的类型
                            law_rule_types = sorted(
                                list(all_types.union(current_types))
                            )
                    ds["law_rule_types"] = law_rule_types
                data_sources.append(ds)

            # 然后添加默认数据源中不存在的数据源（按名称匹配）
            for default_ds in default_data_sources:
                default_name = default_ds.get("name")
                if default_name not in config_source_names:
                    data_sources.append(default_ds)
        else:
            # 使用默认数据源
            data_sources = default_data_sources

        return {"data_sources": data_sources}
    except Exception as e:
        logger.error(f"获取数据源列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取数据源列表失败: {str(e)}")


@router.get("/crawler", response_model=CrawlerConfigResponse)
def get_crawler_config(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """获取爬虫配置"""
    try:
        config = config_service.get_crawler_config(db)
        return CrawlerConfigResponse(**config)
    except Exception as e:
        logger.error(f"获取爬虫配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取爬虫配置失败: {str(e)}")


@router.put("/crawler", response_model=CrawlerConfigResponse)
def update_crawler_config(
    update: CrawlerConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新爬虫配置"""
    try:
        config_dict = update.model_dump(exclude_unset=True)
        config = config_service.update_crawler_config(db, config_dict)
        return CrawlerConfigResponse(**config)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"更新爬虫配置失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"更新爬虫配置失败: {str(e)}")


@router.post("/crawler/test-kdl", response_model=TestResponse)
def test_kdl_connection(
    request: KDLTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """测试快代理连接"""
    try:
        result = config_service.test_kdl_connection(
            db, request.secret_id, request.secret_key
        )
        return TestResponse(**result)
    except Exception as e:
        logger.error(f"测试快代理连接失败: {e}", exc_info=True)
        return TestResponse(
            success=False, message=f"测试快代理连接失败: {str(e)}", error=str(e)
        )
