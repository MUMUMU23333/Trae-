# -*- coding: utf-8 -*-
"""render.py — 成品生成：md（归档）+ HTML v2（专业卡片可视化）+ 企微简版结论。
纯 stdlib，GitHub Actions ubuntu 可跑。HTML 深色金融 Dashboard 风，普通人一眼看懂。
"""
import datetime
import html as htmlmod
import json

from libs import insight

HEADER = """# 多平台大V财经观点统计（{date}）

> 数据截止：{ts} | 抓取通道：GitHub Actions 全云自动 | 来源口径：盘面/同花顺/券商/雪球
> 非投资建议，据此操作风险自负。

"""

# ---------- 工具 ----------

def _fmt_amount(amt):
    """成交额(万元)→ 亿元 展示。空/非数返回 '—'。"""
    try:
        v = float(amt or 0)
    except (TypeError, ValueError):
        return "—"
    if v <= 0:
        return "—"
    return "%.0f亿" % (v / 10000.0)


def _pct_arrow(pct):
    try:
        p = float(pct or 0)
    except (TypeError, ValueError):
        return "—", ""
    if p > 0:
        return "▲", "up"
    if p < 0:
        return "▼", "down"
    return "—", "flat"


def _zh_views(data):
    """聚合知乎+雪球有观点账户 → insight views。"""
    accounts = []
    for key in ("zhihu", "xueqiu"):
        src = data.get(key, {})
        if isinstance(src, dict):
            accounts.extend(src.get("accounts", []))
    return insight.build_views(accounts)


# ---------- 企微简版结论（≤300字） ----------

def render_summary(data, limit=800):
    """简版结论（企微文字快览）：当日共识 + 大V加权top + 盘面 + 要闻 + 研报。"""
    out = []
    views = _zh_views(data)
    ov = insight.build_overview(views)
    if ov["conclusion"]:
        # 提取或补全共识说明与拥挤度
        conclusion_text = ov["conclusion"].replace("**", "")
        # 计算多空权重分
        bull_w = sum(v.get("weight", 1) for v in views if v.get("direction") == "bull")
        bear_w = sum(v.get("weight", 1) for v in views if v.get("direction") == "bear")
        warning = " ⚠️注意拥挤，过热方向勿追高。" if bull_w >= 6.0 else (" 💡极度悲观区域，防恐慌杀跌后的逆向黄金底。" if bear_w >= 6.0 else "")
        out.append("【共识】" + conclusion_text + warning)

    # 大V加权 top（方向 + 核心论据）
    if views:
        top = sorted(views, key=lambda v: -(v.get("weight") or 1))[:4]
        t_items = []
        for v in top:
            name = v["name"].split("（")[0][:8]
            point = v.get("point", "").strip()[:35]
            dir_str = "看多" if v.get("direction") == "bull" else ("看空" if v.get("direction") == "bear" else "中性")
            t_items.append("(%s)%s %s" % (name, point, dir_str))
        out.append("【大V】" + "；".join(t_items))
    elif data.get("ths_bigv", {}).get("accounts"):
        # 降级：从同花顺大V中提取有效观点
        tb_items = []
        for a in data["ths_bigv"]["accounts"]:
            if a.get("items"):
                first = a["items"][0]
                tb_items.append("(%s)%s" % (a["name"][:8], first.get("title", "")[:35]))
        if tb_items:
            out.append("【大V】" + "；".join(tb_items[:4]))

    # 盘面行情
    tenc = data.get("tencent", [])
    if tenc:
        pieces = []
        for it in tenc[:4]:
            pct = it.get("chg_pct") or "0.00"
            arrow, _ = _pct_arrow(pct)
            name = it["name"].replace("指数", "").replace("深证成指", "深成").replace("沪深300", "沪深300")
            pieces.append("%s%s%s%%" % (name[:5], arrow, pct))
        out.append("【盘面】" + " | ".join(pieces))

    # 要闻
    ths = data.get("ths", [])
    if ths:
        out.append("【要闻】" + "；".join((x.get("title") or "")[:35] for x in ths[:2]))

    # 研报
    brs = [b for b in data.get("brokers", []) if b.get("reports")]
    if brs:
        tot = sum(len(b["reports"]) for b in brs)
        out.append("【研报】%d家共%d篇；代表：%s" % (len(brs), tot, brs[0]["reports"][0]["title"][:40]))

    text = "\n".join(out)
    if len(text) > limit:
        text = text[:limit].rsplit("\n", 1)[0]
    return text + "\n\n（详细版 HTML 见下一条文件消息）"


