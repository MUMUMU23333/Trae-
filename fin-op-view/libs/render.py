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

def render_summary(data, limit=280):
    """简版结论（企微文字快览）：当日共识 + 大V加权top + 盘面 + 要闻 + 研报。"""
    out = []
    views = _zh_views(data)
    ov = insight.build_overview(views)
    if ov["conclusion"]:
        out.append("【共识】" + ov["conclusion"].replace("**", ""))
    # 大V加权 top3（方向 + 一句话）
    if views:
        top = sorted(views, key=lambda v: -(v["weight"] or 1))[:3]
        t = "；".join("(%s)%s" % (
            v["name"].split("（")[0][:6],
            ("%s %s" % (v["point"][:20], "看多" if v["direction"] == "bull" else ("看空" if v["direction"] == "bear" else ""))).strip()) for v in top)
        out.append("【大V】" + t)
    # 盘面
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
        out.append("【要闻】" + "；".join((x.get("title") or "")[:26] for x in ths[:2]))
    # 研报
    brs = [b for b in data.get("brokers", []) if b.get("reports")]
    if brs:
        tot = sum(len(b["reports"]) for b in brs)
        out.append("【研报】%d家共%d篇；代表：%s" % (len(brs), tot, brs[0]["reports"][0]["title"][:30]))
    # 降级提醒
    warns = [w for w in (data.get("warnings") or []) if "人工" in w or "降级" in w]
    for w in warns[:1]:
        out.append("【注意】" + w[:30])
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
            act = [a for a in src["accounts"] if a["items"]]
      # ---------- HTML v2（专业金融 Terminal Dashboard） ----------

