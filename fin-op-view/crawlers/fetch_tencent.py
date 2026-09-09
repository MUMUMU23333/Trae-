# -*- coding: utf-8 -*-
"""fetch_tencent.py — 盘面行情（腾讯 qt.gtimg.cn，GBK，免费公开无头可跑）。
输出结构化列表：[{"name","code","price","chg","chg_pct","amount","vol_gbk"}]
"""
import re
from libs import common

INDICES = [
    ("s_sh000001", "上证指数"),
    ("s_sz399001", "深证成指"),
    ("s_sz399006", "创业板指"),
    ("s_sh000300", "沪深300"),
]


def fetch():
    q = ",".join(k for k, _ in INDICES)
    url = "https://qt.gtimg.cn/q=%s" % q
    raw = common.http_get(url, raw_bytes=True).decode("gbk", "ignore")
    out = []
    for line in raw.split(";"):
        if "=" not in line:
            continue
        key, rest = line.split("=", 1)
        key = key.split("v_")[-1].strip()
        m = re.search(r'"(.*)"', rest)
        if not m:
            continue
        f = m.group(1).split("~")
        if len(f) < 6:
            continue
        name = f[1]
        price = f[3]
        chg = f[4]
        chg_pct = f[5]
        amount = f[7] if len(f) > 7 else ""  # 成交额(万元)
        out.append({
            "name": name, "code": key, "price": price,
            "chg": chg, "chg_pct": chg_pct, "amount": amount,
        })
    return out


if __name__ == "__main__":
    common.enable_utf8()
    for it in fetch():
        print(it["name"], it["price"], it["chg"], it["chg_pct"], it["amount"])