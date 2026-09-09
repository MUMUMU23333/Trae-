# -*- coding: utf-8 -*-
"""fetch_broker.py — 券商 6 家当日研报（东财 reportapi，公开无头可跑）。
按 brokers.json 的 orgSName 模糊匹配当日研报。
"""
import json
import os
import ssl
from datetime import datetime
from urllib.request import Request, urlopen

from libs import common

BROKERS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources", "brokers.json")


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _fetch_reports(begin, end, page=1, size=60):
    url = ("https://reportapi.eastmoney.com/report/list?industryCode=*"
           "&pageSize=%d&pageNo=%d&qType=1&beginTime=%s&endTime=%s"
           % (size, page, begin, end))
    h = {"Referer": "https://data.eastmoney.com/report/"}
    raw = common.retry_get(url, headers=h)
    return (json.loads(raw).get("data") or []), (json.loads(raw).get("TotalPage") or 1)


def fetch(target=None):
    target = target or _today()
    brokers = json.load(open(BROKERS_PATH, encoding="utf-8")).get("brokers", [])
    # 先按当日拉列表，扫完总页
    reports = []
    pn, total = 1, 1
    # 若当日无研报（清晨未出），回退到最近 2 日，避免空表
    begin = target
    first, _ = _fetch_reports(begin, target)
    if not first:
        now = datetime.now()
        begin = (now.replace(day=now.day - 3)).strftime("%Y-%m-%d") if now.day > 3 else "2026-01-01"
    while pn <= total and pn <= 8:
        batch, total = _fetch_reports(begin, target, pn)
        if not batch:
            break
        reports.extend(batch)
        pn += 1
    # 按机构名模糊分组
    grouped = {}
    for b in brokers:
        grouped[b["name"]] = []
    for r in reports:
        org = (r.get("orgSName") or "")
        for b in brokers:
            if org and (b["orgSName"] in org or org in b["orgSName"]):
                grouped[b["name"]].append({
                    "title": r.get("title", ""),
                    "time": (r.get("publishDate") or "")[:16],
                })
                break
    return [{"name": k, "orgSName": v.get("orgSName"), "reports": grouped[k]}
            for k, v in ((b["name"], b) for b in brokers)]


if __name__ == "__main__":
    common.enable_utf8()
    for it in fetch():
        print("== %s 共%d篇 ==" % (it["name"], len(it["reports"])))
        for r in it["reports"][:3]:
            print("   ", r["time"], "|", r["title"][:40])