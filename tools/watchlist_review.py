# -*- coding: utf-8 -*-
"""自选股复盘数据抓取

数据源：
  - 自选股清单：Gitee 同步库 sync-db.json（bucket=custom 且未删除）
  - 行情（价/涨跌/量/额/换手）：腾讯 qt.gtimg.cn（批量，稳定）
  - 资金流（主力净额）：东方财富 push2（优先）；失败降级新浪 MoneyFlow
  - 韩股（腾讯不支持）：东财 push2 单只查询

输出：watchlist_data/quotes.json  + 控制台摘要
"""
import base64
import json
import subprocess
import time
import urllib.parse
from pathlib import Path

GITEE_TOKEN = "b93b81ee3f63328a9a65a612b8bb219b"
GITEE_API = ("https://gitee.com/api/v5/repos/ray597/wb-sync/"
             "contents/sync-db.json?access_token=" + GITEE_TOKEN)
OUT = Path(__file__).parent / "watchlist_data"

# 东财资金流 / 行情字段
EM_FIELDS = "f12,f14,f2,f3,f5,f6,f8,f62,f184,f66,f72,f78,f84"


def curl(url: str, timeout: int = 20, retries: int = 2, decode: str = "utf-8"):
    """带重试的 curl 抓取"""
    last = None
    for _ in range(retries + 1):
        try:
            r = subprocess.run(["curl", "-s", "--max-time", str(timeout), url],
                               capture_output=True, timeout=timeout + 5)
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.decode(decode, errors="ignore")
            last = f"rc={r.returncode} empty"
        except Exception as e:
            last = str(e)
        time.sleep(1.0)
    print(f"  [warn] 抓取失败({last}): {url[:90]}")
    return None


def curl_json(url: str, **kw):
    t = curl(url, **kw)
    if not t:
        return None
    try:
        return json.loads(t)
    except Exception as e:
        print(f"  [warn] JSON 解析失败: {e} — {t[:120]}")
        return None


def load_watchlist() -> list:
    d = curl_json(GITEE_API)
    if not d:
        raise RuntimeError("无法读取 Gitee 自选股数据")
    db = json.loads(base64.b64decode(d["content"]).decode("utf-8"))
    out = []
    for k, v in (db.get("recs") or {}).items():
        if v.get("bucket") != "custom" or v.get("deleted"):
            continue
        val = v.get("value") or {}
        if val.get("code"):
            out.append(val)
    return out


def tx_code(secid: str, code: str):
    """东财 secid -> 腾讯代码前缀（腾讯支持 sh/sz/hk/kr）"""
    if secid.startswith("1."):
        return "sh" + code
    if secid.startswith("0."):
        return "sz" + code
    if secid.startswith("116."):
        return "hk" + code
    if secid.startswith("177."):
        return "kr" + code           # 韩股：kr000660
    return None


def num(x):
    try:
        if x is None or x == "" or x == "-":
            return None
        return float(x)
    except Exception:
        return None


def grab_tx(entries: list) -> dict:
    """腾讯批量行情：返回 {code: {...}}"""
    pairs = []
    for e in entries:
        tc = tx_code(e["secid"], e["code"])
        if tc:
            pairs.append((tc, e))
    if not pairs:
        return {}
    codes = ",".join(tc for tc, _ in pairs)
    text = curl(f"http://qt.gtimg.cn/q={codes}", decode="gbk")
    if not text:
        return {}
    out = {}
    for line in text.strip().split("\n"):
        if '="' not in line:
            continue
        key = line.split("=")[0].replace("v_", "").strip()
        body = line.split('="', 1)[1].rstrip('";')
        f = body.split("~")
        if len(f) < 40:
            continue
        prefix, pure = key[:2], key[2:]
        g = lambda i: num(f[i]) if i < len(f) else None
        amt_raw = g(37)
        if prefix == "hk":
            amount = amt_raw                     # 港股：元
            vol_unit = "股"
            currency = "HKD/CNY"
        elif prefix == "kr":
            amount = (g(45) or 0) * 1e6          # 韩股：百万韩元 -> 韩元
            vol_unit = "股"
            currency = "KRW"
        else:
            amount = (amt_raw or 0) * 1e4        # A股：万元 -> 元
            vol_unit = "手"
            currency = "CNY"
        out[pure] = {
            "name": f[1] if len(f) > 1 else None,
            "price": g(3), "prev": g(4), "open": g(5),
            "volume": g(6), "volume_unit": vol_unit,
            "chg": g(31), "chg_pct": g(32),
            "high": g(33), "low": g(34),
            "amount": amount,
            "currency": currency,
            "turnover": g(38) if prefix in ("sh", "sz") else None,
            "amplitude": g(43) if prefix in ("sh", "sz") else None,
            "float_cap": g(44) if prefix in ("sh", "sz") else None,
            "total_cap": g(45) if prefix in ("sh", "sz") else None,
            "src": "腾讯",
        }
    return out


