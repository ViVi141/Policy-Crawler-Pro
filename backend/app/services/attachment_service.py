"""
附件内容提取和处理服务
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..services.storage_service import StorageService
from ..core.converter import DocumentConverter

logger = logging.getLogger(__name__)


class AttachmentService:
    """附件内容提取和处理服务"""

    def __init__(self):
        """初始化附件服务"""
        self.storage_service = StorageService()
        self.document_converter = DocumentConverter()

    def extract_attachment_content(
        self,
        policy_id: int,
        attachment_filename: str,
        task_id: Optional[int] = None,
        prefer_local_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        从附件文件中提取文本内容

        Args:
            policy_id: 政策ID
            attachment_filename: 附件文件名
            task_id: 任务ID（可选，用于路径构造）
            prefer_local_path: 优先使用的本地绝对路径（如爬虫写入的 output_dir/files/…），
                与存储服务标准目录 policies/…/attachments/ 不一致时必须传入，否则合并会找不到文件。

        Returns:
            提取的文本内容，如果提取失败则返回None
        """
        try:
            file_path = None
            if prefer_local_path and os.path.isfile(prefer_local_path):
                file_path = prefer_local_path
            if not file_path:
                file_path = self.storage_service.get_attachment_file_path(
                    policy_id, attachment_filename, task_id
                )

            if not file_path or not os.path.exists(file_path):
                logger.warning(f"附件文件不存在: {file_path}")
                return None

            # 根据文件扩展名选择提取方法
            file_ext = Path(attachment_filename).suffix.lower()

            if file_ext == ".pdf":
                return self.document_converter.extract_pdf_text(file_path)
            elif file_ext in [".docx"]:
                return self.document_converter.extract_docx_text(file_path)
            elif file_ext in [".doc"]:
                return self._extract_doc_content(file_path)
            else:
                logger.info(f"不支持的文件类型: {file_ext}")
                return None

        except Exception as e:
            logger.error(f"提取附件内容失败: {e}", exc_info=True)
            return None

    def _extract_doc_content(self, file_path: str) -> Optional[str]:
        """从DOC文件中提取文本内容"""
        # DOC文件需要先转换为DOCX格式，然后提取文本
        # 这里使用DocumentConverter的doc_to_markdown方法，然后提取纯文本

        try:
            # 先尝试转换为Markdown，然后提取纯文本
            markdown_content = self.document_converter.doc_to_markdown(file_path)
            if markdown_content:
                # 从Markdown中提取纯文本（去除Markdown格式）
                import re

                # 去除Markdown标题标记
                text = re.sub(r"^#{1,6}\s+", "", markdown_content, flags=re.MULTILINE)
                # 去除其他Markdown标记（简化处理）
                text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)  # 粗体
                text = re.sub(r"\*([^*]+)\*", r"\1", text)  # 斜体
                text = re.sub(r"`([^`]+)`", r"\1", text)  # 代码
                text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)  # 链接
                return text.strip()

            logger.warning("DOC文件转换失败，无法提取内容")
            return None

        except Exception as e:
            logger.error(f"DOC内容提取失败: {e}")
            return None

    def merge_attachment_to_content(
        self,
        policy_id: int,
        attachment_ids: List[int],
        task_id: Optional[int] = None,
        separator: str = "\n\n--- 附件内容 ---\n\n",
    ) -> Dict[str, Any]:
        """
        将多个附件的文本内容合并到政策正文中

        Args:
            policy_id: 政策ID
            attachment_ids: 要合并的附件ID列表
            task_id: 任务ID（可选）
            separator: 附件内容之间的分隔符

        Returns:
            包含合并结果的字典
        """
        result = {
            "success": False,
            "merged_content": "",
            "processed_attachments": [],
            "errors": [],
        }

        try:
            from ..models.attachment import Attachment
            from ..database import SessionLocal

            db = SessionLocal()
            try:
                # 获取附件信息
                attachments = (
                    db.query(Attachment)
                    .filter(Attachment.id.in_(attachment_ids))
                    .filter(Attachment.policy_id == policy_id)
                    .all()
                )

                merged_parts = []

                for attachment in attachments:
                    try:
                        # 提取附件内容（优先使用数据库中的 file_path，兼容爬虫目录 crawled_data/files）
                        content = self.extract_attachment_content(
                            policy_id,
                            attachment.file_name,
                            task_id,
                            prefer_local_path=attachment.file_path,
                        )

                        if content:
                            attachment_info = {
                                "id": attachment.id,
                                "filename": attachment.file_name,
                                "content_length": len(content),
                                "success": True,
                            }
                            merged_parts.append(f"附件: {attachment.file_name}")
                            merged_parts.append(content)
                        else:
                            attachment_info = {
                                "id": attachment.id,
                                "filename": attachment.file_name,
                                "success": False,
                                "error": "无法提取内容",
                            }
                            result["errors"].append(
                                f"附件 {attachment.file_name} 内容提取失败"
                            )

                        result["processed_attachments"].append(attachment_info)

                    except Exception as e:
                        logger.error(f"处理附件 {attachment.file_name} 失败: {e}")
                        result["errors"].append(
                            f"附件 {attachment.file_name} 处理失败: {str(e)}"
                        )
                        result["processed_attachments"].append(
                            {
                                "id": attachment.id,
                                "filename": attachment.file_name,
                                "success": False,
                                "error": str(e),
                            }
                        )

                # 合并内容
                if merged_parts:
                    result["merged_content"] = separator.join(merged_parts)
                    result["success"] = True
                else:
                    result["errors"].append("没有成功提取到任何附件内容")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"合并附件内容失败: {e}", exc_info=True)
            result["errors"].append(f"系统错误: {str(e)}")

        return result

    def get_supported_formats(self) -> List[str]:
        """获取支持的文件格式列表"""
        formats = []

        if getattr(self.document_converter, "PDF_AVAILABLE", False):
            formats.append("PDF")
        if getattr(self.document_converter, "MAMMOTH_AVAILABLE", False) or getattr(
            self.document_converter, "DOCX_AVAILABLE", False
        ):
            formats.append("DOCX")
        # DOC格式支持依赖于LibreOffice或poword
        if getattr(self.document_converter, "LIBREOFFICE_AVAILABLE", False) or getattr(
            self.document_converter, "POWORD_AVAILABLE", False
        ):
            formats.append("DOC")

        return formats

    def check_dependencies(self) -> Dict[str, bool]:
        """检查依赖库是否可用"""
        # 通过DocumentConverter获取依赖状态
        return {
            "mammoth": getattr(self.document_converter, "MAMMOTH_AVAILABLE", False),
            "pypdf": getattr(self.document_converter, "PDF_AVAILABLE", False),
            "python_docx": getattr(self.document_converter, "DOCX_AVAILABLE", False),
        }
