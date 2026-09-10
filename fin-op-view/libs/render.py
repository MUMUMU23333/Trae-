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


# ---------- HTML v2（专业卡片 Dashboard） ----------

CSS = """
:root{--bg:#0b0f1a;--card:#121a2c;--card2:#0f1626;--line:#1f2b44;--txt:#e8ecf8;--dim:#8a94b0;
--blue:#5b8cff;--green:#2fd67f;--red:#ff5d6c;--gold:#ffc857;--purple:#a78bfa}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'PingFang SC','Microsoft YaHei','Noto Sans SC',system-ui,sans-serif;background:var(--bg);
color:var(--txt);line-height:1.65;padding:24px;max-width:1080px;margin:0 auto}
.masthead{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:8px;
border-bottom:2px solid var(--blue);padding-bottom:14px;margin-bottom:20px}
.masthead h1{font-size:1.45rem;color:#fff;letter-spacing:.5px}
.masthead .sub{color:var(--dim);font-size:.82rem;margin-top:4px}
.tag{display:inline-block;background:rgba(91,140,255,.14);color:var(--blue);border:1px solid rgba(91,140,255,.35);
border-radius:20px;padding:3px 12px;font-size:.78rem}
.warn-tag{background:rgba(255,197,87,.12);color:var(--gold);border-color:rgba(255,197,87,.35)}
.sec{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:18px}
.sec-title{display:flex;align-items:center;gap:10px;font-size:1.05rem;font-weight:600;margin-bottom:14px;color:#fff}
.sec-title .ico{width:26px;height:26px;border-radius:8px;display:flex;align-items:center;justify-content:center;
font-size:.9rem;background:rgba(91,140,255,.15)}
.conclusion{background:linear-gradient(135deg,rgba(91,140,255,.14),rgba(167,139,250,.10));
border-left:4px solid var(--blue);border-radius:10px;padding:14px 18px;font-size:.98rem;color:#dbe4ff;margin-bottom:14px}
.conclusion b{color:#fff}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}
.kpi{background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .name{color:var(--dim);font-size:.8rem}
.kpi .num{font-size:1.3rem;font-weight:700;margin:4px 0 2px}
.kpi .pct{font-size:.95rem;font-weight:600}
.kpi .amt{color:var(--dim);font-size:.75rem;margin-top:2px}
.up{color:var(--green)}.down{color:var(--red)}.flat{color:var(--dim)}
.con-row{display:flex;align-items:center;gap:14px;padding:9px 4px;border-bottom:1px dashed var(--line)}
.con-row:last-child{border-bottom:none}
.con-row .cs{width:110px;font-weight:600;color:#cdd7f5;flex-shrink:0}
.bar-wrap{flex:1;display:flex;gap:2px;height:14px;border-radius:4px;overflow:hidden;background:var(--card2)}
.bar-b{background:var(--green)}.bar-s{background:var(--red)}.bar-n{background:var(--line)}
.con-row .stat{width:150px;text-align:right;color:var(--dim);font-size:.78rem;flex-shrink:0}
.v-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.vcard{background:var(--card2);border:1px solid var(--line);border-radius:12px;padding:13px 15px;position:relative}
.vcard .top{display:flex;align-items:center;gap:8px;margin-bottom:7px;flex-wrap:wrap}
.avatar{width:26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-size:.72rem;font-weight:700;color:#0b0f1a;flex-shrink:0}
.vcard .who{font-weight:600;color:#fff;font-size:.9rem}
.badge{font-size:.68rem;padding:1px 8px;border-radius:10px;border:1px solid}
.b-w{background:rgba(255,197,87,.12);color:var(--gold);border-color:rgba(255,197,87,.4)}
.b-{background:rgba(91,140,255,.12);color:var(--blue);border-color:rgba(91,140,255,.4)}
.bull{background:rgba(47,214,127,.12);color:var(--green);border-color:rgba(47,214,127,.4)}
.bear{background:rgba(255,93,108,.12);color:var(--red);border-color:rgba(255,93,108,.4)}
.neutral{background:rgba(138,148,176,.12);color:var(--dim);border-color:rgba(138,148,176,.4)}
.vcard .point{font-size:.86rem;color:#d3daef}
.vcard .time{color:var(--dim);font-size:.72rem;margin-top:6px}
.news{display:flex;gap:10px;padding:8px 2px;border-bottom:1px dashed var(--line);font-size:.86rem}
.news:last-child{border-bottom:none}
.news .t{color:var(--dim);font-size:.75rem;white-space:nowrap;flex-shrink:0;padding-top:1px}
.news b{color:#e8ecf8}
.rpt{margin-bottom:12px}
.rpt .org{font-weight:600;color:#cdd7f5;margin-bottom:6px}
.rpt li{list-style:none;padding:5px 0 5px 14px;border-left:2px solid var(--line);margin-bottom:6px;
font-size:.85rem;color:#c6cfe8}
.rpt li b{color:#fff}
.meta{color:var(--dim);font-size:.75rem;margin-left:6px}
.foot{text-align:center;color:var(--dim);font-size:.75rem;margin-top:22px;padding-top:14px;border-top:1px solid var(--line)}
@media(max-width:640px){.con-row .cs{width:80px}.con-row .stat{width:110px}}
"""


