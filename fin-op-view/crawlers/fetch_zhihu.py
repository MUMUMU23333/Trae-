# -*- coding: utf-8 -*-
"""fetch_zhihu.py — 知乎 21 源。
用 x-zse-96 v3 签名直连 moments 接口。Cookie 从 ZHIHU_COOKIE env 读（GitHub Secret）。
签名算法移植自 WorkBuddy zhihu_cookie_fetch.py（RSSHub x-zse-96 v3）。
Cookie 缺失/失效/签名变化 → 降级标注需人工，不中断整条管线。
"""
import hashlib
import json
import os
import re
import random
import time
from libs import common

SOURCES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "sources", "zhihu.json")
BASE_URL = "https://www.zhihu.com"

M32 = 0xFFFFFFFF
SALT = "6fpLRqJO8M/c3jnYxFkUVC4ZIG12SiH=5v0mXDazWBTsuw7QetbKdoPyAl+hN9rgE"

ZK = [1170614578, 1024848638, 1413669199, -343334464, -766094290, -1373058082, -143119608,
      -297228157, 1933479194, -971186181, -406453910, 460404854, -547427574, -1891326262,
      -1679095901, 2119585428, -2029270069, 2035090028, -1521520070, -5587175, -77751101,
      -2094365853, -1243052806, 1579901135, 1321810770, 456816404, -1391643889, -229302305,
      330002838, -788960546, 363569021, -1947871109]
ZB = [
      20, 223, 245, 7, 248, 2, 194, 209, 87, 6, 227, 253, 240, 128, 222, 91, 237, 9, 125, 157, 230, 93, 252, 205, 90, 79, 144, 199, 159, 197, 186, 167, 39, 37, 156, 198, 38, 42, 43, 168, 217, 153, 15, 103, 80, 189, 71, 191, 97, 84,
      247, 95, 36, 69, 14, 35, 12, 171, 28, 114, 178, 148, 86, 182, 32, 83, 158, 109, 22, 255, 94, 238, 151, 85, 77, 124, 254, 18, 4, 26, 123, 176, 232, 193, 131, 172, 143, 142, 150, 30, 10, 146, 162, 62, 224, 218, 196, 229, 1, 192,
      213, 27, 110, 56, 231, 180, 138, 107, 242, 187, 54, 120, 19, 44, 117, 228, 215, 203, 53, 239, 251, 127, 81, 11, 133, 96, 204, 132, 41, 115, 73, 55, 249, 147, 102, 48, 122, 145, 106, 118, 74, 190, 29, 16, 174, 5, 177, 129, 63, 113,
      99, 31, 161, 76, 246, 34, 211, 13, 60, 68, 207, 160, 65, 111, 82, 165, 67, 169, 225, 57, 112, 244, 155, 51, 236, 200, 233, 58, 61, 47, 100, 137, 185, 64, 17, 70, 234, 163, 219, 108, 170, 166, 59, 149, 52, 105, 24, 212, 78, 173,
      45, 0, 116, 226, 119, 136, 206, 135, 175, 195, 25, 92, 121, 208, 126, 139, 3, 75, 141, 21, 130, 98, 241, 40, 154, 66, 184, 49, 181, 46, 243, 88, 101, 183, 8, 23, 72, 188, 104, 179, 210, 134, 250, 201, 164, 89, 216, 202, 220, 50,
      221, 152, 140, 33, 235, 214
]


def _put_int(e, t, n):
    t[n] = 255 & (e >> 24)
    t[n + 1] = 255 & (e >> 16)
    t[n + 2] = 255 & (e >> 8)
    t[n + 3] = 255 & e


def _get_int(e, t):
    return ((255 & int(e[t])) << 24 | (255 & int(e[t + 1])) << 16
            | (255 & int(e[t + 2])) << 8 | (255 & int(e[t + 3]))) & M32


def _rol(e, t):
    return ((e << t) | (e >> (32 - t))) & M32


def _g_func(e):
    e &= M32
    t = [0, 0, 0, 0]
    _put_int(e, t, 0)
    n = [ZB[255 & t[0]], ZB[255 & t[1]], ZB[255 & t[2]], ZB[255 & t[3]]]
    r = _get_int(n, 0)
    return (r ^ _rol(r, 2) ^ _rol(r, 10) ^ _rol(r, 18) ^ _rol(r, 24)) & M32


def _block_r(e):
    t = [0] * 16
    n = [0] * 36
    n[0] = _get_int(e, 0)
    n[1] = _get_int(e, 4)
    n[2] = _get_int(e, 8)
    n[3] = _get_int(e, 12)
    for r in range(32):
        o = _g_func(n[r + 1] ^ n[r + 2] ^ n[r + 3] ^ (ZK[r] & M32))
        n[r + 4] = (n[r] ^ o) & M32
    _put_int(n[35], t, 0)
    _put_int(n[34], t, 4)
    _put_int(n[33], t, 8)
    _put_int(n[32], t, 12)
    return t


def _block_x(e, t):
    n = []
    r = len(e)
    i = 0
    while r > 0:
        a = [0] * 16
        for c in range(16):
            a[c] = e[16 * i + c] ^ t[c]
        t = _block_r(a)
        n.extend(t)
        i += 1
        r -= 16
    return n


