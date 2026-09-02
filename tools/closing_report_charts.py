# -*- coding: utf-8 -*-
"""A股收盘财报图表生成器（2026-09-01 真实收盘数据）

生成 6 张图表，配色遵循中国市场习惯：涨红跌绿。
输出目录：closing_charts/
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti TC", "Songti SC",
                                   "Arial Unicode MS", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

OUT = Path(__file__).parent / "closing_charts"
OUT.mkdir(exist_ok=True)

RED, GREEN, GRAY, BLUE = "#d93026", "#0f9d58", "#9aa0a6", "#3370ff"
DATE = "2026-09-01"


def style(ax, title, ylabel="", grid_axis="y"):
    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=10)
    ax.grid(axis=grid_axis, linestyle="--", alpha=.35)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# ---------- 1. 主要指数涨跌幅 ----------
fig, ax = plt.subplots(figsize=(7.6, 4.0), dpi=110)
names = ["上证指数", "深证成指", "创业板指", "科创50", "北证50"]
vals = [-0.16, -1.02, -1.32, -2.19, 1.34]
cols = [RED if v > 0 else GREEN for v in vals]
bars = ax.bar(names, vals, color=cols, width=.55)
ax.axhline(0, color="#5f6368", lw=.9)
for r, v in zip(bars, vals):
    off = 0.07 if v >= 0 else -0.16
    ax.text(r.get_x() + r.get_width() / 2, v + off, f"{v:+.2f}%",
            ha="center", va="bottom" if v >= 0 else "top",
            fontsize=10, fontweight="bold", color=r.get_facecolor())
ax.set_ylim(min(vals) - .8, max(vals) + .8)
style(ax, f"{DATE}  主要指数收盘涨跌幅", "涨跌幅 (%)")
fig.tight_layout()
fig.savefig(OUT / "idx_chg.png")
plt.close(fig)

# ---------- 2. 市场情绪：涨跌家数 + 涨停跌停 ----------
fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.0), dpi=110)

ax = axes[0]
sizes = [3386, 2040, 119]
labels = [f"上涨 {sizes[0]}", f"下跌 {sizes[1]}", f"平盘 {sizes[2]}"]
wedges, texts, autotexts = ax.pie(
    sizes, labels=labels, autopct=lambda p: f"{p:.1f}%",
    colors=[RED, GREEN, GRAY], startangle=90,
    wedgeprops=dict(width=.55, edgecolor="white", linewidth=1.5),
    textprops=dict(fontsize=10))
for t in autotexts:
    t.set_color("white")
    t.set_fontweight("bold")
ax.set_title(f"{DATE}  涨跌家数分布", fontsize=13, fontweight="bold", pad=8)

ax = axes[1]
lb = ["涨停", "跌停"]
lv = [86, 0]
b = ax.bar(lb, lv, color=[RED, GREEN], width=.45)
for r, v in zip(b, lv):
    ax.text(r.get_x() + r.get_width() / 2, v + 1.5, str(v),
            ha="center", va="bottom", fontsize=12, fontweight="bold",
            color=r.get_facecolor())
ax.set_ylim(0, max(lv) * 1.35 + 8)
style(ax, "涨停 / 跌停 家数", "家数")
fig.tight_layout()
fig.savefig(OUT / "breadth.png")
plt.close(fig)

# ---------- 3. 资金流向 + 成交额 ----------
fig, axes = plt.subplots(1, 2, figsize=(9.6, 3.9), dpi=110)

ax = axes[0]
fn = ["电子行业\n主力净额", "两市主力\n净额"]
fv = [-221.68, -237.77]
b = ax.barh(fn, fv, color=GREEN, height=.5)
for r, v in zip(b, fv):
    ax.text(v - 12, r.get_y() + r.get_height() / 2, f"{v:.2f} 亿",
            ha="right", va="center", fontsize=10, fontweight="bold", color=GREEN)
ax.axvline(0, color="#5f6368", lw=.9)
ax.set_xlim(min(fv) * 1.35, 0)
ax.set_xlabel("亿元（负值为净流出）", fontsize=9)
style(ax, "主力资金流向", grid_axis="x")

ax = axes[1]
dn = ["前一交易日", "今日"]
dv = [21310, 20334]
b = ax.bar(dn, dv, color=[GRAY, BLUE], width=.45)
for r, v in zip(b, dv):
    ax.text(r.get_x() + r.get_width() / 2, v + 260, f"{v:,}",
            ha="center", va="bottom", fontsize=11, fontweight="bold")
ax.set_ylim(0, max(dv) * 1.22)
style(ax, "两市成交额对比（亿元）", "亿元")
ax.text(0.5, -0.22, "今日较前一交易日缩量约 976 亿元",
        transform=ax.transAxes, ha="center", fontsize=9, color="#5f6368")
fig.tight_layout()
fig.savefig(OUT / "fund_flow.png")
plt.close(fig)

# ---------- 4. 板块涨跌幅红绿榜 ----------
fig, ax = plt.subplots(figsize=(7.6, 3.8), dpi=110)
sn = ["商贸零售", "农林牧渔", "银行", "煤炭", "电子"]
sv = [3.08, 2.48, 1.88, -2.13, -2.99]
sc = [RED if v > 0 else GREEN for v in sv]
b = ax.barh(sn, sv, color=sc, height=.55)
ax.axvline(0, color="#5f6368", lw=.9)
for r, v in zip(b, sv):
    off = 0.09 if v > 0 else -0.09
    ax.text(v + off, r.get_y() + r.get_height() / 2, f"{v:+.2f}%",
            ha="left" if v > 0 else "right", va="center",
            fontsize=10, fontweight="bold", color=r.get_facecolor())
ax.set_xlim(min(sv) * 1.35, max(sv) * 1.35)
ax.set_xlabel("当日涨跌幅 (%)", fontsize=10)
style(ax, f"{DATE}  板块涨跌幅榜（涨幅前3 / 跌幅前2）", grid_axis="x")
ax.invert_yaxis()
fig.tight_layout()
fig.savefig(OUT / "sector.png")
plt.close(fig)

# ---------- 5. 期指净空对比 ----------
fig, ax = plt.subplots(figsize=(7.6, 3.8), dpi=110)
qn = ["IF2609\n沪深300", "IH2609\n上证50", "IC2609\n中证500", "IM2609\n中证1000"]
qv = [10775, 9615, 5964, 17731]
b = ax.bar(qn, qv, color="#6b7fd7", width=.5)
for r, v in zip(b, qv):
    ax.text(r.get_x() + r.get_width() / 2, v + 380, f"{v:,}",
            ha="center", va="bottom", fontsize=10, fontweight="bold", color="#3b4a8f")
ax.set_ylim(0, max(qv) * 1.22)
style(ax, f"{DATE}  中信期指净空持仓对比", "净空（手）")
ax.text(0.5, -0.20, "四大合约均为「空方占优」，IM（中证1000）净空压力最大",
        transform=ax.transAxes, ha="center", fontsize=9, color="#5f6368")
fig.tight_layout()
fig.savefig(OUT / "futures_net.png")
plt.close(fig)

# ---------- 6. 期指多空持仓对比 ----------
fig, ax = plt.subplots(figsize=(8.4, 4.0), dpi=110)
gn = ["IF2609\n沪深300", "IC2609\n中证500", "IH2609\n上证50", "IM2609\n中证1000"]
longs = [102928, 110472, 48567, 159373]
shorts = [113703, 116436, 58182, 177104]
x = np.arange(len(gn))
w = .34
b1 = ax.bar(x - w / 2, longs, w, label="前20多单", color=RED)
b2 = ax.bar(x + w / 2, shorts, w, label="前20空单", color=GREEN)
for bars in (b1, b2):
    for r in bars:
        ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 2600,
                f"{int(r.get_height()):,}", ha="center", va="bottom",
                fontsize=9, fontweight="bold")
ax.set_xticks(x)
ax.set_xticklabels(gn)
ax.set_ylim(0, max(shorts) * 1.2)
ax.legend(fontsize=10, frameon=False, ncol=2, loc="upper left")
style(ax, f"{DATE}  中信期指前20多空持仓对比", "持仓（手）")
fig.tight_layout()
fig.savefig(OUT / "futures_pos.png")
plt.close(fig)

print("图表已生成：")
for p in sorted(OUT.glob("*.png")):
    print(f"  {p.name}  ({p.stat().st_size/1024:.1f} KB)")
