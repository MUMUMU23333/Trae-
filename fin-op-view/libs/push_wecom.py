# -*- coding: utf-8 -*-
"""push_wecom.py — 企微机器人推送（key 从 WECOM_KEY env 取，markdown 分块）。
HTML 版存为 artifact，企微仅推 markdown 摘要 + GitHub Artifacts/网页链接。
"""
import os
import urllib.request
from libs import common

LIMIT = 3800  # UTF-8 bytes per message


def _chunks(text):
    paras = text.split("\n")
    chunks, cur, cur_b = [], [], 0
    for p in paras:
        pb = len(p.encode("utf-8")) + 1
        if cur and cur_b + pb > LIMIT:
            chunks.append("\n".join(cur))
            cur, cur_b = [], 0
        cur.append(p)
        cur_b += pb
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def push_markdown(text, key=None):
    key = key or os.environ.get("WECOM_KEY", "").strip()
    if not key:
        return {"ok": False, "msg": "无 WECOM_KEY 环境变量/参数，跳过推送"}
    url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=%s" % key
    results = []
    ok = True
    for c in _chunks(text):
        payload = {"msgtype": "markdown", "markdown": {"content": c}}
        try:
            st, body = common.http_post_json(url, payload)
            errcode_ok = '"errcode":0' in body
            results.append((st, body[:80]))
            ok = ok and st == 200 and errcode_ok
        except Exception as e:
            results.append(("ERR", str(e)[:80]))
            ok = False
    return {"ok": ok, "results": results}


if __name__ == "__main__":
    common.enable_utf8()
    r = push_markdown("测试：fin-op-view 企微推送通道 \n\n> 这条来自 Git 仓库脚本，key 取 env。")
    print(r)