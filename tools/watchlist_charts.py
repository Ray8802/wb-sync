# -*- coding: utf-8 -*-
"""自选股复盘图表生成

读取 watchlist_data/quotes.json，生成 3 张图表：
  wl_flow.png   —— 主力资金净流入红绿榜（横向柱，涨红跌绿）
  wl_chg.png    —— 当日涨跌幅红绿榜
  wl_amount.png —— 成交额对比
配色遵循中国市场习惯：流入/上涨=红，流出/下跌=绿。
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti TC", "Songti SC",
                                   "Arial Unicode MS", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

BASE = Path(__file__).parent
OUT = BASE / "closing_charts"
DATA = BASE / "watchlist_data" / "quotes.json"

RED, GREEN, GRAY, BLUE = "#d93026", "#0f9d58", "#9aa0a6", "#3370ff"
DATE = "2026-09-01"


def short(name: str, n: int = 12) -> str:
    """截断长名称，便于图表展示"""
    if not name:
        return "—"
    return name if len(name) <= n else name[:n] + "…"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


# ---------- 1. 主力资金净流入红绿榜 ----------
def chart_flow(rows):
    data = [r for r in rows if r.get("main_net") is not None]
    data.sort(key=lambda r: r["main_net"])
    if not data:
        return
    names = [short(r["name"]) for r in data]
    vals = [r["main_net"] / 1e8 for r in data]          # 亿元
    cols = [RED if v > 0 else GREEN for v in vals]

    fig, ax = plt.subplots(figsize=(8.6, max(4.2, len(data) * 0.42)), dpi=110)
    bars = ax.barh(names, vals, color=cols, height=.62)
    ax.axvline(0, color="#5f6368", lw=.9)
    for b, v in zip(bars, vals):
        off = 0.02 if v >= 0 else -0.02
        ax.text(v + off, b.get_y() + b.get_height() / 2,
                f"{v:+.2f} 亿", ha="left" if v >= 0 else "right",
                va="center", fontsize=9.5, fontweight="bold",
                color=RED if v >= 0 else GREEN)
    ax.set_xlim(min(vals) * 1.35 if min(vals) < 0 else -0.5,
                max(vals) * 1.35 if max(vals) > 0 else 0.5)
    ax.set_xlabel("主力资金净流入（亿元）", fontsize=10)
    ax.set_title(f"{DATE}  自选股｜主力资金净流入榜", fontsize=13,
                 fontweight="bold", pad=10)
    ax.grid(axis="x", linestyle="--", alpha=.3)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "wl_flow.png")
    plt.close(fig)


# ---------- 2. 涨跌幅红绿榜 ----------
def chart_chg(rows):
    data = [r for r in rows if r.get("chg_pct") is not None]
    data.sort(key=lambda r: r["chg_pct"])
    if not data:
        return
    names = [short(r["name"]) for r in data]
    vals = [r["chg_pct"] for r in data]
    cols = [RED if v > 0 else (GREEN if v < 0 else GRAY) for v in vals]

    fig, ax = plt.subplots(figsize=(8.6, max(4.2, len(data) * 0.42)), dpi=110)
    bars = ax.barh(names, vals, color=cols, height=.62)
    ax.axvline(0, color="#5f6368", lw=.9)
    for b, v in zip(bars, vals):
        off = 0.06 if v >= 0 else -0.06
        ax.text(v + off, b.get_y() + b.get_height() / 2,
                f"{v:+.2f}%", ha="left" if v >= 0 else "right",
                va="center", fontsize=9.5, fontweight="bold",
                color=RED if v >= 0 else GREEN)
    ax.set_xlim(min(vals) * 1.4 if min(vals) < 0 else -0.5,
                max(vals) * 1.4 if max(vals) > 0 else 0.5)
    ax.set_xlabel("当日涨跌幅（%）", fontsize=10)
    ax.set_title(f"{DATE}  自选股｜当日涨跌幅榜", fontsize=13,
                 fontweight="bold", pad=10)
    ax.grid(axis="x", linestyle="--", alpha=.3)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "wl_chg.png")
    plt.close(fig)


# ---------- 3. 成交额对比 ----------
def chart_amount(rows):
    # 只画人民币计价标的（韩股为韩元，单位不可比，单独标注）
    data = [r for r in rows
            if r.get("amount") and (r.get("currency") or "CNY") != "KRW"]
    data.sort(key=lambda r: r["amount"])
    if not data:
        return
    names = [short(r["name"]) for r in data]
    vals = [r["amount"] / 1e8 for r in data]            # 亿元
    cols = [BLUE] * len(vals)

    fig, ax = plt.subplots(figsize=(8.6, max(4.2, len(data) * 0.42)), dpi=110)
    bars = ax.barh(names, vals, color=cols, height=.62)
    for b, v in zip(bars, vals):
        ax.text(v + max(vals) * 0.012, b.get_y() + b.get_height() / 2,
                f"{v:.2f} 亿", ha="left", va="center",
                fontsize=9.5, fontweight="bold", color="#1a4fa0")
    ax.set_xlim(0, max(vals) * 1.22)
    ax.set_xlabel("成交额（亿元）", fontsize=10)
    ax.set_title(f"{DATE}  自选股｜成交额对比（人民币计价）",
                 fontsize=13, fontweight="bold", pad=10)
    ax.grid(axis="x", linestyle="--", alpha=.3)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    # 韩股备注
    kr = [r for r in rows if (r.get("currency") or "") == "KRW"]
    if kr:
        txt = "；".join(f"{r['name']} {r.get('amount_str')}" for r in kr)
        ax.text(0.0, -0.13, f"* 韩股（韩元计价，未纳入对比）：{txt}",
                transform=ax.transAxes, fontsize=8.5, color="#5f6368")
    fig.tight_layout()
    fig.savefig(OUT / "wl_amount.png")
    plt.close(fig)


def main():
    rows = load()
    OUT.mkdir(exist_ok=True)
    chart_flow(rows)
    chart_chg(rows)
    chart_amount(rows)
    print("自选股复盘图表已生成：")
    for n in ("wl_flow.png", "wl_chg.png", "wl_amount.png"):
        p = OUT / n
        if p.exists():
            print(f"  {n}  ({p.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
