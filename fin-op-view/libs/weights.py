# -*- coding: utf-8 -*-
"""weights.py — 权重系统（仅读 fin-op-view/sources/weights.json，唯一权威）。
提供：
  weight_of(name)         账户权重（主名 + 前缀回退）
  hits_of(name)           历史命中(hits)
  consensus_converge(views)  多空共识收敛（ΣW 置信度 / 拥挤标记）
升级 weights.json 即自动生效，勿在此硬编码权重。
"""
import json
import os

_WEIGHTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "sources", "weights.json")


def _load():
    try:
        data = json.load(open(_WEIGHTS_PATH, encoding="utf-8"))
    except Exception:
        return {}, {}
    return data.get("accounts") or {}, data.get("consensus_rule") or {}


def weight_of(name):
    """账户权重。name 可能带括号后缀(如「启四（zhang-kuo-ye）」)或别名(「航哥分红退休之路」→「航哥」)。"""
    wt, _ = _load()
    base = name.split("（")[0].split("(")[0]
    if base in wt:
        return int(wt[base].get("weight", 1))
    # 前缀回退：别名>=2字避免误配
    for k, v in wt.items():
        if len(k) >= 2 and base.startswith(k):
            return int(v.get("weight", 1))
    return 1


def hits_of(name):
    """历史命中次数，默认 0。"""
    wt, _ = _load()
    base = name.split("（")[0].split("(")[0]
    if base in wt:
        return int(wt[base].get("hits", 0) or 0)
    for k, v in wt.items():
        if len(k) >= 2 and base.startswith(k):
            return int(v.get("hits", 0) or 0)
    return 0


def consensus_converge(views):
    """多空共识收敛。
    views: [{"name","weight","direction","sector"}]，direction ∈ bull/bear/neutral。
    返回 dict：bull_w、bear_w、bull_n、bear_n、confidence（high/mid/low）、crowded(bool)、结论句。
    """
    rule = _load()[1]
    bull_w = sum(v["weight"] for v in views if v["direction"] == "bull")
    bear_w = sum(v["weight"] for v in views if v["direction"] == "bear")
    bull_n = sum(1 for v in views if v["direction"] == "bull")
    bear_n = sum(1 for v in views if v["direction"] == "bear")

    # 方向聚类：按 sector 聚合
    sectors = {}
    for v in views:
        if v["direction"] == "neutral":
            continue
        sec = v.get("sector") or "大盘"
        s = sectors.setdefault(sec, {"bull_w": 0, "bear_w": 0, "bull_n": 0, "bear_n": 0})
        s["bull_w" if v["direction"] == "bull" else "bear_w"] += v["weight"]
        s["bull_n" if v["direction"] == "bull" else "bear_n"] += 1

    hot = []
    for sec, s in sectors.items():
        if s["bull_n"] + s["bear_n"] >= 3:
            side = "看多" if s["bull_w"] > s["bear_w"] else "看空"
            hot.append("%s: %d人%s(ΣW=%.0f)" % (sec, s["bull_n"] + s["bear_n"], side,
                                                max(s["bull_w"], s["bear_w"])))
    # 拥挤门槛：单方向参与>=5 或 ΣW>=15
    crowded = max(bull_n, bear_n) >= 5 or max(bull_w, bear_w) >= 15

    # 置信度：多方ΣW >= 空方ΣW×1.5 高；1.0~1.5 中；否则低
    if bull_w >= bear_w * 1.5:
        conf, side = "high", "多方占优"
    elif bull_w >= bear_w:
        conf, side = "mid", "多方略优"
    else:
        conf, side = "low", "空方占优"

    line = "多: ΣW=%.0f(%d人) / 空: ΣW=%.0f(%d人) → %s（置信度:%s）" % (
        bull_w, bull_n, bear_w, bear_n, side, conf)
    if hot:
        line += " | 板块共识: " + "；".join(hot)
    if crowded:
        line += " | ⚠️拥挤，过热方向勿追"
    return {"bull_w": bull_w, "bear_w": bear_w, "bull_n": bull_n, "bear_n": bear_n,
            "confidence": conf, "crowded": crowded, "summary": line}


if __name__ == "__main__":
    # 自测
    assert weight_of("启四（zhang-kuo-ye）") == 2, weight_of("启四（zhang-kuo-ye）")
    assert weight_of("航哥分红退休之路") == 2, weight_of("航哥分红退休之路")
    assert weight_of("龙头18868") == 3
    assert weight_of("不存在的人") == 1
    print("weight_of: OK")
    r = consensus_converge([
        {"name": "a", "weight": 3, "direction": "bull", "sector": "有色"},
        {"name": "b", "weight": 3, "direction": "bull", "sector": "有色"},
        {"name": "c", "weight": 3, "direction": "bull", "sector": "有色"},
        {"name": "d", "weight": 2, "direction": "bear", "sector": "另类"},
    ])
    print(r["summary"])
    assert r["crowded"]
    print("consensus_converge: OK")