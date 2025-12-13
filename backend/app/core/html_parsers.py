"""
HTML解析器模块
为不同的网站提供专门的解析器
支持UTF-8编码和特殊字符处理
"""

from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable
from urllib.parse import urljoin
import logging
import re
import html

logger = logging.getLogger(__name__)


class BaseHTMLParser:
    """HTML解析器基类"""

    def __init__(self, base_url: str, level: str = "自然资源部"):
        self.base_url = base_url
        self.level = level

    def parse(
        self,
        soup: BeautifulSoup,
        callback: Optional[Callable] = None,
        category_name: str = "",
    ) -> List[Dict]:
        """解析HTML，返回政策列表"""
        raise NotImplementedError

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """解析日期字符串为datetime对象"""
        if not date_str:
            return None
        for fmt in ("%Y年%m月%d日", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
            try:
                return datetime.strptime(date_str, fmt)
            except Exception:
                continue
        return None

    def _clean_text(self, text: str) -> str:
        """清洗文本，处理特殊字符和UTF-8编码问题

        Args:
            text: 原始文本

        Returns:
            清洗后的文本
        """
        if not text:
            return ""

        # 确保文本是UTF-8编码
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")

        # HTML实体解码（处理&nbsp等）
        text = html.unescape(text)

        # 处理常见的特殊字符和不可见字符
        replacements = {
            "\xa0": " ",  # 不间断空格
            "\u2002": " ",  # 间隙
            "\u2003": " ",  # 制表符
            "\u2004": " ",  # 三分之一空白
            "\u2005": " ",  # 四分之一空白
            "\u2006": " ",  # 六分之一空白
            "\u2007": " ",  # 图形变体空白
            "\u2008": " ",  # 标点空白
            "\u2009": " ",  # 薄空格
            "\u200a": " ",  # 头发空格
            "\u200b": "\u00ad",  # 零宽度空格 -> 软连字符
            "\u200c": "",  # 零宽度非连接符
            "\u200d": "",  # 零宽度连接符
            "\u200e": "",  # 左到右标记
            "\u200f": "",  # 右到左标记
            "\u2028": "\n",  # 行分隔符
            "\u2029": "\n",  # 段落分隔符
            "\u202a": "",  # 左到右嵌入
            "\u202b": "",  # 右到左嵌入
            "\u202c": "",  # 弹出方向格式
            "\u202d": "",  # 左到右覆盖
            "\u202e": "",  # 右到左覆盖
            "\u202f": " ",  # 窄不间断空格
            "\u205f": " ",  # 中等数学空格
            "\u2060": "",  # 字连接符
            "\u2061": "",  # 函数应用
            "\u2062": "",  # 不可见乘号
            "\u2063": "",  # 不可见分隔符
            "\u2064": "",  # 不可见加号
            "\u2066": "",  # 左到右隔离
            "\u2067": "",  # 右到左隔离
            "\u2068": "",  # 第一个强隔离
            "\u2069": "",  # 弹出方向隔离
            "\u206a": "",  # 激活对称交换
            "\u206b": "",  # 非激活对称交换
            "\u206c": "",  # 非激活对称交换
            "\u206d": "",  # 激活对称交换
            "\u206e": "",  # 非激活对称交换
            "\u206f": "",  # 名义数字形状
            "\ufeff": "",  # 字节顺序标记
            "\u00ad": "-",  # 软连字符 -> 普通连字符
            "\u2010": "-",  # 连字符
            "\u2011": "-",  # 非断开连字符
            "\u2012": "-",  # 图形连字符
            "\u2013": "-",  # 短破折号
            "\u2014": "-",  # 长破折号
            "\u2015": "-",  # 水平条
            "\u2212": "-",  # 减号
            "\u2044": "/",  # 分数斜杠
            "\u2215": "/",  # 除号
            "\u2018": "'",  # 左单引号
            "\u2019": "'",  # 右单引号
            "\u201a": "'",  # 低位单引号
            "\u201b": "'",  # 单高位反引号
            "\u201c": '"',  # 左双引号
            "\u201d": '"',  # 右双引号
            "\u201e": '"',  # 低位双引号
            "\u201f": '"',  # 双高位反引号
            "\u2039": "<",  # 单左尖括号
            "\u203a": ">",  # 单右尖括号
            "\u00ab": "<<",  # 左双尖括号
            "\u00bb": ">>",  # 右双尖括号
            "\u2026": "...",  # 水平省略号
            "\u2027": ".",  # 连字点
            "\u00b7": "·",  # 中间点
            "\u2219": "·",  # 项目符号
            "\u2022": "•",  # 项目符号
            "\u2023": "‣",  # 三角项目符号
            "\u2043": "⁓",  # 连接符号
            "\u00d7": "×",  # 乘号
            "\u00f7": "÷",  # 除号
            "\u221a": "√",  # 平方根
            "\u221b": "∛",  # 立方根
            "\u221c": "∜",  # 第四根
            "\u2202": "∂",  # 偏导数
            "\u2206": "Δ",  # 增量
            "\u220f": "∏",  # 乘积
            "\u2211": "∑",  # 求和
            "\u221e": "∞",  # 无穷大
            "\u2220": "∠",  # 角
            "\u2229": "∩",  # 交集
            "\u222a": "∪",  # 并集
            "\u2260": "≠",  # 不等于
            "\u2264": "≤",  # 小于等于
            "\u2265": "≥",  # 大于等于
            "\u00b2": "²",  # 上标2
            "\u00b3": "³",  # 上标3
            "\u00b9": "¹",  # 上标1
            "\u00bc": "¼",  # 四分之一
            "\u00bd": "½",  # 二分之一
            "\u00be": "¾",  # 四分之三
            "\u2153": "⅓",  # 三分之一
            "\u2154": "⅔",  # 三分之二
            "\u2155": "⅕",  # 五分之一
            "\u2156": "⅖",  # 五分之二
            "\u2157": "⅗",  # 五分之三
            "\u2158": "⅘",  # 五分之四
            "\u2159": "⅙",  # 六分之一
            "\u215a": "⅚",  # 六分之五
            "\u215b": "⅛",  # 八分之一
            "\u215c": "⅜",  # 八分之三
            "\u215d": "⅝",  # 八分之五
            "\u215e": "⅞",  # 八分之七
            "\u00a9": "(c)",  # 版权符号
            "\u00ae": "(r)",  # 注册商标
            "\u2122": "(tm)",  # 商标
            "\u00a3": "£",  # 英镑
            "\u20ac": "€",  # 欧元
            "\u00a5": "¥",  # 日元
            "\u00a2": "¢",  # 美分
            "\u00b0": "°",  # 度数
            "\u00b1": "±",  # 正负号
            "\u00d8": "Ø",  # 斜线O
            "\u00f8": "ø",  # 斜线o
            "\u00c6": "Æ",  # AE连字（大写）
            "\u00e6": "æ",  # ae连字（小写）
            "\u00c0": "À",  # A重音
            "\u00c1": "Á",  # A重音
            "\u00c2": "Â",  # A重音
            "\u00c3": "Ã",  # A重音
            "\u00c4": "Ä",  # A重音
            "\u00c5": "Å",  # A圆圈
            "\u00c7": "Ç",  # C下加符
            "\u00c8": "È",  # E重音
            "\u00c9": "É",  # E重音
            "\u00ca": "Ê",  # E重音
            "\u00cb": "Ë",  # E重音
            "\u00cc": "Ì",  # I重音
            "\u00cd": "Í",  # I重音
            "\u00ce": "Î",  # I重音
            "\u00cf": "Ï",  # I重音
            "\u00d0": "Ð",  # D上划线
            "\u00d1": "Ñ",  # N波浪
            "\u00d2": "Ò",  # O重音
            "\u00d3": "Ó",  # O重音
            "\u00d4": "Ô",  # O重音
            "\u00d5": "Õ",  # O重音
            "\u00d6": "Ö",  # O重音
            "\u00d9": "Ù",  # U重音
            "\u00da": "Ú",  # U重音
            "\u00db": "Û",  # U重音
            "\u00dc": "Ü",  # U重音
            "\u00dd": "Ý",  # Y重音
            "\u00de": "Þ",  # 冰岛语TH
            "\u00df": "ß",  # 德语双s（德语）
            "\u00e0": "à",  # a重音
            "\u00e1": "á",  # a重音
            "\u00e2": "â",  # a重音
            "\u00e3": "ã",  # a重音
            "\u00e4": "ä",  # a重音
            "\u00e5": "å",  # a圆圈
            "\u00e7": "ç",  # c下加符
            "\u00e8": "è",  # e重音
            "\u00e9": "é",  # e重音
            "\u00ea": "ê",  # e重音
            "\u00eb": "ë",  # e重音
            "\u00ec": "ì",  # i重音
            "\u00ed": "í",  # i重音
            "\u00ee": "î",  # i重音
            "\u00ef": "ï",  # i重音
            "\u00f0": "ð",  # d上划线
            "\u00f1": "ñ",  # n波浪
            "\u00f2": "ò",  # o重音
            "\u00f3": "ó",  # o重音
            "\u00f4": "ô",  # o重音
            "\u00f5": "õ",  # o重音
            "\u00f6": "ö",  # o重音
            "\u00f9": "ù",  # u重音
            "\u00fa": "ú",  # u重音
            "\u00fb": "û",  # u重音
            "\u00fc": "ü",  # u重音
            "\u00fd": "ý",  # y重音
            "\u00fe": "þ",  # 冰岛语th
            "\u00ff": "ÿ",  # y重音
        }

        # 应用字符替换
        for old, new in replacements.items():
            text = text.replace(old, new)

        # 处理连续的空白字符
        text = re.sub(r"[ \t]+", " ", text)  # 将多个空格制表符合并为单个空格
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)  # 将多个连续换行合并为双换行

        # 处理特殊的控制字符
        # 移除控制字符（除了换行和制表符）
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        return text.strip()