CSS = """
:root {
  --bg: #070a12;
  --card: #0d1424;
  --card-sub: #111a30;
  --card-hover: #16223f;
  --border: #1c2b4d;
  --border-sub: #253863;
  --txt: #f0f4ff;
  --txt-dim: #7e8ea8;
  --txt-muted: #52607a;
  --accent: #3b82f6;
  --accent-glow: rgba(59, 130, 246, 0.25);
  --bull: #10b981;
  --bull-bg: rgba(16, 185, 129, 0.12);
  --bull-border: rgba(16, 185, 129, 0.35);
  --bear: #ef4444;
  --bear-bg: rgba(239, 68, 68, 0.12);
  --bear-border: rgba(239, 68, 68, 0.35);
  --gold: #f59e0b;
  --gold-bg: rgba(245, 158, 11, 0.12);
  --purple: #8b5cf6;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  background-color: var(--bg);
  color: var(--txt);
  line-height: 1.6;
  padding: 24px 16px;
  max-width: 1200px;
  margin: 0 auto;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  padding: 20px 24px;
  background: linear-gradient(135deg, #0d1833 0%, #090e1c 100%);
  border: 1px solid var(--border);
  border-radius: 16px;
  margin-bottom: 24px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
}
.header-title { font-size: 1.5rem; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 10px; }
.header-meta { color: var(--txt-dim); font-size: 0.85rem; margin-top: 4px; }
.badge-live {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(16, 185, 129, 0.15); color: var(--bull);
  border: 1px solid var(--bull-border); border-radius: 20px;
  padding: 4px 14px; font-size: 0.8rem; font-weight: 600;
}
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--bull); box-shadow: 0 0 8px var(--bull); }
.sec {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px 22px;
  margin-bottom: 22px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
}
.sec-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 1.1rem;
  font-weight: 600;
  color: #fff;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  padding-bottom: 10px;
}
.sec-title-left { display: flex; align-items: center; gap: 10px; }
.icon {
  width: 28px; height: 28px; border-radius: 8px;
  background: var(--accent-glow); color: var(--accent);
  display: flex; align-items: center; justify-content: center; font-size: 0.95rem;
}
.conclusion-box {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.12), rgba(139, 92, 246, 0.08));
  border-left: 4px solid var(--accent);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 16px;
  font-size: 0.95rem;
  color: #dbe4ff;
}
.conclusion-box b { color: #fff; font-weight: 700; }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 12px;
}
.kpi-card {
  background: var(--card-sub);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
  transition: transform 0.2s, border-color 0.2s;
}
.kpi-card:hover { transform: translateY(-2px); border-color: var(--border-sub); }
.kpi-name { color: var(--txt-dim); font-size: 0.82rem; font-weight: 500; }
.kpi-num { font-size: 1.4rem; font-weight: 700; margin: 4px 0 2px; }
.kpi-pct { font-size: 0.95rem; font-weight: 700; }
.kpi-amt { color: var(--txt-muted); font-size: 0.78rem; margin-top: 4px; }
.up { color: var(--bull); }
.down { color: var(--bear); }
.flat { color: var(--txt-dim); }

.con-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px 6px;
  border-bottom: 1px dashed var(--border);
}
.con-row:last-child { border-bottom: none; }
.con-sector { width: 110px; font-weight: 600; color: #fff; flex-shrink: 0; font-size: 0.92rem; }
.bar-wrap {
  flex: 1; height: 16px; display: flex; border-radius: 6px; overflow: hidden;
  background: rgba(255, 255, 255, 0.05);
}
.bar-bull { background: linear-gradient(90deg, #059669, #10b981); }
.bar-bear { background: linear-gradient(90deg, #dc2626, #ef4444); }
.con-stat { font-size: 0.8rem; color: var(--txt-dim); text-align: right; width: 220px; flex-shrink: 0; }

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.filter-btn {
  background: var(--card-sub);
  border: 1px solid var(--border);
  color: var(--txt-dim);
  padding: 6px 14px;
  border-radius: 8px;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s;
}
.filter-btn:hover, .filter-btn.active {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
}

.views-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 14px;
}
.view-card {
  background: var(--card-sub);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  transition: all 0.2s;
}
.view-card:hover { border-color: var(--border-sub); box-shadow: 0 4px 16px rgba(0,0,0,0.3); }
.view-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}
.view-user { display: flex; align-items: center; gap: 10px; }
.avatar {
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 0.85rem; color: #fff;
}
.user-name { font-weight: 600; color: #fff; font-size: 0.95rem; }
.user-tags { display: flex; gap: 6px; margin-top: 2px; }
.tag-badge {
  font-size: 0.72rem; padding: 2px 7px; border-radius: 6px; border: 1px solid;
}
.tag-w3 { background: var(--gold-bg); color: var(--gold); border-color: rgba(245, 158, 11, 0.4); font-weight: 600; }
.tag-w2 { background: rgba(59, 130, 246, 0.15); color: var(--accent); border-color: rgba(59, 130, 246, 0.4); }
.tag-w1 { background: rgba(255, 255, 255, 0.08); color: var(--txt-dim); border-color: rgba(255, 255, 255, 0.15); }
.tag-sector { background: rgba(139, 92, 246, 0.12); color: var(--purple); border-color: rgba(139, 92, 246, 0.3); }

.dir-badge {
  font-size: 0.75rem; font-weight: 700; padding: 3px 10px; border-radius: 8px; border: 1px solid;
}
.dir-bull { background: var(--bull-bg); color: var(--bull); border-color: var(--bull-border); }
.dir-bear { background: var(--bear-bg); color: var(--bear); border-color: var(--bear-border); }
.dir-neutral { background: rgba(255, 255, 255, 0.08); color: var(--txt-dim); border-color: var(--border); }

.view-summary {
  font-size: 0.88rem; color: #e2e8f0; line-height: 1.5; margin-bottom: 10px;
}
.view-details {
  border-top: 1px dashed var(--border);
  padding-top: 8px;
  margin-top: 6px;
}
.view-details summary {
  font-size: 0.78rem;
  color: var(--accent);
  cursor: pointer;
  user-select: none;
  font-weight: 500;
  outline: none;
}
.view-details summary:hover { text-decoration: underline; }
.view-full-text {
  font-size: 0.83rem;
  color: #cbd5e1;
  background: rgba(0, 0, 0, 0.25);
  padding: 10px 12px;
  border-radius: 8px;
  margin-top: 8px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
.view-time { font-size: 0.72rem; color: var(--txt-muted); margin-top: 8px; text-align: right; }

.news-item {
  display: flex;
  gap: 14px;
  padding: 10px 6px;
  border-bottom: 1px dashed var(--border);
  font-size: 0.88rem;
}
.news-item:last-child { border-bottom: none; }
.news-time { color: var(--txt-muted); font-size: 0.78rem; white-space: nowrap; flex-shrink: 0; padding-top: 2px; }
.news-content b { color: #fff; }

.reports-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}
.broker-card {
  background: var(--card-sub);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
}
.broker-name { font-weight: 700; color: #fff; font-size: 0.95rem; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between; }
.report-li {
  list-style: none;
  padding: 8px 0 8px 12px;
  border-left: 2px solid var(--border);
  margin-bottom: 6px;
  font-size: 0.84rem;
  color: #cbd5e1;
}
.report-li b { color: #fff; font-size: 0.86rem; display: block; margin-bottom: 2px; }
.report-meta { color: var(--txt-muted); font-size: 0.74rem; display: flex; gap: 8px; }

.footer {
  text-align: center;
  color: var(--txt-muted);
  font-size: 0.78rem;
  margin-top: 30px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}
@media (max-width: 640px) {
  .con-stat { width: 120px; font-size: 0.72rem; }
  .con-sector { width: 80px; font-size: 0.85rem; }
  .views-grid { grid-template-columns: 1fr; }
}
"""


