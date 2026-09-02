"""Build watchlist full HTML report with per-stock news."""
import base64
import json
import pathlib

DATA = pathlib.Path("watchlist_data/quotes.json")
IMGS = pathlib.Path("closing_charts")
rows = json.loads(DATA.read_text(encoding="utf-8"))

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
    name = r["name"]
    code = r["code"]
    chg = chg_s(r.get("chg_pct"))
    amt = amt_s(r)
    net = net_s(r)
    vol = f'{r["volume"]:,}' if r.get("volume") else "&mdash;"
    unit = r.get("volume_unit") or "手"
    src = r.get("flow_src") or "&mdash;"
    fl = flag(r)
    trs.append(
        f'<tr><td><b>{name}</b>{fl}</td>'
        f'<td class="mono">{code}</td>'
        f'<td>{chg}</td><td>{amt}</td>'
        f'<td class="num">{vol} {unit}</td>'
        f'<td>{net}</td><td class="src">{src}</td></tr>'
    )

NEWS = """
<div class="news"><span class="tag">601606 长城军工</span><b>板块联动 +4.46%</b>（盘中最高 33.80）。内蒙一机 600967 直线涨停 +10.02% 领涨，晟楠科技 +7.34%、北方长龙 +5.45%、天秦装备 +3.79%、航天彩虹 +3.48% 跟涨。<b>中证军工 80 家公司 2026H1 营收 3774.94 亿（同比 +18.89%），归母净利 247.72 亿（+32.92%）</b>，业绩向好验证行业景气。<br><b>风险：</b>雪球财报情报站指出 2026H1 营收 4.69 亿（同比 -32.89%），归母净利 -0.96 亿（由盈转亏），扣非 -1.05 亿，四家军品子公司全线亏损，年初至今 -30.81%；雪球讨论指向<b>对台军售</b>题材炒作。</div>
<div class="news"><span class="tag">601106 中国一重</span><b>+0.33% (3.07 元)</b>，盘中临时停牌过。<b>半年报 8/28 已披露</b>：营收 42.89 亿 / -8.38%，归母净利 -271.17 万（同比减亏 1.03 亿），扣非净利 -1549.56 万，EPS -0.0004，经营现金流 -4.99 亿。<br>2026H1 推进核心装备国产化，签了<b>南阳汉冶 5000mm 宽厚板轧机和核电常规岛整锻低压转子</b>等重要合同；治理优化推"提质增效重回报"，PE(TTM) -101.5 倍，市净率 4.08 倍。</div>
<div class="news"><span class="tag">002195 岩山科技</span><b>+1.55% (6.56 元)</b>，成交 6.88 亿，换手 1.87%。<b>8/28 半年报</b>：营收 3.42 亿 / +7.97%，归母净利 5951 万 / -11.33%，EPS 0.0105。<br><b>AI 板块转向</b>：Nullmax 不再纳入合并报表（出表），AI 业务收入 -91.90%；定位"<b>物理 AI 世界模型基座</b>"再校准；新设境外主体（<b>瑞復资本香港、Ruixin BVI、Ruiyan BVI</b>）配套 AI PC 出海，注销 7 家境内网络科技子公司。<br><b>研发投入 -53.75%</b>（归因于纽劢出表 + 股权激励减少），岩芯数智 +4 项授权发明专利，资产负债率仅 2.71%。向神思动量增资 2000 万（脑机接口商业化）。</div>
<div class="news"><span class="tag">600111 北方稀土</span><b>主力净流出 1.52 亿（多源一致）</b>，占 -12.43%。<b>板块弱势</b>：稀土永磁主力净流出 16.78 亿（行业 24/28 排名）。<br><b>技术面走弱</b>：9/1 RSI 死叉 + 短期 RSI 下穿 50；8/20 日线熊点，未有效突破 41.68 元压力位前需谨慎。<br><b>资金面</b>：近 10 日主力累计流出 13.48 亿；连续 3 日被减仓；<b>北向资金</b>（仍披露港股部分）最新减持 51.31 万股；融资近 10 日累计卖出 1.65 亿，杠杆资金看空。总市值 1452 亿，PE(TTM) 43.05。</div>
<div class="news"><span class="tag">512980 传媒ETF广发</span><b>逆市领涨 +3% (跟踪中证传媒399971)</b>，传媒板块全天主力净流入 +55.31 亿、+3.80% 领涨全市场。芒果超媒连续第二日 20cm 涨停（封单超 42 万手），粤传媒、掌阅科技、竞业达、壹网壹创、遥望科技、欢瑞世纪、中广天择、大晟文化等多股涨停。<br><b>催化</b>：8/31 国内首部 AIGC 长剧《后西游记》登陆湖南卫视黄金档（Seedance 2.0/2.5 生成、无真人演员、边制边播模式）；工信部发布《AI 应用服务商培育专项行动》。<br><b>ETF</b>：冲击 4 连涨，至 8/31 连续 3 日资金净流入 2.81 亿。</div>
<div class="news"><span class="tag">512710 军工龙头ETF富国</span><b>+0.64% (盘中异动)</b>，成交 1.11 亿，<b>跟随长城军工 +4.46%、内蒙一机 +10.02%</b> 板块联动。<br><b>催化</b>：9/1 经济观察网：<b>军工核心上市公司整体业绩向好</b>，板块异动拉升；中信建投指出关注商业航天投资机会。<br><b>事件</b>：8/25 SpaceX 宣布 1000 亿美元在路易斯安那州建全球最大发射场（最早 2029 首飞，每年数千次发射）；8/21 国务院常务会议听取新一代通信网建设情况汇报，<b>首次将空间网络/低轨卫星互联网</b>纳入国家级统筹；8/31 长城军工融资买入 3391.92 万。</div>
<div class="news"><span class="tag">159206 卫星ETF永赢</span><b>-1.36% (跟踪卫星互联网)</b>，板块主力净流出 38.06 亿。<b>8/31 大涨 +4.26%</b>后今日冲高回落。波导股份 600130 涨停 +10.04%（板块唯一涨停）；中国卫通 24.3 元 -0.41%。<br><b>催化</b>：9/1 工信部批复浙江时空道宇科技<b>卫星物联网商用试验两年</b>（依托低轨星座提供全球物联）；阿里创业投资+上汽金控入股<b>垣信卫星</b>（"千帆星座"专属主体，注册资本增至 24.8 亿）；长光卫星建成 19 星全球最大立体测绘星群；东升宇航研制 10kW 算力卫星；9/1 安徽造"智神星一号"中大型可重复使用火箭酒泉首飞。</div>
<div class="news"><span class="tag">159937 芯片ETF鹏华</span><b>-2.50% (跟踪国证芯片)</b>，科技板块集体回调：HBM -3.51% / 存储器 -2.95% / 光芯片 -1.93% / 半导设备 -3.73%。<br><b>消息面上</b>：隔夜美股存储芯片多数上涨（闪迪 +5.5%、美光 +2.77%、SK海力士 +2.20%），但今日<b>A 股存储/光通信板块集体回调</b>，压制指数；国金证券 8/30 研报：高速光模块交付提速，800G/1.6T 全球化交付，7-8 月供应链齐套率恢复至 70%，<b>Q3-Q4 供应约束有望缓解</b>；爱建证券：2025-2030 全球光模块市场 CAGR 约 22%，CPO 2026-2027 放量。</div>
<div class="news"><span class="tag">159216 电池ETF广发</span><b>-1.39% (跟踪电池板块)</b>，板块主力净流出 30.53 亿。锂电池概念收 -0.62% / 储能 -0.19%。<b>龙头表现</b>：宁德时代 358.1 元 -1.50%（主力净流出）、比亚迪 88.71 元 +0.58%；领湃科技 21.15 元 +11.14% 涨停（储能电池系统集成）。<br><b>催化</b>：力神电池苏州对锂离子蓄电池消费税成本上调客户联络函；阳光电源 H1 归母净利 52.59 亿 / -32.01%；赣锋锂业 H1 42.57 亿 / 扭亏；天齐锂业 H1 42.42 亿 / +4925.46%；7 月太阳能新增装机 1408 万千瓦 / +27.5%。</div>
<div class="news"><span class="tag">512400 有色ETF南方</span><b>-0.92% (跟踪中证有色)</b>，板块今日普跌：工业有色 -0.98% / 有色金属 -1.11% / 细分有色 -1.00%。<br><b>金属个股</b>：白银有色 6.74 元 -1.89%、中稀有色 81.76 元 -2.33%、华锡有色 47.00 元 -1.71%。<b>期货端</b>：沪铜 +0.50%、沪铝 +0.63%、沪锌 +2.71% 偏强；沪铅 -0.65%、沪锡 +0.93%。<br><b>驱动</b>：锡/锑/铋/锆等多品种期货回调；稀土板块主力净流出 -16.78 亿（北方稀土流出最重）。</div>
<div class="news"><span class="tag">161226 国投白银LOF</span><b>-1.84%</b>，<b>白银市场承压</b>：沪银主力 16212 元/千克 -2.74%（国内）；COMEX 白银 66.81 美元 -1.45%；白银 T+D 16150 元 -1.78%。<br><b>核心驱动</b>：美联储主席<b>沃什杰克逊霍尔鹰派讲话</b>推升 9 月加息概率至 60-66%；美 10Y 国债收益率 4.76% 创 2025-01 来最高；美伊冲突升级，霍尔木兹海峡通行安全恶化，油价 WTI +1.82% / 布伦特 +1.76% 重上 92。<br><b>SPDR Gold Trust 持仓</b>8/28 降至 1042.35 吨，<b>上周累计减持 4.85 吨</b>（持续增持数周后首次显著减仓）；国际现货金跌破 4400 美元（4379.92 美元 -1.6%）；金银比 66.9。</div>
<div class="news"><span class="tag">161129 国投商品LOF</span><b>-0.43% (跟踪上海期交所商品综合指数)</b>，<b>今日期货盘 38 涨 21 跌</b>，大宗指数 sh000979 -0.82% / 7042.52 点。<br><b>强势品种</b>：乙二醇 +6.37%（受地缘 + 油价 + 减产共振），甲醇 +5.43%，沥青 +4.18%，PVC +4.09%，对二甲苯 +4.01%，多晶硅 +3.22%。<br><b>弱势品种</b>：红枣 -3.02%（旧季高库存去化缓慢），生猪 -2.67%（开学季备货需求不及预期），苹果 -2.11%，沪银 -2.54%，沪金 -1.87%。<br><b>事件</b>：8/29 国家能源局宣布光伏发电装机历史性超过煤电，成为装机规模最大的电源品类。</div>
<div class="news"><span class="tag">513310 中韩半导体ETF</span><b>+1.42% 主力净流入</b>（跟踪韩国半导体），成交 78.31 亿（自选股第一），换手 67.36%（跨境 ETF 高换手，可能为溢价套利资金）。今日韩国 KOSPI 收涨 +0.23%。<b>SK海力士 +1.14%</b>（169.3 万韩元 / 1.2 万亿韩元成交 ≈ 62 亿人民币）；<b>美股存储芯片</b>（SK海力士 ADR -0.74%、闪迪美股盘前 -3%、美光 -1.71%、西部数据 -1.34%）；HBM 板块 -3.51% / 存储器 -2.95%。</div>
<div class="news"><span class="tag">518880 黄金ETF博时</span><b>-1.87% (跟踪 AU9999 国内金)</b>，<b>沪金主力 959.84 元/克 -1.88%</b>（创 6 周来最大单日跌幅）。<br><b>国际</b>：COMEX 黄金 4478.71 美元 -1.13%，<b>现货金跌破 4400 美元</b>（4379.92 美元 -1.6%）；沪银 -2.54% 跌幅大于金。<br><b>驱动</b>：沃什鹰派讲话推升 9 月加息概率至 60-66%；美元指数 99.59 拉升；10Y 美债收益率 4.756% 创 2025-01 来最高；SPDR Gold Trust 上周累计减持 4.85 吨（首次显著减仓）。<br><b>机构观点</b>：瑞银维持 2027-09 目标价 5400 美元；高盛重申年底 4900 美元。</div>
<div class="news"><span class="tag">116.07709 南方东英SK海力士 2 倍做多</span><b>+1.04%</b>，成交 32.08 亿港币。<b>关联美股</b>SK海力士 ADR SKHY.US 163.36 美元 -0.74%（盘前跌 1.26%），总市值 11596 亿美元，PE(TTM) 11.13，年初至今 +9.64%。<br><b>财报预期</b>：DRAM 占比 77.10%（527.04 亿美元），NAND 占比 21.30%（145.58 亿美元）。HBM 主线：智谱 GLM-5.3-Flash 承载 10 万张国产芯片推理流量，国产算力从实验室测试迈入生产环境，<b>端到端性能提升 3 倍</b>（浙商证券）。</div>
"""

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>自选股复盘｜2026-09-01（含每只标的重大新闻）</title>
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
.news{{background:#fff8e1;border-left:4px solid #f5a623;padding:12px 16px;border-radius:6px;margin:10px 0;font-size:12.5px;}}
.news b{{color:#1f2329;}}
.tag{{display:inline-block;background:#d93026;color:#fff;font-size:11px;padding:2px 7px;border-radius:3px;margin-right:6px;white-space:nowrap;}}
.foot{{color:#8f959e;font-size:11px;margin-top:18px;padding-top:14px;border-top:1px solid #f0f1f3;}}
.warn{{background:#fff3e0;border-left:3px solid #ff9800;padding:10px 12px;border-radius:4px;margin:8px 0;font-size:12px;color:#5d4037;}}
</style>
</head>
<body>
<div class="wrap">
<h1>自选股复盘｜2026-09-01（含每只标的重大新闻）</h1>
<p class="meta">共 {len(rows)} 只自选股｜行情源：腾讯 qt.gtimg.cn（A股/ETF/LOF/港股/韩股）｜资金流源：东财优先（限流时降级新浪）｜新闻源：腾讯财经/东方财富/中新经纬/华尔街见闻/智通财经/同花顺等公开数据，实时抓取｜配色：涨红跌绿</p>

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
<div class="warn">⚠️ 数据口径：行情 100% 腾讯实时接口（A 股/ETF/LOF/港股/韩股全支持，稳定）；<b>资金流</b>东财今日整体限流，降级新浪财经（主力=超大单+大单净额）；新浪 r0+r1 与东财 f62 口径有差异，表中已标注资金源。</div>

<h2>⑤ 15 只自选股重大新闻（按板块聚合）</h2>
{NEWS}

<p class="foot">* 本页为单文件 HTML（图表 base64 内嵌），无外链依赖；数据均来自 2026-09-01 实时公开源；新闻时效限今日 09:30-15:00 增量；不构成投资建议。</p>
</div>
</body>
</html>"""

out = pathlib.Path("watchlist_data/watchlist_report_2026-09-01.html")
out.write_text(html, encoding="utf-8")
print("生成", out, "大小", out.stat().st_size // 1024, "KB")
print("新闻块数:", NEWS.count('<div class="news">'))
