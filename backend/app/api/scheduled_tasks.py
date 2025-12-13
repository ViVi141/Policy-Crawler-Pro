"""
定时任务API路由
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import logging

from ..database import get_db
from ..middleware.auth import get_current_user
from ..models.user import User
from ..schemas.scheduled_task import (
    ScheduledTaskCreate,
    ScheduledTaskUpdate,
    ScheduledTaskResponse,
    ScheduledTaskListItem,
    ScheduledTaskListResponse,
    ScheduledTaskRunsResponse,
)
from ..services.scheduler_service import get_scheduler_service
from ..config import settings

router = APIRouter(prefix="/scheduled-tasks", tags=["定时任务"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=ScheduledTaskResponse, status_code=201)
def create_scheduled_task(
    task_data: ScheduledTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建定时任务"""
    scheduler_service = get_scheduler_service()
    if not scheduler_service.is_enabled():
        raise HTTPException(
            status_code=400,
            detail="定时任务功能未启用，请在系统配置中启用定时任务功能",
        )

    try:
        scheduler_service = get_scheduler_service()
        task = scheduler_service.create_scheduled_task(
            db=db,
            task_type=task_data.task_type,
            task_name=task_data.task_name,
            cron_expression=task_data.cron_expression,
            config=task_data.config,
            is_enabled=task_data.is_enabled,
        )
        return ScheduledTaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建定时任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"创建定时任务失败: {str(e)}")


@router.get("/", response_model=ScheduledTaskListResponse)
def get_scheduled_tasks(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    task_type: Optional[str] = Query(None, description="任务类型筛选"),
    is_enabled: Optional[bool] = Query(None, description="是否启用筛选"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取定时任务列表"""
    try:
        scheduler_service = get_scheduler_service()
        tasks, total = scheduler_service.get_scheduled_tasks(
            db=db, skip=skip, limit=limit, task_type=task_type, is_enabled=is_enabled
        )

        items = [ScheduledTaskListItem.model_validate(task) for task in tasks]

        return ScheduledTaskListResponse(
            items=items, total=total, skip=skip, limit=limit
        )
    except Exception as e:
        logger.error(f"获取定时任务列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取定时任务列表失败: {str(e)}")


@router.get("/{task_id}", response_model=ScheduledTaskResponse)
def get_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取定时任务详情"""
    try:
        scheduler_service = get_scheduler_service()
        task = scheduler_service.get_scheduled_task(db, task_id)

        if not task:
            raise HTTPException(status_code=404, detail="定时任务不存在")

        return ScheduledTaskResponse.model_validate(task)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取定时任务详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取定时任务详情失败: {str(e)}")


@router.put("/{task_id}/enable", response_model=ScheduledTaskResponse)
def enable_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """启用定时任务"""
    scheduler_service = get_scheduler_service()
    if not scheduler_service.is_enabled():
        raise HTTPException(status_code=400, detail="定时任务功能未启用")

    try:
        scheduler_service = get_scheduler_service()
        task = scheduler_service.enable_scheduled_task(db, task_id)
        return ScheduledTaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"启用定时任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"启用定时任务失败: {str(e)}")


@router.put("/{task_id}/disable", response_model=ScheduledTaskResponse)
def disable_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """禁用定时任务"""
    try:
        scheduler_service = get_scheduler_service()
        task = scheduler_service.disable_scheduled_task(db, task_id)
        return ScheduledTaskResponse.model_validate(task)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"禁用定时任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"禁用定时任务失败: {str(e)}")


@router.delete("/{task_id}", status_code=204)
def delete_scheduled_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除定时任务"""
    try:
        scheduler_service = get_scheduler_service()
        success = scheduler_service.delete_scheduled_task(db, task_id)

        if not success:
            raise HTTPException(status_code=404, detail="定时任务不存在")

        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除定时任务失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除定时任务失败: {str(e)}")


@router.get("/{task_id}/runs", response_model=ScheduledTaskRunsResponse)
def get_task_runs(
    task_id: int,
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取定时任务执行历史"""
    try:
        scheduler_service = get_scheduler_service()
        runs, total = scheduler_service.get_task_runs(
            db=db, task_id=task_id, skip=skip, limit=limit
        )

        from ..schemas.scheduled_task import ScheduledTaskRunResponse

        items = [ScheduledTaskRunResponse.model_validate(run) for run in runs]

        return ScheduledTaskRunsResponse(
            items=items, total=total, skip=skip, limit=limit
        )
    except Exception as e:
        logger.error(f"获取任务执行历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取任务执行历史失败: {str(e)}")
