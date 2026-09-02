"""v6: per-stock top3 news + sector-level top3 news from 3 sources."""
import json
import pathlib
import re

RAW = pathlib.Path("watchlist_data/news_raw_0901.json")
OUT = pathlib.Path("watchlist_data/news_v6_0901.json")

# 个股关键词
STOCK_KW = {
    "长城军工 601606": ["长城军工", "内蒙一机", "军贸", "国防军工", "军工装备"],
    "中国一重 601106": ["中国一重"],
    "岩山科技 002195": ["岩山科技", "脑机接口", "物理AI"],
    "北方稀土 600111": ["北方稀土", "稀土永磁"],
    "传媒ETF 512980": ["传媒", "芒果超媒", "短剧", "AIGC", "影视", "出版"],
    "军工龙头ETF 512710": ["军工", "商业航天", "导弹", "国防"],
    "卫星ETF 159206": ["卫星", "低轨", "千帆", "垣信", "火箭", "卫星互联网"],
    "芯片ETF 159937": ["芯片", "半导体", "存储", "HBM", "光模块", "CPO", "晶圆"],
    "电池ETF 159216": ["电池", "锂电", "储能", "宁德时代", "碳酸锂", "锂"],
    "有色ETF 512400": ["有色金属", "沪铜", "沪铝", "沪锌", "沪锡", "铜金矿", "铜价"],
    "国投白银LOF 161226": ["白银", "沪银", "银价"],
    "商品LOF 161129": ["甲醇", "乙二醇", "原油", "油价", "沥青", "PVC", "夜盘", "期货"],
    "中韩半导体ETF 513310": ["SK海力士", "海力士", "KOSPI", "韩国半导体", "存储"],
    "黄金ETF 518880": ["黄金", "沪金", "金价", "金饰"],
    "南方东英SK海力士 07709": ["SK海力士", "海力士", "HBM", "DRAM", "NAND"],
    "智能驾驶ETF 516520": ["智能驾驶", "自动驾驶", "无人驾驶", "智驾"],
}

# 板块关键词（持仓相关板块）
SECTOR_KW = {
    "军工/国防": ["军工", "国防", "导弹", "军贸", "内蒙一机"],
    "半导体/存储": ["芯片", "半导体", "存储", "HBM", "DRAM", "NAND", "光模块", "CPO", "晶圆", "SK海力士"],
    "稀土/有色": ["稀土", "永磁", "有色金属", "铜", "铝", "锌", "锡", "铜金矿"],
    "锂电/储能": ["锂", "电池", "储能", "宁德时代", "碳酸锂", "固态电池"],
    "传媒/短剧": ["传媒", "短剧", "芒果超媒", "AIGC", "影视", "出版", "游戏"],
    "卫星/商业航天": ["卫星", "低轨", "千帆", "垣信", "火箭", "商业航天", "卫星互联网"],
    "贵金属": ["黄金", "白银", "沪金", "沪银", "金价", "银价"],
    "原油/商品": ["原油", "油价", "甲醇", "乙二醇", "沥青", "PVC", "夜盘", "期货"],
    "智能驾驶": ["智能驾驶", "自动驾驶", "无人驾驶", "智驾", "车联网"],
    "脑机接口/AI": ["脑机接口", "物理AI", "人形机器人", "具身智能"],
}

def clean(c):
    c = re.sub(r"^【[^】]*】\s*", "", c)
    c = re.sub(r"^金十数据\d+月\d+日[讯]?[,，]?\s*", "", c)
    c = re.sub(r"^财联社\d+月\d+日电[,，]?\s*", "", c)
    return c.strip()

def main():
    items = json.loads(RAW.read_text(encoding="utf-8"))
    # 去重
    seen = {}
    for it in items:
        fp = re.sub(r"\s+", "", it["content"])[:60]
        if fp not in seen:
            seen[fp] = it
        else:
            old = seen[fp]
            if it["important"] and not old["important"]:
                old["important"] = 1
            srcs = old.get("srcs", [old["src"]])
            if it["src"] not in srcs:
                srcs.append(it["src"])
                old["srcs"] = srcs
    items = list(seen.values())

    INTRA = (1788197400, 1788231600)  # 09:30-15:00

    def rank(it):
        t = it["ts"]
        return (it["important"], 1 if INTRA[0] <= t <= INTRA[1] else 0, t)

    def match(text, kws):
        return [kw for kw in kws if kw in text]

    # ---- 个股 top3 ----
    stocks = {}
    for stock, kws in STOCK_KW.items():
        hits = []
        for it in items:
            text = it["content"] + " " + it.get("title", "")
            mk = match(text, kws)
            if mk:
                hits.append((it, mk))
        hits.sort(key=lambda x: rank(x[0]), reverse=True)
        picked = []
        for it, mk in hits[:3]:
            picked.append({
                "time": it["time"],
                "srcs": it.get("srcs", [it["src"]]),
                "content": clean(it["content"]),
                "kws": mk,
            })
        stocks[stock] = picked

    # ---- 板块 top3 ----
    sectors = {}
    for sec, kws in SECTOR_KW.items():
        hits = []
        for it in items:
            text = it["content"] + " " + it.get("title", "")
            mk = match(text, kws)
            if mk:
                hits.append((it, mk))
        hits.sort(key=lambda x: rank(x[0]), reverse=True)
        picked = []
        for it, mk in hits[:3]:
            picked.append({
                "time": it["time"],
                "srcs": it.get("srcs", [it["src"]]),
                "content": clean(it["content"]),
                "kws": mk,
            })
        sectors[sec] = picked

    OUT.write_text(json.dumps({"stocks": stocks, "sectors": sectors}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("== 个股新闻数 ==")
    for k, v in stocks.items():
        print(f"{k}: {len(v)} 条", "|", " / ".join(x['content'][:22] for x in v) if v else "无")
    print("\n== 板块新闻数 ==")
    for k, v in sectors.items():
        print(f"{k}: {len(v)} 条")

if __name__ == "__main__":
    main()