# ---------- Markdown（归档 artifact） ----------

def render_md(data):
    date, ts = data["date"], data["ts"]
    lines = [HEADER.format(date=date, ts=ts)]

    views = _zh_views(data)
    ov = insight.build_overview(views)
    if ov["conclusion"]:
        lines.append("## 📊 当日共识\n")
        lines.append(ov["conclusion"])
        for r in ov["rows"][:6]:
            lines.append("- **{sector}**：{bull_n}多/{bear_n}空（ΣW 多{bull_w}/空{bear_w}），{side}占优 · {names}".format(
                sector=r["sector"], bull_n=r["bull_n"], bear_n=r["bear_n"],
                bull_w=r["bull_w"], bear_w=r["bear_w"], side=r["side"],
                names="、".join(r["names"][:5]) or "—"))
        lines.append("")

    lines.append("## 盘面锚定（腾讯行情）\n")
    for it in data["tencent"]:
        pct = it["chg_pct"] or "0.00"
        arrow, _ = _pct_arrow(pct)
        amt = _fmt_amount(it.get("amount"))
        lines.append("- {name} {price} {arrow}{chg_pct}% ({amt})".format(
            name=it["name"], price=it["price"], arrow=arrow,
            chg_pct=it["chg_pct"], amt=amt))

    warns = data.get("warnings", [])
    if warns:
        lines.append("\n## ⚠️ 特殊提醒\n")
        for w in warns:
            lines.append("- {0}".format(w))

    lines.append("\n## 同花顺新闻热度（{0}）\n".format(date))
    ths = data.get("ths", [])
    if not ths:
        lines.append("> 当日无同花顺新闻（或接口暂未更新）")
    for x in ths[:12]:
        digest = (x.get("digest") or "").strip()
        if digest:
            lines.append("- {time} **{title}**：{digest}".format(
                time=(x.get("time") or "")[:16], title=x.get("title") or "", digest=digest[:120]))
        else:
            lines.append("- {time} {title}".format(
                time=(x.get("time") or "")[:16], title=x.get("title") or ""))
    # 同花顺 4 位大V（张明辉 userPost 在线直抓；其余在股吧 SPA 需 CDP 补录）
    ths_bv = data.get("ths_bigv", {})
    if isinstance(ths_bv, dict) and ths_bv.get("accounts"):
        lines.append("\n## 同花顺大V观点\n")
        act = [a for a in ths_bv["accounts"] if a["items"]]
        if act:
            for a in sorted(act, key=lambda x: -x["weight"]):
                first = a["items"][0]
                lines.append("- **{name}（w{weight}）**：{time} {title}".format(
                    name=a["name"], weight=a["weight"],
                    time=first["time"], title=first["title"][:60]))
                for it in a["items"][1:3]:
                    lines.append("    · {time} {title}".format(
                        time=it["time"], title=it["title"][:60]))
        else:
            for a in ths_bv["accounts"]:
                lines.append("- **{name}**：{status} {msg}".format(
                    name=a["name"], status=a["status"], msg=a.get("msg", "")))
        if ths_bv.get("note"):
            lines.append("\n> {0}".format(ths_bv["note"].strip()))

    lines.append("\n## 券商 6 家当日研报（东财）\n")
    for b in data.get("brokers", []):
        if not b["reports"]:
            lines.append("- **{0}**：当日无研报".format(b["name"]))
            continue
        lines.append("- **{0}**：".format(b["name"]))
        for r in b["reports"][:6]:
            meta = []
            if r.get("rating"):
                meta.append(r["rating"])
            if r.get("author"):
                meta.append("研报作者: {0}".format(r["author"]))
            if r.get("pages"):
                meta.append("{0}页".format(r["pages"]))
            suffix = "（" + "，".join(meta) + "）" if meta else ""
            lines.append("  - {time} {title}{suffix}".format(
                time=r["time"][:10], title=r["title"][:70], suffix=suffix))

    for sec_name, sec_key in (("雪球 10 源观点", "xueqiu"), ("知乎 21 源观点（加权）", "zhihu")):
        lines.append("\n## {0}\n".format(sec_name))
        src = data.get(sec_key, {})
        if isinstance(src, dict) and src.get("accounts"):
            if act:
                for a in sorted(act, key=lambda x: -x["weight"]):
                    lines.append("- **{name}（w{weight}）**：{first}".format(
                        name=a["name"], weight=a["weight"], first=a["items"][0]["text"][:90]))
                    for it in a["items"][1:3]:
                        lines.append("    · {0}".format(it["text"][:70]))
            else:
                for a in src["accounts"]:
                    lines.append("- **{name}**：{status} {msg}".format(
                        name=a["name"], status=a["status"], msg=a.get("msg", "")))
        if isinstance(src, dict) and src.get("note"):
            lines.append("\n> {0}".format(src["note"]))

    lines.append("\n---\n> Actions 自动生成，记录归档见 Artifact。")
    return "\n".join(lines)


