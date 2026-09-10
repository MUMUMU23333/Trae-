# -*- coding: utf-8 -*-
"""insight.py — 大V观点归纳引擎（纯规则，无 LLM key，GitHub Actions 可跑）。

把知乎/雪球大V的碎片化原文，归纳为：
  - 每条观点: 一句话要点(截断+话题标签) + 板块归属 + 方向(多/空/中性)
  - 板块共识: 用 weights.consensus_converge 聚合板块看多/看空人数与ΣW
  - 当日总览: 一句结论(共识最强板块 + 人数 + 拥挤度)

板块/方向词表集中在下方常量，调优只需改此文件，无需动抓取。
"""
import re

# 板块关键词（顺序优先，命中即归属）
SECTORS = [
    ("有色/黄金", ["有色", "黄金", "铜", "金", "稀土", "铝", "锂", "钴", "贵金属", "金属", "矿业"]),
    ("半导体", ["半导体", "芯片", "晶圆", "光刻", "存储", "先进封装", "算力芯片", "PCB"]),
    ("AI/算力", ["AI", "算力", "大模型", "GPU", "英伟达", "人工智能", "机器人", "具身智能"]),
    ("通信/光模块", ["光模块", "光通信", "CPO", "通信", "5G", "光纤"]),
    ("新能源/电车", ["新能源", "电车", "锂电", "光伏", "储能", "宁德", "比亚迪", "特斯拉", "充电"]),
    ("消费", ["消费", "白酒", "食品", "零售", "家电", "免税", "医药商业"]),
    ("医药/CRO", ["医药", "CRO", "创新药", "CXO", "生物医药", "疫苗", "药明"]),
    ("银行/红利", ["银行", "红利", "高股息", "中特估", "股息"]),
    ("券商/金融", ["券商", "证券", "保险", "金融", "多元金融"]),
    ("军工/低空", ["军工", "低空", "航空", "航天", "无人机", "商业航天"]),
    ("出海/全球化", ["出海", "全球化", "出口", "海外营收", "一带一路", "跨境"]),
    ("创业板/成长", ["创业板", "科创50", "科创100", "双创", "成长股", "微盘", "中证1000"]),
    ("煤炭/能源", ["煤炭", "石油", "能源", "油气", "电力", "天然气"]),
    ("房地产", ["房地产", "地产", "楼市", "城中村"]),
]

# 看多/看空/中性词表
BULL_WORDS = ["看好", "看多", "加仓", "买入", "上涨", "主升", "机会", "持有", "增持", "突破",
              "反弹", "利好", "加速", "走强", "新高", "低估", "底部", "补涨", "进攻", "乐观",
              "硬逻辑", "坚定", "荣辱与共", "不换头像"]
BEAR_WORDS = ["看空", "看跌", "减仓", "卖出", "下跌", "风险", "谨慎", "回避", "谨慎", "崩",
              "回调", "利空", "杀跌", "走弱", "破位", "高估", "顶部", "逃顶", "防守", "悲观",
              "风险出清", "不负责", "不追高", "注意", "担心"]
NEUTRAL_WORDS = ["观察", "观望", "中性", "震荡", "横盘", "持有不动", "等待", "研究", "学习",
                 "复盘", "梳理", "记录", "准备", "思考"]

# weights.json 的 exclude 词（观点属闲聊/无方向时跳过）
EXCLUDE_WORDS = ["不追高", "减仓", "持有不动", "观望", "无更新"]


def classify(text):
    """返回 (sector, direction)。direction ∈ bull/bear/neutral。"""
    if not text:
        return "大盘", "neutral"
    sector = "大盘"
    for name, kws in SECTORS:
        for kw in kws:
            if kw in text:
                sector = name
                break
        if sector != "大盘":
            break
    bull = sum(1 for w in BULL_WORDS if w in text)
    bear = sum(1 for w in BEAR_WORDS if w in text)
    if any(w in text for w in EXCLUDE_WORDS):
        return sector, "neutral"
    if bull > bear:
        return sector, "bull"
    if bear > bull:
        return sector, "bear"
    return sector, "neutral"


