"""
HTTP 请求超时：政务站点（如 search.mnr.gov.cn）响应常较慢，读取阶段单独放宽。
"""

from typing import Any, Tuple


def request_timeout_tuple(
    config: Any,
    *,
    default_read: float = 90.0,
    default_connect: float = 15.0,
) -> Tuple[float, float]:
    """返回 requests 可用的 (connect, read) 秒数。

    Args:
        config: 带 .get 的配置对象（如 Config）
        default_read: 未配置时的读取超时
        default_connect: 未配置时的连接超时
    """
    read_sec = float(config.get("timeout", default_read))
    connect_sec = float(config.get("connect_timeout", default_connect))
    if read_sec < 5.0:
        read_sec = 5.0
    if connect_sec < 3.0:
        connect_sec = 3.0
    if connect_sec > read_sec:
        connect_sec = read_sec
    return (connect_sec, read_sec)
