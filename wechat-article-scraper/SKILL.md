---
name: wechat-article-scraper
description: Scrape WeChat public account articles from mp.weixin.qq.com and convert to clean Markdown files.
category: media
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [WeChat, 公众号, article, scraping, markdown]
---

# WeChat Article Scraper

Scrape articles from WeChat public accounts (mp.weixin.qq.com) and convert to clean Markdown.

## Limitations

- **No public article index API** for listing every article in a public account. Full-account archiving requires one of: user-operated tools, official-ish reading surfaces, third-party APIs, or authenticated WeChat client/session parameters captured by the user.
- **Paid articles** behind 微信豆 paywall cannot be fully scraped — only the free preview is accessible. Do not bypass paywalls.
- **Images** hosted on WeChat CDN expire after some time — download separately if needed
- Articles are dynamic; `curl` only gets partial content, use **browser** for full extraction
- Use only for personal research/knowledge-base archiving or content the user has rights to process. Avoid high-frequency scraping and commercial redistribution.

## Methods

### Fast path for a single user-provided article

For a `https://mp.weixin.qq.com/s/...` article, try these in order:

1. **Direct mobile-UA extraction**. WeChat public articles often embed the full article in `#js_content` when fetched with a mobile WeChat-like User-Agent. A tested helper script is bundled at `scripts/wechat_article_extract.py`. Run it from this skill directory, or copy it to `~/.hermes/scripts/`:

   ```bash
   python3 scripts/wechat_article_extract.py 'https://mp.weixin.qq.com/s/ARTICLE_ID'
   # or machine-readable:
   python3 scripts/wechat_article_extract.py 'https://mp.weixin.qq.com/s/ARTICLE_ID' --json
   ```

2. **Browser fallback** when direct extraction hits verification, login, or dynamic rendering:

   ```js
   (() => {
     const title = document.querySelector('#activity-name')?.innerText?.trim();
     const author = document.querySelector('#js_name')?.innerText?.trim();
     const time = document.querySelector('#publish_time')?.innerText?.trim();
     const content = document.querySelector('#js_content')?.innerText?.trim();
     return {title, author, time, chars: content?.length, content};
   })()
   ```

3. **Jina Reader** (`https://r.jina.ai/http://r.jina.ai/http://...`) can be tried for ordinary web pages, but for WeChat it often returns `环境异常/完成验证` instead of article content, so do not rely on it as the primary path.

If the article is paywalled, login-only, deleted, or blocked by CAPTCHA, report that honestly. Do not bypass paywalls or verification.

### 0. Bulk public-account archiving options

When the user wants to archive many/all articles from a公众号 into Markdown/Obsidian, choose the lowest-friction method that fits the need:

| Situation | Method | Notes |
| --- | --- | --- |
| User wants results only | Human/marketplace export service | Cheap and low effort, but format/privacy vary; useful for getting URL lists first. |
| User can operate a browser | Visual tools such as changfengbox/wechatDownload | Paste one article URL, obtain account id/session through WeChat, then batch export Markdown; split large accounts into batches. |
| User needs automation | Third-party content/data APIs | Paid per article; easier to connect to n8n/Coze/Make; verify rights and costs. |
| User requires official-ish channel | WeChat Reading/微信读书 route | More compliant but more manual; may require cookies/session handled by the user. |
| User needs full control | User-captured WeChat session parameters + scripts | The user must capture their own authenticated parameters; implement rate limiting, checkpointing, and re-auth on expiry. |

For full-account archiving, use a two-stage pipeline:
1. Build a URL inventory with title/date/source metadata.
2. Download each URL to Markdown, then clean WeChat UI residue and save to the user’s knowledge-base schema.

Operational guardrails:
- Save progress every 10 articles or so; support resume/skip existing files.
- Throttle requests, typically 2–3 seconds between article downloads.
- Treat captured `key`, `pass_ticket`, cookies, and similar session parameters as secrets: never print them into chat or memory.
- Expect session parameters to expire; refresh by having the user reopen an article in WeChat.
- Clean common residue: QR-follow blocks, share/like/favorite text, mini-program prompts, excessive blank lines, empty bold markers.
- Fallbacks for single articles: Jina Reader (`r.jina.ai`) may work for public pages; browser/Playwright is the final fallback for dynamic pages.

### 1. Simple scrape (python3 + urllib) — for static/free articles

```bash
python3 -c "
import urllib.request, re, html

req = urllib.request.Request(
    'https://mp.weixin.qq.com/s/{ARTICLE_ID}',
    headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
)
resp = urllib.request.urlopen(req, timeout=30)
body = resp.read().decode('utf-8')

# Extract title
title_match = re.search(r'<h1[^>]*id=\"activity-name\"[^>]*>(.*?)</h1>', body, re.DOTALL)
title = html.unescape(re.sub(r'<[^>]+>', '', title_match.group(1)).strip()) if title_match else '未知'

# Extract author
author_match = re.search(r'id=\"js_name\"[^>]*>(.*?)</a>', body, re.DOTALL)
author = html.unescape(re.sub(r'<[^>]+>', '', author_match.group(1)).strip()) if author_match else '未知'

# Extract content (js_content div)
content_match = re.search(r'<div[^>]*id=\"js_content\"[^>]*>(.*)', body, re.DOTALL)
content_html = content_match.group(1) if content_match else ''

# Convert to markdown
text = content_html
text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<br\s*/?>', '\n\n', text)
text = re.sub(r'</p>', '\n\n', text)
text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text, flags=re.DOTALL)
text = re.sub(r'<b>(.*?)</b>', r'**\1**', text, flags=re.DOTALL)
text = re.sub(r'<em>(.*?)</em>', r'*\1*', text, flags=re.DOTALL)
text = re.sub(r'<a[^>]*href=\"([^\"]*)\"[^>]*>(.*?)</a>', r'[\2](\1)', text, flags=re.DOTALL)
text = re.sub(r'<li>(.*?)</li>', r'- \1', text, flags=re.DOTALL)
text = re.sub(r'<h1>(.*?)</h1>', r'# \1', text, flags=re.DOTALL)
text = re.sub(r'<h2>(.*?)</h2>', r'## \1', text, flags=re.DOTALL)
text = re.sub(r'<h3>(.*?)</h3>', r'### \1', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', '', text)
text = html.unescape(text)
text = re.sub(r'\n{3,}', '\n\n', text)
text = text.strip()

print(f'# {title}')
print(f'\n**来源**: 公众号「{author}」')
print(f'**原文链接**: https://mp.weixin.qq.com/s/{ARTICLE_ID}')
print(f'\n---\n\n{text}')
"
```

### 2. Browser scrape — for dynamic/partial articles

Use when simple scrape only gets partial content (common with paid or long articles):

```
1. browser_navigate(url)
2. browser_snapshot() or browser_console(expression="document.getElementById('js_content').innerText")
3. Save to file
```

### 3. Common pitfalls

- **Paid articles (50 微信豆)**: Only free preview accessible. User must paste full text manually.
- **Dynamic content**: `curl`/`urllib` may only get partial HTML. Switch to browser for full content.
- **Links from extraction**: Other mp.weixin.qq.com links found on a page are usually ads/guides, not other articles.
- **Image URLs expire**: WeChat CDN images are temporary. Download immediately if needed.