def grab_em_flow(entries: list) -> dict:
    """东财资金流（分批 5 只，逗号保持原样）"""
    cn = [e for e in entries if e["secid"].startswith(("1.", "0."))]
    out = {}
    BATCH = 5
    for i in range(0, len(cn), BATCH):
        chunk = cn[i:i + BATCH]
        secids = ",".join(e["secid"] for e in chunk)
        url = ("https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2"
               f"&secids={urllib.parse.quote(secids, safe=',')}&fields={EM_FIELDS}")
        d = curl_json(url, retries=1)
        if not d:
            continue
        for it in ((d.get("data") or {}).get("diff") or []):
            out[str(it.get("f12"))] = {
                "main_net": it.get("f62"),
                "main_pct": it.get("f184"),
                "super_net": it.get("f66"),
                "big_net": it.get("f72"),
                "mid_net": it.get("f78"),
                "small_net": it.get("f84"),
                "src": "东财",
            }
        time.sleep(0.6)
    return out


def grab_sina_flow(entries: list) -> dict:
    """新浪资金流兜底：主力净额 = 超大单(r0) + 大单(r1) 净额"""
    out = {}
    for e in entries:
        tc = tx_code(e["secid"], e["code"])
        if not tc or tc.startswith("hk"):
            continue
        url = ("https://vip.stock.finance.sina.com.cn/quotes_service/"
               f"api/json_v2.php/MoneyFlow.ssi_ssfx_flzjtj?daima={tc}")
        d = curl_json(url, retries=1)
        if not d:
            continue
        try:
            r0 = num(d.get("r0_in")) or 0
            r0o = num(d.get("r0_out")) or 0
            r1 = num(d.get("r1_in")) or 0
            r1o = num(d.get("r1_out")) or 0
            main = (r0 - r0o) + (r1 - r1o)
            amt = num(d.get("r0")) or 0
            total_amt = (num(d.get("r0")) or 0) + (num(d.get("r1")) or 0) + \
                        (num(d.get("r2")) or 0) + (num(d.get("r3")) or 0)
            out[str(e["code"])] = {
                "main_net": main,
                "main_pct": (main / total_amt * 100) if total_amt else None,
                "super_net": r0 - r0o,
                "big_net": r1 - r1o,
                "src": "新浪",
            }
        except Exception as ex:
            print(f"  [warn] 新浪资金流解析失败 {e['name']}: {ex}")
        time.sleep(0.4)
    return out


def grab_kr(entries: list) -> dict:
    """韩股（secid 177.*）—— 东财单只"""
    out = {}
    for e in entries:
        if not e["secid"].startswith("177."):
            continue
        url = ("https://push2.eastmoney.com/api/qt/stock/get?fltt=2"
               f"&secid={e['secid']}&fields=f57,f58,f43,f60,f169,f170,f47,f48,f46")
        d = curl_json(url, retries=1)
        if not d:
            continue
        it = d.get("data") or {}
        price = it.get("f43")
        prev = it.get("f60")
        chg = it.get("f170")
        # 韩股价格/涨跌幅需除以 100（东财返回整数放大值）
        out[str(e["code"])] = {
            "name": it.get("f58") or e["name"],
            "price": (price / 100) if isinstance(price, int) else price,
            "prev": (prev / 100) if isinstance(prev, int) else prev,
            "chg_pct": (chg / 100) if isinstance(chg, int) else chg,
            "volume": it.get("f47"),
            "volume_unit": "股",
            "amount": it.get("f48"),
            "src": "东财",
        }
        time.sleep(0.5)
    return out


