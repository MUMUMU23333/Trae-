# -*- coding: utf-8 -*-
"""run.py — 统一入口：抓多源（盘面/同花顺/券商/雪球/知乎）→ 生成 md + HTML → 存 artifact → 推企微。
用法: python run.py            （正常跑，推企微）
      python run.py --no-push  （只出产物，不推）
      python run.py --date 2026-09-10  （指定日期，测试用）
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from libs import common
from libs import push_wecom
from libs import render
from crawlers import fetch_tencent, fetch_ths, fetch_broker, fetch_xueqiu, fetch_zhihu, fetch_ths_bigv


OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def main():
    common.enable_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--date", default=None)
    ap.add_argument("--warnings", default="")
    args = ap.parse_args()

    date = args.date or datetime.datetime.now().strftime("%Y-%m-%d")
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    print("== [1/5] 盘面行情（腾讯）==")
    try:
        tencent = fetch_tencent.fetch()
        print("   indices:", len(tencent))
    except Exception as e:
        tencent = []
        print("   FAIL", e)

    print("== [2/5] 同花顺新闻 ==")
    try:
        ths = fetch_ths.fetch()
        print("   items:", len(ths))
    except Exception as e:
        ths = []
        print("   FAIL", e)

    print("== [3/5] 券商 6 家研报 ==")
    try:
        brokers = fetch_broker.fetch()
        print("   broker groups:", len(brokers))
    except Exception as e:
        brokers = []
        print("   FAIL", e)

    print("== [4/4] 雪球 10 源 ==")
    try:
        xueqiu = fetch_xueqiu.fetch()
        n_ok = sum(1 for a in xueqiu.get("accounts", []) if a["items"])
        print("   accounts:", len(xueqiu.get("accounts", [])), "| 有观点:", n_ok,
              "| waf:", xueqiu.get("waf"), "| expired:", xueqiu.get("login_expired"))
    except Exception as e:
        xueqiu = {"accounts": [], "note": str(e)}
        print("   FAIL", e)

    print("== [5/6] 同花顺 4 位大V ==")
    try:
        ths_bigv = fetch_ths_bigv.fetch()
        n_ok = sum(1 for a in ths_bigv.get("accounts", []) if a["items"])
        print("   accounts:", len(ths_bigv.get("accounts", [])), "| 有观点:", n_ok)
    except Exception as e:
        ths_bigv = {"accounts": [], "note": str(e)}
        print("   FAIL", e)
    for a in ths_bigv.get("accounts", []):
        if not a["items"]:
            ths_bigv.setdefault("note", "")
            ths_bigv["note"] += "[%s]%s\n" % (a["name"], a["msg"])

    print("== [6/6] 知乎 21 源（加权） ==")
    try:
        zhihu = fetch_zhihu.fetch()
        n_ok = sum(1 for a in zhihu.get("accounts", []) if a["items"])
        print("   accounts:", len(zhihu.get("accounts", [])), "| 有观点:", n_ok,
              "| expired:", zhihu.get("login_expired"))
    except Exception as e:
        zhihu = {"accounts": [], "note": str(e)}
        print("   FAIL", e)

    warnings = [w for w in (args.warnings.split("|") if args.warnings else []) if w]

    data = {
        "date": date, "ts": ts,
        "tencent": tencent, "ths": ths,
        "brokers": brokers, "xueqiu": xueqiu, "zhihu": zhihu,
        "ths_bigv": ths_bigv,
        "warnings": warnings,
    }

    md = render.render_md(data)
    html = render.render_html(data)

    os.makedirs(OUT_DIR, exist_ok=True)
    md_path = os.path.join(OUT_DIR, "多平台大V财经观点统计_%s.md" % date)
    html_path = os.path.join(OUT_DIR, "多平台大V财经观点统计_%s.html" % date)
    raw_path = os.path.join(OUT_DIR, "raw_%s.json" % date)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("\nSAVED:", md_path)
    print("SAVED:", html_path)

    # 简版结论（≤280字，企微文字快览）；详细全量走完整 HTML 文件
    digest = render.render_summary(data)

    if args.no_push:
        print("[skip] --no-push，未推送企微")
        return 0

    print("== 推送企微（简版结论） ==")
    r = push_wecom.push_markdown(digest)
    print("push md:", r)
    ok = r.get("ok", False)
    if ok:
        print("== 推送 HTML 文件 ==")
        fr = push_wecom.push_file(html_path)
        print("push file:", fr)
        ok = ok and fr.get("ok", False)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())