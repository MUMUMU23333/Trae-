# Central Skills & Experts Router for Trae

## 核心规则
本项目已连接 D:\ARUANJIAN\SKILL 中央技能库。
- 当用户提到'专家团'时，默认激活【天枢总指挥部统帅专家团】。
- 严禁使用 // TODO 占位符，输出完整可运行代码。
- 保持老资深 7 级减法天梯 (Ponytail)，杜绝过度工程。

## ⚡ 自然语言自动路由（收到任务即绑定，无需用户指定技能名）
> 用户用自然语言提出需求时，先匹配下方领域 → 激活专家团 → 按需 Read 技能文件执行。
> 完整 197 技能映射见 `D:\ARUANJIAN\SKILL\ROUTER.md`。
> ⚠️ 图中"→"右侧目标分两类，注意区分：
> - **专家团·有规则文件**（下方挂载清单，共 12 团）；
> - **底层技能·SKILL 库**（`D:\ARUANJIAN\SKILL\skills/<id>` 直接调用，不占专家团编号，如 fund-analysis、web-harvest-studio、truth-sentry、wecom-unified、deep-research、universal-code-reviewer、mem0-memory-engine 等）。

| 用户意图（自然语言示例） | 激活专家团 / 首选技能 |
|---|---|
| 查行情/诊断股票/抄底逃顶/支撑阻力/回测/聚宽/Ptrade | `smart-stock-analyst` → `westockdata`·`westock-data`·`joinquant-skill`·`quant2ptrader-mcp`·`westock-3yr-backtest` |
| 多空辩论/圆桌研报/这只票贵不贵 | `stock-partner-team` → `md-to-html`·`westock-data` |
| 基金/ETF分析/持仓诊断/基金交易 | `fund-analysis`·`thsfund`·`mx-finance-data` |
| 抓网页/爬数据/反爬/公众号/视频下载/OCR | `web-harvest-studio` → `crawl4ai`·`jina-reader`·`markitdown-parser`·`umi-ocr-local`·`video-downloader`·`wechat-article-search` |
| 核实真假/打假/辟谣/图片PS/论文撤稿 | `truth-sentry` → `multi-search-engine`·`umi-ocr-local` |
| 分析性格/人物画像/数字分身 | `persona-psych-profiler` → `people-deep-miner`·8大分身技能 |
| 深挖背景/人员尽调（先做合规评估） | `osint-investigator-team` → `people-deep-miner`·`truth-sentry` |
| 写小说/网文/世界观/去AI味/拆镜生图 | `novel-writer-suite` → `novel-architect`·`deep-humanizer-pro`·`creative-unshackle`·`story-to-scenes` |
| 小红书/抖音文案/海报/生图提示词 | `ai-content-creator-team` → `flux-midjourney-prompter`·`character-consistency-engine`·`canvas-design`·`multi-wordcheck` |
| 做PPT/Slides/演讲稿/杂志风HTML | `humanize-ppt-team` → `html-ppt`·`guizang-ppt-skill`·`pptx-generator`·`frontend-slides`·`humanize-ppt` |
| 高端官网/Bento/毛玻璃/响应式网页 | `modern-web-architects` → `ui-ux-pro-max`·`taste-skill`·`frontend-dev`·`frontend-design` |
| HTML5小游戏/打击感/音效 | `indie-game-studio` → `game-juice-engine`·`web-audio-synth`·`brainstorm` |
| 分析Excel/CSV/财务表/三格式报告 | `huashu-data-pro` → `minimax-xlsx`·`markitdown-parser`·`data-autocleaning` |
| 写后端/API/数据库/重构/排查Bug/高并发 | `engineering-cybernetics-council` → `backend-dev`·`python-development`·`database-design`·`universal-code-reviewer`·`debugger`·`security-auditor` |
| 代码审查/安全扫描/TDD/反过度设计 | `universal-code-reviewer`·`security-auditor`·`superpowers`·`ponytail`·`pua` |
| 企业微信/文档/日程/群指令 | `wecom-unified`·`wecom-interactive-commander`·`langbot-gateway` |
| 深度调研/论文精读/大模型应用/Gemini | `deep-research`·`paper-distiller`·`context7-docs`·`gemini-context-caching`·`llm-application-dev` |
| 润色/去AI味/翻译/简历/违禁词 | `write`·`humanizer`·`deep-humanizer-pro`·`academic-translation`·`reactive-resume-builder`·`multi-wordcheck` |
| 长期记忆/会话检索/Token用量 | `mem0-memory-engine`·`memory-bank`·`session-history-search`·`token-usage-tracker` |

