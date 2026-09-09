# -*- coding: utf-8 -*-
"""common.py — 统一 HTTP / cookie / 失效探测工具（fin-op-view 只跑 GitHub Actions ubuntu）。
纯 stdlib，无三方依赖。"""
import json
import os
import re
import ssl
import sys
import time
from urllib.request import Request, urlopen

ssl._create_default_https_context = ssl._create_unverified_context

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"


def enable_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_cookie(name):
    """从 env 读 cookie（GitHub Secret + 本地 .env 均可）。"""
    return os.environ.get(name, "").strip()


def http_get(url, headers=None, timeout=20, raw_bytes=False):
    """GET，自动补 UA。返回 str 或 bytes。"""
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = Request(url, headers=h)
    data = urlopen(req, timeout=timeout).read()
    return data if raw_bytes else data.decode("utf-8", "ignore")


def http_post_json(url, payload, headers=None, timeout=20):
    h = {"Content-Type": "application/json", "User-Agent": UA}
    if headers:
        h.update(headers)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=body, headers=h, method="POST")
    with urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "ignore")


def is_waf_page(html):
    """阿里云 WAF 反爬标记检测。"""
    return ("aliyun_waf" in html) or ("verify.baidu" in html) or (re.search(r"<textarea[^>]*renderData", html) and "aliyun_waf_aa" in html)


def retry_get(url, tries=3, headers=None, timeout=20, sleep=1.5, raw_bytes=False):
    last = None
    for i in range(tries):
        try:
            return http_get(url, headers=headers, timeout=timeout, raw_bytes=raw_bytes)
        except Exception as e:
            last = e
            time.sleep(sleep)
    raise RuntimeError("GET failed after %d tries: %s" % (tries, last))


def tag_status(status):
    return {"status": status, "data": None, "msg": ""}