def summarize_text(text, maxlen=42):
    """观点一句话要点：去首部无意义词 + 截断。"""
    if not text:
        return ""
    t = re.sub(r"\s+", " ", text).strip()
    # 去掉开头常见口水词
    t = re.sub(r"^(今天|昨日|最近|上周|复盘|简单|其实|我|我们|反正|毕竟|然后|那)\s*", "", t)
    if len(t) > maxlen:
        t = t[:maxlen] + "…"
    return t


def build_views(accounts):
    """accounts: [{'name','weight','items':[{'text','time'}]}]
    返回: [{name, weight, sector, direction, point, time}] 仅保留有观点者。"""
    views = []
    for a in accounts:
        items = [it for it in (a.get("items") or []) if it.get("text")]
        if not items:
            continue
        # 取最新一条（items 按时间升序，取最后一条）
        latest = items[-1]
        text = latest.get("text") or ""
        sector, direction = classify(text)
        views.append({
            "name": a["name"],
            "weight": a.get("weight") or 1,
            "sector": sector,
            "direction": direction,
            "point": summarize_text(text),
            "time": latest.get("time", ""),
        })
    return views


def build_overview(views, zhihu_note=""):
    """当日共识总览：按板块聚合 → 最多人看多板块 + 拥挤度 + 一句话结论。"""
    from libs import weights

    by_sector = {}
    for v in views:
        if v["direction"] == "neutral":
            continue
        sec = v["sector"]
        s = by_sector.setdefault(sec, {"bull": [], "bear": []})
        (s["bull"] if v["direction"] == "bull" else s["bear"]).append(v)

    rows = []
    for sec, s in sorted(by_sector.items(), key=lambda kv: -(
            sum(v["weight"] for v in kv[1]["bull"]) + sum(v["weight"] for v in kv[1]["bear"]))):
        bull_w = sum(v["weight"] for v in s["bull"])
        bear_w = sum(v["weight"] for v in s["bear"])
        bull_n, bear_n = len(s["bull"]), len(s["bear"])
        side = "看多" if bull_w >= bear_w else "看空"
        rows.append({
            "sector": sec, "bull_n": bull_n, "bear_n": bear_n,
            "bull_w": bull_w, "bear_w": bear_w, "side": side,
            "names": [v["name"].split("（")[0] for v in (s["bull"] if bull_w >= bear_w else s["bear"])],
        })

    # 一句话结论
    conclusion = ""
    if rows:
        top = rows[0]
        n = top["bull_n"] + top["bear_n"]
        if top["bull_n"] >= 3 and top["side"] == "看多":
            conclusion = "共识最强：**{sector}** {n}人看多（ΣW={w}），方向偏多。".format(
                sector=top["sector"], n=top["bull_n"], w=top["bull_w"])
        elif top["bear_n"] >= 3 and top["side"] == "看空":
            conclusion = "共识最强：**{sector}** {n}人看空（ΣW={w}），方向偏空。".format(
                sector=top["sector"], n=top["bear_n"], w=top["bear_w"])
        elif n >= 3:
            conclusion = "共识较强：**{sector}** {n}人参与（ΣW={w}），{side}略占优。".format(
                sector=top["sector"], n=n, w=max(top["bull_w"], top["bear_w"]), side=top["side"])
        else:
            conclusion = "观点分散，暂无板块强共识，以观望为主。"
        if top["bull_n"] + top["bear_n"] >= 5 or max(top["bull_w"], top["bear_w"]) >= 15:
            conclusion += " ⚠️注意拥挤，过热方向勿追高。"
    else:
        conclusion = "当日大V多为中性/闲聊观点，无明确方向信号。"

    return {"rows": rows, "conclusion": conclusion, "total": len(views)}


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # 自测
    assert classify("看好有色黄金")[0] == "有色/黄金" and classify("看好有色黄金")[1] == "bull"
    assert classify("半导体注意回调风险")[0] == "半导体" and classify("半导体注意回调风险")[1] == "bear"
    assert classify("今天复盘一下学习记录")[1] == "neutral"
    print("classify: OK")
    v = build_views([{"name": "a（x）", "weight": 3, "items": [
        {"text": "看好有色黄金铜，主升不换头像", "time": "2026-09-10 08:00"}]}])
    assert v[0]["sector"] == "有色/黄金" and v[0]["direction"] == "bull"
    print("build_views: OK")
    print("overview:", build_overview(v, "")["conclusion"])
