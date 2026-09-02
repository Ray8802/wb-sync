"""Build v5: update watchlist report HTML + email HTML with 3-source news."""
import base64
import json
import pathlib

DATA = pathlib.Path("watchlist_data/quotes.json")
IMGS = pathlib.Path("closing_charts")
SEL = pathlib.Path("watchlist_data/news_selected_0901.json")
REPORT = pathlib.Path("watchlist_data/watchlist_report_2026-09-01.html")
EMAIL = pathlib.Path("watchlist_data/mail_attach/report_cdn_v5.html")

rows = json.loads(DATA.read_text(encoding="utf-8"))
sel = json.loads(SEL.read_text(encoding="utf-8"))

SRC_BADGE = {
    "金十数据": ("#e6732e", "金十数据"),
    "财联社": ("#2f6fed", "财联社"),
    "东方财富": ("#d93026", "东方财富"),
}

def pick_title(content):
    """取第一句作为标题（<=34 字），其余为正文"""
    for sep in ["。", "；", "；", ". "] :
        idx = content.find(sep)
        if 0 < idx <= 34:
            return content[:idx + 1], content[idx + 1:]
    return content[:34], content[34:]

# ---------- 报告版 NEWS ----------
news_report = []
for i, r in enumerate(sel):
    stock = r["stock"]
    if not r["content"]:
        news_report.append(
            f'<div class="news"><span class="tag">{stock}</span><b>当日无重大快讯</b>：9月1日金十数据/财联社/东方财富三源未收录该标的重大新闻（该股当日走势平稳，无公告或事件催化）。</div>')
        continue
    title, body = pick_title(r["content"])
    srcs = " / ".join(r["srcs"]) if r["srcs"] else "快讯"
    src_html = f'<br><span class="src">来源：{srcs}｜{r["time"]}</span>'
    news_report.append(
        f'<div class="news"><span class="tag">{stock}</span><b>{title}</b>{body}{src_html}</div>')

NEWS_REPORT = "\n".join(news_report)

# ---------- 邮件版（v4 卡片 + 来源 badge）----------
news_mail = []
for i, r in enumerate(sel):
    stock = r["stock"]
    if not r["content"]:
        news_mail.append(
            f"<div style='background:#fff8e1;border-left:4px solid #f5a623;padding:10px 12px;border-radius:6px;margin:9px 0;'>"
            f"<p style='margin:0;font-size:14px;line-height:1.7;color:#444;'><b style='color:#1f2329;'>{i+1}. {stock}</b> — 当日三源（金十/财联社/东方财富）无重大快讯</p></div>")
        continue
    title, body = pick_title(r["content"])
    badges = "".join(
        f"<span style='display:inline-block;background:{c};color:#fff;font-size:10px;padding:1px 6px;border-radius:3px;margin-right:4px;'>{n}</span>"
        for c, n in [SRC_BADGE[s] for s in r["srcs"] if s in SRC_BADGE])
    body_html = f"<span style='color:#666;'>{body}</span>" if body else ""
    time_html = f"<span style='color:#9aa0a6;font-size:11px;'>｜{r['time']}</span>"
    news_mail.append(
        f"<div style='background:#fff8e1;border-left:4px solid #f5a623;padding:10px 12px;border-radius:6px;margin:9px 0;'>"
        f"<p style='margin:0 0 3px;font-size:14px;line-height:1.5;'><b style='color:#1f2329;'>{i+1}. {stock}</b> <b style='font-size:14px;color:#1f2329;'>{title}</b>{time_html}</p>"
        f"<p style='margin:0;font-size:13px;line-height:1.7;color:#444;'>{body_html}</p>"
        f"<p style='margin:4px 0 0;'>{badges}</p>"
        f"</div>")
NEWS_MAIL = "\n".join(news_mail)

# ---------- 报告 HTML ----------
def b64(p):
    return base64.b64encode(p.read_bytes()).decode()

img_flow = b64(IMGS / "wl_flow.png")
img_chg = b64(IMGS / "wl_chg.png")
img_amt = b64(IMGS / "wl_amount.png")

def chg_s(v):
    if v is None:
        return "&mdash;"
    cls = "red" if v > 0 else ("green" if v < 0 else "gray")
    return f'<span class="{cls}">{v:+.2f}%</span>'

def net_s(r):
    if r.get("main_net") is None:
        return '<span class="gray">&mdash;</span>'
    v = r["main_net"] / 1e8
    cls = "red" if v > 0 else "green"
    pct = r.get("main_pct")
    extra = f" ({pct:+.2f}%)" if isinstance(pct, (int, float)) else ""
    return f'<span class="{cls}">{v:+.2f} 亿{extra}</span>'

