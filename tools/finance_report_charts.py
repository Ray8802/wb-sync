#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
finance_report_charts.py  ·  财报结构化数据图表可视化工具
============================================================
自动读取财报中的结构化数据（Excel / CSV / JSON / Markdown 表格），
按常见财报板块（营收、利润、资产负债、现金流等）识别数据类型，
生成清晰、适配财报展示场景的图表（折线图 / 柱状图 / 饼图），
并输出 PNG 与单文件 HTML 汇总页。

用法
----
  # 用内置示例数据生成演示（营收/利润/资产负债/现金流/营收分部 全覆盖）
  python finance_report_charts.py --demo

  # 读取你自己的财报
  python finance_report_charts.py --input 财报.xlsx --out out/
  python finance_report_charts.py --input 财报.csv  --out out/
  python finance_report_charts.py --input 财报.md   --out out/
  python finance_report_charts.py --input 财报.json --out out/   # 需含 sections 结构

依赖
----
  pip install pandas matplotlib openpyxl
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import re
from pathlib import Path

import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---------- 中文字体（财报场景必须） ----------
CN_FONTS = [
    "PingFang SC", "Arial Unicode MS", "Heiti SC", "SimHei",
    "Microsoft YaHei", "WenQuanYi Micro Hei", "Noto Sans CJK SC",
]
_available = {f.name for f in font_manager.fontManager.ttflist}
_chosen = [f for f in CN_FONTS if f in _available] or ["DejaVu Sans"]
plt.rcParams["font.sans-serif"] = _chosen + ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 140
plt.rcParams["savefig.bbox"] = "tight"
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.25
plt.rcParams["grid.color"] = "#BBBBBB"

# ---------- 财报风格配色 ----------
PALETTE = [
    "#2E5A87", "#4E89C7", "#7FB3D5", "#E1A33B", "#C0392B",
    "#27AE60", "#8E44AD", "#16A085", "#D35400", "#2C3E50",
]

# 板块关键字 -> (默认图表类型, 友好标题)
#  type: line=趋势折线, bar=分类对比柱状, pie=占比饼图
SECTION_PRESETS = {
    "营收": ("line", "营业收入趋势"),
    "利润": ("line", "利润趋势"),
    "盈利": ("line", "盈利趋势"),
    "资产": ("line", "资产规模趋势"),
    "负债": ("line", "负债规模趋势"),
    "现金": ("line", "现金流趋势"),
    "费用": ("bar", "费用对比"),
    "毛利": ("bar", "毛利率对比"),
    "构成": ("pie", "构成占比"),
    "结构": ("pie", "结构占比"),
    "占比": ("pie", "占比分析"),
}


def section_preset(name: str):
    # 构成 / 结构 / 占比 优先识别为饼图
    for k in ("构成", "结构", "占比"):
        if k in name:
            return ("pie", name)
    for k, v in SECTION_PRESETS.items():
        if k in name:
            return v
    return (None, name)


def detect_period_col(df: pd.DataFrame):
    """找一列其取值像年份 / 季度 / 报告期。"""
    for col in df.columns:
        s = df[col].astype(str)
        if s.str.match(r"^(19|20)\d{2}$").any() or \
           s.str.contains(r"Q[1-4]|季度|半年度|年度|报告期", regex=True).any():
            return col
    return None


def to_wide(df: pd.DataFrame):
    """把常见财报布局统一成 期次(index) × 指标(columns) 的宽表。
    返回 (wide_df, has_period)。"""
    # 情形A：列名是年份 -> 转置（行=指标，列=年份）
    year_cols = [c for c in df.columns if re.match(r"^(19|20)\d{2}$", str(c))]
    if len(year_cols) >= 2:
        label_cols = [c for c in df.columns if c not in year_cols]
        label = label_cols[0] if label_cols else df.columns[0]
        w = df[[label] + year_cols].set_index(label)[year_cols].T
        w.index.name, w.columns.name = "期次", "指标"
        return w, True
    # 情形B：某列的值是年份（每行一期）
    pcol = detect_period_col(df)
    if pcol:
        num = [c for c in df.columns
               if pd.api.types.is_numeric_dtype(df[c]) and c != pcol]
        label = [c for c in df.columns
                 if c != pcol and not pd.api.types.is_numeric_dtype(df[c])]
        if label and num:
            w = df.pivot(index=pcol, columns=label[0], values=num[0])
        else:
            w = df.set_index(pcol)[num]
        w.index.name = "期次"
        if hasattr(w, "columns"):
            w.columns.name = "指标"
        return w, True
    # 情形C：无期次（分类快照）
    return df, False


def _fmt(v):
    try:
        f = float(v)
        return f"{f:,.0f}" if abs(f) < 1e8 else f"{f / 1e8:,.2f}亿"
    except Exception:
        return str(v)


