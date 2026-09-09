# -*- coding: utf-8 -*-
"""push_wecom.py — 企微机器人推送（key 从 WECOM_KEY env 取）。
支持 markdown 分块文本 + 文件（HTML 等）上传发送。
HTML 版存为 artifact，企微推 markdown 摘要 + 完整 HTML 文件（可下载浏览器打开）。
"""
import os
import re
import urllib.request

from libs import common

LIMIT = 3800  # UTF-8 bytes per message
UPLOAD_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/upload_media?key=%s&type=file"
SEND_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=%s"


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
    url = SEND_URL % key
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


def push_file(path, filename=None, key=None):
    """上传本地文件并发送为企微 file 消息。返回 (ok, media/err 信息)。"""
    key = key or os.environ.get("WECOM_KEY", "").strip()
    if not key:
        return {"ok": False, "msg": "无 WECOM_KEY 环境变量/参数，跳过推送"}
    if not os.path.exists(path):
        return {"ok": False, "msg": "文件不存在: %s" % path}
    filename = filename or os.path.basename(path)
    with open(path, "rb") as f:
        fdata = f.read()
    if len(fdata) > 20 * 1024 * 1024:
        return {"ok": False, "msg": "文件超过 20MB，企微限制"}

    # 1) 上传媒体，拿 media_id
    _tag = re.sub(r"[^0-9A-Za-z]", "", filename)[:14]
    boundary = "----finopmv" + (_tag if _tag else "wxb")
    head = ("--%s\r\nContent-Disposition: form-data; name=\"media\"; filename=\"%s\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n" % (boundary, filename)).encode("utf-8")
    tail = ("\r\n--%s--\r\n" % boundary).encode("utf-8")
    body = head + fdata + tail
    req = urllib.request.Request(
        UPLOAD_URL % key, data=body,
        headers={"Content-Type": "multipart/form-data; boundary=%s" % boundary,
                 "User-Agent": common.UA}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            up = json_loads_bytes(r.read())
    except Exception as e:
        return {"ok": False, "msg": "上传失败: %s" % str(e)[:100]}
    media_id = (up or {}).get("media_id")
    if not media_id:
        return {"ok": False, "msg": "上传未返回 media_id: %s" % str(up)[:120]}

    # 2) 发送文件消息
    payload = {"msgtype": "file", "file": {"media_id": media_id}}
    try:
        st, body = common.http_post_json(SEND_URL % key, payload)
        ok = st == 200 and '"errcode":0' in body
        return {"ok": ok, "results": [(st, body[:80])], "media_id": media_id}
    except Exception as e:
        return {"ok": False, "msg": "发送失败: %s" % str(e)[:100]}


def json_loads_bytes(b):
    import json
    return json.loads(b.decode("utf-8", "ignore"))


if __name__ == "__main__":
    common.enable_utf8()
    r = push_markdown("测试：fin-op-view 企微推送通道 \n\n> 这条来自 Git 仓库脚本，key 取 env。")
    print(r)