**执行约定**：
1. 意图命中 → 先激活专家团，团队自主调用底层技能；
2. 技能按需读取：Read `D:\ARUANJIAN\SKILL\skills\<id>\SKILL.md` 后按其规范执行；
3. 金融数据统一经 `powershell -ExecutionPolicy Bypass -File D:\ARUANJIAN\SKILL\bin\westock.ps1` 调用（自动联网探测，断网立即中止不傻等），网页先走 web-access/浏览器通道；
4. **联网前先探测（防卡死）**：任何联网操作（npx/爬虫/搜索/API）执行前，先用快速探测命令（如 `curl.exe -s -m 3 -o NUL -w "%{http_code}" https://registry.npmjs.org`）验证连通性；探测失败立即改走本地路径或明确告知用户"需要网络"，禁止无超时傻等；
5. 长联网任务放后台运行 + 轮询，不阻塞对话回合；
6. OSINT/换脸/人员深挖先做合法性与隐私评估。

## 挂载的专家团清单
- **supreme-commander** (天枢总指挥部统帅专家团 (Supreme Commander & Chief Engineers))
- **smart-stock-analyst** (星辰投研团 (5人决策组))
- **stock-partner-team** (腾讯自选股股票投研专家团 (7人圆桌组))
- **huashu-data-pro** (花叔数据分析专家团 (4人并行组))
- **humanize-ppt-team** (卡尔的人感PPT专家团 (7人全流程组))
- **indie-game-studio** (独立小游戏全流程工坊 (6人全流程组))
- **modern-web-architects** (高端互动网页与体验架构师 (5人全栈组))
- **ai-content-creator-team** (AI内容创作与多模态工作室 (7人全链路组))
- **novel-writer-suite** (长篇小说与文学创作专家团 (6人编剧组))
- **engineering-cybernetics-council** (全栈系统架构与工程研发专家组 (Engineering Cybernetics Council))
- **persona-psych-profiler** (心理学与社会学人物画像专家团 (Persona Psych Profiler))
- **osint-investigator-team** (猎鹰开源情报与全域人员深度穿透专家团 (OSINT Investigator Team))

> ✅ 以上 12 团均有独立规则文件（`.trae/rules/*.md`），含触发词 / 定位 / 角色 / 交付标准。

## 底层技能与专用通道（非专家团，直接调用 SKILL 库）
路由表中出现的以下目标属于 `D:\ARUANJIAN\SKILL` 库的**底层技能 / 专用通道**，无独立专家团规则文件；收到相关意图时按 `ROUTER.md` 直接调用对应 SKILL：

- 基金/ETF：`fund-analysis`·`thsfund`·`mx-finance-data`
- 网页抓取/反爬/OCR/下载：`web-harvest-studio` → `crawl4ai`·`jina-reader`·`markitdown-parser`·`umi-ocr-local`·`video-downloader`·`wechat-article-search`
- 打假辟谣/取证：`truth-sentry` → `multi-search-engine`·`umi-ocr-local`
- 企业微信/文档/日程：`wecom-unified`·`wecom-interactive-commander`·`langbot-gateway`
- 深度调研/论文/大模型：`deep-research`·`paper-distiller`·`context7-docs`·`gemini-context-caching`·`llm-application-dev`
- 代码审查/安全/反过度设计：`universal-code-reviewer`·`security-auditor`·`superpowers`·`ponytail`·`pua`
- 润色/去AI味/翻译/简历/违禁词：`write`·`humanizer`·`deep-humanizer-pro`·`academic-translation`·`reactive-resume-builder`·`multi-wordcheck`
- 长期记忆/会话检索/Token：`mem0-memory-engine`·`memory-bank`·`session-history-search`·`token-usage-tracker`