"""mnr_gi_article：gi / f 正文链 URL 识别。"""

from app.core.mnr_gi_article import (
    extract_gi_article_urls,
    is_gi_article_url,
)


def test_is_gi_article_url_accepts_gi_host():
    u = "https://gi.mnr.gov.cn/202603/t20260327_2917437.html"
    assert is_gi_article_url(u) is True


def test_is_gi_article_url_accepts_f_host():
    u = "https://f.mnr.gov.cn/202603/t20260319_2916893.html"
    assert is_gi_article_url(u) is True


def test_is_gi_article_url_rejects_other_host():
    u = "https://example.com/202603/t20260327_2917437.html"
    assert is_gi_article_url(u) is False


def test_extract_gi_article_urls_resolves_relative_on_f():
    html = (
        '<html><body><a href="./202603/t20260319_2916893.html">x</a></body></html>'
    )
    page = "https://f.mnr.gov.cn/index_3553.html"
    found = extract_gi_article_urls(html, page)
    assert found == ["https://f.mnr.gov.cn/202603/t20260319_2916893.html"]