def _bar_labels(ax, bars):
    for b in bars:
        h = b.get_height()
        ax.annotate(_fmt(h), (b.get_x() + b.get_width() / 2, h),
                    ha="center", va="bottom", fontsize=8.5, color="#333")


def _save(fig, outdir: Path, title: str):
    safe = re.sub(r"[^\w\u4e00-\u9fff-]", "_", title)[:40]
    png = outdir / f"{safe}.png"
    fig.savefig(png, dpi=140)
    buf = io.BytesIO()
    fig.savefig(buf, dpi=140, format="png")
    plt.close(fig)
    return png, base64.b64encode(buf.getvalue()).decode()


def render_trend(w: pd.DataFrame, title: str, outdir: Path):
    """期次 × 多指标 -> 折线图（财务趋势首选）。"""
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    periods = [str(p) for p in w.index]
    for i, col in enumerate(w.columns):
        yv = w[col].astype(float)
        ax.plot(periods, yv, marker="o", linewidth=2,
                color=PALETTE[i % len(PALETTE)], label=str(col))
        ax.annotate(_fmt(yv.iloc[-1]), (len(periods) - 1, yv.iloc[-1]),
                    textcoords="offset points", xytext=(6, 0), fontsize=8,
                    color=PALETTE[i % len(PALETTE)])
    ax.set_title(title, fontsize=13, fontweight="bold", color="#1A1A1A")
    ax.set_xlabel("报告期", fontsize=10)
    ax.legend(fontsize=9, frameon=False)
    ax.margins(x=0.05, y=0.18)
    fig.tight_layout()
    png, b64 = _save(fig, outdir, title)
    return title, png, b64


def render_bar(df: pd.DataFrame, cat_col, val_col, title: str, outdir: Path):
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    bars = ax.bar(df[cat_col].astype(str), df[val_col].astype(float),
                  color=PALETTE[:len(df)])
    _bar_labels(ax, bars)
    ax.set_title(title, fontsize=13, fontweight="bold", color="#1A1A1A")
    ax.set_ylabel(str(val_col), fontsize=10)
    ax.margins(y=0.15)
    fig.tight_layout()
    png, b64 = _save(fig, outdir, title)
    return title, png, b64


def render_pie(df: pd.DataFrame, cat_col, val_col, title: str, outdir: Path):
    fig, ax = plt.subplots(figsize=(6.6, 5.2))
    vals = df[val_col].astype(float)
    wedges, _, autot = ax.pie(
        vals, labels=df[cat_col].astype(str), autopct=lambda p: f"{p:.1f}%",
        colors=PALETTE, startangle=90, counterclock=False,
        textprops={"fontsize": 9}, pctdistance=0.78)
    for t in autot:
        t.set_color("white")
        t.set_fontsize(8.5)
    ax.set_title(title, fontsize=13, fontweight="bold", color="#1A1A1A")
    ax.axis("equal")
    fig.tight_layout()
    png, b64 = _save(fig, outdir, title)
    return title, png, b64


def render_section(name: str, df: pd.DataFrame, outdir: Path):
    """返回 [(title, png_path, b64), ...]"""
    out = []
    preset, friendly = section_preset(name)
    w, has_period = to_wide(df)

    if has_period:
        if preset == "bar" or (len(w.columns) == 1 and preset in (None, "bar")):
            fig, ax = plt.subplots(figsize=(8.2, 4.6))
            periods = [str(p) for p in w.index]
            x = list(range(len(periods)))
            width = 0.8 / max(len(w.columns), 1)
            for j, col in enumerate(w.columns):
                ax.bar([i + width * j for i in x], w[col].astype(float),
                       width, label=str(col), color=PALETTE[j % len(PALETTE)])
            ax.set_xticks(x)
            ax.set_xticklabels(periods)
            ax.set_title(friendly, fontsize=13, fontweight="bold")
            ax.legend(fontsize=9, frameon=False)
            ax.margins(y=0.15)
            fig.tight_layout()
            png, b64 = _save(fig, outdir, friendly)
            out.append((friendly, png, b64))
        else:
            out.append(render_trend(w, friendly, outdir))
        return out

    # 无期次：分类快照
    cat_col = df.columns[0]
    num_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if not num_cols:
        return out
    if preset == "pie" or (any(k in name for k in ("构成", "结构", "占比", "资产", "负债"))
                            and len(df) <= 10):
        out.append(render_pie(df, cat_col, num_cols[0], friendly, outdir))
    else:
        out.append(render_bar(df, cat_col, num_cols[0], friendly, outdir))
    return out


def md_tables_to_df(path: str) -> pd.DataFrame:
    text = Path(path).read_text(encoding="utf-8")
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("|") and "---" not in line:
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows.append(cells)
    if len(rows) < 2:
        return pd.DataFrame()
    header, body = rows[0], rows[1:]
    maxc = max(len(r) for r in body + [header])
    header += [""] * (maxc - len(header))
    body = [r + [""] * (maxc - len(r)) for r in body]
    return pd.DataFrame(body, columns=header)


