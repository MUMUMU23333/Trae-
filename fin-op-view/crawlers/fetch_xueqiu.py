# -*- coding: utf-8 -*-
"""fetch_xueqiu.py — 雪球 10 源。
带 XUEQIU_COOKIE 直连 status API；WAF→降级标注需人工。
Cookie 失效/缺失不中断整条管线。
"""
import json
import os
from libs import common

SOURCES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sources", "xueqiu.json")


def _api_url(uid, page=1, count=10, max_id=None):
    base = "https://xueqiu.com/v4/statuses/user_timeline.json?user_id=%s&page=%d&count=%d" % (uid, page, count)
    return base


def fetch(cookie=None):
    cookie = cookie if cookie is not None else common.get_cookie("XUEQIU_COOKIE")
    accounts = json.load(open(SOURCES_PATH, encoding="utf-8")).get("accounts", [])
    result = {"accounts": [], "waf": False, "login_expired": False, "note": ""}
    headers = {}
    if cookie:
        headers["Cookie"] = cookie
    for a in accounts:
        entry = {"name": a["name"], "uid": a["uid"], "weight": a.get("weight", 1),
                 "status": "ok", "items": [], "msg": ""}
        try:
            raw = common.retry_get(_api_url(a["uid"]), tries=2, headers=headers,
                                   timeout=20, sleep=1.5)
        except Exception as e:
            entry["status"] = "error"
            entry["msg"] = str(e)[:120]
            result["accounts"].append(entry)
            continue
        if common.is_waf_page(raw):
            result["waf"] = True
            entry["status"] = "waf"
            entry["msg"] = "被阿里云WAF拦截，需人工WebFetch"
            result["accounts"].append(entry)
            continue
        try:
            data = json.loads(raw)
        except Exception:
            entry["status"] = "html"
            entry["msg"] = "非JSON（可能登录墙/风控），需人工"
            result["accounts"].append(entry)
            continue
        if not data.get("data") or not isinstance(data.get("data").get("list"), list):
            entry["status"] = "expired"
            entry["msg"] = "接口返回空/登录态失效"
            result["login_expired"] = True
            result["accounts"].append(entry)
            continue
        for st in data["data"]["list"][:5]:
            txt = (st.get("text") or st.get("title") or "").strip()
            txt = common_clean(txt)
            if txt:
                entry["items"].append({"time": (st.get("created_at") or "")[:16], "text": txt[:300]})
        result["accounts"].append(entry)
    if result["waf"] or result["login_expired"]:
        result["note"] = "部分源登录态失效，需本地重刷 XUEQIU_COOKIE Secret（Actions 无法扫码）"
    return result


def common_clean(t):
    import re
    t = re.sub(r"<[^>]+>", "", t)
    return t.replace("\n", " ").strip()


if __name__ == "__main__":
    common.enable_utf8()
    r = fetch()
    for a in r["accounts"]:
        print(a["name"], a["status"], len(a["items"]), a["msg"])
    print("note:", r["note"])