# =====================================================================
# HTML v3（全球态势日报同款 4K Bento 响应式全景大屏）
# =====================================================================

CSS = """
:root {
  --bg-primary: #050811;
  --bg-card: rgba(13, 20, 38, 0.82);
  --bg-card-hover: rgba(22, 34, 60, 0.95);
  --bg-inner: rgba(9, 14, 28, 0.85);
  --border-color: rgba(56, 80, 130, 0.38);
  --border-highlight: rgba(96, 165, 250, 0.7);
  --text-primary: #f8fafc;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --accent-gold: #f59e0b;
  --accent-green: #10b981;
  --accent-red: #ef4444;
  --accent-blue: #38bdf8;
  --accent-purple: #a855f7;
}
* { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif; }
body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
  min-height: 100vh;
  padding: 24px 16px;
  line-height: 1.65;
  background-image: 
    radial-gradient(circle at 10% 15%, rgba(30, 58, 138, 0.42) 0%, transparent 45%),
    radial-gradient(circle at 90% 85%, rgba(88, 28, 135, 0.38) 0%, transparent 45%);
}
.container { max-width: 1400px; margin: 0 auto; }

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 24px 30px;
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  margin-bottom: 22px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.55);
}
.header-title h1 {
  font-size: 24px;
  font-weight: 800;
  background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 45%, #94a3b8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  display: flex;
  align-items: center;
  gap: 10px;
}
.header-title p { font-size: 13px; color: var(--text-secondary); margin-top: 5px; }
.header-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 16px;
  background: rgba(16, 185, 129, 0.18);
  border: 1px solid rgba(16, 185, 129, 0.5);
  border-radius: 30px;
  color: #34d399;
  font-size: 13px;
  font-weight: 700;
}
.pulse-dot {
  width: 8px; height: 8px;
  background-color: var(--accent-green);
  border-radius: 50%;
  box-shadow: 0 0 12px var(--accent-green);
  animation: pulse 2s infinite;
}
@keyframes pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.3; transform: scale(1.4); }
  100% { opacity: 1; transform: scale(1); }
}

.bento-grid {
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 20px;
  margin-bottom: 22px;
}
.card {
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  padding: 24px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
}
.card:hover {
  border-color: var(--border-highlight);
  box-shadow: 0 16px 45px rgba(0, 0, 0, 0.55);
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 12px;
}
.card-title {
  font-size: 17px;
  font-weight: 750;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 8px;
}

.col-12 { grid-column: span 12; }
.col-8 { grid-column: span 8; }
.col-4 { grid-column: span 4; }
@media (max-width: 1080px) {
  .col-8, .col-4 { grid-column: span 12; }
}

/* 核心共识雷达 */
.consensus-box {
  background: linear-gradient(135deg, rgba(56, 189, 248, 0.12), rgba(168, 85, 247, 0.08));
  border-left: 4px solid var(--accent-blue);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 18px;
  font-size: 14.5px;
  line-height: 1.6;
}
.consensus-box b { color: #fff; }
.con-stat-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 6px;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.06);
}
.con-stat-row:last-child { border-bottom: none; }
.con-sec-name { width: 110px; font-weight: 700; color: #fff; font-size: 14px; flex-shrink: 0; }
.con-bar-track {
  flex: 1; height: 16px; border-radius: 8px; overflow: hidden;
  background: rgba(255, 255, 255, 0.06); display: flex;
}
.bar-bull { background: linear-gradient(90deg, #059669, #10b981); }
.bar-bear { background: linear-gradient(90deg, #dc2626, #ef4444); }
.con-summary-text { font-size: 12.5px; color: var(--text-secondary); width: 260px; text-align: right; flex-shrink: 0; }

/* 盘面行情 KPI */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.kpi-card {
  background: var(--bg-inner);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 16px 18px;
  transition: transform 0.2s, border-color 0.2s;
}
.kpi-card:hover { transform: translateY(-2px); border-color: rgba(56, 189, 248, 0.4); }
.kpi-name { font-size: 12.5px; color: var(--text-secondary); font-weight: 600; }
.kpi-price { font-size: 22px; font-weight: 800; margin: 4px 0 2px; }
.kpi-chg { font-size: 13.5px; font-weight: 700; }
.kpi-amt { font-size: 11.5px; color: var(--text-muted); margin-top: 4px; }
.up { color: var(--accent-green); }
.down { color: var(--accent-red); }

/* 筛选与全局控制条 */
.control-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 20px;
}
.filter-tabs { display: flex; gap: 8px; flex-wrap: wrap; }
.btn-filter {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: var(--text-secondary);
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
}
.btn-filter:hover, .btn-filter.active {
  background: rgba(56, 189, 248, 0.2);
  border-color: var(--accent-blue);
  color: var(--accent-blue);
}
.mode-toggle-group { display: flex; gap: 8px; align-items: center; }
.btn-mode {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.35);
  color: #fbbf24;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-mode:hover { background: rgba(245, 158, 11, 0.25); }

/* 大V观点全景穿透网格 */
.v-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 18px;
}
.v-card {
  background: var(--bg-inner);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 18px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: all 0.25s ease;
}
.v-card:hover {
  border-color: rgba(56, 189, 248, 0.4);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}
.v-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}
.v-author { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 36px; height: 36px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 14px; color: #fff;
  flex-shrink: 0;
}
.v-author-info { display: flex; flex-direction: column; }
.v-name { font-size: 15px; font-weight: 750; color: #fff; }
.v-badges { display: flex; gap: 6px; margin-top: 3px; }
.badge-w {
  font-size: 11px; font-weight: 700; padding: 2px 7px; border-radius: 6px; border: 1px solid;
}
.w3 { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border-color: rgba(245, 158, 11, 0.4); }
.w2 { background: rgba(56, 189, 248, 0.15); color: #38bdf8; border-color: rgba(56, 189, 248, 0.4); }
.w1 { background: rgba(255, 255, 255, 0.06); color: var(--text-secondary); border-color: rgba(255, 255, 255, 0.12); }
.badge-sector { background: rgba(168, 85, 247, 0.12); color: #c084fc; border-color: rgba(168, 85, 247, 0.3); }

.badge-dir {
  font-size: 12px; font-weight: 750; padding: 3px 10px; border-radius: 12px; border: 1px solid;
}
.dir-bull { background: rgba(16, 185, 129, 0.14); color: #34d399; border-color: rgba(16, 185, 129, 0.4); }
.dir-bear { background: rgba(239, 68, 68, 0.14); color: #f87171; border-color: rgba(239, 68, 68, 0.4); }
.dir-neutral { background: rgba(148, 163, 184, 0.12); color: #94a3b8; border-color: rgba(148, 163, 184, 0.3); }

/* 核心观点一句话速览 */
.v-headline {
  font-size: 14px;
  font-weight: 650;
  color: #f1f5f9;
  background: rgba(255, 255, 255, 0.03);
  padding: 10px 14px;
  border-radius: 10px;
  border-left: 3px solid var(--accent-blue);
  line-height: 1.55;
  margin-bottom: 10px;
}

/* 全球态势日报同款：双模切换条 */
.intel-switch-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 0 8px 0;
  padding-bottom: 6px;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.08);
}
.intel-tab-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #94a3b8;
  font-size: 11.5px;
  padding: 4px 12px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.intel-tab-btn:hover { background: rgba(255, 255, 255, 0.1); color: #f8fafc; }
.intel-tab-btn.active {
  background: rgba(56, 189, 248, 0.22);
  border-color: rgba(56, 189, 248, 0.65);
  color: #38bdf8;
  font-weight: 700;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.25);
}

/* 详情态势全文区（可切换显示当天全部观点） */
.v-all-items {
  display: block; /* 由 JS 控制隐藏或呈现 */
  margin-top: 8px;
}
.v-single-item {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 8px;
  line-height: 1.65;
  font-size: 13px;
  color: #cbd5e1;
  word-break: break-word;
}
.v-single-item:last-child { margin-bottom: 0; }
.v-item-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11.5px;
  color: var(--text-muted);
  margin-bottom: 6px;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.06);
  padding-bottom: 4px;
}

.v-time-footer {
  font-size: 11.5px;
  color: var(--text-muted);
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 券商与要闻 */
.reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}
.broker-box {
  background: var(--bg-inner);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px;
  padding: 16px 18px;
}
.broker-title {
  font-weight: 750;
  font-size: 14.5px;
  color: #fff;
  margin-bottom: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.rpt-item {
  list-style: none;
  padding: 8px 0 8px 12px;
  border-left: 2px solid rgba(56, 189, 248, 0.4);
  margin-bottom: 6px;
  font-size: 13px;
}
.rpt-item b { color: #f8fafc; font-size: 13.5px; display: block; margin-bottom: 2px; }
.rpt-meta { font-size: 11.5px; color: var(--text-muted); display: flex; gap: 8px; }

.news-row {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.06);
  font-size: 13.5px;
}
.news-row:last-child { border-bottom: none; }
.news-time { font-size: 12px; color: var(--text-muted); white-space: nowrap; flex-shrink: 0; padding-top: 2px; }
.news-body b { color: #fff; }

.footer {
  text-align: center;
  padding: 30px;
  color: var(--text-muted);
  font-size: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  margin-top: 24px;
}
@media (max-width: 640px) {
  .v-grid { grid-template-columns: 1fr; }
  .con-summary-text { width: 140px; font-size: 11px; }
  .con-sec-name { width: 80px; font-size: 12.5px; }
}
"""


