"""Build v6 email HTML: per-stock multi-news + sector highlights."""
import json
import pathlib
import re

V6 = pathlib.Path("watchlist_data/news_v6_0901.json")
EMAIL = pathlib.Path("watchlist_data/mail_attach/report_cdn_v6.html")

data = json.loads(V6.read_text(encoding="utf-8"))
stocks = data["stocks"]
sectors = data["sectors"]

# 泛化/低质条目过滤
GENERIC = ["三大指数", "指数走弱", "创业板指下挫", "开盘涨跌互现", "沪指开", "恒生指数开", "点击阅读", "A股开盘，沪指"]
# 板块顺序
SECTOR_ORDER = ["军工/国防", "卫星/商业航天", "半导体/存储", "稀土/有色", "锂电/储能", "传媒/短剧", "贵金属", "原油/商品", "智能驾驶", "脑机接口/AI"]

def is_good(c):
    if len(c) < 20:
        return False
    if any(g in c for g in GENERIC):
        return False
    return True

def dedupe(lst, maxn):
    """同事件去重（前16字指纹），保留重要度高的"""
    out = []
    fp_seen = set()
    for x in lst:
        if not is_good(x["content"]):
            continue
        fp = re.sub(r"\s+", "", x["content"])[:16]
        if fp in fp_seen:
            continue
        fp_seen.add(fp)
        out.append(x)
        if len(out) >= maxn:
            break
    return out

SRC_STYLE = {"金十数据": "#e6732e", "财联社": "#2f6fed", "东方财富": "#d93026"}

def badges(srcs):
    return "".join(
        f"<span style='display:inline-block;background:{SRC_STYLE[s]};color:#fff;font-size:10px;padding:1px 6px;border-radius:3px;margin-right:4px;'>{s}</span>"
        for s in srcs if s in SRC_STYLE)

def card(num, name, item):
    if item is None:
        return (f"<div style='background:#fff8e1;border-left:4px solid #f5a623;padding:10px 12px;border-radius:6px;margin:9px 0;'>"
                f"<p style='margin:0;font-size:14px;line-height:1.7;color:#444;'><b style='color:#1f2329;'>{num}. {name}</b> — 当日三源（金十/财联社/东方财富）无重大快讯</p></div>")
    title = item["content"]
    if len(title) > 60:
        title = title[:60] + "…"
    return (f"<div style='background:#fff8e1;border-left:4px solid #f5a623;padding:10px 12px;border-radius:6px;margin:9px 0;'>"
            f"<p style='margin:0 0 3px;font-size:14px;line-height:1.5;'><b style='color:#1f2329;'>{num}. {name}</b> <b style='color:#1f2329;'>{title}</b>"
            f"<span style='color:#9aa0a6;font-size:11px;'>｜{item['time'][5:16]}</span></p>"
            f"<p style='margin:0;font-size:13px;line-height:1.7;color:#444;'>{item['content']}</p>"
            f"<p style='margin:4px 0 0;'>{badges(item['srcs'])}</p></div>")

# ============ 个股部分（每只 2 条）============
stock_cards = []
n = 0
for stock, lst in stocks.items():
    lst = dedupe(lst, 2)
    if not lst:
        n += 1
        stock_cards.append(card(n, stock, None))
        continue
    for it in lst:
        n += 1
        stock_cards.append(card(n, stock, it))

# ============ 板块部分（每板块 2 条）============
sector_cards = []
m = 0
for sec in SECTOR_ORDER:
    lst = sectors.get(sec, [])
    lst = dedupe(lst, 2)
    if not lst:
        continue
    m += 1
    head = (f"<p style='margin:14px 0 4px;font-size:14px;font-weight:bold;color:#1f2329;border-left:3px solid #2f6fed;padding-left:8px;'>"
            f"📌 板块要闻：{sec}</p>")
    body = "".join(card(f"{m}.{i+1}", sec, it) for i, it in enumerate(lst))
    sector_cards.append(head + body)

# ============ 组装 ============
head_html = (
    "<div style='font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;max-width:760px;margin:0 auto;color:#1f2329;'>"
    "<h2 style='color:#d93026;font-size:18px;margin:12px 0 4px;'>📊 2026-09-01 收盘财报（多新闻+板块版）</h2>"
    "<p style='color:#646a73;font-size:12px;margin:0 0 14px;'>数据时效：2026-09-01 A股/ETF/LOF/港股/韩股收盘 ｜ 新闻源：金十数据 / 财联社 / 东方财富（3730 条筛选）</p>"
    "<h3 style='font-size:15px;border-left:4px solid #d93026;padding-left:8px;margin:16px 0 8px;'>一、大盘概况</h3>"
    "<table style='border-collapse:collapse;width:100%;font-size:12px;'><tr>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>指数</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>收盘</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>涨跌幅</th></tr>"
    "<tr><td style='padding:4px 8px;border:1px solid #e5e6eb;'>上证指数</td><td style='padding:4px 8px;border:1px solid #e5e6eb;'>3979.89</td><td style='padding:4px 8px;border:1px solid #e5e6eb;color:#0f9d58;font-weight:bold;'>-0.16%</td></tr>"
    "<tr><td style='padding:4px 8px;border:1px solid #e5e6eb;'>深证成指</td><td style='padding:4px 8px;border:1px solid #e5e6eb;'>13872.38</td><td style='padding:4px 8px;border:1px solid #e5e6eb;color:#0f9d58;font-weight:bold;'>-1.02%</td></tr>"
    "<tr><td style='padding:4px 8px;border:1px solid #e5e6eb;'>创业板指</td><td style='padding:4px 8px;border:1px solid #e5e6eb;'>3393.43</td><td style='padding:4px 8px;border:1px solid #e5e6eb;color:#0f9d58;font-weight:bold;'>-1.32%</td></tr>"
    "<tr><td style='padding:4px 8px;border:1px solid #e5e6eb;'>科创50</td><td style='padding:4px 8px;border:1px solid #e5e6eb;'>—</td><td style='padding:4px 8px;border:1px solid #e5e6eb;color:#0f9d58;font-weight:bold;'>-2.19%</td></tr>"
    "<tr><td style='padding:4px 8px;border:1px solid #e5e6eb;'>北证50</td><td style='padding:4px 8px;border:1px solid #e5e6eb;'>—</td><td style='padding:4px 8px;border:1px solid #e5e6eb;color:#d93026;font-weight:bold;'>+1.34%</td></tr></table>"
    "<p style='font-size:12px;color:#5f6368;margin:6px 0;'>两市成交 20334 亿（缩量 976 亿）；涨 3386 / 跌 2040，涨停 86；主力净流出 237.77 亿。领涨：商贸零售 +3.08%、农林牧渔 +2.48%、银行 +1.88%；领跌：电子 -2.99%、煤炭 -2.13%。</p>"
)

