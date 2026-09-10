# -*- coding: utf-8 -*-
"""fetch_ths_bigv.py — 同花顺 4 位大V主页观点抓取。

通道: 优先走 userPost API (https://t.10jqka.com.cn/newcircle/user/userPost/)
+ curl_cffi Chrome 指纹，无 WAF、无需登录，标题/摘要/时间全在返回 posthtml 里。
已验证: 张明辉(9936457) 正常返回最新帖子。
备注: 全能的野人(639669238)/纳指水蛭(661387218)/我的人生如股票(295155932)
的 userPost 为空——内容发布在"股吧话题流"(Vue SPA 无 SSR)，线上无法直抓，
需本地 CDP 渲染补录（见 xq_cdp_fetch.py 同思路的 cdp 版本）。
"""
import json
import os
import re
import sys
import time
from datetime import datetime

try:
    from curl_cffi import requests as _creq
    HAS_CURL = True
except ImportError:
    HAS_CURL = False
from urllib.request import Request, urlopen

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES_PATH = os.path.join(BASE, "sources", "ths_bigv.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36")

# 帖子块: li.ucwlist-all.post-single ...（userPost 返回的 posthtml 结构）
BLOCK_RE = re.compile(
    r'<li class="ucwlist-all post-single[^"]*"[^>]*>.*?</li>', re.S)
TITLE_RE = re.compile(r'ucwlist-fd-title[^>]*>\s*<a[^>]*>([^<]{2,120})</a>', re.S)
DETAIL_RE = re.compile(r'<div class="ucwlist-fd-detail">(.*?)</div>', re.S)
TIME_RE = re.compile(r'ucwlist-fd-time[^>]*>([^<]{1,12})</a>', re.S)
PID_RE = re.compile(r'href="https://t\.10jqka\.com\.cn/pid_(\d+)\.shtml"')


def _clean(t):
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"\s+", " ", t).strip()


def fetch_profile(uid, limit=8):
    """抓单一大V userPost，返回观点列表 [{time,title,text,pid}]。"""
    url = ("https://t.10jqka.com.cn/newcircle/user/userPost/?first=1&userid=%s" % uid)
    headers = dict(
        {"X-Requested-With": "XMLHttpRequest"},
        Referer="https://t.10jqka.com.cn/%s/" % uid)
    if HAS_CURL:
        r = _creq.get(url, impersonate="chrome", timeout=15, headers=headers)
        html = r.json().get("result", {}).get("posthtml", "")
    else:
        req = Request(url, headers={"User-Agent": UA, "X-Requested-With": "XMLHttpRequest",
                                    "Referer": "https://t.10jqka.com.cn/%s/" % uid})
        html = json.loads(urlopen(req, timeout=15).read().decode("utf-8", "ignore")) \
            .get("result", {}).get("posthtml", "")
    items = []
    for blk in BLOCK_RE.findall(html):
        m = TITLE_RE.search(blk)
        if not m:
            continue
        title = m.group(1).strip()
        if len(title) < 2:
            continue
        d = DETAIL_RE.search(blk)
        text = _clean(d.group(1)) if d else ""
        tm = TIME_RE.search(blk)
        t = tm.group(1).strip() if tm else ""
        p = PID_RE.search(blk)
        items.append({"time": t, "title": title,
                      "text": text[:300], "pid": p.group(1) if p else ""})
        if len(items) >= limit:
            break
    return items


def fetch(accounts=None):
    if accounts is None:
        accounts = json.load(open(SOURCES_PATH, encoding="utf-8")).get("accounts", [])
    result = {"accounts": [], "note": ""}
    for a in accounts:
        entry = {"name": a["name"], "uid": a["uid"], "weight": a.get("weight", 1),
                 "status": "ok", "items": [], "msg": ""}
        try:
            items = fetch_profile(a["uid"])
            if not items:
                entry["status"] = "empty"
                entry["msg"] = "主页无解析出帖子（改版？）"
            else:
                entry["items"] = items
        except Exception as e:
            entry["status"] = "error"
            entry["msg"] = str(e)[:120]
        result["accounts"].append(entry)
        time.sleep(0.8)
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    r = fetch()
    for a in r["accounts"]:
        print("==", a["name"], a["uid"], a["status"], a["msg"], "| 条数:", len(a["items"]))
        for it in a["items"][:4]:
            print("   ", it["time"], "|", it["title"][:40])