def render_html(data):
    """生成完全对标【全球态势日报】规格的 4K 响应式全景大屏，支持大V当天全部观点列表与长文展开双模切换。"""
    date, ts = data.get("date", ""), data.get("ts", "")
    views = _zh_views(data)
    ov = insight.build_overview(views)

    # 调色池
    palette = ["#38bdf8", "#10b981", "#f59e0b", "#a855f7", "#ec4899", "#06b6d4", "#f97316", "#84cc16"]
    def avatar_color(name):
        return palette[sum(ord(c) for c in name) % len(palette)]

    # 1. 盘面行情
    kpis = []
    for it in data.get("tencent", [])[:4]:
        pct = it.get("chg_pct") or "0.00"
        arrow, cls = _pct_arrow(pct)
        amt = _fmt_amount(it.get("amount"))
        kpis.append(
            "<div class='kpi-card'>"
            "<div class='kpi-name'>{name}</div>"
            "<div class='kpi-price'>{price}</div>"
            "<div class='kpi-chg {cls}'>{arrow} {pct}%</div>"
            "<div class='kpi-amt'>成交额 {amt}</div>"
            "</div>".format(
                name=htmlmod.escape(it["name"]),
                price=htmlmod.escape(it.get("price") or "—"),
                cls=cls, arrow=arrow, pct=htmlmod.escape(pct),
                amt=amt or "—"
            )
        )

    # 2. 板块共识天平
    cons_html = ""
    for r in ov["rows"][:8]:
        total_w = r["bull_w"] + r["bear_w"]
        bull_ratio = int(r["bull_w"] * 100 / total_w) if total_w else 50
        bear_ratio = 100 - bull_ratio
        bar = (
            "<div class='bar-bull' style='width:{b_ratio}%' title='多方权重分 {bw}'></div>"
            "<div class='bar-bear' style='width:{s_ratio}%' title='空方权重分 {sw}'></div>"
        ).format(b_ratio=bull_ratio, s_ratio=bear_ratio, bw=r["bull_w"], sw=r["bear_w"])
        
        names_str = "、".join(r["names"][:4]) or "—"
        cons_html += (
            "<div class='con-stat-row'>"
            "<div class='con-sec-name'>{sector}</div>"
            "<div class='con-bar-track'>{bar}</div>"
            "<div class='con-summary-text'>"
            "<span style='color:{dir_col};font-weight:700;'>{side}</span> (多{bull}/空{bear}) · {names}"
            "</div>"
            "</div>"
        ).format(
            sector=htmlmod.escape(r["sector"]),
            bar=bar,
            dir_col="var(--accent-green)" if r["side"] == "看多" else "var(--accent-red)",
            side=r["side"],
            bull=r["bull_n"],
            bear=r["bear_n"],
            names=htmlmod.escape(names_str)
        )
    if not cons_html:
        cons_html = "<div class='con-stat-row'><div class='con-sec-name'>—</div><div class='con-bar-track'></div><div class='con-summary-text'>今日无显著多空分歧</div></div>"

    # 3. 大V观点卡片（支持当天全部观点时间轴与长文双模切换）
    cards = []
    card_idx = 0
    for v in sorted(views, key=lambda x: -(x.get("weight") or 1)):
        card_idx += 1
        d = v.get("direction", "neutral")
        if d == "bull":
            dir_cls = "dir-bull"
            dir_txt = "▲ 看多"
        elif d == "bear":
            dir_cls = "dir-bear"
            dir_txt = "▼ 看空"
        else:
            dir_cls = "dir-neutral"
            dir_txt = "⚪ 中性"

        w = v.get("weight") or 1
        w_cls = "w3" if w >= 3 else ("w2" if w == 2 else "w1")
        w_txt = "w%d 顶级" % w if w >= 3 else ("w%d 核心" % w if w == 2 else "w%d" % w)

        raw_name = v.get("name", "").split("（")[0]
        items = v.get("items") or []
        point = v.get("point") or ""
        num_items = len(items) if items else 1

        # 构造当天全部观点的时间轴列表
        items_html_list = []
        if items:
            for i, it in enumerate(items, 1):
                i_text = htmlmod.escape(it.get("text") or "").replace("\n", "<br>")
                i_time = htmlmod.escape(it.get("time") or "")
                i_sec = htmlmod.escape(it.get("sector") or "")
                i_d = it.get("direction", "neutral")
                d_color = "var(--accent-green)" if i_d == "bull" else ("var(--accent-red)" if i_d == "bear" else "var(--text-secondary)")
                items_html_list.append(
                    "<div class='v-single-item'>"
                    "<div class='v-item-meta'>"
                    "<span><b>观点 #{idx}</b> · {time}</span>"
                    "<span style='color:{d_col};'>【{sec}】{d_label}</span>"
                    "</div>"
                    "<div>{content}</div>"
                    "</div>".format(
                        idx=i, time=i_time, sec=i_sec, d_col=d_color,
                        d_label="看多" if i_d == "bull" else ("看空" if i_d == "bear" else "中性"),
                        content=i_text
                    )
                )
        else:
            full_text = htmlmod.escape(v.get("full_text") or point).replace("\n", "<br>")
            items_html_list.append(
                "<div class='v-single-item'>"
                "<div class='v-item-meta'><span>{time}</span></div>"
                "<div>{content}</div>"
                "</div>".format(time=htmlmod.escape(v.get("time") or ""), content=full_text)
            )

        items_full_html = "".join(items_html_list)

        cards.append(
            "<div class='v-card' id='vcard-{cidx}' data-dir='{dir_val}' data-sector='{sec_val}'>"
            "<div>"
            "<div class="
            "'v-header'>"
            "<div class='v-author'>"
            "<div class='avatar' style='background:{av}'>{ini}</div>"
            "<div class='v-author-info'>"
            "<span class='v-name'>{name}</span>"
            "<div class='v-badges'>"
            "<span class='badge-w {w_cls}'>{w_txt}</span>"
            "<span class='badge-w badge-sector'>{sector}</span>"
            "</div></div></div>"
            "<span class='badge-dir {dir_cls}'>{dir_txt}</span>"
            "</div>"

            # 核心速览金句
            "<div class='v-headline' id='brief-{cidx}'>{point}</div>"

            # 全球态势日报同款：双模切换条
            "<div class='intel-switch-bar'>"
            "<button class='intel-tab-btn' onclick=\"switchVCardMode('{cidx}', 'brief')\">📝 观点速览</button>"
            "<button class='intel-tab-btn active' onclick=\"switchVCardMode('{cidx}', 'full')\">📖 当天全部观点长文 ({n_items}条) ▾</button>"
            "</div>"

            # 当天全部观点内容容器
            "<div class='v-all-items' id='full-{cidx}'>"
            "{items_container}"
            "</div>"
            "</div>"

            "<div class='v-time-footer'>"
            "<span>数据源：知乎/雪球权威加权</span>"
            "<span>最新更新: {time}</span>"
            "</div>"
            "</div>".format(
                cidx=card_idx,
                dir_val=d,
                sec_val=htmlmod.escape(v.get("sector") or ""),
                av=avatar_color(raw_name),
                ini=htmlmod.escape(raw_name[:1]),
                name=htmlmod.escape(raw_name),
                w_cls=w_cls,
                w_txt=w_txt,
                sector=htmlmod.escape(v.get("sector") or "大盘"),
                dir_cls=dir_cls,
                dir_txt=dir_txt,
                point=htmlmod.escape(point),
                n_items=num_items,
                items_container=items_full_html,
                time=htmlmod.escape(v.get("time") or "")
            )
        )

    # 4. 券商研报
    rpts_boxes = []
    for b in data.get("brokers", []):
        r_list = b.get("reports") or []
        if not r_list:
            continue
        lis = []
        for r in r_list[:4]:
            meta = []
            if r.get("rating"):
                meta.append("评级: %s" % r["rating"])
            if r.get("author"):
                meta.append("分析师: %s" % r["author"])
            if r.get("pages"):
                meta.append("%s页" % r["pages"])
            meta_str = " · ".join(htmlmod.escape(m) for m in meta)
            lis.append(
                "<li class='rpt-item'>"
                "<b>{title}</b>"
                "<div class='rpt-meta'><span>{time}</span><span>{meta}</span></div>"
                "</li>".format(
                    title=htmlmod.escape(r.get("title") or ""),
                    time=htmlmod.escape((r.get("time") or "")[:10]),
                    meta=meta_str
                )
            )
        rpts_boxes.append(
            "<div class='broker-box'>"
            "<div class='broker-title'><span>🏛️ {name}</span><span style='font-size:11px;color:var(--accent-gold);'>金牌金股推荐</span></div>"
            "<ul>{lis}</ul>"
            "</div>".format(name=htmlmod.escape(b.get("name") or ""), lis="".join(lis))
        )

    # 5. 当日要闻
    news_rows = []
    for x in data.get("ths", [])[:12]:
        digest = (x.get("digest") or "").strip()
        title = htmlmod.escape(x.get("title") or "")
        t_str = htmlmod.escape((x.get("time") or "")[:16])
        if digest:
            body = "<b>{title}</b>：{digest}".format(title=title, digest=htmlmod.escape(digest[:140]))
        else:
            body = "<b>{title}</b>".format(title=title)
        news_rows.append(
            "<div class='news-row'>"
            "<div class='news-time'>{time}</div>"
            "<div class='news-body'>{body}</div>"
            "</div>".format(time=t_str, body=body)
        )

    # 原生 JS：双模切换、卡片筛选与全局长文模式
    script = """
    <script>
    function switchVCardMode(cidx, mode) {
      const fullEl = document.getElementById('full-' + cidx);
      const cardEl = document.getElementById('vcard-' + cidx);
      const btns = cardEl.querySelectorAll('.intel-tab-btn');
      if (mode === 'brief') {
        fullEl.style.display = 'none';
        btns[0].classList.add('active');
        btns[1].classList.remove('active');
      } else {
        fullEl.style.display = 'block';
        btns[0].classList.remove('active');
        btns[1].classList.add('active');
      }
    }

    function toggleAllModes(mode) {
      const allFulls = document.querySelectorAll('.v-all-items');
      allFulls.forEach(el => {
        el.style.display = mode === 'full' ? 'block' : 'none';
      });
      document.querySelectorAll('.v-card').forEach(card => {
        const btns = card.querySelectorAll('.intel-tab-btn');
        if (mode === 'brief') {
          btns[0]?.classList.add('active');
          btns[1]?.classList.remove('active');
        } else {
          btns[0]?.classList.remove('active');
          btns[1]?.classList.add('active');
        }
      });
    }

    function filterCards(type, val, btn) {
      document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const cards = document.querySelectorAll('.v-card');
      cards.forEach(card => {
        if (type === 'all') {
          card.style.display = 'flex';
        } else if (type === 'dir') {
          card.style.display = card.dataset.dir === val ? 'flex' : 'none';
        } else if (type === 'sector') {
          card.style.display = card.dataset.sector.includes(val) ? 'flex' : 'none';
        }
      });
    }
    </script>
    """

    conclusion_text = ov.get("conclusion", "")
    if conclusion_text:
        conclusion_html = conclusion_text.replace("**", "<b>").replace("**", "</b>")
    else:
        conclusion_html = "今日市场多空处于均衡博弈阶段，建议耐心防御。"

    body = (
        "<div class='container'>"
        "<!-- 头部 Header -->"
        "<div class='header'>"
        "<div class='header-title'>"
        "<h1>🏛️ 多平台大V财经观点全景深度研报 · 全球态势版</h1>"
        "<p>GitHub Actions 全云自动巡检 · 21位知乎加权大V深度追踪 · 6大券商金股协同 · 当天全部观点全量穿透</p>"
        "</div>"
        "<div class='header-badge'>"
        "<span class='pulse-dot'></span>"
        "<span>{date} 盘后权威锁定版</span>"
        "</div>"
        "</div>"

        "<div class='bento-grid'>"
        "<!-- 一、 当日全网舆情共识与多空雷达 -->"
        "<div class='card col-12'>"
        "<div class='card-header'>"
        "<div class='card-title'>🎯 当日全网舆情共识与多空对决雷达</div>"
        "<span style='font-size:12px;color:var(--text-secondary);'>贝叶斯权重收敛 · 数据截止：{ts}</span>"
        "</div>"
        "<div class='consensus-box'>🔥 <b>今日核心共识</b>：{conclusion}</div>"
        "{cons_html}"
        "</div>"

        "<!-- 二、 核心指数与盘面异动监控 -->"
        "<div class='card col-12'>"
        "<div class='card-header'>"
        "<div class='card-title'>📈 核心指数收盘锚定 (腾讯行情基准)</div>"
        "<span style='font-size:12px;color:var(--text-secondary);'>大跌中见真章 · 资金博弈分歧</span>"
        "</div>"
        "<div class='kpi-grid'>{kpis}</div>"
        "</div>"

        "<!-- 三、 大V观点全景穿透矩阵 (支持当天全部观点长文双模阅读) -->"
        "<div class='card col-12'>"
        "<div class='card-header'>"
        "<div class='card-title'>💬 知乎与雪球加权大V深度观点全景穿透 (含当天全部长文)</div>"
        "<div class='mode-toggle-group'>"
        "<button class='btn-mode' onclick=\"toggleAllModes('full')\">⚡ 一键展开所有大V长文</button>"
        "<button class='btn-mode' style='background:rgba(255,255,255,0.06);border-color:rgba(255,255,255,0.15);color:var(--text-secondary);' onclick=\"toggleAllModes('brief')\">📌 一键折叠为速览模式</button>"
        "</div>"
        "</div>"

        "<div class='control-bar'>"
        "<div class='filter-tabs'>"
        "<button class='btn-filter active' onclick=\"filterCards('all','',this)\">全部大V</button>"
        "<button class='btn-filter' onclick=\"filterCards('dir','bull',this)\">▲ 看多</button>"
        "<button class='btn-filter' onclick=\"filterCards('dir','bear',this)\">▼ 看空</button>"
        "<button class='btn-filter' onclick=\"filterCards('sector','大盘',this)\">大盘</button>"
        "<button class='btn-filter' onclick=\"filterCards('sector','医药',this)\">医药/CRO</button>"
        "<button class='btn-filter' onclick=\"filterCards('sector','新能源',this)\">新能源</button>"
        "<button class='btn-filter' onclick=\"filterCards('sector','创业板',this)\">创业板</button>"
        "</div>"
        "</div>"

        "<div class='v-grid'>{cards}</div>"
        "</div>"

        "<!-- 四、 金牌券商深度研报 -->"
        "<div class='card col-6 col-12'>"
        "<div class='card-header'>"
        "<div class='card-title'>🏛️ 金牌券商深度研报精读</div>"
        "</div>"
        "<div class='reports-grid'>{rpts}</div>"
        "</div>"

        "<!-- 五、 全球宏观要闻感知 -->"
        "<div class='card col-6 col-12'>"
        "<div class='card-header'>"
        "<div class='card-title'>🌐 全球宏观要闻与突发事件感知</div>"
        "</div>"
        "{news}"
        "</div>"
        "</div>"

        "<div class='footer'>Actions 深度态势研报引擎 · 详细实战推演归档 · 仅供学习与量化研究参考</div>"
        "</div>"
        "{script}"
    ).format(
        date=htmlmod.escape(date),
        ts=htmlmod.escape(ts),
        conclusion=conclusion_html,
        cons_html=cons_html,
        kpis="".join(kpis),
        cards="".join(cards),
        rpts="".join(rpts_boxes) if rpts_boxes else "<div class='news-row'>当日暂无券商研报</div>",
        news="".join(news_rows) if news_rows else "<div class='news-row'>当日暂无重大要闻</div>",
        script=script
    )

    return (
        "<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>{date} 知乎大V财经观点全景深度研报 · 全球态势版</title><style>{css}</style></head>"
        "<body>{body}</body></html>"
    ).format(date=date, css=CSS, body=body)


if __name__ == "__main__":
    d = {"date": "2026-09-10", "ts": "15:30",
         "tencent": [{"name": "上证指数", "price": "3951.51", "chg_pct": "0.28", "amount": "87370000"}],
         "ths": [{"title": "苹果发布iPhone 18", "time": "2026-09-10 08:00", "digest": "售价1199美元起"}],
         "brokers": [{"name": "国元证券", "reports": [{"title": "机械周报", "time": "2026-09-09 00:00", "rating": "增持", "author": "张三", "pages": "11"}]}],
         "xueqiu": {"accounts": []}, "zhihu": {"accounts": []}, "warnings": []}
    print(render_html(d)[:400])
