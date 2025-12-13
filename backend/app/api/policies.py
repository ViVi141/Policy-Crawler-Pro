"""
政策API路由
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging
import os

from ..database import get_db
from ..middleware.auth import get_current_user
from ..models.user import User
from ..schemas.policy import (
    PolicyListItem,
    PolicyListResponse,
    PolicySearchRequest,
    PolicyDetailResponse,
    AttachmentResponse,
)
from ..services.policy_service import PolicyService
from ..services.search_service import SearchService

router = APIRouter(prefix="/policies", tags=["policies"])
policy_service = PolicyService()
search_service = SearchService()
logger = logging.getLogger(__name__)


@router.get("/", response_model=PolicyListResponse)
def get_policies(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    category: Optional[str] = Query(None, description="分类筛选"),
    level: Optional[str] = Query(None, description="效力级别筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    keyword: Optional[str] = Query(None, description="关键词搜索"),
    publisher: Optional[str] = Query(None, description="发布机构筛选"),
    source_name: Optional[str] = Query(None, description="数据源筛选"),
    task_id: Optional[int] = Query(
        None, description="任务ID筛选，只返回该任务爬取的政策"
    ),
    use_fulltext: bool = Query(
        False, description="是否使用全文搜索（当提供keyword时）"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取政策列表（带筛选和分页）"""
    try:
        # 过滤空字符串参数，并转换日期格式
        from datetime import date

        parsed_start_date = None
        parsed_end_date = None

        if start_date and start_date.strip():
            try:
                parsed_start_date = date.fromisoformat(start_date.strip())
            except ValueError:
                logger.warning(f"无效的开始日期格式: {start_date}")

        if end_date and end_date.strip():
            try:
                parsed_end_date = date.fromisoformat(end_date.strip())
            except ValueError:
                logger.warning(f"无效的结束日期格式: {end_date}")
        # 过滤空字符串
        filtered_category = category.strip() if category and category.strip() else None
        filtered_level = level.strip() if level and level.strip() else None
        filtered_keyword = keyword.strip() if keyword and keyword.strip() else None
        filtered_publisher = (
            publisher.strip() if publisher and publisher.strip() else None
        )
        filtered_source_name = (
            source_name.strip() if source_name and source_name.strip() else None
        )

        # 统一搜索API：如果提供关键词且启用全文搜索，使用全文搜索；否则使用普通筛选
        if filtered_keyword and use_fulltext:
            # 使用全文搜索
            policies, total = search_service.search(
                db=db,
                query=filtered_keyword,
                skip=skip,
                limit=limit,
                category=filtered_category,
                level=filtered_level,
                start_date=(
                    parsed_start_date.strftime("%Y-%m-%d")
                    if parsed_start_date
                    else None
                ),
                end_date=(
                    parsed_end_date.strftime("%Y-%m-%d") if parsed_end_date else None
                ),
            )
        else:
            # 使用普通筛选
            policies, total = policy_service.get_policies(
                db=db,
                skip=skip,
                limit=limit,
                category=filtered_category,
                level=filtered_level,
                start_date=parsed_start_date,
                end_date=parsed_end_date,
                keyword=filtered_keyword,
                publisher=filtered_publisher,
                source_name=filtered_source_name,
                task_id=task_id,
            )

        # 安全序列化，处理可能的None值
        items = []
        for policy in policies:
            try:
                item_dict = PolicyListItem.model_validate(policy).model_dump()
                # 添加 publish_date 字段用于前端兼容（前端期望 publish_date 而不是 pub_date）
                if item_dict.get("pub_date"):
                    item_dict["publish_date"] = (
                        item_dict["pub_date"].isoformat()
                        if hasattr(item_dict["pub_date"], "isoformat")
                        else str(item_dict["pub_date"])
                    )
                else:
                    item_dict["publish_date"] = None
                # 添加 law_type 字段（前端期望 law_type 而不是 level）
                item_dict["law_type"] = item_dict.get("level")
                items.append(item_dict)
            except Exception as e:
                logger.warning(f"序列化政策失败 (ID: {policy.id}): {e}")
                continue

        # 注意：items 现在是字典列表，但 PolicyListResponse 期望 PolicyListItem 列表
        # 由于 Pydantic 会自动转换，我们可以直接使用字典
        # 但为了类型安全，我们需要手动构造响应
        from typing import Any, Dict

        response_dict: Dict[str, Any] = {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

        # 使用 model_validate 来确保类型正确
        return PolicyListResponse.model_validate(response_dict)
    except Exception as e:
        logger.error(f"获取政策列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取政策列表失败: {str(e)}")


@router.post("/search", response_model=PolicyListResponse)
def search_policies(
    request: PolicySearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """搜索政策（全文搜索）"""
    # 如果有搜索关键词，使用全文搜索；否则使用普通筛选
    if request.keyword:
        policies, total = search_service.search(
            db=db,
            query=request.keyword,
            skip=request.skip,
            limit=request.limit,
            category=request.category,
            level=request.level,
            start_date=(
                request.start_date.strftime("%Y-%m-%d") if request.start_date else None
            ),
            end_date=(
                request.end_date.strftime("%Y-%m-%d") if request.end_date else None
            ),
        )
    else:
        # 无关键词时使用普通筛选
        policies, total = policy_service.get_policies(
            db=db,
            skip=request.skip,
            limit=request.limit,
            category=request.category,
            level=request.level,
            start_date=request.start_date,
            end_date=request.end_date,
            keyword=None,
        )

    items = [PolicyListItem.model_validate(policy) for policy in policies]

    return PolicyListResponse(
        items=items, total=total, skip=request.skip, limit=request.limit
    )


@router.get("/{policy_id}", response_model=PolicyDetailResponse)
def get_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取政策详情"""
    policy = policy_service.get_policy_by_id(db, policy_id)

    if not policy:
        raise HTTPException(status_code=404, detail="政策不存在")

    # 获取附件
    from ..models.attachment import Attachment

    attachments = db.query(Attachment).filter(Attachment.policy_id == policy_id).all()

    detail = PolicyDetailResponse.model_validate(policy)
    detail.attachments = [AttachmentResponse.model_validate(att) for att in attachments]

    # 转换为字典进行字段名映射（与列表页保持一致）
    detail_dict = detail.model_dump()

    # 添加前端期望的字段名（兼容性）
    pub_date_value = detail_dict.get("pub_date")
    logger.info(f"原始pub_date值: {pub_date_value}, 类型: {type(pub_date_value)}")

    if pub_date_value:
        detail_dict["publish_date"] = (
            pub_date_value.isoformat()
            if hasattr(pub_date_value, "isoformat")
            else str(pub_date_value)
        )
        logger.info(f"转换后publish_date: {detail_dict['publish_date']}")
    else:
        detail_dict["publish_date"] = ""
        logger.info("pub_date为空，设置publish_date为空字符串")

    # 确保日期字段格式正确（dayjs期望ISO格式）
    if detail_dict.get("effective_date"):
        detail_dict["effective_date"] = (
            detail_dict["effective_date"].isoformat()
            if hasattr(detail_dict["effective_date"], "isoformat")
            else str(detail_dict["effective_date"])
        )

    if detail_dict.get("created_at"):
        detail_dict["created_at"] = (
            detail_dict["created_at"].isoformat()
            if hasattr(detail_dict["created_at"], "isoformat")
            else str(detail_dict["created_at"])
        )

    # 添加前端期望的字段别名
    detail_dict["publishDate"] = detail_dict.get("publish_date")  # camelCase版本
    detail_dict["effectiveDate"] = detail_dict.get("effective_date")  # camelCase版本
    detail_dict["docNumber"] = detail_dict.get("doc_number")  # camelCase版本
    detail_dict["lawLevel"] = detail_dict.get("level")  # 前端期望的字段名
    detail_dict["law_type"] = detail_dict.get("level")  # 另一个前端期望的字段名
    detail_dict["createdAt"] = detail_dict.get("created_at")  # camelCase版本

    # 调试：打印返回的数据结构
    logger.info(
        f"详细页API返回数据: publisher={detail_dict.get('publisher')}, level={detail_dict.get('level')}, law_type={detail_dict.get('law_type')}"
    )
    logger.info(
        f"详细页API日期字段: pub_date={detail_dict.get('pub_date')}, publish_date={detail_dict.get('publish_date')}, publishDate={detail_dict.get('publishDate')}"
    )
    logger.info(f"详细页API完整数据: {detail_dict}")

    # 直接返回修改后的字典（不重新验证，避免覆盖映射）
    return detail_dict


@router.delete("/{policy_id}")
def delete_policy(
    policy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除政策"""
    success = policy_service.delete_policy(db, policy_id)

    if not success:
        raise HTTPException(status_code=404, detail="政策不存在或删除失败")

    return {"message": "政策已删除", "id": policy_id}


@router.get("/meta/categories", response_model=List[str])
def get_categories(
    source_name: Optional[str] = Query(
        None, description="数据源名称，如果提供则只返回该数据源的分类"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取分类列表（可选按数据源筛选）"""
    return policy_service.get_categories(db, source_name=source_name)


@router.get("/meta/levels", response_model=List[str])
def get_levels(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """获取所有效力级别列表"""
    return policy_service.get_levels(db)


@router.get("/meta/source-names", response_model=List[str])
def get_source_names(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """获取所有数据源名称列表"""
    return policy_service.get_source_names(db)


@router.post("/search/rebuild-index")
def rebuild_search_index(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """重建全文搜索索引"""
    result = search_service.build_search_index(db)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "索引重建失败"))

    return result


@router.get("/{policy_id}/file/{file_type}")
def get_policy_file(
    policy_id: int,
    file_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取政策文件（markdown/docx）"""
    policy = policy_service.get_policy_by_id(db, policy_id)

    if not policy:
        raise HTTPException(status_code=404, detail="政策不存在")

    if file_type not in ["markdown", "docx"]:
        raise HTTPException(status_code=400, detail="不支持的文件类型")

    # 使用存储服务获取文件路径（使用policy的task_id，确保文件路径正确）
    from ..services.storage_service import StorageService

    storage_service = StorageService()
    file_path = storage_service.get_policy_file_path(
        policy_id, file_type, task_id=policy.task_id
    )

    # 如果文件不存在，尝试重新生成（作为后备方案）
    # 注意：正常情况下，文件应该在任务执行时已保存到存储服务
    if not file_path or not os.path.exists(file_path):
        logger.warning(
            f"政策 {policy_id} 的 {file_type} 文件不存在，尝试重新生成（正常情况下文件应在任务执行时已保存）..."
        )
        try:
            # 使用storage_service的临时目录
            from ..services.file_cleanup_service import get_cleanup_service

            cleanup_service = get_cleanup_service()

            temp_base_dir = (
                storage_service.local_dir / "temp_generated" / str(policy_id)
            )
            temp_base_dir.mkdir(parents=True, exist_ok=True)
            # 将文件类型转换为实际扩展名
            file_ext = "md" if file_type == "markdown" else file_type
            temp_file_path = temp_base_dir / f"{policy_id}.{file_ext}"

            # 根据文件类型生成文件
            if file_type == "markdown":
                from .tasks import _generate_markdown_from_policy

                md_content = _generate_markdown_from_policy(policy)
                with open(temp_file_path, "w", encoding="utf-8") as f:
                    f.write(md_content)
            elif file_type == "docx":
                from .tasks import _generate_docx_from_policy
                from ..core.converter import DocumentConverter

                converter = DocumentConverter()
                _generate_docx_from_policy(policy, str(temp_file_path), converter)

            if temp_file_path.exists() and temp_file_path.stat().st_size > 0:
                file_path = str(temp_file_path)
                cleanup_service.register_temp_file(file_path)

                # 重新生成后，保存到存储服务，以便后续使用（使用policy的task_id）
                try:
                    storage_result = storage_service.save_policy_file(
                        policy_id, file_type, file_path, task_id=policy.task_id
                    )
                    if storage_result.get("success"):
                        # 更新数据库中的路径
                        if file_type == "markdown":
                            policy.markdown_local_path = storage_result.get(
                                "local_path"
                            )
                            policy.markdown_s3_key = storage_result.get("s3_key")
                        elif file_type == "docx":
                            policy.docx_local_path = storage_result.get("local_path")
                            policy.docx_s3_key = storage_result.get("s3_key")
                        db.commit()
                        logger.info(
                            f"重新生成的文件已保存到存储服务: {storage_result.get('local_path')}"
                        )
                except Exception as e:
                    logger.warning(f"保存重新生成的文件到存储服务失败: {e}")

                logger.info(f"成功重新生成政策 {policy_id} 的 {file_type} 文件")
            else:
                raise HTTPException(status_code=404, detail="文件不存在且无法重新生成")
        except Exception as e:
            logger.error(f"重新生成政策 {policy_id} 的 {file_type} 文件失败: {e}")
            raise HTTPException(
                status_code=404, detail=f"文件不存在且重新生成失败: {str(e)}"
            )

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    # 返回文件
    from fastapi.responses import FileResponse

    media_type_map = {
        "markdown": "text/markdown",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    # 将文件类型转换为实际扩展名
    file_ext = "md" if file_type == "markdown" else file_type
    return FileResponse(
        file_path,
        media_type=media_type_map.get(file_type, "application/octet-stream"),
        filename=f"policy_{policy_id}.{file_ext}",
    )


@router.get("/{policy_id}/attachments/{attachment_id}/download")
def download_attachment(
    policy_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载附件文件"""
    # 验证政策存在
    policy = policy_service.get_policy_by_id(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="政策不存在")

    # 获取附件
    from ..models.attachment import Attachment

    attachment = (
        db.query(Attachment)
        .filter(Attachment.id == attachment_id, Attachment.policy_id == policy_id)
        .first()
    )

    if not attachment:
        raise HTTPException(status_code=404, detail="附件不存在")

    # 使用存储服务获取文件路径
    from ..services.storage_service import StorageService

    storage_service = StorageService()

    # 获取附件文件路径（使用policy的task_id，确保文件路径正确）
    file_path = None
    if attachment.file_path and os.path.exists(attachment.file_path):
        file_path = attachment.file_path
    elif attachment.file_s3_key:
        # 从S3下载
        file_path = storage_service.get_attachment_file_path(
            policy_id, attachment.file_name, task_id=policy.task_id
        )
    else:
        # 尝试从原始URL下载（如果文件未保存）
        logger.warning(f"附件 {attachment_id} 的文件路径不存在，尝试从URL下载")
        # 这里可以添加从URL下载的逻辑，但通常附件应该已经保存

    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="附件文件不存在")

    # 返回文件
    from fastapi.responses import FileResponse

    return FileResponse(
        file_path, media_type="application/octet-stream", filename=attachment.file_name
    )
