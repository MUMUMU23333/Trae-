# 更新日志 (CHANGELOG) — 总索引

> **本文件为专家团配置更新的总索引**。各专家团的明细更新记录位于 `.trae/rules/changelogs/<团名>.md`（每团一份，统一格式「日期 | 改动 | 理由 | 结果」）。
> 修改任一专家团规则后：**优先更新对应团的独立日志**，并在此追加一条总目索引。
>
> 十二团日志索引：
> - [supreme-commander](rules/changelogs/supreme-commander.md)（统帅）· [smart-stock-analyst](rules/changelogs/smart-stock-analyst.md)（星辰投研）
> - [stock-partner-team](rules/changelogs/stock-partner-team.md)（圆桌）· [huashu-data-pro](rules/changelogs/huashu-data-pro.md)（花叔数据）
> - [humanize-ppt-team](rules/changelogs/humanize-ppt-team.md)（人感PPT）· [indie-game-studio](rules/changelogs/indie-game-studio.md)（小游戏）
> - [modern-web-architects](rules/changelogs/modern-web-architects.md)（Web架构）· [ai-content-creator-team](rules/changelogs/ai-content-creator-team.md)（内容创作）
> - [novel-writer-suite](rules/changelogs/novel-writer-suite.md)（文学创作）· [engineering-cybernetics-council](rules/changelogs/engineering-cybernetics-council.md)（工程议会）
> - [persona-psych-profiler](rules/changelogs/persona-psych-profiler.md)（人物画像）· [osint-investigator-team](rules/changelogs/osint-investigator-team.md)（情报穿透）

---

## 2026-09-09 — 【系统级】建立每团独立更新日志
- **对象**: 新增 `.trae/rules/changelogs/` 目录，12 团各建一份统一格式日志；本文件改为总索引。
- **改动**: ① 创建 12 份 `changelogs/<团名>.md`，统一头部说明「日期 | 改动 | 理由 | 结果」，并回填各自历史；② 全局 CHANGELOG 改为总索引 + 索引链接；③ 约定此后改哪个团就更新哪份日志。
- **理由**: 用户要求每个专家团具备独立、统一的更新日志，便于按团追溯更改记录与内容。
- **结果**: 全部历史回填归档，各团日志可独立翻阅，全局日志提供一览入口。

## 2026-09-09 — 统帅专家团总控调度闭环优化

- **对象**: `.trae/rules/supreme-commander.md`
- **改动**: 新增「总控调度闭环 (Orchestration Loop)」「冲突裁决优先级」「可观测与审计」三节；核心定位从「工程把关/审核」升级为「总控大脑」。
- **理由（参考 GitHub 优秀设计）**:
  - agent-hub：Router + DAG Scheduler 的分层拆解并行编排；
  - a2a-mesh：Smart Router 能力路由与多智能体 Consensus 共识；
  - yuri-os：Generative DAG 的依赖编排与条件分支；
  - NeMo Switchyard：Escalation Router / watchdog 的升级回退。
  - 此前统帅团只定义了「审什么」，缺少「怎么控」——无任务拆解、无依赖排序、无并行调度、无冲突裁决、无失败回退，本质是质检查房而非总控。
- **结果**: 补全五步闭环（路由拆解 → DAG 编排 → 协作策略 → 质检收口 → 升级裁决），明确冲突优先级（安全一票否决 → 极简 → 需求 → 可行性 → 质量），并约定每次决策回写本日志。

### 状态
- [x] 已确认保留「冲突裁决优先级」固定排序（安全一票否决 → 极简 → 需求 → 可行性 → 质量）
- [x] 已确认升级裁决「连续 3 轮无进展即降级」阈值保留（3 轮）
- [x] 已确认总控调度闭环五步方案（路由拆解 → DAG 编排 → 协作策略 → 质检收口 → 升级裁决），方案定稿

## 2026-09-09 — 专家团配置完整性统一化（A+B）

- **对象**: `.trae/rules/{smart-stock-analyst,stock-partner-team,huashu-data-pro,humanize-ppt-team,indie-game-studio,modern-web-architects,ai-content-creator-team,novel-writer-suite,persona-psych-profiler,osint-investigator-team}.md` + `00_central_orchestrator.md`
- **改动 (A)**: 为 10 个原先缺验收标准的专家团补齐统一的「交付标准」段（零占位符 / 可运行可验证 / 防过度 + 各团专属验收点），结构对齐 supreme-commander。
- **改动 (B)**: 修正中心编排器口径混乱——路由表加区分说明，明确"→"右侧目标分「专家团·有规则文件」与「底层技能·SKILL 库」两类；在挂载清单后新增「底层技能与专用通道（非专家团）」清单，收纳 fund-analysis / web-harvest-studio / truth-sentry / wecom-unified / deep-research 等无独立规则文件的能力。
- **理由**: ① 12 团仅有统帅与工程议会带验收标准，其余只列角色，交付不可度量；② 路由表把"专家团"与"SKILL 技能"混排，触发激活语义模糊。
- **结果**: 12 团全部具备「触发词 + 定位 + 角色 + 交付标准」统一结构；路由表与挂载清单口径分离，专家团 / 底层技能归属清晰。