def render_html(data):
    """生成具备高保真金融大屏、完整原文展开与动态筛选的专业 HTML。"""
    date, ts = data.get("date", ""), data.get("ts", "")
    views = _zh_views(data)
    ov = insight.build_overview(views)

    # 调色盘
    palette = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899", "#06b6d4", "#f97316", "#84cc16"]
    def avatar_color(name):
        return palette[sum(ord(c) for c in name) % len(palette)]

    # --- 盘面 KPI ---
    kpis = []
    for it in data.get("tencent", [])[:4]:
        pct = it.get("chg_pct") or "0.00"
        arrow, cls = _pct_arrow(pct)
        amt = _fmt_amount(it.get("amount"))
        kpis.append(
            "<div class='kpi-card'>"
            "<div class='kpi-name'>{name}</div>"
            "<div class='kpi-num'>{price}</div>"
            "<div class='kpi-pct {cls}'>{arrow} {pct}%</div>"
            "<div class='kpi-amt'>成交额 {amt}</div>"
            "</div>".format(
                name=htmlmod.escape(it["name"]),
                price=htmlmod.escape(it.get("price") or "—"),
                cls=cls, arrow=arrow, pct=htmlmod.escape(pct),
                amt=amt or "—"
            )
        )

    # --- 板块共识天平 ---
    cons = ""
    for r in ov["rows"][:8]:
        total_w = r["bull_w"] + r["bear_w"]
        bull_ratio = int(r["bull_w"] * 100 / total_w) if total_w else 50
        bear_ratio = 100 - bull_ratio
        bar = (
            "<div class='bar-bull' style='width:{b_ratio}%' title='多方权重 {bw}'></div>"
            "<div class='bar-bear' style='width:{s_ratio}%' title='空方权重 {sw}'></div>"
        ).format(b_ratio=bull_ratio, s_ratio=bear_ratio, bw=r["bull_w"], sw=r["bear_w"])
        
        names_str = "、".join(r["names"][:4]) or "—"
        cons += (
            "<div class='con-row'>"
            "<div class='con-sector'>{sector}</div>"
            "<div class='bar-wrap'>{bar}</div>"
            "<div class='con-stat'>"
            "<span style='color:{dir_col};font-weight:600;'>{side}</span> (多{bull}/空{bear}) · {names}"
            "</div>"
            "</div>"
        ).format(
            sector=htmlmod.escape(r["sector"]),
            bar=bar,
            dir_col="var(--bull)" if r["side"] == "看多" else "var(--bear)",
            side=r["side"],
            bull=r["bull_n"],
            bear=r["bear_n"],
            names=htmlmod.escape(names_str)
        )
    if not cons:
        cons = "<div class='con-row'><div class='con-sector'>—</div><div class='bar-wrap'></div><div class='con-stat'>暂无显著多空分歧</div></div>"

    # --- 大V观点卡片（保留完整长文与展开详情） ---
    cards = []
    for v in sorted(views, key=lambda x: -(x.get("weight") or 1)):
        d = v.get("direction", "neutral")
        if d == "bull":
            dir_cls = "dir-bull"
            dir_txt = "▲ 看多"
        elif d == "bear":
            dir_cls = "dir-bear"
            dir_txt = "▼ 看空"
        else:
            dir_cls = "dir-neutral"
            dir_txt = "— 中性"

        w = v.get("weight") or 1
        w_cls = "tag-w3" if w >= 3 else ("tag-w2" if w == 2 else "tag-w1")
        w_txt = "w%d 核心" % w if w >= 3 else ("w%d 重点" % w if w == 2 else "w%d" % w)

        raw_name = v.get("name", "").split("（")[0]
        full_text = v.get("full_text") or v.get("point") or ""
        point = v.get("point") or ""

        # 详情展开部分
        details_html = ""
        if full_text and (len(full_text) > len(point) or "\n" in full_text):
            details_html = (
                "<details class='view-details'>"
                "<summary>展开完整实战推演全文（含逻辑细节）</summary>"
                "<div class='view-full-text'>{full}</div>"
                "</details>"
            ).format(full=htmlmod.escape(full_text))

        cards.append(
            "<div class='view-card' data-dir='{dir_val}' data-sector='{sec_val}'>"
            "<div>"
            "<div class='view-header'>"
            "<div class='view-user'>"
            "<div class='avatar' style='background:{av}'>{ini}</div>"
            "<div>"
            "<div class='user-name'>{name}</div>"
            "<div class='user-tags'>"
            "<span class='tag-badge {w_cls}'>{w_txt}</span>"
            "<span class='tag-badge tag-sector'>{sector}</span>"
            "</div></div></div>"
            "<span class='dir-badge {dir_cls}'>{dir_txt}</span>"
            "</div>"
            "<div class='view-summary'>{point}</div>"
            "{details}"
            "</div>"
            "<div class='view-time'>{time}</div>"
            "</div>".format(
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
                details=details_html,
                time=htmlmod.escape(v.get("time") or "")
            )
        )
    if not cards:
        cards.append("<div class='view-card'><div class='view-summary'>本次抓取无明显大V观点更新</div></div>")

    # --- 要闻 ---
    news_html = ""
    for x in data.get("ths", [])[:12]:
        digest = (x.get("digest") or "").strip()
        title = htmlmod.escape(x.get("title") or "")
        t_str = htmlmod.escape((x.get("time") or "")[:16])
        if digest:
            body = "<b>{title}</b>：{digest}".format(title=title, digest=htmlmod.escape(digest[:130]))
        else:
            body = "<b>{title}</b>".format(title=title)
        news_html += (
            "<div class='news-item'>"
            "<div class='news-time'>{time}</div>"
            "<div class='news-content'>{body}</div>"
            "</div>"
        ).format(time=t_str, body=body)
    if not news_html:
        news_html = "<div class='news-item'><div class='news-content'>当日暂无重大要闻</div></div>"

    # --- 券商研报 ---
    rpts_html = ""
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
                "<li class='report-li'>"
                "<b>{title}</b>"
                "<div class='report-meta'><span>{time}</span><span>{meta}</span></div>"
                "</li>".format(
                    title=htmlmod.escape(r.get("title") or ""),
                    time=htmlmod.escape((r.get("time") or "")[:10]),
                    meta=meta_str
                )
            )
        rpts_html += (
            "<div class='broker-card'>"
            "<div class='broker-name'><span>🏛️ {name}</span><span style='font-size:0.75rem;color:var(--gold);'>精选研报</span></div>"
            "<ul>{lis}</ul>"
            "</div>"
        ).format(name=htmlmod.escape(b.get("name") or ""), lis="".join(lis))
    if not rpts_html:
        rpts_html = "<div class='broker-card'><div class='broker-name'>当日暂无券商研报收录</div></div>"

    # JS 筛选器脚本
    script = """
    <script>
    function filterCards(type, val, btn) {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const cards = document.querySelectorAll('.view-card');
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
        conclusion_html = "今日市场处于震荡博弈阶段，未形成绝对单边共识。"

    body = (
        "<div class='header'>"
        "<div>"
        "<div class='header-title'>⚡ 知乎/多平台大V 财经观点全景深度研报</div>"
        "<div class='header-meta'>数据截止：{ts} · 贝叶斯加权与多空收敛引擎驱动 · 非投资建议，据此操作风险自负</div>"
        "</div>"
        "<div class='badge-live'><div class='dot'></div> 自动全云抓取 ({date})</div>"
        "</div>"

        "<div class='sec'>"
        "<div class='sec-title'><div class='sec-title-left'><div class='icon'>🎯</div>核心观点与大盘盘面</div></div>"
        "<div class='conclusion-box'>{conclusion}</div>"
        "<div class='kpi-grid'>{kpis}</div>"
        "</div>"

        "<div class='sec'>"
        "<div class='sec-title'><div class='sec-title-left'><div class='icon'>⚖️</div>板块多空共识天平（多空人数 · 权重 ΣW）</div></div>"
        "{cons}"
        "</div>"

        "<div class='sec'>"
        "<div class='sec-title'>"
        "<div class='sec-title-left'><div class='icon'>💬</div>大V深度推演与核心持仓逻辑</div>"
        "<span style='font-size:0.8rem;color:var(--txt-dim);'>支持展开阅读完整长文</span>"
        "</div>"
        "<div class='filters'>"
        "<button class='filter-btn active' onclick=\"filterCards('all','',this)\">全部大V</button>"
        "<button class='filter-btn' onclick=\"filterCards('dir','bull',this)\">▲ 仅看看多</button>"
        "<button class='filter-btn' onclick=\"filterCards('dir','bear',this)\">▼ 仅看看空</button>"
        "<button class='filter-btn' onclick=\"filterCards('sector','大盘',this)\">大盘多空</button>"
        "<button class='filter-btn' onclick=\"filterCards('sector','医药',this)\">医药/CRO</button>"
        "<button class='filter-btn' onclick=\"filterCards('sector','新能源',this)\">新能源</button>"
        "<button class='filter-btn' onclick=\"filterCards('sector','创业板',this)\">创业板</button>"
        "</div>"
        "<div class='views-grid'>{cards}</div>"
        "</div>"

        "<div class='sec'>"
        "<div class='sec-title'><div class='sec-title-left'><div class='icon'>🏛️</div>金牌券商深度研报</div></div>"
        "<div class='reports-grid'>{rpts}</div>"
        "</div>"

        "<div class='sec'>"
        "<div class='sec-title'><div class='sec-title-left'><div class='icon'>🌐</div>全球宏观要闻与突发事件</div></div>"
        "{news}"
        "</div>"

        "<div class='footer'>Actions 深度研报生成引擎 · 详细实战推演归档 · 仅供学习与量化研究参考</div>"
        "{script}"
    ).format(
        date=htmlmod.escape(date),
        ts=htmlmod.escape(ts),
        conclusion=conclusion_html,
        kpis="".join(kpis),
        cons=cons,
        cards="".join(cards),
        rpts=rpts_html,
        news=news_html,
        script=script
    )

    return (
        "<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>{date} 知乎大V财经观点全景深度研报</title><style>{css}</style></head>"
        "<body>{body}</body></html>"
    ).format(date=date, css=CSS, body=body)


if __name__ == "__main__":
    d = {"date": "2026-09-10", "ts": "15:30",
         "tencent": [{"name": "上证指数", "price": "3951.51", "chg_pct": "0.28", "amount": "87370000"}],
         "ths": [{"title": "苹果发布iPhone 18", "time": "2026-09-10 08:00", "digest": "售价1199美元起"}],
         "brokers": [{"name": "国元证券", "reports": [{"title": "机械周报", "time": "2026-09-09 00:00", "rating": "增持", "author": "张三", "pages": "11"}]}],
         "xueqiu": {"accounts": []}, "zhihu": {"accounts": []}, "warnings": []}
    print(render_html(d)[:400])
