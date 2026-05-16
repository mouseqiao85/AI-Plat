# gstack 23 专家角色清单

> 来源：`C:\Projects\gstack`，共 46 个 SKILL.md，其中 23 个作为"专家角色"面向前端勾选面板。
> README 自述 "Twenty-three specialists and eight power tools"，本文从 README 三大分区列出的 25 个候选中剔除 2 个纯工具/配置类得到 23。
> 更新：2026-05-13

---

## 一、23 专家角色（面向前端勾选）

### Plan-mode reviews（7 个） — 动工前的想法/计划评审团

| slug | 中文职能 | 一句话能力 | 建议适配的工具场景 |
|---|---|---|---|
| office-hours | 产品启动诊所 | 六问直击需求真实度与最小楔子 | product-discovery |
| plan-ceo-review | CEO 视角评审 | 四模式拷问计划，找 10 分产品 | product-discovery |
| plan-eng-review | 架构评审 | 架构/数据流/边界/测试锁定 | plan-review |
| plan-design-review | 设计计划评审 | 每维度 0-10 打分并改到 10 | plan-review |
| plan-devex-review | 开发者体验评审 | 为 API/CLI/SDK 评 DX 分 | plan-review |
| autoplan | 自动评审流水线 | 串联 CEO/Eng/Design/DX 一条龙 | plan-review |
| design-consultation | 设计系统咨询 | 从零生成 DESIGN.md 源真相 | design-discovery |

### Implementation + review（11 个） — 动手写代码与评审环节

| slug | 中文职能 | 一句话能力 | 建议适配的工具场景 |
|---|---|---|---|
| review | PR 落地评审 | 落地前审 diff，查 SQL/LLM/边界风险 | code-review |
| codex | 独立第二意见 | Codex 审/挑战/咨询三模式 | code-review |
| investigate | 根因调试 | 四步调查法，无根因不改码 | debug |
| design-review | 视觉 QA 修复 | 发现视觉问题并原子化提交修复 | design-qa |
| design-shotgun | 设计方案霰弹 | 一次生成多稿设计对比选优 | design-discovery |
| design-html | 设计落地 HTML | 把稿子变成可跑的 HTML/CSS | implementation |
| devex-review | DX 实测审计 | 真跑一遍 onboarding 打分 | dx-audit |
| qa | 系统化 QA 修复 | 测-改-验闭环 + 健康分 | qa |
| qa-only | 只报不改 QA | 结构化 bug 报告无代码改动 | qa |
| scrape | 网页抓取 | 原型/固化两段式抓数据 | data-collection |
| skillify | 流程固化 | 把成功 scrape 固化为 skill | automation |

### Release + deploy（5 个） — 发布与上线后观测

| slug | 中文职能 | 一句话能力 | 建议适配的工具场景 |
|---|---|---|---|
| ship | 打包上 PR | 合基、跑测、改版、建 PR 一条龙 | release |
| land-and-deploy | 合并部署 | 合 PR、等 CI、健康检查 | release |
| canary | 金丝雀监控 | 部署后盯控制台/性能/截图对比 | release-monitor |
| landing-report | 发布队列看板 | 只读看当前版本槽与队列 | release-monitor |
| document-release | 发布后补文档 | 同步 README/ARCH/CHANGELOG | release-docs |

---

## 二、剔除/候补说明

README 在三大"角色"分区列出了 25 条，本文剔除以下 2 条收敛到 23 人：

| slug | 为何未入选 |
|---|---|
| setup-deploy | 一次性配置脚本（选平台、写 CLAUDE.md），属于"安装部署"基础设施，不是复现性人设 |
| plan-tune | 调教 AskUserQuestion 提问频率的元工具，是 harness 开关，不是评审角色 |

其余 ~23 个 skill 不作为人设出现，归入"辅助工具 / 基础设施"：

| slug | 性质 |
|---|---|
| benchmark / benchmark-models | 模型 benchmark 基准工具 |
| browse / open-gstack-browser / setup-browser-cookies | 浏览器会话基础设施 |
| careful / guard / freeze / unfreeze | 安全守卫 hook（非角色） |
| context-save / context-restore | 会话状态持久化 |
| health | 仓库健康体检脚本 |
| gstack-upgrade / sync-gbrain / setup-gbrain | gstack 自身升级/同步 |
| make-pdf | PDF 导出工具 |
| learn | 跨会话学习库管理 |
| retro | 周度工程回顾（可按需升级为人设） |
| cso | 安全官（未在 README 三区，但实为强人设，可作为候补 24 号） |
| pair-agent | 远程 agent 配对工具 |

> 备注：如产品侧想扩展到 24-25 人，`cso`（Chief Security Officer）和 `retro`（工程回顾官）是最佳增量候选。

---

## 三、工具场景建议映射

基于 23 角色与现有 agent 工具池（`brave_search` / `skill_*_run` / `create_plan` / `file_gen`），推荐以下场景预设：

```yaml
scenarios:
  - name: product-discovery
    description: 从想法到计划：一起想清楚要不要做、做多大
    roles: [office-hours, plan-ceo-review]
    tools: [skill_office-hours_run, skill_plan-ceo-review_run, brave_search, create_plan]

  - name: plan-review
    description: 动工前的多角度计划评审（架构/设计/DX/全量）
    roles: [plan-eng-review, plan-design-review, plan-devex-review, autoplan]
    tools: [skill_plan-eng-review_run, skill_plan-design-review_run, skill_plan-devex-review_run, skill_autoplan_run, create_plan]

  - name: code-review
    description: PR 落地前的双评审（gstack + codex 二意见）
    roles: [review, codex, investigate]
    tools: [skill_review_run, skill_codex_run, skill_investigate_run, brave_search]

  - name: design-build
    description: 从设计系统到可跑 HTML 的一条龙
    roles: [design-consultation, design-shotgun, design-html, design-review]
    tools: [skill_design-consultation_run, skill_design-shotgun_run, skill_design-html_run, skill_design-review_run, file_gen]

  - name: qa
    description: 上线前系统化 QA 与修复
    roles: [qa, qa-only, devex-review]
    tools: [skill_qa_run, skill_qa-only_run, skill_devex-review_run]

  - name: release
    description: 打 PR → 合并部署 → 金丝雀监控
    roles: [ship, land-and-deploy, canary, landing-report]
    tools: [skill_ship_run, skill_land-and-deploy_run, skill_canary_run, skill_landing-report_run]

  - name: release-docs
    description: 发布后文档同步
    roles: [document-release]
    tools: [skill_document-release_run, file_gen]

  - name: data-automation
    description: 网页数据抓取与固化
    roles: [scrape, skillify]
    tools: [skill_scrape_run, skill_skillify_run, brave_search]
```

---

## 四、最终 23 slug 速查

```
office-hours, plan-ceo-review, plan-eng-review, plan-design-review,
plan-devex-review, autoplan, design-consultation,
review, codex, investigate, design-review, design-shotgun, design-html,
devex-review, qa, qa-only, scrape, skillify,
ship, land-and-deploy, canary, landing-report, document-release
```