## 2026-09-09 — 统帅团协作策略升级（直读 GitHub 源码强化）

- **对象**: `.trae/rules/supreme-commander.md`
- **改动**: 把「总控调度闭环」第 3 步「协作策略」从 3 条笼统规则升级为**穷举策略表 + 退出条件**（7 模式，对标 agent-hub 源码）。
- **理由**: 用 WebFetch 直读 Agent-hub 真实源码结构，取得其 7 种协作策略（fan_out / debate / reflection / vote / plan_execute / hitl / pipeline）+ 循环退出条件（score ≥ 90 / pass_rate > 0.9）；此前本方仅"多空圆桌/单专家/串行交接"三条，粒度不足。
- **结果**: 策略覆盖独立并行、辩论修复、自反思、多视角投票、规划执行、人机协同、串行管线 7 类场景，并给出收敛阈值；校验台标注来源为 AI 直读 GitHub。

## 2026-09-09 — 统帅团接入智能路由增强

- **对象**: `.trae/rules/supreme-commander.md`
- **改动**: 在五步闭环后新增「智能路由增强」小节，套用 agent-hub 路由层四项机制：路由记忆 / 置信度门禁 / 输入优化·模糊匹配 / 规则回退。
- **理由**: agent-hub 源码表明单一意图路由易误判或重复劳动；补上记忆复用与置信度门禁（<0.7 交统帅复核）可降低误路由，规则回退兜底保证始终有响应。
- **结果**: 统帅团在调度之上具备更稳的路由兜底，重复请求走记忆、低置信走复核、高置信直接执行；hitl 策略保留。

## 2026-09-09 — 工程议会补全角色分工表并统一交付标准

- **对象**: `.trae/rules/engineering-cybernetics-council.md`
- **改动**: 新增「团队角色与分工」表（总架构师 / 后端开发 / 数据库工程师 / 代码审查官 / 安全审计员 5 角色）；将「团队核心准则」更名为统一的「交付标准」，并补第 5 条零占位符要求。
- **理由**: 该团此前仅方法论准则、缺角色分工表，交付标准标题与其它团不一致——12 团结构中唯一异常点。
- **结果**: 12 团全部同构：触发词 + 定位 + 角色分工 + 交付标准，异常清零。

## 2026-09-09 — 工程议会依优秀工程实践补全

- **对象**: `.trae/rules/engineering-cybernetics-council.md`
- **改动**: ① 角色新增「可观测/可靠性工程师」（第 6 人）；② 交付标准新增 3 条：配置外部化 / 可观测三支柱 / 可重复构建与发布分离。
- **理由**: 学习官方 12-Factor App、Observability Best Practices 2026、Google SRE 原则后发现该团缺失现代工程的三个必选项——观测性、配置外部化、可重复发布链路。
- **结果**: 角色覆盖开发全链路（架构→后端→数据库→审查→安全→观测），交付标准覆盖 12-Factor 关键因子；配置外部化与项目 .env 密钥约束一致。

## 2026-09-09 — 11 团遍历体检：补齐 3 项必修合规维度

- **对象**: persona-psych-profiler / ai-content-creator-team / huashu-data-pro
- **改动**: 各自补充 1 条必修交付标准——persona「隐私与伦理边界」、ai-content-creator「平台合规与内容安全」、huashu-data-pro「敏感列脱敏铁律」。
- **理由**: 对 11 个非统帅团做领域最佳实践遍历体检，发现这 3 团缺失必须的隐私/合规/安全约束（其它团或已含合规、或属建议/可选级）。
- **结果**: 三类高风险领域（人物画像 / 内容创作 / 数据分析）现已具备硬性边界与脱敏要求；🟠🟡 级别项保持待办未动。
- **勘误**: 「ai-content-creator-team」一条「平台合规与内容安全」经用户确认取消并删除；保留项现为 persona「隐私与伦理边界」与 huashu-data-pro「敏感列脱敏铁律」2 项。

## 2026-09-09 — 11 团遍历体检：补齐 🟠+🟡 级 7 项

- **对象**: smart-stock-analyst / stock-partner-team / osint-investigator-team / modern-web-architects / indie-game-studio / novel-writer-suite / humanize-ppt-team
- **改动**: 各补 1 条交付标准——「时效与免责声明」「观点收敛与时效免责」「取证可存档」「无障碍 a11y」「可玩性验收」「版权与敏感审校」「字体与兼容性」。
- **理由**: 完成上轮遍历体检的 🟠(3)+🟡(4) 待办，使各团交付标准覆盖各自领域的硬性风险与体验底线。
- **结果**: 🔴🟠🟡 三项全部落地；11 团体检闭环完成。