class GIMNRParser(BaseHTMLParser):
    """政府信息公开平台 (gi.mnr.gov.cn) 解析器

    结构特点：
    - 使用列表表格 (table.table)
    - 每行是一个政策
    - 格式：索引 | 标题(链接) | 发文字号 | 发布日期
    """

    def parse(
        self,
        soup: BeautifulSoup,
        callback: Optional[Callable] = None,
        category_name: str = "",
    ) -> List[Dict]:
        """解析政府信息公开平台的HTML"""
        policies = []

        try:
            # 查找列表表格
            table = soup.find("table", class_="table")
            if not table:
                if callback:
                    callback("未找到政策列表表格 (gi.mnr.gov.cn结构)")
                return policies

            # 查找所有政策行（跳过表头）
            rows = table.find_all("tr")[1:]
            if callback:
                callback(f"找到 {len(rows)} 条政策 (gi.mnr.gov.cn)")

            for row in rows:
                try:
                    cells = row.find_all("td")
                    if len(cells) < 4:
                        continue

                    # 检查是否是主政策行
                    first_cell = self._clean_text(cells[0].get_text(strip=True))
                    if not first_cell or first_cell in [
                        "标题",
                        "索引",
                        "发文字号",
                        "生成日期",
                        "实施日期",
                    ]:
                        continue

                    # 检查是否是有效的政策索引号（以数字开头）
                    if (
                        not first_cell
                        or len(first_cell) < 4
                        or not first_cell[0].isdigit()
                    ):
                        continue

                    # 这个网站使用标签-值对的结构，需要解析所有列
                    # 结构：索引 | 标题 | '标题'标签 | 标题值(链接) | '索引'标签 | 索引值 | ... | '生成日期'标签 | 日期值 | ...

                    title = ""
                    detail_url = ""
                    doc_number = ""
                    pub_date = ""

                    # 遍历所有列，查找标签-值对
                    for i in range(len(cells) - 1):
                        label = self._clean_text(cells[i].get_text(strip=True)).replace(
                            " ", ""
                        )
                        value = self._clean_text(
                            cells[i + 1].get_text(strip=True)
                            if i + 1 < len(cells)
                            else ""
                        )

                        # 查找标题和链接
                        if "标题" in label or "名称" in label:
                            # 标题可能在当前列或下一列
                            link = (
                                cells[i + 1].find("a", href=True)
                                if i + 1 < len(cells)
                                else None
                            )
                            if not link:
                                link = cells[i].find("a", href=True)

                            if link:
                                title = self._clean_text(link.get_text(strip=True))
                                detail_url = link.get("href", "")
                                if not title and value:
                                    title = self._clean_text(value)
                            elif value:
                                title = self._clean_text(value)

                        # 查找发文字号
                        elif "发文字号" in label or ("文号" in label and "发" in label):
                            if value:
                                doc_number = self._clean_text(value)

                        # 查找发布日期（优先使用'生成日期'，如果没有则使用'发布日期'）
                        elif "生成日期" in label:
                            if value and (
                                any(
                                    keyword in self._clean_text(value)
                                    for keyword in ["年", "月", "日"]
                                )
                                or len(self._clean_text(value)) >= 8
                            ):
                                pub_date = self._clean_text(value)
                        elif "发布日期" in label and not pub_date:
                            if value and (
                                any(
                                    keyword in self._clean_text(value)
                                    for keyword in ["年", "月", "日"]
                                )
                                or len(self._clean_text(value)) >= 8
                            ):
                                pub_date = self._clean_text(value)

                    # 如果没找到标题，尝试从链接中获取
                    if not title:
                        for cell in cells:
                            link = cell.find("a", href=True)
                            if link:
                                href = link.get("href", "")
                                if href and not href.startswith("javascript"):
                                    title = self._clean_text(link.get_text(strip=True))
                                    detail_url = href
                                    break

                    if not title:
                        continue

                    # 构建完整链接
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = urljoin(self.base_url, detail_url)

                    # 解析并格式化日期
                    pub_date_formatted = ""
                    if pub_date:
                        parsed_date = self._parse_date(pub_date)
                        if parsed_date:
                            pub_date_formatted = parsed_date.strftime("%Y-%m-%d")
                        else:
                            pub_date_formatted = pub_date.strip()

                    policy = {
                        "level": self.level,
                        "title": self._clean_text(title),
                        "pub_date": pub_date_formatted,
                        "doc_number": self._clean_text(doc_number),
                        "source": detail_url,
                        "link": detail_url,
                        "url": detail_url,
                        "content": "",
                        "crawl_time": datetime.now(timezone.utc).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "category": category_name,
                        "validity": "",
                        "effective_date": "",
                        "publisher": "",  # 发布机构，从详情页提取
                    }

                    policies.append(policy)

                except Exception as e:
                    if callback:
                        callback(f"解析政策项失败: {e}")
                    logger.warning(f"解析政策项失败: {e}", exc_info=True)
                    continue

        except Exception as e:
            if callback:
                callback(f"解析HTML结果失败: {e}")
            logger.error(f"解析HTML结果失败: {e}", exc_info=True)

        return policies


