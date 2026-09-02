"""Fetch 2026-09-01 all-day flash news from Jin10 / CLS / Eastmoney, filter by watchlist keywords."""
import hashlib
import json
import pathlib
import subprocess
import time

SINCE = 1788192000  # 2026-09-01 00:00:00 GMT+8
UNTIL = 1788278399  # 2026-09-01 23:59:59 GMT+8
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
OUT = pathlib.Path("watchlist_data/news_raw_0901.json")

def curl(url, extra=()):
    cmd = ["curl", "-s", "--max-time", "20", url, "-H", f"user-agent: {UA}"] + list(extra)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        return r.stdout
    except Exception as e:
        print("curl err", e)
        return ""

def ts_of(s):
    try:
        return int(time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S")))
    except Exception:
        return None

# ---------- Jin10 (max_time 为字符串时间) ----------
def fetch_jin10():
    items = []
    max_time = ""
    pages = 0
    while pages < 120:
        url = f"https://flash-api.jin10.com/get_flash_list?max_time={max_time}&channel=-8200"
        raw = curl(url, ["-H", "x-app-id: bVBF4FyRTn5NJF5n", "-H", "x-version: 1.0.0"])
        try:
            lst = json.loads(raw).get("data", [])
        except Exception:
            break
        if not lst:
            break
        stop = False
        for it in lst:
            ts = ts_of(it.get("time", ""))
            if ts is None:
                continue
            if UNTIL >= ts >= SINCE:
                items.append({
                    "src": "金十数据", "ts": ts, "time": it["time"],
                    "content": it["data"].get("content", ""),
                    "important": it.get("important", 0),
                    "title": it["data"].get("title", ""),
                })
            elif ts < SINCE:
                stop = True
        last = lst[-1].get("time", "")
        max_time = last
        pages += 1
        time.sleep(0.4)
        if stop or ts_of(last) is None or ts_of(last) <= SINCE:
            break
    print(f"jin10 pages={pages} items={len(items)}")
    return items

# ---------- CLS (ctime 秒级时间戳) ----------
def fetch_cls():
    items = []
    last_time = 0
    pages = 0
    while pages < 120:
        params = f"app=CailianpressWeb&category=&last_time={last_time}&os=web&rn=30&sv=8.4.6"
        sign = hashlib.md5(hashlib.sha1(params.encode()).hexdigest().encode()).hexdigest()
        url = f"https://www.cls.cn/v1/roll/get_roll_list?{params}&sign={sign}"
        raw = curl(url, ["-H", "Referer: https://www.cls.cn/telegraph"])
        try:
            lst = json.loads(raw).get("data", {}).get("roll_data", [])
        except Exception:
            break
        if not lst:
            break
        stop = False
        for it in lst:
            ts = it.get("ctime") or 0
            if UNTIL >= ts >= SINCE:
                items.append({
                    "src": "财联社", "ts": ts,
                    "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
                    "content": it.get("content", ""),
                    "important": 1 if it.get("level") == "A" else 0,
                    "title": it.get("title", ""),
                })
            elif ts < SINCE:
                stop = True
        last = lst[-1].get("ctime") or 0
        last_time = last - 1
        pages += 1
        time.sleep(0.4)
        if stop or last <= SINCE:
            break
    print(f"cls pages={pages} items={len(items)}")
    return items

# ---------- Eastmoney ----------
def fetch_em():
    items = []
    sort_end = ""
    pages = 0
    while pages < 80:
        url = ("https://np-listapi.eastmoney.com/comm/web/getFastNewsList?"
               f"client=web&biz=web_724&fastColumn=102&sortEnd={sort_end}&pageSize=50&req_trace=1")
        raw = curl(url, ["-H", "Referer: https://kuaixun.eastmoney.com/"])
        try:
            d = json.loads(raw)
            data = d.get("data", {})
            lst = data.get("fastNewsList", [])
        except Exception:
            break
        if not lst:
            break
        stop = False
        for it in lst:
            ts = ts_of(it.get("showTime", ""))
            if ts is None:
                continue
            if UNTIL >= ts >= SINCE:
                items.append({
                    "src": "东方财富", "ts": ts, "time": it["showTime"],
                    "content": it.get("summary", "") or it.get("title", ""),
                    "important": 1 if it.get("stockList") else 0,
                    "title": it.get("title", ""),
                    "stocks": it.get("stockList", []),
                })
            elif ts < SINCE:
                stop = True
        sort_end = data.get("sortEnd", "")
        pages += 1
        time.sleep(0.4)
        if stop or not sort_end:
            break
    print(f"em pages={pages} items={len(items)}")
    return items

if __name__ == "__main__":
    all_items = []
    all_items += fetch_jin10()
    all_items += fetch_cls()
    all_items += fetch_em()
    all_items.sort(key=lambda x: x["ts"])
    OUT.write_text(json.dumps(all_items, ensure_ascii=False, indent=1), encoding="utf-8")
    print("total:", len(all_items), "->", OUT)