def render_html(data):
    """结构化生成专业卡片 HTML（不再经 md 中转）。"""
    date, ts = data["date"], data["ts"]
    views = _zh_views(data)
    ov = insight.build_overview(views)

    # 头像色池（按名字 hash 稳定取色）
    palette = ["#5b8cff", "#2fd67f", "#ffc857", "#a78bfa", "#ff5d6c", "#3ec6d6", "#f78fb3", "#82c91e"]

    def avatar_color(name):
        return palette[sum(ord(c) for c in name) % len(palette)]

    # --- 盘面 KPI ---
    kpis = []
    for it in data.get("tencent", [])[:4]:
        pct = it.get("chg_pct") or "0.00"
        arrow, cls = _pct_arrow(pct)
        amt = _fmt_amount(it.get("amount"))
        kpis.append(
            "<div class='kpi'><div class='name'>{name}</div>"
            "<div class='num'>{price}</div>"
            "<div class='pct {cls}'>{arrow}{pct}%</div>"
            "<div class='amt'>{amt}</div></div>".format(
                name=htmlmod.escape(it["name"]), price=htmlmod.escape(it.get("price") or "—"),
                cls=cls, arrow=arrow, pct=htmlmod.escape(pct), amt=amt or "—"))

    # --- 共识行 ---
    cons = ""
    for r in ov["rows"][:7]:
        total = r["bull_n"] + r["bear_n"]
        bull_w_ratio = int(r["bull_w"] * 100 / (r["bull_w"] + r["bear_w"])) if (r["bull_w"] + r["bear_w"]) else 50
        bar = ("<div class='bar-b' style='width:%d%%'></div>" % bull_w_ratio +
               "<div class='bar-s' style='width:%d%%'></div>" % (100 - bull_w_ratio))
        names = "、".join(r["names"][:4]) or "—"
        cons += ("<div class='con-row'><div class='cs'>{sector}</div>{bar}"
                 "<div class='stat'>{n}人参与 · 多{bull}/空{bear} · {names}</div></div>").format(
            sector=htmlmod.escape(r["sector"]), bar=bar, n=total,
            bull=r["bull_n"], bear=r["bear_n"], names=htmlmod.escape(names))
    if not cons:
        cons = "<div class='con-row'><div class='cs'>—</div><div class='bar-wrap'></div><div class='stat'>暂无明确板块共识</div></div>"

    # --- 大V观点卡 ---
    cards = []
    for v in sorted(views, key=lambda x: -(x["weight"] or 1)):
        d_badge = ("<span class='badge bull'>看多</span>" if v["direction"] == "bull"
                   else ("<span class='badge bear'>看空</span>" if v["direction"] == "bear"
                         else "<span class='badge neutral'>中性</span>"))
        cards.append(
            "<div class='vcard'><div class='top'>"
            "<div class='avatar' style='background:{av}'>{initial}</div>"
            "<span class='who'>{name}</span>"
            "<span class='badge b-w'>w{w}</span>"
            "<span class='badge b-'>{sector}</span>{d_badge}"
            "</div><div class='point'>{point}</div>"
            "<div class='time'>{time}</div></div>".format(
                av=avatar_color(v["name"]),
                initial=htmlmod.escape(v["name"][:1]),
                name=htmlmod.escape(v["name"].split("（")[0]),
                w=v["weight"], sector=htmlmod.escape(v["sector"]),
                d_badge=d_badge, point=htmlmod.escape(v["point"]),
                time=htmlmod.escape(v["time"])))
    if not cards:
        cards.append("<div class='vcard'><div class='point'>本次无大V观点（cookie 失效或均为中性）</div></div>")

    # --- 要闻 ---
    news = ""
    for x in data.get("ths", [])[:12]:
        digest = (x.get("digest") or "").strip()
        title = htmlmod.escape(x.get("title") or "")
        if digest:
            body = "<b>{title}</b>：{digest}".format(title=title, digest=htmlmod.escape(digest[:110]))
        else:
            body = "<b>{title}</b>".format(title=title)
        news += ("<div class='news'><div class='t'>{time}</div><div>{body}</div></div>").format(
            time=htmlmod.escape((x.get("time") or "")[:16]), body=body)

    # --- 研报 ---
    rpts = ""
    for b in data.get("brokers", []):
        if not b.get("reports"):
            rpts += "<div class='rpt'><div class='org'>{org}</div><ul><li>当日无研报</li></ul></div>".format(
                org=htmlmod.escape(b["name"]))
            continue
        lis = []
        for r in b["reports"][:5]:
            meta = []
            if r.get("rating"):
                meta.append(r["rating"])
            if r.get("author"):
                meta.append(r["author"])
            if r.get("pages"):
                meta.append("%s页" % r["pages"])
            m = "<span class='meta'>%s</span>" % (" · ".join(htmlmod.escape(x) for x in meta)) if meta else ""
            lis.append("<li>{time} <b>{title}</b>{meta}</li>".format(
                time=htmlmod.escape(r["time"][:10]),
                title=htmlmod.escape(r["title"][:60]), meta=m))
        rpts += "<div class='rpt'><div class='org'>{org}</div><ul>{lis}</ul></div>".format(
            org=htmlmod.escape(b["name"]), lis="\n".join(lis))

    # 提醒
    warns_html = ""
    warns = [w for w in (data.get("warnings") or []) if w]
    for src in ("xueqiu", "zhihu"):
        s = data.get(src, {})
        if isinstance(s, dict) and s.get("note"):
            warns.append(s["note"])
    if warns:
        warns_html = ("<div class='sec'><div class='sec-title'><div class='ico'>⚠</div>注意事项</div>"
                      + "".join("<div class='news'><div>{w}</div></div>".format(w=htmlmod.escape(w[:80])) for w in warns[:3])
                      + "</div>")

    # --- 同花顺大V ---
    ths_bv = data.get("ths_bigv", {})
    ths_cards = ""
    if isinstance(ths_bv, dict) and ths_bv.get("accounts"):
        for a in ths_bv["accounts"]:
            if not a["items"]:
                continue
            it = a["items"][0]
            body = htmlmod.escape(("%s %s" % (it["title"] or "", it["text"] or "")).strip()[:90])
            ths_cards += ("<div class='vcard'><div class='top'>"
                          "<div class='avatar' style='background:{av}'>{ini}</div>"
                          "<span class='who'>{name}</span><span class='badge b-w'>w{w}</span>"
                          "<span class='badge b-'>同花顺</span></div>"
                          "<div class='point'>{body}</div>"
                          "<div class='time'>{time}</div></div>").format(
                av=avatar_color(a["name"]), ini=htmlmod.escape(a["name"][:1]),
                name=htmlmod.escape(a["name"]), w=a["weight"],
                body=body, time=htmlmod.escape(it["time"]))
    ths_note = (ths_bv.get("note") or "").strip() if isinstance(ths_bv, dict) else ""
    if ths_cards:
        sec_inner = "<div class='v-grid'>{cards}</div>".format(cards=ths_cards)
        if ths_note:
            sec_inner += "<div class='news'><div>{n}</div></div>".format(n=htmlmod.escape(ths_note))
        warns_html += ("<div class='sec'><div class='sec-title'><div class='ico'>🏮</div>同花顺大V观点"
                       "（在线直抓）</div>{inner}</div>").format(inner=sec_inner)
    elif ths_note:
        warns_html += ("<div class='sec'><div class='sec-title'><div class='ico'>🏮</div>同花顺大V</div>"
                       "<div class='news'><div>{n}</div></div></div>").format(n=htmlmod.escape(ths_note))

    body = (
        "<div class='masthead'><div><h1>📊 多平台大V财经观点统计</h1>"
        "<div class='sub'>数据截止：{ts} · GitHub Actions 全云自动抓取 · 非投资建议，据此操作风险自负</div></div>"
        "<span class='tag'>{date}</span></div>"

        "<div class='sec'><div class='sec-title'><div class='ico'>🎯</div>今日观点结论</div>"
        "<div class='conclusion'>{conclusion}</div>"
        "<div class='kpi-grid'>{kpis}</div></div>"

        "<div class='sec'><div class='sec-title'><div class='ico'>🧭</div>板块共识（多空人数 · 权重ΣW）</div>"
        "{cons}</div>"

        "<div class='sec'><div class='sec-title'><div class='ico'>💬</div>大V观点（按权重排序，已归纳）</div>"
        "<div class='v-grid'>{cards}</div></div>"

        "<div class='sec'><div class='sec-title'><div class='ico'>📰</div>当日要闻</div>{news}</div>"

        "<div class='sec'><div class='sec-title'><div class='ico'>📄</div>券商研报（东财）</div>{rpts}</div>"

        "{warns_html}"

        "<div class='foot'>Actions 自动生成 · 数据仅供研究参考 · 归档见 Actions Artifact</div>"
    ).format(
        date=htmlmod.escape(date), ts=htmlmod.escape(ts),
        conclusion=ov["conclusion"].replace("**", "<b>").replace("**", "</b>") if ov["conclusion"] else "当日无明确方向信号",
        kpis="\n".join(kpis), cons=cons, cards="\n".join(cards),
        news=news or "<div class='news'><div>当日无新闻</div></div>",
        rpts=rpts or "<div class='news'><div>当日无研报</div></div>",
        warns_html=warns_html)

    return ("<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>{date} 财经观点统计</title><style>{css}</style></head>"
            "<body>{body}</body></html>").format(date=date, css=CSS, body=body)


if __name__ == "__main__":
    d = {"date": "2026-09-10", "ts": "15:30",
         "tencent": [{"name": "上证指数", "price": "3951.51", "chg_pct": "0.28", "amount": "87370000"}],
         "ths": [{"title": "苹果发布iPhone 18", "time": "2026-09-10 08:00", "digest": "售价1199美元起"}],
         "brokers": [{"name": "国元证券", "reports": [{"title": "机械周报", "time": "2026-09-09 00:00", "rating": "增持", "author": "张三", "pages": "11"}]}],
         "xueqiu": {"accounts": []}, "zhihu": {"accounts": []}, "warnings": []}
    print(render_html(d)[:400])
