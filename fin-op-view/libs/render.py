# -*- coding: utf-8 -*-
"""render.py — 拼成品 md + 自包含 HTML（深色金融风格）。复用现有档结构。
"""
import datetime
import html as htmlmod
import json

HEADER = """# 多平台大V财经观点统计（{date}）

> 数据截止：{ts} | 抓取通道：GitHub Actions 全云自动 | 来源口径：盘面/同花顺/券商/雪球
> 非投资建议，据此操作风险自负。

"""


def _fmt_amount(amt):
    """成交额(万元)→ 亿元 展示。空/非数返回 '—'。"""
    try:
        v = float(amt or 0)
    except (TypeError, ValueError):
        return "—"
    if v <= 0:
        return "—"
    return "成交额%.0f亿" % (v / 10000.0)


def render_summary(data, limit=280):
    """简版结论（企微文字快览，≤limit 字）：盘面锚定 + 当日要闻 + 券商亮点 + 知乎加权 top。
    详细全量内容走完整 md / HTML 文件。"""
    out = []
    # 1) 盘面锚定
    tenc = data.get("tencent", [])
    if tenc:
        pieces = []
        for it in tenc[:4]:
            pct = it.get("chg_pct") or "0.00"
            try:
                arrow = "▲" if float(pct) > 0 else ("▼" if float(pct) < 0 else "—")
            except ValueError:
                arrow = "—"
            amt = _fmt_amount(it.get("amount"))
            pieces.append("%s %s%s%%(%s)" % (it["name"], arrow, pct, amt))
        out.append("【盘面】" + " | ".join(pieces))
    # 2) 当日要闻（同花顺 top2）
    ths = data.get("ths", [])
    if ths:
        out.append("【要闻】" + "；".join((x.get("title") or "")[:30] for x in ths[:2]))
    # 3) 券商亮点（有研报机构数 + 首篇标题）
    brs = [b for b in data.get("brokers", []) if b.get("reports")]
    if brs:
        tot = sum(len(b["reports"]) for b in brs)
        top = brs[0]["reports"][0]["title"]
        out.append("【研报】%d家机构共%d篇；代表：%s" % (len(brs), tot, top[:35]))
    # 4) 知乎加权 top（权重最大 3 位观点首句）
    zh = data.get("zhihu", {})
    acts = [a for a in zh.get("accounts", []) if a.get("items")]
    if acts:
        top = sorted(acts, key=lambda a: -(a.get("weight") or 1))[:3]
        t = "；".join("(%s)%s" % (a["name"].split("（")[0][:8], a["items"][0]["text"][:28]) for a in top)
        out.append("【大V】" + t)
    # 5) 降级提醒
    warns = [w for w in (data.get("warnings") or []) if "人工" in w or "降级" in w]
    for w in warns[:2]:
        out.append("【注意】" + w[:40])
    text = "\n".join(out)
    if len(text) > limit:
        text = text[:limit].rsplit("\n", 1)[0]
    return text + "\n\n（详细版 HTML 见下一条文件消息）"


