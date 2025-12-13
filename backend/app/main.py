# ==============================================================================
# MNR Law Crawler Online - FastAPI主应用
# ==============================================================================
#
# 项目名称: MNR Law Crawler Online (自然资源部法规爬虫系统 - Web版)
# 项目地址: https://github.com/ViVi141/MNR-Law-Crawler-Online
# 作者: ViVi141
# 许可证: MIT License
#
# 描述: FastAPI应用的主入口文件，包含路由注册、中间件配置等
#
# ==============================================================================

"""
FastAPI主应用
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from .config import settings
from .database import engine, Base
from .api import auth, policies, tasks, scheduled_tasks, config, backups

# 配置日志
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("应用启动中...")

    # 初始化数据库表（如果不存在）
    # 注意：使用多worker时，多个进程可能同时执行此代码
    # 使用 try-except 捕获并发创建导致的错误
    try:
        # 导入所有模型以确保它们被注册到Base.metadata
        from .models import (
            User,
            Policy,
            Task,
            TaskPolicy,
            Attachment,
            ScheduledTask,
            ScheduledTaskRun,
            SystemConfig,
            BackupRecord,
        )

        # 使用 checkfirst=True 检查表是否存在，避免重复创建
        # 如果表已存在，不会报错
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("数据库表检查完成")
    except Exception as e:
        # 捕获所有可能的错误，包括并发创建导致的错误
        error_msg = str(e).lower()
        # 检查是否是"已存在"相关的错误（表、类型、索引等）
        if any(
            keyword in error_msg
            for keyword in [
                "already exists",
                "duplicate key",
                "pg_type_typname_nsp_index",
                "relation",
                "table",
                "constraint",
            ]
        ):
            logger.info(
                f"数据库表/类型已存在，跳过创建（这是正常的，特别是在多worker环境下）"
            )
        else:
            logger.error(f"数据库表检查失败: {e}")
            logger.exception(e)

    # 创建默认用户（如果不存在）
    # 使用数据库锁和错误处理来防止并发创建
    try:
        from .database import SessionLocal
        from .services.auth_service import AuthService
        from .models.user import User
        from sqlalchemy import text

        db = SessionLocal()
        try:
            # 使用数据库锁来防止并发创建
            # 先尝试获取锁（如果其他进程正在创建，会等待）
            db.execute(text("SELECT pg_advisory_lock(123456)"))
            try:
                # 检查是否有用户（在锁保护下）
                existing_user = db.query(User).filter(User.username == "admin").first()
                if not existing_user:
                    # 创建默认用户
                    try:
                        AuthService.create_default_user(
                            db,
                            username="admin",
                            password="admin123",
                            email="admin@example.com",
                        )
                        logger.info("创建默认用户: admin/admin123")
                    except Exception as create_error:
                        # 捕获创建时的重复键错误（可能其他进程已创建）
                        error_msg = str(create_error).lower()
                        if (
                            "duplicate key" in error_msg
                            or "already exists" in error_msg
                        ):
                            logger.info("默认用户已由其他进程创建，跳过")
                        else:
                            logger.warning(f"创建默认用户时出现错误: {create_error}")
                else:
                    logger.info("默认用户已存在，跳过创建")
            finally:
                # 释放锁
                db.execute(text("SELECT pg_advisory_unlock(123456)"))
        except Exception as db_error:
            # 捕获所有数据库错误，包括锁相关的错误
            error_msg = str(db_error).lower()
            if "duplicate key" in error_msg or "already exists" in error_msg:
                logger.info("默认用户已存在，跳过创建（并发创建检测）")
            else:
                logger.warning(f"创建默认用户时出现错误（可忽略）: {db_error}")
        finally:
            db.close()
    except Exception as e:
        # 如果表不存在等严重错误，记录警告但不阻止启动
        logger.warning(f"创建默认用户失败（可忽略）: {e}")

    # 启动定时任务调度器
    try:
        from .services.scheduler_service import get_scheduler_service

        scheduler_service = get_scheduler_service()
        scheduler_service.start()
        logger.info("定时任务调度器启动完成")

        # 注册文件清理任务（每天凌晨2点执行）
        if scheduler_service.scheduler and scheduler_service.scheduler.running:
            from .services.file_cleanup_service import get_cleanup_service

            cleanup_service = get_cleanup_service()

            def cleanup_job():
                """清理过期临时文件的任务"""
                try:
                    # 执行垃圾回收，释放内存
                    import gc

                    gc.collect()

                    cleanup_service.cleanup_old_files(max_age_hours=24)

                    # 记录内存使用情况
                    import psutil

                    process = psutil.Process()
                    memory_info = process.memory_info()
                    logger.info(
                        f"内存清理完成，当前内存使用: {memory_info.rss / 1024 / 1024:.1f} MB"
                    )

                except Exception as e:
                    logger.error(f"文件清理任务执行失败: {e}", exc_info=True)

            scheduler_service.scheduler.add_job(
                cleanup_job,
                trigger="cron",
                hour=2,
                minute=0,
                id="file_cleanup",
                name="清理过期临时文件",
                replace_existing=True,
            )
            logger.info("文件清理任务已注册（每天凌晨2点执行）")
    except Exception as e:
        logger.error(f"启动定时任务调度器失败: {e}", exc_info=True)

    yield

    # 关闭时执行
    logger.info("应用关闭中...")

    # 关闭定时任务调度器
    try:
        from .services.scheduler_service import get_scheduler_service

        scheduler_service = get_scheduler_service()
        scheduler_service.shutdown()
        logger.info("定时任务调度器已关闭")
    except Exception as e:
        logger.error(f"关闭定时任务调度器失败: {e}", exc_info=True)


# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="自然资源部法规爬虫系统 - Web版本",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    import traceback

    error_detail = str(exc)
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    logger.error(f"异常堆栈: {traceback.format_exc()}")
    # 在调试模式下返回详细错误信息
    if settings.debug:
        return JSONResponse(
            status_code=500, content={"detail": f"服务器内部错误: {error_detail}"}
        )
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误"})


# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(policies.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(scheduled_tasks.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(backups.router, prefix="/api")


# 根路由
@app.get("/")
async def root():
    """根路由"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