wl_table = (
    "<h3 style='font-size:15px;border-left:4px solid #d93026;padding-left:8px;margin:16px 0 8px;'>二、自选股 15 只收盘</h3>"
    "<table style='border-collapse:collapse;width:100%;font-size:12px;'><tr>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>名称</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>现价</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>涨跌幅</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>成交额</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>主力净流入</th></tr>"
    + open('watchlist_data/mail_attach/_wl_table.html', encoding='utf-8').read() if False else ""
)

# 自选股表（从 quotes 动态生成）
import base64
quotes = json.loads(pathlib.Path("watchlist_data/quotes.json").read_text(encoding="utf-8"))
rows_mail = []
for q in quotes:
    chg = q['chg_pct'] or 0
    color = '#d93026' if chg > 0 else ('#0f9d58' if chg < 0 else '#666')
    mns = q.get('main_net_str') or '—'
    mcol = '#d93026' if str(mns).startswith('+') else ('#0f9d58' if str(mns).startswith('-') else '#666')
    price = q['price']
    if q.get('currency') == 'KRW' and price and price >= 100000:
        price = f'{price/10000:.1f}万'
    rows_mail.append(
        f"<tr><td style='padding:4px 8px;border:1px solid #e5e6eb;font-size:12px;'>{q['name']}</td>"
        f"<td style='padding:4px 8px;border:1px solid #e5e6eb;font-size:12px;'>{price}</td>"
        f"<td style='padding:4px 8px;border:1px solid #e5e6eb;font-size:12px;color:{color};font-weight:bold;'>{chg:+.2f}%</td>"
        f"<td style='padding:4px 8px;border:1px solid #e5e6eb;font-size:12px;'>{q['amount_str']}</td>"
        f"<td style='padding:4px 8px;border:1px solid #e5e6eb;font-size:12px;color:{mcol};'>{mns}</td></tr>")
wl_table = (wl_table.replace("+ open('watchlist_data/mail_attach/_wl_table.html', encoding='utf-8').read() if False else \"\"", "") if False else
    "<h3 style='font-size:15px;border-left:4px solid #d93026;padding-left:8px;margin:16px 0 8px;'>二、自选股 15 只收盘</h3>"
    "<table style='border-collapse:collapse;width:100%;font-size:12px;'><tr>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>名称</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>现价</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>涨跌幅</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>成交额</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>主力净流入</th></tr>"
    + "".join(rows_mail) + "</table>")

charts = (
    "<h3 style='font-size:15px;border-left:4px solid #d93026;padding-left:8px;margin:16px 0 8px;'>三、图表（已内嵌正文）</h3>"
    "<p style='font-size:11px;color:#9aa0a6;margin:2px 0 6px;'>（若图表未显示，请点击邮件上方的【显示图片】按钮）</p>"
    "<img src='https://wb-sync.pages.dev/charts/chart_flow.png' alt='chart_flow' style='max-width:100%;height:auto;border:1px solid #e5e6eb;border-radius:6px;'>"
    "<img src='https://wb-sync.pages.dev/charts/chart_chg.png' alt='chart_chg' style='max-width:100%;height:auto;border:1px solid #e5e6eb;border-radius:6px;'>"
    "<img src='https://wb-sync.pages.dev/charts/chart_amount.png' alt='chart_amount' style='max-width:100%;height:auto;border:1px solid #e5e6eb;border-radius:6px;'>"
)

news_section = (
    "<h3 style='font-size:15px;border-left:4px solid #d93026;padding-left:8px;margin:16px 0 8px;'>四、自选股重大新闻（多源 · 多条）</h3>"
    + "".join(stock_cards)
    + "<h3 style='font-size:15px;border-left:4px solid #2f6fed;padding-left:8px;margin:20px 0 8px;'>五、持仓相关板块要闻</h3>"
    + "".join(sector_cards)
)

foot = "<p style='color:#9aa0a6;font-size:11px;margin-top:14px;border-top:1px solid #f0f1f3;padding-top:10px;'>本邮件自动生成，数据来自公开实时源，不构成投资建议。</p></div>"

body = (head_html + wl_table + charts + news_section + foot).replace("\n", "").replace("\r", "")
EMAIL.write_text(body, encoding="utf-8")
print("v6 email:", EMAIL, len(body), "chars")
print("stock cards:", len(stock_cards), "| sector groups:", len(sector_cards))