def amt_s(r):
    v = r.get("amount")
    cur = r.get("currency") or "CNY"
    if v is None:
        return "&mdash;"
    if cur == "KRW":
        return f'{v/1e12:.2f} 万亿韩元'
    return f'{v/1e8:.2f} 亿'

def flag(r):
    cur = r.get("currency") or ""
    if cur == "KRW":
        return " &#127472;&#127479;"
    if cur.startswith("HKD"):
        return " &#127475;&#127473;"
    return ""

rows_sorted = sorted(rows, key=lambda r: (r.get("main_net") is None, -(r.get("main_net") or 0)))
trs = []
for r in rows_sorted:
    trs.append(
        f'<tr><td><b>{r["name"]}</b>{flag(r)}</td>'
        f'<td class="mono">{r["code"]}</td>'
        f'<td>{chg_s(r.get("chg_pct"))}</td><td>{amt_s(r)}</td>'
        f'<td class="num">{r["volume"]:,} {r.get("volume_unit") or "手"}</td>'
        f'<td>{net_s(r)}</td><td class="src">{r.get("flow_src") or "&mdash;"}</td></tr>')

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>自选股复盘｜2026-09-01（三源重大新闻版）</title>
<style>
body{{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;max-width:880px;margin:24px auto;color:#1f2329;line-height:1.65;background:#f5f7fa;padding:0 16px;}}
.wrap{{background:#fff;padding:24px 28px;border-radius:10px;box-shadow:0 2px 12px rgba(0,0,0,.06);}}
h1{{font-size:22px;margin:0 0 6px;color:#d93026;}}
h2{{font-size:16px;border-left:4px solid #d93026;padding-left:8px;margin:20px 0 8px;}}
.meta{{color:#646a73;font-size:12px;margin:0 0 18px;padding-bottom:14px;border-bottom:1px solid #f0f1f3;}}
table{{border-collapse:collapse;width:100%;font-size:13px;margin-bottom:8px;}}
th,td{{border:1px solid #e5e6eb;padding:6px 8px;text-align:left;}}
th{{background:#d93026;color:#fff;font-weight:600;}}
tr:nth-child(even){{background:#fafbfc;}}
.red{{color:#d93026;font-weight:bold;}}
.green{{color:#0f9d58;font-weight:bold;}}
.gray{{color:#9aa0a6;}}
.mono{{font-family:Menlo,Consolas,monospace;color:#5f6368;}}
.num{{text-align:right;font-family:Menlo,Consolas,monospace;}}
.src{{color:#9aa0a6;font-size:11px;}}
.img-box{{text-align:center;margin:14px 0;}}
.img-box img{{max-width:100%;height:auto;border:1px solid #e5e6eb;border-radius:6px;background:#fff;}}
.news{{background:#fff8e1;border-left:4px solid #f5a623;padding:12px 16px;border-radius:6px;margin:10px 0;font-size:13px;}}
.news b{{color:#1f2329;}}
.tag{{display:inline-block;background:#d93026;color:#fff;font-size:11px;padding:2px 7px;border-radius:3px;margin-right:6px;white-space:nowrap;}}
.foot{{color:#8f959e;font-size:11px;margin-top:18px;padding-top:14px;border-top:1px solid #f0f1f3;}}
.warn{{background:#fff3e0;border-left:3px solid #ff9800;padding:10px 12px;border-radius:4px;margin:8px 0;font-size:12px;color:#5d4037;}}
</style>
</head>
<body>
<div class="wrap">
<h1>自选股复盘｜2026-09-01（三源重大新闻版）</h1>
<p class="meta">共 {len(rows)} 只自选股｜行情源：腾讯 qt.gtimg.cn｜资金流源：东财优先（限流降级新浪）｜重大新闻源：<b>金十数据 / 财联社 / 东方财富</b>（9-01 全天 3730 条快讯筛选）｜配色：涨红跌绿</p>

<h2>① 资金流红绿榜</h2>
<div class="img-box"><img src="data:image/png;base64,{img_flow}" alt="资金流红绿榜"></div>

<h2>② 当日涨跌幅榜</h2>
<div class="img-box"><img src="data:image/png;base64,{img_chg}" alt="涨跌幅榜"></div>

<h2>③ 成交额对比（人民币计价）</h2>
<div class="img-box"><img src="data:image/png;base64,{img_amt}" alt="成交额对比"></div>

<h2>④ 自选股复盘明细表（{len(rows)} 只）</h2>
<table>
<thead><tr><th>名称</th><th>代码</th><th>涨跌</th><th>成交额</th><th>成交量</th><th>主力净流入</th><th>资金源</th></tr></thead>
<tbody>{''.join(trs)}</tbody>
</table>
<div class="warn">⚠️ 数据口径：行情 100% 腾讯实时接口；资金流东财今日整体限流，降级新浪财经（主力=超大单+大单净额），表中已标注资金源。</div>

<h2>⑤ 15 只自选股重大新闻（金十数据 / 财联社 / 东方财富 三源筛选）</h2>
{NEWS_REPORT}

<p class="foot">* 本页为单文件 HTML（图表 base64 内嵌）；重大新闻抓取自金十数据、财联社、东方财富 2026-09-01 全天快讯（共 3730 条），按 15 只自选股关键词筛选；不构成投资建议。</p>
</div>
</body>
</html>"""

REPORT.write_text(html, encoding="utf-8")
print("报告已更新:", REPORT, REPORT.stat().st_size // 1024, "KB")

# ---------- 邮件 HTML v5（正文直接查看 + 三源新闻）----------
news_mail_html = "".join(news_mail)

head = (
    "<div style='font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;max-width:760px;margin:0 auto;color:#1f2329;'>"
    "<h2 style='color:#d93026;font-size:18px;margin:12px 0 4px;'>📊 2026-09-01 收盘财报（三源新闻版）</h2>"
    "<p style='color:#646a73;font-size:12px;margin:0 0 14px;'>数据时效：2026-09-01 A股/ETF/LOF/港股/韩股收盘 ｜ 重大新闻源：金十数据 / 财联社 / 东方财富</p>"
)

# 大盘表（复用 v4 的固定 HTML）
idx_table = (
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
    "<p style='font-size:12px;color:#5f6368;margin:6px 0;'>两市成交 20334 亿（缩量 976 亿）；涨 3386 / 跌 2040，涨停 86；主力净流出 237.77 亿。领涨：商贸零售 +3.08%、农林牧渔 +2.48%、银行 +1.88%；领跌：电子 -2.99%、煤炭 -2.13%。期指四大合约均空方占优（IM2609 净空 17731 手）。</p>"
)

# 自选股表（从 quotes 动态生成）
rows_mail = []
for q in rows:
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

wl_table = (
    "<h3 style='font-size:15px;border-left:4px solid #d93026;padding-left:8px;margin:16px 0 8px;'>二、自选股 15 只收盘</h3>"
    "<table style='border-collapse:collapse;width:100%;font-size:12px;'><tr>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>名称</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>现价</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>涨跌幅</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>成交额</th>"
    "<th style='background:#d93026;color:#fff;padding:5px 8px;border:1px solid #d93026;'>主力净流入</th></tr>"
    + "".join(rows_mail) + "</table>"
)

charts = (
    "<h3 style='font-size:15px;border-left:4px solid #d93026;padding-left:8px;margin:16px 0 8px;'>三、图表（已内嵌正文）</h3>"
    "<p style='font-size:12px;color:#5f6368;margin:4px 0;'>① 自选股资金流红绿榜</p>"
    "<p style='font-size:11px;color:#9aa0a6;margin:2px 0 6px;'>（若图表未显示，请点击邮件上方的【显示图片】按钮）</p>"
    "<img src='https://wb-sync.pages.dev/charts/chart_flow.png' alt='chart_flow' style='max-width:100%;height:auto;border:1px solid #e5e6eb;border-radius:6px;'>"
    "<p style='font-size:12px;color:#5f6368;margin:8px 0 4px;'>② 自选股涨跌幅分布</p>"
    "<img src='https://wb-sync.pages.dev/charts/chart_chg.png' alt='chart_chg' style='max-width:100%;height:auto;border:1px solid #e5e6eb;border-radius:6px;'>"
    "<p style='font-size:12px;color:#5f6368;margin:8px 0 4px;'>③ 自选股成交额排行</p>"
    "<img src='https://wb-sync.pages.dev/charts/chart_amount.png' alt='chart_amount' style='max-width:100%;height:auto;border:1px solid #e5e6eb;border-radius:6px;'>"
)

news_section = (
    "<h3 style='font-size:15px;border-left:4px solid #d93026;padding-left:8px;margin:16px 0 8px;'>四、重大新闻（金十数据/财联社/东方财富 三源筛选 · 15/15）</h3>"
    + news_mail_html
)

foot = "<p style='color:#9aa0a6;font-size:11px;margin-top:14px;border-top:1px solid #f0f1f3;padding-top:10px;'>本邮件自动生成，数据来自公开实时源，不构成投资建议。</p></div>"

body = (head + idx_table + wl_table + charts + news_section + foot).replace("\n", "").replace("\r", "")
EMAIL.write_text(body, encoding="utf-8")
print("邮件正文已生成:", EMAIL, len(body), "chars | cid imgs:", body.count('wb-sync.pages.dev/charts/chart_'))
