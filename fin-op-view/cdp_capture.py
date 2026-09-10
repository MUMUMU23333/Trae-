# -*- coding: utf-8 -*-
"""cdp_capture.py — 本地每日补录工具（解决线上 WAF/SPA 抓不到的部分）。

背景: GitHub Actions 全云无浏览器，雪球 10 源被阿里云 WAF 拦截、同花顺 3 位大V
(全能的野人/纳指水蛭/我的人生如股票) 主页为 Vue SPA 内容在股吧话题流，线上全部抓不到。
本脚本复用本机已登录的专用 Chrome(CDP 端口 9223)，在浏览器环境内执行 fetch/渲染，
把对应源观点抓到本地，输出与管线同构的 JSON，供你本地跑完再人工补录到 push 前。

用法:
  前提: 用 --remote-debugging-port=9223 --user-data-dir=... 启动专用 Chrome 并登录
        xueqiu.com 与 t.10jqka.com.cn
  python cdp_capture.py            # 全量抓雪球10源 + 同花顺4大V
  python cdp_capture.py --xueqiu   # 只抓雪球
  python cdp_capture.py --ths      # 只抓同花顺
输出: output/xueqiu_cdp.json、output/ths_bigv_cdp.json
"""
import json
import os
import queue
import re
import sys
import threading
import time
from urllib.request import urlopen

try:
    import websocket
except ImportError:
    print("缺依赖: pip install websocket-client")
    sys.exit(1)

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "output")
PORT = "9223"


def http_json(url, timeout=6):
    return json.loads(urlopen(url, timeout=timeout).read().decode("utf-8", "replace"))


# ============ CDP 客户端 ============
class Cdp:
    def __init__(self, port):
        pages = [t for t in http_json("http://127.0.0.1:%s/json/list" % port)
                 if t.get("type") == "page" and not (t.get("url") or "").startswith(("devtools://", "chrome://"))]
        if not pages:
            raise RuntimeError("专用 Chrome(port %s) 未运行，请先启动。" % port)
        self.ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=120,
                                              origin="http://localhost:%s" % port,
                                              suppress_origin=True,
                                              header=["Origin: http://localhost:%s" % port])
        self.q = queue.Queue()
        self.n = [0]
        threading.Thread(target=self._reader, daemon=True).start()
        # 建独立空白页
        r = self.call("Target.createTarget", {"url": "about:blank"})
        self.tid = r["result"]["targetId"]
        r = self.call("Target.attachToTarget", {"targetId": self.tid, "flatten": True})
        self.sid = r["result"]["sessionId"]
        self.call("Page.enable", sid=self.sid)
        self.call("Runtime.enable", sid=self.sid)

    def _reader(self):
        try:
            while True:
                self.q.put(json.loads(self.ws.recv()))
        except Exception:
            pass

    def call(self, method, params=None, sid=None, timeout=40):
        self.n[0] += 1
        mid = self.n[0]
        payload = {"id": mid, "method": method}
        if sid:
            payload["sessionId"] = sid
        if params:
            payload["params"] = params
        self.ws.send(json.dumps(payload))
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self.q.get(timeout=timeout)
            except queue.Empty:
                break
            if msg.get("id") == mid:
                return msg
        return {"error": {"message": "timeout"}}

    def ev(self, expr, timeout=40):
        r = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                           "awaitPromise": True}, sid=self.sid, timeout=timeout)
        rv = (r.get("result") or {}).get("result", {})
        if r.get("error") or rv.get("subtype") == "error":
            return None
        return rv.get("value")

    def nav(self, url, wait=4):
        self.call("Page.navigate", {"url": url}, sid=self.sid)
        time.sleep(wait)

    def close(self):
        try:
            self.call("Target.closeTarget", {"targetId": self.tid}, sid=self.sid)
        except Exception:
            pass
        try:
            self.ws.close()
        except Exception:
            pass


# ============ 雪球 ============
def fetch_xueqiu(cdp, accounts):
    cdp.nav("https://xueqiu.com/", wait=3)
    out = {"accounts": [], "note": ""}
    for a in accounts:
        uid = a["uid"]
        expr = ("fetch('/v4/statuses/user_timeline.json?user_id=%s&page=1&count=5',"
                "{headers:{'Accept':'application/json'}})"
                ".then(r=>r.text()).catch(e=>JSON.stringify({err:String(e)}))" % uid)
        val = cdp.ev("(%s)" % expr, timeout=30)
        entry = {"name": a["name"], "uid": uid, "weight": a.get("weight", 1),
                 "status": "ok", "items": [], "msg": ""}
        sts = None
        if val:
            try:
                data = json.loads(val)
                if isinstance(data.get("data"), dict) and isinstance(data["data"].get("list"), list):
                    sts = data["data"]["list"]
                elif isinstance(data.get("statuses"), list):
                    sts = data["statuses"]
            except Exception:
                entry["msg"] = "解析失败"
        if sts:
            for st in sts[:5]:
                txt = re.sub(r"<[^>]+>", "", (st.get("text") or st.get("title") or ""))
                txt = re.sub(r"\s+", " ", txt).strip()
                if txt:
                    created = st.get("created_at") or ""
                    try:
                        created = time.strftime("%Y-%m-%d %H:%M",
                                                time.localtime(int(created) / 1000))
                    except Exception:
                        created = str(created)[:16]
                    entry["items"].append({"time": created, "text": txt[:300]})
            if not entry["items"]:
                entry["status"] = "empty"
                entry["msg"] = "接口返回空"
        else:
            entry["status"] = "empty"
            entry["msg"] = (val or "")[:80] or "无返回"
        out["accounts"].append(entry)
    return out