class FMNRParser(BaseHTMLParser):
    """政策法规库 (f.mnr.gov.cn) 解析器

    结构特点：
    - 每个政策是一个独立的表格
    - 表格通常有5行左右
    - 格式：每行是 [标签, 值] 的形式
    """

    def parse(
        self,
        soup: BeautifulSoup,
        callback: Optional[Callable] = None,
        category_name: str = "",
    ) -> List[Dict]:
        """解析政策法规库的HTML"""
        policies = []

        try:
            # 查找所有表格
            all_tables = soup.find_all("table")
            if not all_tables:
                if callback:
                    callback("未找到任何表格 (f.mnr.gov.cn结构)")
                return policies

            # 查找政策表格（每个政策是一个独立的表格）
            policy_tables = []
            for table in all_tables:
                rows = table.find_all("tr")
                # 政策表格通常有2-10行
                if 2 <= len(rows) <= 10:
                    first_row = rows[0]
                    first_row_cells = first_row.find_all(["td", "th"])
                    if len(first_row_cells) >= 1:
                        first_cell_text = first_row_cells[0].get_text()
                        # 检查是否包含"标题"或"名称"
                        has_title = (
                            "标题" in first_cell_text or "名称" in first_cell_text
                        )
                        has_biao_ti = (
                            "标" in first_cell_text and "题" in first_cell_text
                        )
                        has_ming_cheng = (
                            "名" in first_cell_text and "称" in first_cell_text
                        )

                        if has_title or has_biao_ti or has_ming_cheng:
                            policy_tables.append(table)

            if not policy_tables:
                if callback:
                    callback(f"未找到政策表格（共检查了 {len(all_tables)} 个表格）")
                return policies

            if callback:
                callback(f"找到 {len(policy_tables)} 个政策表格 (f.mnr.gov.cn)")

            for table in policy_tables:
                try:
                    rows = table.find_all("tr")
                    if len(rows) < 2:
                        continue

                    # 初始化变量
                    title = ""
                    doc_number = ""
                    pub_date = ""
                    detail_url = ""
                    validity = ""

                    # 遍历表格的每一行
                    for row in rows:
                        cells = row.find_all(["td", "th"])
                        if len(cells) < 2:
                            continue

                        label_raw = self._clean_text(cells[0].get_text())
                        label = label_raw.replace(" ", "").strip()
                        value = self._clean_text(cells[1].get_text(strip=True))

                        # 根据标签提取信息
                        if (
                            "标题" in label
                            or "名称" in label
                            or ("标" in label and "题" in label)
                            or ("名" in label and "称" in label)
                        ):
                            title = value
                            # 查找标题中的链接
                            link = cells[1].find("a", href=True)
                            if link:
                                detail_url = link.get("href", "")
                                if not title:
                                    title = self._clean_text(link.get_text(strip=True))
                        elif (
                            "发文字号" in label
                            or "文号" in label
                            or ("发" in label and "号" in label)
                        ):
                            doc_number = value
                        elif (
                            "成文时间" in label
                            or "生成日期" in label
                            or "发布日期" in label
                            or "公布日期" in label
                        ) and not ("效力" in label or "级别" in label):
                            # 验证值是否是日期格式
                            if (
                                any(keyword in value for keyword in ["年", "月", "日"])
                                or len(value) >= 8
                            ):
                                pub_date = value
                        elif "实施日期" in label or "生效日期" in label:
                            if not pub_date:
                                pub_date = value
                        elif "效力级别" in label or "级别" in label:
                            validity = value

                    # 如果标题为空，尝试从表格中查找所有链接
                    if not title:
                        links = table.find_all("a", href=True)
                        for link in links:
                            link_text = self._clean_text(link.get_text(strip=True))
                            link_href = link.get("href", "")
                            if link_href and not link_href.startswith("javascript"):
                                if len(link_text) > 5:
                                    title = link_text
                                    detail_url = link_href
                                    break

                    if not title:
                        continue

                    # 构建完整链接
                    if detail_url and not detail_url.startswith("http"):
                        detail_url = urljoin(self.base_url, detail_url)

                    # 解析并格式化日期
                    pub_date_formatted = ""
                    if pub_date:
                        parsed_date = self._parse_date(pub_date)
                        if parsed_date:
                            pub_date_formatted = parsed_date.strftime("%Y-%m-%d")
                        else:
                            pub_date_formatted = pub_date.strip()

                    policy = {
                        "level": self.level,
                        "title": self._clean_text(title),
                        "pub_date": pub_date_formatted,
                        "doc_number": self._clean_text(doc_number),
                        "source": detail_url,
                        "link": detail_url,
                        "url": detail_url,
                        "content": "",
                        "crawl_time": datetime.now(timezone.utc).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        "category": category_name,
                        "validity": self._clean_text(validity),
                        "effective_date": "",
                        "publisher": "",  # 发布机构，从详情页提取
                    }

                    policies.append(policy)

                except Exception as e:
                    if callback:
                        callback(f"解析政策表格失败: {e}")
                    logger.warning(f"解析政策表格失败: {e}", exc_info=True)
                    continue

            if callback:
                callback(f"成功解析 {len(policies)} 条政策 (f.mnr.gov.cn)")

        except Exception as e:
            if callback:
                callback(f"解析HTML结果失败: {e}")
            logger.error(f"解析HTML结果失败: {e}", exc_info=True)

        return policies


def get_parser_for_data_source(data_source: Dict) -> BaseHTMLParser:
    """根据数据源配置获取对应的解析器

    Args:
        data_source: 数据源配置字典

    Returns:
        对应的HTML解析器实例
    """
    base_url = data_source.get("base_url", "")
    level = data_source.get("level", "自然资源部")

    # 根据base_url判断使用哪个解析器
    if "gi.mnr.gov.cn" in base_url:
        # 政府信息公开平台
        return GIMNRParser(base_url, level)
    elif "f.mnr.gov.cn" in base_url:
        # 政策法规库
        return FMNRParser(base_url, level)
    else:
        # 默认使用政府信息公开平台解析器
        logger.warning(f"未知的数据源URL: {base_url}，使用默认解析器")
        return GIMNRParser(base_url, level)