def fmt_amount(x, currency: str = "CNY"):
    if x is None:
        return "—"
    if currency == "KRW":                     # 韩元：按万亿/亿韩元显示
        if abs(x) >= 1e12:
            return f"{x/1e12:.2f} 万亿韩元"
        if abs(x) >= 1e8:
            return f"{x/1e8:.0f} 亿韩元"
        return f"{x:.0f} 韩元"
    if abs(x) >= 1e8:
        return f"{x/1e8:.2f} 亿"
    if abs(x) >= 1e4:
        return f"{x/1e4:.0f} 万"
    return f"{x:.0f}"


def fmt_net(x):
    if x is None:
        return "—"
    s = "+" if x > 0 else ""
    if abs(x) >= 1e8:
        return f"{s}{x/1e8:.2f} 亿"
    if abs(x) >= 1e4:
        return f"{s}{x/1e4:.0f} 万"
    return f"{s}{x:.0f}"


def main():
    OUT.mkdir(exist_ok=True)
    print("== 自选股清单 ==")
    entries = load_watchlist()
    print(f"  共 {len(entries)} 只\n")

    print("== 行情（腾讯）==")
    tx = grab_tx(entries)
    print(f"  拿到 {len(tx)} 只")

    print("== 资金流（东财优先，降级新浪）==")
    flow = grab_em_flow(entries)
    if len(flow) < len([e for e in entries if e["secid"].startswith(("1.", "0."))]):
        print(f"  东财仅覆盖 {len(flow)} 只，启用新浪兜底…")
        sina = grab_sina_flow(entries)
        for k, v in sina.items():
            flow.setdefault(k, v)
    print(f"  资金流覆盖 {len(flow)} 只")

    print("== 韩股（东财）==")
    kr = grab_kr(entries)
    print(f"  拿到 {len(kr)} 只")

    # 合并
    rows = []
    for e in entries:
        code = str(e["code"])
        q = tx.get(code) or kr.get(code) or {}
        fl = flow.get(code) or {}
        rows.append({
            "code": code,
            "name": e.get("name") or q.get("name"),
            "market": e.get("market"),
            "type": e.get("type"),
            "price": q.get("price"),
            "chg_pct": q.get("chg_pct"),
            "volume": q.get("volume"),
            "volume_unit": q.get("volume_unit") or "手",
            "amount": q.get("amount"),
            "currency": q.get("currency") or "CNY",
            "amount_str": fmt_amount(q.get("amount"), q.get("currency") or "CNY"),
            "turnover": q.get("turnover"),
            "amplitude": q.get("amplitude"),
            "high": q.get("high"),
            "low": q.get("low"),
            "main_net": fl.get("main_net"),
            "main_net_str": fmt_net(fl.get("main_net")),
            "main_pct": fl.get("main_pct"),
            "super_net": fl.get("super_net"),
            "big_net": fl.get("big_net"),
            "flow_src": fl.get("src"),
        })

    rows.sort(key=lambda r: (r["main_net"] is None, -(r["main_net"] or 0)))

    print(f"\n{'名称':<20}{'代码':<8}{'涨跌%':>8}{'成交额':>11}{'换手%':>8}{'主力净额':>13}{'占比%':>8}{'源':>6}")
    print("-" * 88)
    for r in rows:
        c = r["chg_pct"]
        c = f"{c:+.2f}" if isinstance(c, (int, float)) else "—"
        t = r["turnover"]
        t = f"{t:.2f}" if isinstance(t, (int, float)) else "—"
        p = r["main_pct"]
        p = f"{p:+.2f}" if isinstance(p, (int, float)) else "—"
        print(f"{str(r['name'])[:20]:<20}{r['code']:<8}{c:>8}{r['amount_str']:>11}"
              f"{t:>8}{r['main_net_str']:>13}{p:>8}{str(r['flow_src'] or '—'):>6}")

    out = OUT / "quotes.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已保存 {out}")


if __name__ == "__main__":
    main()
