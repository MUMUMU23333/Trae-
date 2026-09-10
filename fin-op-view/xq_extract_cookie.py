# -*- coding: utf-8 -*-
"""专用调试 Chrome 中提取雪球明文 cookie -> .xueqiu_cookie.secret。

用法: python xq_extract_cookie.py [port]   # 默认 9223
前提: 已用 --remote-debugging-port=9223 --user-data-dir=... 启动专用 Chrome 并登录 xueqiu.com
"""
import sys, os, json
from urllib.request import urlopen
import websocket

BASE = os.path.dirname(os.path.abspath(__file__))
XQ_DOM = (".xueqiu.com", "xueqiu.com")


def http_json(url, timeout=6):
    return json.loads(urlopen(url, timeout=timeout).read().decode("utf-8", "replace"))


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "9223"
    try:
        pages = http_json("http://127.0.0.1:%s/json/list" % port)
    except Exception as e:
        print("RESULT: FAIL - 专用 Chrome(port %s)未监听: %s" % (port, e))
        sys.exit(1)
    pages = [t for t in pages if t.get("type") == "page" and (t.get("url") or "").strip()]
    if not pages:
        print("RESULT: MISS - 无可用页面 target")
        sys.exit(3)

    got = {}
    _n = {"n": 0}

    def merge(ws_url):
        ws = None
        here = {}
        try:
            ws = websocket.create_connection(ws_url, timeout=20)
            def call(method, params=None, timeout=15):
                _n["n"] += 1
                mid = _n["n"]
                payload = {"id": mid, "method": method}
                if params:
                    payload["params"] = params
                ws.settimeout(timeout)
                ws.send(json.dumps(payload))
                while True:
                    msg = json.loads(ws.recv())
                    if msg.get("id") == mid:
                        return msg
            r = call("Network.getAllCookies")
            for c in ((r.get("result") or {}).get("cookies")) or []:
                d = (c.get("domain") or "").lower()
                if any(x in d for x in XQ_DOM):
                    here[c.get("name")] = c.get("value", "")
        except Exception as e:
            print("[warn] %s 提取失败 %s" % (ws_url[-40:], type(e).__name__))
        finally:
            try:
                if ws:
                    ws.close()
            except Exception:
                pass
        return here

    for t in pages:
        got.update(merge(t["webSocketDebuggerUrl"]))
        if "xq_a_token" in got:
            break

    if not got:
        print("RESULT: MISS - 无雪球 cookie（请在专用 Chrome 登录 xueqiu.com 后刷新）")
        sys.exit(3)
    ck = "; ".join("%s=%s" % (k, v) for k, v in got.items())
    out = os.path.join(BASE, ".xueqiu_cookie.secret")
    with open(out, "w", encoding="utf-8") as f:
        f.write(ck)
    logged = "xq_a_token" in got
    print("RESULT: %s - 已提取 %d 条雪球 cookie(含 xq_a_token=%s)，写入 %s"
          % ("OK" if logged else "STALE", len(got), logged, out))


if __name__ == "__main__":
    main()