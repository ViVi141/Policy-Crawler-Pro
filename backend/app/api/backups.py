"""
备份管理API路由
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from ..middleware.auth import get_current_user
from ..models.user import User
from ..services.backup_service import BackupService
from ..schemas.backup import (
    BackupRecordResponse,
    BackupRecordListResponse,
    BackupCreateRequest,
    BackupRestoreRequest,
    BackupRestoreResponse,
    BackupCleanupResponse,
)

router = APIRouter(prefix="/backups", tags=["backups"])
backup_service = BackupService()
logger = logging.getLogger(__name__)


@router.post(
    "/", response_model=BackupRecordResponse, status_code=status.HTTP_201_CREATED
)
def create_backup(
    request: BackupCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建数据库备份"""
    try:
        backup_record = backup_service.create_backup(
            db=db, backup_type=request.backup_type, backup_name=request.backup_name
        )
        return BackupRecordResponse.model_validate(backup_record)
    except Exception as e:
        logger.error(f"创建备份失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建备份失败: {str(e)}",
        )


@router.post("/upload", response_model=BackupRecordResponse)
async def upload_backup(
    file: UploadFile = File(..., description="备份文件"),
    backup_name: Optional[str] = Query(None, description="备份名称"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传备份文件并创建备份记录"""
    try:
        # 验证文件类型（filename 在部分客户端可能为空）
        if not file.filename or not file.filename.lower().endswith(".sql"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="只支持 .sql 格式的备份文件",
            )

        # 读取文件内容
        content = await file.read()

        # 创建备份记录
        backup_record = backup_service.create_backup_from_upload(
            db=db,
            file_content=content,
            filename=file.filename,
            backup_name=backup_name,
            user_id=current_user.id,
        )

        return BackupRecordResponse.model_validate(backup_record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传备份失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"上传备份失败: {str(e)}",
        )


@router.get("/", response_model=BackupRecordListResponse)
def get_backups(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    backup_type: Optional[str] = Query(None, description="备份类型筛选"),
    status_filter: Optional[str] = Query(None, alias="status", description="状态筛选"),
    source_type: Optional[str] = Query(
        None, description="来源类型筛选 (manual/task/scheduled)"
    ),
    source_deleted: Optional[bool] = Query(None, description="来源是否已删除筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取备份记录列表"""
    try:
        records, total = backup_service.get_backup_records(
            db=db,
            skip=skip,
            limit=limit,
            backup_type=backup_type,
            status=status_filter,
            source_type=source_type,
            source_deleted=source_deleted,
        )
        return BackupRecordListResponse(
            items=[BackupRecordResponse.model_validate(record) for record in records],
            total=total,
            skip=skip,
            limit=limit,
        )
    except Exception as e:
        logger.error(f"获取备份列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取备份列表失败: {str(e)}",
        )


@router.get("/{backup_id}", response_model=BackupRecordResponse)
def get_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取备份记录详情"""
    try:
        backup_record = backup_service.get_backup_record(db, backup_id)
        if not backup_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="备份记录不存在"
            )
        return BackupRecordResponse.model_validate(backup_record)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取备份详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取备份详情失败: {str(e)}",
        )


@router.post("/{backup_id}/restore", response_model=BackupRestoreResponse)
def restore_backup(
    backup_id: str,
    request: BackupRestoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """恢复数据库备份

    ⚠️ 警告：此操作将覆盖目标数据库的所有数据！
    """
    try:
        result = backup_service.restore_backup(
            backup_id=backup_id, target_database=request.target_database
        )
        return BackupRestoreResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复备份失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"恢复备份失败: {str(e)}",
        )


@router.get("/{backup_id}/download")
def download_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """下载备份文件"""
    try:
        backup_record = backup_service.get_backup_record(db, backup_id)
        if not backup_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="备份记录不存在"
            )

        if backup_record.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="备份未完成，无法下载"
            )

        # 获取备份文件路径
        from pathlib import Path
        import os
        from fastapi.responses import FileResponse

        backup_path = None
        if backup_record.local_path and Path(backup_record.local_path).exists():
            backup_path = backup_record.local_path
        elif backup_record.s3_key:
            # 从S3下载到临时文件
            from ..services.s3_service import S3Service

            s3_service = S3Service()
            if s3_service.is_enabled():
                import tempfile

                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".sql")
                temp_path = temp_file.name
                temp_file.close()
                if s3_service.download_file(backup_record.s3_key, temp_path):
                    backup_path = temp_path
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="从S3下载备份文件失败",
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="备份文件不存在"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="备份文件不存在"
            )

        if not backup_path or not os.path.exists(backup_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="备份文件不存在"
            )

        # 生成下载文件名
        backup_name = backup_record.source_name or backup_record.id
        filename = f"{backup_name}_{backup_record.backup_type}_{backup_record.start_time.strftime('%Y%m%d_%H%M%S')}.sql"

        return FileResponse(
            backup_path, media_type="application/sql", filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载备份失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"下载备份失败: {str(e)}",
        )


@router.delete("/{backup_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_backup(
    backup_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除备份记录和文件"""
    try:
        success = backup_service.delete_backup(db, backup_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="备份记录不存在或无法删除"
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除备份失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除备份失败: {str(e)}",
        )


@router.post("/cleanup", response_model=BackupCleanupResponse)
def cleanup_backups(
    keep_count: int = Query(10, ge=1, le=100, description="保留的备份数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """清理旧备份，保留最新的N个"""
    try:
        result = backup_service.cleanup_old_backups(db, keep_count=keep_count)
        return BackupCleanupResponse(**result)
    except Exception as e:
        logger.error(f"清理备份失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清理备份失败: {str(e)}",
        )
