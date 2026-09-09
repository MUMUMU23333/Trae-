# -*- coding: utf-8 -*-
"""fetch_ths.py — 同花顺新闻（公开 API，按日过滤当日新闻，无头可跑）。
4 位同花顺大V（全能的野人/张明辉/纳指水蛭/我的人生如股票）主页是 JS SPA，
ABC 线上无头环境抓不到，故本节用同花顺新闻 API 反映当日市场热度，
并在成品标"需人工每日 WebFetch 补录大V观点"。
"""
import json
import re
from datetime import datetime
from libs import common

PAGES = 4  # 每页 30 条，共 ~120 条当日新闻


def _ts2day(s):
    """同花顺 ctime/rtime 是 Unix 秒时间戳 → 归一为 YYYYMMDD。非纯数字返回 ''。"""
    if not s:
        return ""
    digits = re.sub(r"\D", "", s)
    if not digits:
        return ""
    try:
        return datetime.fromtimestamp(int(digits)).strftime("%Y%m%d")
    except Exception:
        return ""


def fetch(target=None):
    ref = {"Referer": "https://news.10jqka.com.cn/"}
    items = []
    for page in range(1, PAGES + 1):
        url = ("https://news.10jqka.com.cn/tapp/news/push/stock/"
               "?page=%d&tag=&track=website&pagesize=30" % page)
        try:
            raw = common.retry_get(url, headers=ref)
            data = json.loads(raw).get("data", {}).get("list", [])
        except Exception:
            continue
        items.extend(data)
        common_rs = len(items) > 90  # 已够当日，提前停
        if common_rs:
            break
    target = target or datetime.now().strftime("%Y%m%d")

    tod = [x for x in items if _ts2day(x.get("ctime")) == target or _ts2day(x.get("rtime")) == target]
    dedup, seen = [], set()
    for x in tod:
        if x.get("title") in seen:
            continue
        seen.add(x.get("title"))
        dedup.append({
            "title": x.get("title", ""),
            "digest": (x.get("digest") or "")[:300],
            "time": _ts2day(x.get("ctime")),
            "url": x.get("url", ""),
        })
    return dedup


if __name__ == "__main__":
    common.enable_utf8()
    for it in fetch():
        print(it["time"][:16], "|", it["title"])