def load_input(path: str):
    """返回 (meta, sections)；sections = list of (name, df)。"""
    p = Path(path)
    ext = p.suffix.lower()
    if ext in (".xlsx", ".xls"):
        sheets = pd.read_excel(path, sheet_name=None)
        return {}, [(str(k), v) for k, v in sheets.items()]
    if ext == ".csv":
        return {}, [("财务数据", pd.read_csv(path))]
    if ext == ".json":
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "sections" in data:
            meta = {k: v for k, v in data.items() if k != "sections"}
            secs = []
            for s in data["sections"]:
                rows = s.get("rows")
                if rows is not None:
                    df = pd.DataFrame(rows)
                else:
                    df = pd.DataFrame({r["name"]: r["values"]
                                       for r in s.get("series", [])})
                secs.append((s.get("name", "板块"), df))
            return meta, secs
        return {}, [("财务数据", pd.DataFrame(data))]
    if ext in (".md", ".markdown"):
        return {}, [("财务数据", md_tables_to_df(path))]
    raise ValueError(f"不支持的格式: {ext}")


def build_html(company, items):
    head = f"<h1>{company}</h1>" if company else "<h1>财报图表</h1>"
    parts = [head]
    for title, _, b64 in items:
        parts.append(
            f'<section style="margin:18px 0">'
            f'<h2 style="font-family:sans-serif;color:#1A1A1A">{title}</h2>'
            f'<img src="data:image/png;base64,{b64}" '
            f'style="max-width:100%;border:1px solid #eee;border-radius:8px"></section>')
    return ("<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
            "<style>body{max-width:920px;margin:auto;padding:24px;color:#222;"
            "font-family:'PingFang SC',sans-serif;background:#fff}</style>"
            "</head><body>" + "".join(parts) + "</body></html>")


def generate_demo(outdir: Path):
    years = [2021, 2022, 2023, 2024, 2025]
    ycols = [str(y) for y in years]
    profit = pd.DataFrame([
        ["营业收入", 120, 145, 168, 190, 221],
        ["营业成本", 80, 95, 110, 125, 142],
        ["净利润", 12, 16, 19, 23, 28],
        ["扣非净利润", 10, 14, 17, 21, 26],
    ], columns=["指标"] + ycols)
    balance_trend = pd.DataFrame([
        ["总资产", 300, 340, 380, 420, 470],
        ["总负债", 150, 168, 185, 200, 218],
        ["净资产", 150, 172, 195, 220, 252],
    ], columns=["指标"] + ycols)
    asset_struct = pd.DataFrame({
        "资产项目": ["货币资金", "应收账款", "存货", "固定资产", "无形资产"],
        "2025": [120, 60, 80, 150, 60]})
    cash = pd.DataFrame([
        ["经营活动现金流", 20, 24, 28, 32, 36],
        ["投资活动现金流", -15, -18, -22, -20, -25],
        ["筹资活动现金流", -5, -3, -4, -8, -6],
    ], columns=["指标"] + ycols)
    rev_split = pd.DataFrame([
        ["国内营收", 90, 105, 120, 135, 155],
        ["海外营收", 30, 40, 48, 55, 66],
    ], columns=["指标"] + ycols)
    with pd.ExcelWriter(outdir / "示例财报.xlsx") as xw:
        profit.to_excel(xw, sheet_name="利润表", index=False)
        balance_trend.to_excel(xw, sheet_name="资产负债趋势", index=False)
        asset_struct.to_excel(xw, sheet_name="资产构成", index=False)
        cash.to_excel(xw, sheet_name="现金流量表", index=False)
        rev_split.to_excel(xw, sheet_name="营收分部", index=False)
    return outdir / "示例财报.xlsx"


def main():
    ap = argparse.ArgumentParser(description="财报结构化数据图表可视化工具")
    ap.add_argument("--input", help="财报文件 xlsx/csv/json/md")
    ap.add_argument("--out", default="finance_charts_output", help="输出目录")
    ap.add_argument("--demo", action="store_true", help="生成示例数据并出图")
    ap.add_argument("--html", default="report.html", help="HTML 汇总文件名")
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.demo:
        demo = generate_demo(outdir)
        args.input = str(demo)
        print(f"[demo] 示例财报已生成: {demo}")

    if not args.input:
        ap.error("请指定 --input 财报文件，或加 --demo 生成示例")

    meta, sections = load_input(args.input)
    company = meta.get("company", Path(args.input).stem)
    items = []
    for name, df in sections:
        if df is None or df.empty:
            continue
        for title, png, b64 in render_section(name, df, outdir):
            items.append((title, png, b64))
            print(f"[ok] {title} -> {png}")

    html = build_html(company, items)
    (outdir / args.html).write_text(html, encoding="utf-8")
    print(f"[done] HTML 汇总: {outdir / args.html}  (共 {len(items)} 张图)")


if __name__ == "__main__":
    main()
