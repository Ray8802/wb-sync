"""Filter 3-source news by watchlist keywords, dedupe, pick top items per stock."""
import json
import pathlib
import re

RAW = pathlib.Path("watchlist_data/news_raw_0901.json")
OUT = pathlib.Path("watchlist_data/news_filtered_0901.json")

# 15 只自选股关键词映射
KEYWORDS = {
    "长城军工 601606": ["长城军工", "内蒙一机", "军贸", "国防军工"],
    "中国一重 601106": ["中国一重", "一重"],
    "岩山科技 002195": ["岩山科技", "纽劢", "脑机接口", "物理AI"],
    "北方稀土 600111": ["北方稀土", "稀土永磁", "稀土"],
    "传媒ETF 512980": ["传媒", "芒果超媒", "短剧", "AIGC", "影视", "游戏版号", "后西游记"],
    "军工龙头ETF 512710": ["军工", "商业航天", "国防", "导弹"],
    "卫星ETF 159206": ["卫星", "低轨", "千帆", "垣信", "火箭", "卫星互联网", "星链"],
    "芯片ETF 159937": ["芯片", "半导体", "存储芯片", "HBM", "光模块", "CPO", "光通信", "晶圆"],
    "电池ETF 159216": ["电池", "锂电", "储能", "宁德时代", "比亚迪", "赣锋", "天齐", "锂价"],
    "有色ETF 512400": ["有色金属", "沪铜", "沪铝", "沪锌", "沪锡", "铜价", "铝价", "锡价", "锑", "稀土"],
    "国投白银LOF 161226": ["白银", "沪银", "银价"],
    "商品LOF 161129": ["原油", "油价", "乙二醇", "甲醇", "沥青", "PVC", "对二甲苯", "纯碱", "夜盘", "大宗商品", "期货"],
    "中韩半导体ETF 513310": ["SK海力士", "海力士", "KOSPI", "韩国半导体", "存储芯片", "三星电子"],
    "黄金ETF 518880": ["黄金", "沪金", "金价", "金饰", "AU9999"],
    "南方东英SK海力士 07709": ["SK海力士", "海力士", "HBM", "DRAM", "NAND"],
    "智能驾驶ETF 516520": ["智能驾驶", "自动驾驶", "无人驾驶", "智驾"],
}

def clean_content(c):
    c = re.sub(r"^【[^】]*】", "", c)
    c = re.sub(r"^财联社\d+月\d+日电[,，]", "", c)
    c = re.sub(r"^.*?电[,，]\s*", "", c) if "电，" in c[:40] or "电，" in c[:40] else c
    return c.strip()

def main():
    items = json.loads(RAW.read_text(encoding="utf-8"))
    print("raw items:", len(items))

    # 内容指纹去重（跨源）
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
    print("after dedupe:", len(items))

    # 关键词匹配 → 按股票分组
    groups = {k: [] for k in KEYWORDS}
    for it in items:
        text = it["content"] + " " + it.get("title", "")
        for stock, kws in KEYWORDS.items():
            for kw in kws:
                if kw in text:
                    groups[stock].append(it)
                    break

    result = []
    for stock, lst in groups.items():
        # 排序：important 优先，其次盘中(09:30-15:00)优先，再按时间
        def rank(it):
            t = it["ts"]
            intraday = 1 if 1788197400 <= t <= 1788231600 else 0  # 09:30-15:00
            return (it["important"], intraday, t)
        lst.sort(key=rank, reverse=True)
        picked = lst[:2]
        for it in picked:
            srcs = it.get("srcs", [it["src"]])
            result.append({
                "stock": stock,
                "time": it["time"],
                "srcs": srcs,
                "content": clean_content(it["content"]),
                "important": it["important"],
            })

    # 排序：按股票清单顺序
    order = list(KEYWORDS.keys())
    result.sort(key=lambda r: order.index(r["stock"]))
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("filtered:", len(result))
    for r in result:
        print(f"- {r['stock']} [{r['time']}] {'★' if r['important'] else ''} {r['content'][:50]}")

if __name__ == "__main__":
    main()
