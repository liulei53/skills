---
name: daily-earnings-briefing
description: A股+美股每日财报自动扫描与AI分析推送系统。含数据抓取脚本、定时任务配置、分析Prompt模板。
category: finance
---

# 每日财报研报自动推送系统

## 什么情况下使用
- 需要每天自动监控A股/美股核心公司财报动态
- 想在早上盘前收到带观点的财报快评（而不是冰冷数据）
- 希望美股财报自动映射到A股关联标的

## 系统构成
- **前置脚本** `scripts/earnings_scanner.py`：每日扫描美股+A股核心池财报，输出结构化JSON
- **Cronjob定时任务**：每日北京时间8:30自动运行
- **AI分析Prompt**：将脚本输出转换为交易员视角的研报快评

## 前置依赖
需要在系统Python3.10环境下安装：
```bash
/usr/bin/python3.10 -m pip install yfinance pandas lxml requests beautifulsoup4
```

## 快速部署

### 1. 安装依赖
```bash
/usr/bin/python3.10 -m pip install yfinance pandas lxml requests beautifulsoup4 -q
```

### 2. 将脚本复制到指定位置
```bash
cp scripts/earnings_scanner.py ~/.hermes/scripts/
```

### 3. 创建定时任务
使用 cronjob 工具创建：
- **schedule**: `30 0 * * *` （UTC 0:30 = 北京时间 8:30）
- **script**: `earnings_scanner.py`
- **deliver**: `origin` 或指定 Telegram chat

Prompt 参考模板（核心要点）：
```
你是一位资深交易员/投研分析师...
[见实际配置时填入完整Prompt]
```

## 核心池配置
编辑 `~/.hermes/scripts/earnings_scanner.py` 中的两个字典：

**US_POOL** — 美股核心池（默认15只）：
- 七大巨头: AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA
- AI/算力: ORCL, AMD, AVGO
- 商业航天: RKLB
- 存储芯片: MU
- AI电力: BE
- 其他: PLTR, NFLX

**A_POOL** — A股核心池（默认17只）：
- 新能源/储能: 300274, 300750, 002594
- 半导体/AI芯片: 688256, 688041, 300308
- 光通信: 002281, 300502
- 商业航天: 600118, 002151
- 电网: 600406
- 存储/设备: 603061, 300672, 301308
- 有机硅: 300727
- 其他: 300352, 000026

## 数据源
- **美股**: Yahoo Finance API（通过 yfinance 库），包括 earnings_dates、quarterly_income_stmt、cashflow、balance_sheet
- **A股**: Yahoo Finance（基础财务数据） + 东方财富搜索API（补充市场业绩新闻）
- **市场新闻**: 东方财富 search-api-web 获取最新业绩相关头条

## 分析框架（AI Prompt要求）
1. 不是冰冷数据罗列，要有观点和判断
2. 每家公司回答四个问题：超预期or低于预期、驱动力、财务质量、影响判断
3. 美股必须映射A股关联标的
4. A股联系持仓和关注池
5. 无新财报时也要输出即将发布日程和市场线索

## 定时任务管理
```bash
# 查看任务
cronjob action=list

# 暂停
cronjob action=pause job_id=<id>

# 恢复
cronjob action=resume job_id=<id>

# 删除
cronjob action=remove job_id=<id>
```

## 常见问题
- **yfinance 报错 Missing lxml**: 安装 `lxml`
- **A股数据延迟**: yfinance对A股支持略滞后，如需实时数据可改用东方财富个股公告API替代
- **推送失败**: 检查 deliver 参数是否配置正确，默认 `origin` 返回当前对话
