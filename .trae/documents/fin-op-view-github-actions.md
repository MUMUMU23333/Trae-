# 多平台大V财经观点统计 → GitHub Actions 全云自动抓取+企微推送管线

## Context（背景与目标）

现有"多平台大V财经观点统计"工程位于 `C:\Users\Administrator\WorkBuddy\2026-07-18-01-50-27\`，每天靠人工/半自动抓取四个数据源（雪球10/同花顺4/券商6/盘面行情），再拼出成品《多平台大V财经观点统计_YYYY-MM-DD.md》推企业微信群。过程依赖本机手动 WebFetch/WebSearch，断档频繁（如 09-05~09-09 平台 4 天）。

目标：把这四源做成**自动化抓取通道**，整套管线部署到 AGNES 仓库（GitHub `MUMUMU23333/Trae-`），用 **GitHub Actions 定时全云自动跑**，生成成品后**自动推企业微信（HTML 版）**。用户已确认：两套券商名单都收录、推 HTML、全云自动、可动用技能库。

## 已确认的技术事实（设计依据）

| 数据源 | 自动通道 | 是否需 Secret | Actions 可跑 |
|---|---|---|---|
| 盘面行情 | 腾讯 `qt.gtimg.cn/q=s_sh000001,...`（GBK，免费公开） | 否 | ✅ |
| 同花顺新闻 | `news.10jqka.com.cn/tapp/news/push/stock`（公开） | 否 | ✅ |
| 知乎 21 | 纯 Python x-zse-96 v3 签名 + cookie（`zhihu_cookie_fetch.py`） | ✅ ZHIHU_COOKIE | ✅ |
| 微博 3 | 纯 HTTP + cookie（`weibo_cookie_fetch.py`，需去硬编码绝对路径） | ✅ WEIBO_COOKIE | ✅ |
| 雪球 10 | 带 cookie 直连 status API；WAF 失败→降级标注 | ✅ XUEQIU_COOKIE | ⚠️ 需降级 |
| 券商研报 | 东财 `reportapi.eastmoney.com/report/list` 按机构名过滤（公开） | 否 | ✅ |
| 企微推送 | 机器人 webhook，markdown 分块（`push_wecom.py`） | ✅ WECOM_KEY | ✅ |

关键坑：
- 企微机器人 webhook key 目前硬编码在 `scratch/push_wecom.py` → **必须 env 化**，作为 GitHub Secret，不写入公开仓库。
- 知乎/微博 cookie 刷新仍依赖本地扫码，Actions 无法无头完成 → 设计"失效探测→标记缺失→推送告警提示本地重刷 Secret"。
- 逻辑源脚本有硬编码绝对路径（`weibo_cookie_fetch.py` 的 `SECRET = r"C:\Users\..."`）→ 改用 env。
- Windows 编码：本次只在 Actions(ubuntu) 跑，脚本仍用 `PYTHONIOENCODING=utf-8`。
- 券商名单两套：金股高胜率6家（国元/东北/开源/华鑫/东兴/招商）+ 成品档6家（东方/银河/国泰海通/中金/中银/财信）→ 合并去重，按 orgSName 过滤东财研报。

## 实施状态（2026-09-10）

✅ **已落地到 AGNES 仓库**（`g:\TRAE\MODE\AGNES\`）：
- 目录 `fin-op-view/`（sources + crawlers + libs + run.py + requirements.txt + .gitignore）
- workflow `.github/workflows/daily-op-view.yml`
- 本地 `python run.py --no-push` 已验证：腾讯盘面4指数 ✅ / 同花顺新闻（按日Unix时间戳过滤）✅ / 券商6组研报 ✅ / 雪球10源正确降级WAF ✅
- 关键实现修正（相对初稿）：
  1. 同花顺新闻 `ctime/rtime` 是 **Unix 秒时间戳** → `_ts2day()` 转日期过滤
  2. 腾讯行情取 `f[7]` 为成交额(万元) → 展示转"成交额XX亿"
  3. 雪球探测确认 user_page 被阿里云 WAF（`aliyun_waf_aa` + JS混淆）包裹 → 需 XUEQIU_COOKIE，制造带 cookie 也保持降级标注
  4. 同花顺4位大V（JS SPA）按用户确认改用**同花顺新闻API**，成品标注"需人工每日WebFetch补录大V观点"
  5. 企微推送：key 取 `WECOM_KEY` env，markdown 分块，HTML 存 artifact 附链接（用户确认方案）
- `.gitignore` 排除 `output/`、`*.secret`、`.env`（密钥不入库）

### ✅ 2026-09-10 补充：权重脚本迁移

- `sources/weights.json`：从 WorkBuddy `dav_weight_v2.json` 提取 v3.2 权重唯一权威（21 知乎账户 weight/hits + consensus_rule），升级 json 即自动生效，不硬编码。
- `sources/zhihu.json`：已迁移 21 个知乎账户（含 zhihu_id），抓取通道 x-zse-96 v3 签名 + `ZHIHU_COOKIE` env。
- `libs/weights.py`：`weight_of()`（主名+前缀回退，如"航哥分红退休之路"→"航哥"）、`hits_of()`、`consensus_converge()`（多空 ΣW 置信度 high/mid/low + 拥挤⚠️ + 板块共识）。
- `crawlers/fetch_zhihu.py`：移植 x-zse-96 v3 签名（SALT/ZK/ZB/encrypt 全量），从 `ZHIHU_COOKIE` env 读 cookie；缺失/失效/签名变化 → 降级标"需人工重刷 Secret"，不中断管线。
- `run.py` 新增 `[5/5] 知乎 21 源（加权）`；`render.py` 新增"知乎 21 源观点（加权）"段（按权重降序，统计 ΣW）。
- workflow env 加 `ZHIHU_COOKIE`。
- 本地验证：weights 匹配（启四=2/航哥=2/龙头=3/陌生人=1）✅；知乎无 cookie 降级 21 源 no_cookie ✅；`python run.py --no-push` 全链路出产物 ✅。
- **执行阶段补充：签名移植纠错 + 真实抓取全通**（2026-09-10）——fetch_zhihu.py 首版签名偏移原版（缺 `_block_x`/`pre_process` 无 random 盐/`_block_r` 语义错/**ZB 少 1 项 255/256**），真实抓取最初仅 4/21 ok；已整体替换原版实现并补全 ZB 表。带本地 `.zhihu_cookie.secret` 实测 **21/21 全部成功**，产物加权段（w3/w2）正确渲染。cookie 直接复用 WorkBuddy 现存 `.zhihu_cookie.secret`（无需重新 CDP 扫码，除非该 cookie 失效）。

⏳ 待用户操作：
- 为仓库配置 Secrets：`XUEQIU_COOKIE`、`ZHIHU_COOKIE`（内容 = WorkBuddy `.zhihu_cookie.secret` 全串，含 d_c0）、`WECOM_KEY`
- 首次 push 后手动 `workflow_dispatch` 触发试跑，核对 artifact 与企微

## 目录结构（AGNES 仓库子目录 `fin-op-view/`）

```
g:\TRAE\MODE\AGNES\fin-op-view\
├── .github/workflows/daily-op-view.yml   # Actions 定时 workflow
├── requirements.txt                       # 纯 stdlib，无三方依赖
├── sources/
│   ├── xueqiu.json   # 从 rss_sources_other.json 迁移 10 个雪球大V
│   ├── weibo.json    # 迁移 3 个微博大V + 新浪博客4(归入 fetch_sina)
│   ├── zhihu.json    # 从 rss_sources_zhihu.json 迁移 21 账户
│   ├── ths.json      # 同花顺新闻（或券商2节）
│   └── brokers.json  # 券商10机构名单（金股6 + 成品6 去重，带 orgSName）
├── crawlers/
│   ├── fetch_tencent.py   # 盘面行情：qt.gtimg.cn 解析（GBK→结构：指数点位/涨跌/成交额）
│   ├── fetch_ths.py       # 同花顺新闻：公开 API + 按日过滤（封装 fetch_ths_0811）
│   ├── fetch_zhihu.py     # 知乎：移植 x-zse-96 v3 签名 + ZHIHU_COOKIE env
│   ├── fetch_weibo.py     # 微博：ajax + WEIBO_COOKIE env（去硬编码路径）
│   ├── fetch_xueqiu.py    # 雪球：XUEQIU_COOKIE + WAF 降级标注
│   ├── fetch_broker.py    # 券商：东财 report API 按 brokers.json 过滤
│   └── fetch_sina.py      # 新浪博客：移植 fetch_sina_blogs.py
├── libs/
│   ├── common.py    # cookie 读取env、失效探测、统一标注
│   ├── render.py    # 拼成品 md（复用现有档结构）
│   └── push_wecom.py# 企微推送：key 从 WECOM_KEY env 取，markdown 分块
└── run.py           # 统一 runner：抓四源+知乎+微博+新浪 → 生成 md → 渲染 HTML → 推企微
```

## workflow 骨架（daily-op-view.yml）

```yaml
name: op-view
on:
  workflow_dispatch:
  schedule:
    - cron: "30 7 * * *"   # 15:30 收盘后
    - cron: "30 13 * * *"  # 21:30 晚间
