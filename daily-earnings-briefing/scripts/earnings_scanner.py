#!/usr/bin/env python3
"""
每日财报扫描脚本 - 输出给 AI 分析师做研报
支持美股 + A股核心池
"""

import json
import yfinance as yf
from datetime import datetime, timedelta, timezone
import requests
import re

# ===== 核心观察池 =====
US_POOL = {
    "AAPL": "苹果",
    "MSFT": "微软",
    "GOOGL": "谷歌",
    "AMZN": "亚马逊",
    "META": "Meta",
    "NVDA": "英伟达",
    "TSLA": "特斯拉",
    "ORCL": "Oracle",
    "AMD": "AMD",
    "AVGO": "博通",
    "RKLB": "Rocket Lab",
    "MU": "美光科技",
    "BE": "Bloom Energy",
    "PLTR": "Palantir",
    "NFLX": "奈飞",
}

A_POOL = {
    "300274.SZ": "阳光电源",
    "300727.SZ": "润禾材料",
    "301308.SZ": "江波龙",
    "603061.SS": "金海通",
    "300672.SZ": "国科微",
    "300750.SZ": "宁德时代",
    "002594.SZ": "比亚迪",
    "688256.SS": "寒武纪",
    "688041.SS": "海光信息",
    "300308.SZ": "中际旭创",
    "002281.SZ": "光迅科技",
    "300502.SZ": "新易盛",
    "600118.SS": "中国卫星",
    "002151.SZ": "北斗星通",
    "600406.SS": "国电南瑞",
    "300352.SZ": "北信源",
    "000026.SZ": "飞亚达",
}

# ===== 美股财报扫描 =====
def scan_us_earnings():
    results = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=2)  # 最近2天内发布的财报

    for ticker, cn_name in US_POOL.items():
        try:
            stock = yf.Ticker(ticker)
            ed = stock.earnings_dates
            if ed is None or ed.empty:
                continue

            # 找到已发布（Reported EPS 非 NaN）且日期在 cutoff 之后的
            recent = []
            for date, row in ed.iterrows():
                if pd_isna(row.get('Reported EPS')):
                    continue
                dt = date.to_pydatetime() if hasattr(date, 'to_pydatetime') else date
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= cutoff:
                    recent.append({
                        'date': dt.strftime('%Y-%m-%d'),
                        'eps_estimate': None if pd_isna(row.get('EPS Estimate')) else float(row['EPS Estimate']),
                        'eps_reported': None if pd_isna(row.get('Reported EPS')) else float(row['Reported EPS']),
                        'surprise_pct': None if pd_isna(row.get('Surprise(%)')) else float(row['Surprise(%)']),
                    })

            if not recent:
                continue

            # 获取财务数据
            info = stock.info
            inc_q = stock.quarterly_income_stmt
            cf_q = stock.quarterly_cashflow
            bal_q = stock.quarterly_balance_sheet

            # 提取最新季度关键指标
            latest_fin = {}
            if inc_q is not None and not inc_q.empty:
                cols = list(inc_q.columns)
                if len(cols) > 0:
                    latest = cols[0]
                    latest_fin['period'] = str(latest)[:10]
                    latest_fin['total_revenue'] = safe_get(inc_q, 'Total Revenue', latest)
                    latest_fin['gross_profit'] = safe_get(inc_q, 'Gross Profit', latest)
                    latest_fin['operating_income'] = safe_get(inc_q, 'Operating Income', latest)
                    latest_fin['net_income'] = safe_get(inc_q, 'Net Income Common Stockholders', latest)
                    latest_fin['basic_eps'] = safe_get(inc_q, 'Basic EPS', latest)
                    latest_fin['diluted_eps'] = safe_get(inc_q, 'Diluted EPS', latest)

                    # 同比（如果有上一年同期）
                    if len(cols) >= 5:
                        yoy = cols[4]
                        latest_fin['revenue_yoy'] = calc_yoy(
                            safe_get(inc_q, 'Total Revenue', latest),
                            safe_get(inc_q, 'Total Revenue', yoy)
                        )
                        latest_fin['net_income_yoy'] = calc_yoy(
                            safe_get(inc_q, 'Net Income Common Stockholders', latest),
                            safe_get(inc_q, 'Net Income Common Stockholders', yoy)
                        )

                    # 环比
                    if len(cols) >= 2:
                        qoq = cols[1]
                        latest_fin['revenue_qoq'] = calc_yoy(
                            safe_get(inc_q, 'Total Revenue', latest),
                            safe_get(inc_q, 'Total Revenue', qoq)
                        )

            if cf_q is not None and not cf_q.empty:
                cols = list(cf_q.columns)
                if len(cols) > 0:
                    latest = cols[0]
                    latest_fin['operating_cashflow'] = safe_get(cf_q, 'Operating Cash Flow', latest)
                    latest_fin['free_cashflow'] = safe_get(cf_q, 'Free Cash Flow', latest)

            if bal_q is not None and not bal_q.empty:
                cols = list(bal_q.columns)
                if len(cols) > 0:
                    latest = cols[0]
                    latest_fin['total_cash'] = safe_get(bal_q, 'Cash And Cash Equivalents', latest)
                    latest_fin['total_debt'] = safe_get(bal_q, 'Total Debt', latest)

            results.append({
                'market': 'US',
                'ticker': ticker,
                'name_cn': cn_name,
                'name_en': info.get('shortName', ticker),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'market_cap': info.get('marketCap'),
                'trailing_pe': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'earnings': recent,
                'financials': latest_fin,
            })
        except Exception as e:
            print(f"[!] {ticker} error: {e}", flush=True)

    return results