def render_md(data):
    date, ts = data["date"], data["ts"]
    lines = [HEADER.format(date=date, ts=ts)]

    # 1) 盘面锚定
    lines.append("## 盘面锚定（腾讯行情）\n")
    for it in data["tencent"]:
        pct = it["chg_pct"] or "0.00"
        try:
            arrow = "▲" if float(pct) > 0 else ("▼" if float(pct) < 0 else "—")
        except ValueError:
            arrow = "—"
        amt = _fmt_amount(it.get("amount"))
        lines.append("- {name} {price} {arrow}{chg_pct}% ({amt})".format(
            name=it["name"], price=it["price"], arrow=arrow,
            chg_pct=it["chg_pct"], amt=amt))

    # 2) 特殊提醒
    warns = data.get("warnings", [])
    if warns:
        lines.append("\n## ⚠️ 特殊提醒\n")
        for w in warns:
            lines.append("- {0}".format(w))

    # 3) 同花顺新闻
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
    lines.append("\n> 4位同花顺大V主页为JS SPA，线上无法抓取，需人工每日WebFetch补录观点。")

    # 4) 券商6家研报
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

    # 5) 雪球 10 源
    lines.append("\n## 雪球 10 源观点\n")
    xq = data.get("xueqiu", {})
    for a in xq.get("accounts", []):
        if a["items"]:
            lines.append("- **{name}（w{weight}）**：{first}".format(
                name=a["name"], weight=a["weight"], first=a["items"][0]["text"][:90]))
            for it in a["items"][1:3]:
                lines.append("    · {0}".format(it["text"][:70]))
        else:
            lines.append("- **{name}**：{status} {msg}".format(
                name=a["name"], status=a["status"], msg=a.get("msg", "")))
    if xq.get("waf") or xq.get("login_expired"):
        lines.append("\n> {0}".format(xq.get("note", "")))

    # 6) 知乎 21 源（加权）
    lines.append("\n## 知乎 21 源观点（加权）\n")
    zh = data.get("zhihu", {})
    act = [a for a in zh.get("accounts", []) if a["items"]]
    if act:
        views = []
        for a in sorted(act, key=lambda x: -x["weight"]):
            lines.append("- **{name}（w{weight}）**：{first}".format(
                name=a["name"], weight=a["weight"], first=a["items"][0]["text"][:90]))
            for it in a["items"][1:3]:
                lines.append("    · {0}".format(it["text"][:70]))
            views.append({"name": a["name"], "weight": a["weight"]})
        total_w = sum(v["weight"] for v in views)
        lines.append("\n> 有观点 {n} 人，欢迎访问来源权重 ΣW={w}（维度未自动判向，共识收敛见 raw）".format(
            n=len(views), w=total_w))
    else:
        for a in zh.get("accounts", []):
            lines.append("- **{name}**：{status} {msg}".format(
                name=a["name"], status=a["status"], msg=a.get("msg", "")))
        lines.append("\n> 知乎源本次无观点（cookie 缺失/失效）")
    if zh.get("note"):
        lines.append("\n> {0}".format(zh["note"]))

    lines.append("\n---\n> Actions 自动生成，记录归档见 Artifact。")
    return "\n".join(lines)


def render_html(md_text, date):
    css = (
        "body{font-family:'PingFang SC','Microsoft YaHei',system-ui,sans-serif;color:#e6e6ff;"
        "background:#0f1420;margin:0;padding:2rem;line-height:1.7}"
        "h1,h2{color:#7aa2ff}h1{font-size:1.6rem;border-bottom:1px solid #2a3450;padding-bottom:.5rem}"
        "h2{margin-top:1.8rem;font-size:1.2rem;border-left:4px solid #4b6cff;padding-left:.6rem}"
        "h3{color:#9db4ff}blockquote{color:#8a93ad;border-left:3px solid #3a4460;margin-left:0;padding-left:1rem}"
        "strong{color:#ffd166}a{color:#6fd3ff}div.li,.li2{padding:.15rem 0}"
    )
    body = htmlmod.escape(md_text).replace("\n", "<br>")
    body = _md_light(body)
    return ("<!doctype html><html lang='zh'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>{date} 财经观点统计</title><style>{css}</style></head>"
            "<body>{body}</body></html>").format(date=date, css=css, body=body)


def _md_light(escaped):
    # 极简 md→html：标题/列表/加粗（用之前的转义文本处理）
    lines = escaped.split("<br>")
    out = []
    for ln in lines:
        if ln.startswith("### "):
            out.append("<h3>%s</h3>" % ln[4:])
        elif ln.startswith("## "):
            out.append("<h2>%s</h2>" % ln[3:])
        elif ln.startswith("# "):
            out.append("<h1>%s</h1>" % ln[2:])
        elif ln.startswith("  - "):
            out.append("<div class='li2'>%s</div>" % ln[4:])
        elif ln.startswith("- "):
            out.append("<div class='li'>%s</div>" % ln[2:])
        elif not ln:
            out.append("")
        else:
            out.append("<p>%s</p>" % ln)
    return "\n".join(out)


if __name__ == "__main__":
    d = {"date": "2026-09-10", "ts": "15:30", "tencent": [],
         "ths": [], "brokers": [], "xueqiu": {"accounts": []}, "warnings": []}
    print(render_md(d))