jobs:
  run:
    runs-on: ubuntu-latest
    env:
      TZ: Asia/Shanghai
      PYTHONIOENCODING: utf-8
      WEIBO_COOKIE: ${{ secrets.WEIBO_COOKIE }}
      ZHIHU_COOKIE: ${{ secrets.ZHIHU_COOKIE }}
      XUEQIU_COOKIE: ${{ secrets.XUEQIU_COOKIE }}
      WECOM_KEY: ${{ secrets.WECOM_KEY }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: python run.py
      - uses: actions/upload-artifact@v4   # 保留成品 md+html 供查阅
```

## 复用的现有代码（不重写，增移植）

- 知乎签名算法：`zhihu_cookie_fetch.py` L61-155（x-zse-96 v3）——整块可搬。
- 盘面行情解析：`qt.gtimg.cn` 返回 GBK，需 decode('gbk') 处理中文名（已实测）。
- 新浪博客：`scratch/fetch_sina_blogs.py`（纯 HTTP 列表+正文）。
- 企微分块推送：`scratch/push_wecom.py` L7-46（3800字节分块逻辑），改 key=env。
- 知乎流水线拼装思路：`zhihu_daily_pipeline.py` 的 `hits_of`/`weight_of`/关键词热度。

## 关键实现说明

1. **盘面行情 fetch_tencent**：GET `qt.gtimg.cn/q=` 拼接 indices，decode('gbk')，解析 `v_s_sh000001="..."` 字段（指数名/点位/涨跌/涨跌幅/成交量/成交额），输出结构化 dict，供 render 用 `盘面锚定` 节。
2. **券商 fetch_broker**：GET 东财 `reportapi.eastmoney.com/report/list`，`beginTime/endTime=当日`，`qType=1`，遍历 fields 里的 `orgSName` 匹配 brokers.json 名单，按机构分组输出当日研报标题/评级。金股6家是券商名；成品6家如"东方证券"用 orgSName 模糊匹配。
3. **雪球 fetch_xueqiu**：带 `XUEQIU_COOKIE` 请求 `xueqiu.com/u/<uid>` 或 status API；若返回含 `renderData`/验证码 HTML → 标记该源 `login_expired`，成品标"需人工 WebFetch"。
4. **登录态失效闭环**：`common.py` 定义 `probe()`，知乎返回空 data / 微博 HTTP 4xx 或空 list / 雪球验证码 → 对应源 `status="expired"`，成品该平台段标注"登录态失效"，并附推送告警段"请本地重刷 Secret（Actions 无法扫码）"。
5. **成品 md 结构**：复用现有档（盘面锚定→特殊提醒→分平台统计→加权共识），render.py 按 source 顺序渲染。
6. **HTML 版**：render.py 额外渲染一版自包含 HTML（深色金融风格，CSS 内联），企微推送 markdown 时附带 HTML 链接 → 或直接把 HTML 内容转企微 markdown 摘要+链接。企微机器人不支持 HTML 富文本，故 HTML 作为**推送消息内的链接**（如预览页或 GitHub Pages）或存于 artifact。

## 实施顺序

1. 在 `fin-op-view/` 建目录骨架，迁移 `sources/*.json` 与 4 个纯脚本（tencent/ths/zhihu/weibo），本地 python 跑通（公开源先验证）。
2. 写 `fetch_broker.py`（东财 API），验证按 10 机构名过滤当日研报。
3. 写 `fetch_xueqiu.py`（cookie+降级），本地验 WAF 行为。
4. 拼 `run.py`+`render.py`+`push_wecom.py`（env 化 key），本地出全源成品 md + HTML。
5. 配置 3 个 Secrets，提交 workflow，试跑 `workflow_dispatch` 观察两档 schedule。
6. 加登录态失效告警、上传 artifact；稳定后废弃本地手工步骤。

## 需用户提供的清单

1. **WEIBO_COOKIE / ZHIHU_COOKIE / XUEQIU_COOKIE**：三个 `.secret` 文件原样内容（当前 cookie，过期时本地重刷后更新 Secret）。
2. **WECOM_KEY**：企微机器人 key（从 `push_wecom.py` 取，改为 Secret）。
3. 确认仓库：`fin-op-view/` 放 AGNES 仓库根目录下（与 `.trae/rules` 平级）。
4. GitHub 仓库需开通 Actions（默认免费 runner）。

## 验证方式

- **本地**：`python run.py` 应输出四源 raw JSON + 成品 md + HTML，无异常；核对股票名中文不乱码。
- **失效演练**：临时把某个 cookie 设无效 → run 应把该源标 `expired` 并推告警，不中断整条。
- **Actions**：push 后触发 `workflow_dispatch`，查看 run log 各源 status，确认企微收到消息、artifact 有 md+html。
- **券商**：核对当日东财研报里 10 家机构是否各自出了代表性观点。