# ============ 同花顺 ============
_RE_TITLE = re.compile(r'ucwlist-fd-title[^>]*>\s*<a[^>]*>([^<]{2,120})</a>', re.S)
_RE_DETAIL = re.compile(r'<div class="ucwlist-fd-detail">(.*?)</div>', re.S)
_RE_TIME = re.compile(r'ucwlist-fd-time[^>]*>([^<]{1,12})</a>', re.S)


def _parse_posthtml(html):
    items = []
    for blk in re.findall(r'<li class="ucwlist-all post-single[^"]*"[^>]*>.*?</li>', html, re.S):
        m = _RE_TITLE.search(blk)
        if not m:
            continue
        title = m.group(1).strip()
        if len(title) < 2:
            continue
        d = _RE_DETAIL.search(blk)
        text = re.sub(r"<[^>]+>", "", d.group(1)) if d else ""
        tm = _RE_TIME.search(blk)
        items.append({"time": tm.group(1).strip() if tm else "",
                      "title": title, "text": re.sub(r"\s+", " ", text).strip()[:300]})
    return items


def fetch_ths(cdp, accounts):
    out = {"accounts": [], "note": ""}
    for a in accounts:
        uid = a["uid"]
        entry = {"name": a["name"], "uid": uid, "weight": a.get("weight", 1),
                 "status": "ok", "items": [], "msg": ""}
        # 通道1: 浏览器内 fetch userPost（登录态，覆盖张明辉）
        url = "https://t.10jqka.com.cn/newcircle/user/userPost/?first=1&userid=%s" % uid
        expr = ("fetch('%s',{headers:{'X-Requested-With':'XMLHttpRequest'}})"
                ".then(r=>r.text()).catch(e=>JSON.stringify({err:String(e)}))" % url)
        cdp.nav("https://t.10jqka.com.cn/%s/" % uid, wait=2)
        val = cdp.ev("(%s)" % expr, timeout=30)
        html = ""
        if val:
            try:
                html = (json.loads(val).get("result") or {}).get("posthtml", "")
            except Exception:
                entry["msg"] = ("userPost %s" % (val[:60] or "无返回")).strip()
        items = _parse_posthtml(html) if html else []
        if items:
            entry["items"] = items[:5]
        else:
            # 通道2: 渲染主页, 尝试点"文章"标签取列表
            cdp.nav("https://t.10jqka.com.cn/%s/" % uid, wait=6)
            clicked = cdp.ev("""
              (function(){var els=document.querySelectorAll('.hpage-umtab');
              for(var i=0;i<els.length;i++){var t=(els[i].innerText||'').trim();
              if(t.indexOf('文章')===0){els[i].click();return 'clicked';}}
              return 'none';})()
              """)
            time.sleep(3)
            html2 = cdp.ev("document.querySelector('.hpage-userart')?document.querySelector('.hpage-userart').innerHTML:''")
            items2 = _parse_posthtml(html2 or "") if html2 else []
            if items2:
                entry["items"] = items2[:5]
                entry["msg"] = "来源: 主页文章标签(CDP渲染)"
            else:
                entry["status"] = "empty"
                entry["msg"] = "主页/话题流均空，需人工 WebFetch"
        out["accounts"].append(entry)
    return out


def main():
    global PORT
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    want_xq = ("--xueqiu" in args) or not (("--ths" in args))
    want_ths = ("--ths" in args) or not (("--xueqiu" in args))
    for a in args:
        if not a.startswith("-") and a.isdigit():
            PORT = a

    try:
        cdp = Cdp(PORT)
    except Exception as e:
        print("RESULT: FAIL - %s" % str(e)[:150])
        sys.exit(1)

    if want_xq:
        src = json.load(open(os.path.join(BASE, "sources", "xueqiu.json"), encoding="utf-8"))
        r = fetch_xueqiu(cdp, src["accounts"])
        ok = sum(1 for a in r["accounts"] if a["items"])
        with open(os.path.join(OUT_DIR, "xueqiu_cdp.json"), "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        print("雪球: %d/%d 有观点 -> output/xueqiu_cdp.json" % (ok, len(r["accounts"])))

    if want_ths:
        src = json.load(open(os.path.join(BASE, "sources", "ths_bigv.json"), encoding="utf-8"))
        r = fetch_ths(cdp, src["accounts"])
        ok = sum(1 for a in r["accounts"] if a["items"])
        with open(os.path.join(OUT_DIR, "ths_bigv_cdp.json"), "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=2)
        print("同花顺: %d/%d 有观点 -> output/ths_bigv_cdp.json" % (ok, len(r["accounts"])))
        for a in r["accounts"]:
            if not a["items"]:
                print("   ", a["name"], a["status"], a["msg"])

    cdp.close()
    print("RESULT: DONE")


if __name__ == "__main__":
    main()