def _pre_process(md5_str):
    arr = [ord(ch) for ch in md5_str]
    arr.insert(0, 0)
    arr.insert(0, int(random.random() * 127))
    arr.extend([14] * 15)
    front = arr[:16]
    fix = [48, 53, 57, 48, 53, 51, 102, 55, 100, 49, 53, 101, 48, 49, 100, 55]
    new_front = [front[i] ^ fix[i] ^ 42 for i in range(16)]
    g_r = _block_r(new_front)
    return g_r + _block_x(arr[16:48], g_r)


def _enc64(param):
    return "".join(SALT[(param >> x) & 63] for x in [0, 6, 12, 18])


def _encrypt(md5_str):
    processed = _pre_process(md5_str)
    current = 0
    result = ""
    n = len(processed)
    for i in range(n):
        pop = processed[n - i - 1]
        c = (58 >> (8 * (i % 4))) & 255
        current = (current | ((pop ^ c) << (8 * (i % 3)))) & M32
        if i % 3 == 2:
            result += _enc64(current)
            current = 0
    return result


def _sign(api_path, dc0):
    f = "101_3_3.0+" + api_path + "+" + dc0
    return "2.0_" + _encrypt(hashlib.md5(f.encode()).hexdigest())


def _cookie_val(cookie, key):
    for part in cookie.split(";"):
        k, _, v = part.strip().partition("=")
        if k == key:
            return v
    return ""


def _strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    import html
    s = html.unescape(s)
    return s.strip()


def _target_text(t):
    typ = t.get("type")
    parts = []
    if typ == "pin":
        for item in t.get("content") or []:
            it = item.get("type")
            if it == "text" and item.get("own_text"):
                parts.append(_strip_html(item["own_text"]))
            elif it == "link":
                parts.append("[链接] " + (item.get("title") or ""))
            elif it == "video":
                parts.append("[视频]")
            elif it == "image":
                parts.append("[图片]")
        return "\n".join(parts)
    return _strip_html(t.get("excerpt") or t.get("content") or t.get("title") or "")


def _fetch_raw(cookie, uid, limit=10):
    dc0 = _cookie_val(cookie, "d_c0")
    if not dc0:
        raise RuntimeError("cookie 缺 d_c0")
    api_path = "/api/v3/moments/%s/activities?limit=%d&desktop=true&ws_qiangzhisafe=0" % (uid, limit)
    url = BASE_URL + api_path
    headers = {
        "User-Agent": common.UA,
        "Cookie": cookie,
        "Referer": BASE_URL + "/people/" + uid,
        "x-api-version": "3.0.91",
        "x-zse-93": "101_3_3.0",
        "x-zse-96": _sign(api_path, dc0),
        "x-app-za": "OS=Web",
        "x-requested-with": "fetch",
    }
    try:
        raw = common.retry_get(url, tries=2, headers=headers, timeout=25, sleep=1.5)
    except Exception as e:
        raise RuntimeError("请求失败: %s" % str(e)[:120])
    try:
        data = json.loads(raw)
    except Exception:
        raise RuntimeError("非JSON，大概率登录态失效/签名版本变化")
    if not data.get("data"):
        raise RuntimeError("data 为空，可能是 cookie 失效/签名问题")
    return data["data"]


def fetch(cookie=None):
    cookie = cookie if cookie is not None else common.get_cookie("ZHIHU_COOKIE")
    accounts = json.load(open(SOURCES_PATH, encoding="utf-8")).get("accounts", [])
    result = {"accounts": [], "login_expired": False, "note": ""}
    if not cookie:
        result["note"] = "未配置 ZHIHU_COOKIE env，全部降级需人工"
        for a in accounts:
            result["accounts"].append({
                "name": a["name"], "weight": 1, "status": "no_cookie",
                "items": [], "msg": "未配置 ZHIHU_COOKIE",
            })
        result["login_expired"] = True
        return result

    for a in accounts:
        entry = {"name": a["name"], "zhihu_id": a["zhihu_id"], "weight": 1,
                 "status": "ok", "items": [], "msg": ""}
        try:
            items = _fetch_raw(cookie, a["zhihu_id"], limit=8)
            for it in items:
                target = it.get("target") or {}
                ct = it.get("created_time") or 0
                try:
                    ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(ct))
                except Exception:
                    ts = str(ct)
                text = _target_text(target)
                if text:
                    entry["items"].append({"time": ts, "text": text[:300]})
            entry["weight"] = _weight_of_name(a["name"])
        except Exception as e:
            entry["status"] = "expired"
            entry["msg"] = str(e)[:120]
            result["login_expired"] = True
        result["accounts"].append(entry)
        time.sleep(0.5)
    if result["login_expired"]:
        result["note"] = ("部分源登录态失效/签名变化，需本地用 CDP 重刷 ZHIHU_COOKIE 并更新 GitHub Secret"
                          "（Actions 无法扫码登录知乎）")
    return result


def _weight_of_name(name):
    from libs import weights
    return weights.weight_of(name)


if __name__ == "__main__":
    common.enable_utf8()
    r = fetch()
    for a in r["accounts"]:
        print(a["name"], a["status"], "w%d" % a["weight"], len(a["items"]), a["msg"][:50])
    print("note:", r["note"])