#!/usr/bin/env python3
"""Extract a public WeChat mp.weixin.qq.com article to readable Markdown.

Usage:
  python3 ~/.hermes/scripts/wechat_article_extract.py 'https://mp.weixin.qq.com/s/...'

This is for user-provided public/free articles. It does not bypass login, CAPTCHA, or paywalls.
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
    "Mobile/15E148 MicroMessenger/8.0.50 Safari/604.1"
)


def strip_tags(s: str) -> str:
    s = re.sub(r"<script\b[^>]*>.*?</script>", "", s, flags=re.S | re.I)
    s = re.sub(r"<style\b[^>]*>.*?</style>", "", s, flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|section|h[1-6]|li|blockquote)>", "\n", s, flags=re.I)
    s = re.sub(r"<img\b[^>]*(?:data-src|src)=[\"']([^\"']+)[\"'][^>]*>", r"\n![图片](\1)\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace("\xa0", " ").replace("\u200b", "")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n[ \t]+", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def pick(pattern: str, body: str, flags=re.S | re.I) -> str:
    m = re.search(pattern, body, flags)
    return strip_tags(m.group(1)) if m else ""


def extract_publish_time(body: str) -> str:
    """Extract WeChat publish time from DOM or JS variables."""
    value = pick(r'id=["\']publish_time["\'][^>]*>(.*?)</[^>]+>', body)
    if value:
        return value

    # Many WeChat pages leave #publish_time empty and fill it from JS.
    m = re.search(r'var\s+ct\s*=\s*["\']?(\d{10})["\']?', body)
    if not m:
        m = re.search(r'publish_time(?:%22|"|\')\s*(?::|%3A)\s*(\d{10})', body)
    if m:
        ts = int(m.group(1))
        dt = datetime.fromtimestamp(ts, tz=timezone(timedelta(hours=8)))
        return dt.strftime("%Y年%-m月%-d日 %H:%M")
    return ""


def extract(url: str) -> dict:
    if not re.match(r"^https?://mp\.weixin\.qq\.com/", url):
        raise SystemExit("Only mp.weixin.qq.com URLs are supported")
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": MOBILE_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        final_url = resp.geturl()
        body = resp.read().decode("utf-8", "replace")

    # Detect obvious anti-bot / verification pages.
    plain_head = strip_tags(body[:20000])
    if "环境异常" in plain_head and "完成验证" in plain_head:
        return {"url": final_url, "error": "WeChat verification/CAPTCHA page", "content": ""}

    title = pick(r'<h1[^>]*id=["\']activity-name["\'][^>]*>(.*?)</h1>', body)
    author = pick(r'id=["\']js_name["\'][^>]*>(.*?)</a>', body)
    publish_time = extract_publish_time(body)

    # Prefer the real article container. Stop before js_sponsor_ad_area / comments / scripts when possible.
    m = re.search(r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)(?:<div[^>]*id=["\']js_sponsor_ad_area["\']|<script\b|<div[^>]*id=["\']js_pc_qr_code["\'])', body, re.S | re.I)
    if not m:
        m = re.search(r'<div[^>]*id=["\']js_content["\'][^>]*>(.*?)</div>', body, re.S | re.I)
    content = strip_tags(m.group(1)) if m else ""

    md = []
    md.append(f"# {title or '未命名微信文章'}")
    md.append("")
    meta = []
    if author:
        meta.append(f"来源：公众号「{author}」")
    if publish_time:
        meta.append(f"发布时间：{publish_time}")
    meta.append(f"原文链接：{final_url}")
    md.append("\n".join(meta))
    md.append("")
    md.append("---")
    md.append("")
    md.append(content)

    return {
        "url": final_url,
        "title": title,
        "author": author,
        "publish_time": publish_time,
        "chars": len(content),
        "markdown": "\n".join(md).strip() + "\n",
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: wechat_article_extract.py <mp.weixin.qq.com URL> [--json]")
    url = sys.argv[1]
    data = extract(url)
    if "--json" in sys.argv:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        if data.get("error"):
            raise SystemExit(data["error"])
        print(data["markdown"])


if __name__ == "__main__":
    main()