def pd_isna(v):
    import pandas as pd
    return pd.isna(v)


def safe_get(df, row_name, col):
    try:
        if row_name in df.index:
            v = df.loc[row_name, col]
            return None if pd_isna(v) else float(v)
    except Exception:
        pass
    return None


def calc_yoy(curr, prev):
    if curr is None or prev is None or prev == 0:
        return None
    return round((curr - prev) / abs(prev) * 100, 2)


# ===== A股扫描（简化版：yfinance + 东方财富新闻） =====
def scan_a_earnings():
    results = []
    now = datetime.now()
    cutoff = now - timedelta(days=2)

    for ticker, cn_name in A_POOL.items():
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            inc_q = stock.quarterly_income_stmt

            if inc_q is None or inc_q.empty:
                continue

            cols = list(inc_q.columns)
            if len(cols) == 0:
                continue

            latest = cols[0]
            latest_date = pd_to_date(latest)

            # 只取最近60天内的"新"数据（避免yfinance缓存旧数据）
            if latest_date and latest_date < (now - timedelta(days=60)):
                continue

            latest_fin = {
                'period': str(latest)[:10],
                'total_revenue': safe_get(inc_q, 'Total Revenue', latest),
                'gross_profit': safe_get(inc_q, 'Gross Profit', latest),
                'operating_income': safe_get(inc_q, 'Operating Income', latest),
                'net_income': safe_get(inc_q, 'Net Income Common Stockholders', latest),
                'basic_eps': safe_get(inc_q, 'Basic EPS', latest),
            }

            # 同比
            if len(cols) >= 5:
                yoy = cols[4]
                latest_fin['revenue_yoy'] = calc_yoy(
                    safe_get(inc_q, 'Total Revenue', latest),
                    safe_get(inc_q, 'Total Revenue', yoy)
                )
                latest_fin['net_income_yoy'] = calc_yoy(
                    safe_get(inc_q, 'Net Income Common Stockholders', latest),
                    safe_get(inc_q, 'Net Income Common Stockholders', yoy)
                )

            results.append({
                'market': 'A',
                'ticker': ticker,
                'name_cn': cn_name,
                'sector': info.get('sector'),
                'financials': latest_fin,
                'data_freshness': str(latest)[:10],
            })
        except Exception as e:
            print(f"[!] {ticker} error: {e}", flush=True)

    return results


def pd_to_date(ts):
    try:
        import pandas as pd
        if isinstance(ts, pd.Timestamp):
            return ts.to_pydatetime()
        if isinstance(ts, datetime):
            return ts
    except Exception:
        pass
    return None


# ===== 东方财富：补充扫描全市场昨日业绩新闻（取代表性） =====
def scan_market_earnings_news():
    """从东方财富搜索 API 拿最近业绩新闻，帮 AI 判断哪些值得写"""
    try:
        url = 'https://search-api-web.eastmoney.com/search/jsonp'
        keywords = [
            "一季度 净利润 同比增长 大幅",
            "年报 净利润 同比 增长 翻倍",
        ]
        all_news = []
        for kw in keywords:
            param = {
                'uid': '',
                'keyword': kw,
                'type': ['cmsArticleWebOld'],
                'client': 'web',
                'clientVersion': 'curr',
                'clientType': 'web',
                'param': {
                    'cmsArticleWebOld': {
                        'sort': 'time',
                        'pageIndex': 1,
                        'pageSize': 10,
                        'preTag': '<em>',
                        'postTag': '</em>'
                    }
                }
            }
            import urllib.parse
            full_url = url + '?cb=cb&param=' + urllib.parse.quote(
                json.dumps(param, separators=(',', ':'), ensure_ascii=False)
            ) + '&_=1'
            resp = requests.get(full_url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Referer': 'https://so.eastmoney.com/'
            }, timeout=15)
            text = resp.text
            m = re.search(r'^cb\((.*)\)$', text)
            if m:
                data = json.loads(m.group(1))
                for item in data.get('result', {}).get('cmsArticleWebOld', []):
                    all_news.append({
                        'date': item.get('date', '')[:10],
                        'title': re.sub('<.*?>', '', item.get('title', '')),
                        'url': item.get('url', ''),
                    })
        return all_news[:15]
    except Exception as e:
        print(f"[!] market news error: {e}", flush=True)
        return []


# ===== 主流程 =====
def main():
    import pandas as pd  # 确保导入
    print(f"=== 财报扫描 {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    print()

    print("--- 美股核心池 ---")
    us_results = scan_us_earnings()
    if us_results:
        print(json.dumps(us_results, ensure_ascii=False, indent=2, default=str))
    else:
        print("最近2天无核心池美股发布财报")
    print()

    print("--- A股核心池 ---")
    a_results = scan_a_earnings()
    if a_results:
        print(json.dumps(a_results, ensure_ascii=False, indent=2, default=str))
    else:
        print("核心池A股无近期数据更新")
    print()

    print("--- 市场业绩新闻 ---")
    news = scan_market_earnings_news()
    if news:
        print(json.dumps(news, ensure_ascii=False, indent=2, default=str))
    else:
        print("无新增")


if __name__ == '__main__':
    main()
