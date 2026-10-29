# Model Onboarding Lab v1.2

**Capability Arena 方法：用多 Agent 尝试优化 Model Onboarding 链路**

- **Status**：Draft v1.2
- **Date**：2026-10-29
- **Language**：中文（HTML 中英文版已生成）
- **Format**：Markdown 源稿；排版版见 [中文 HTML](model-onboarding-lab-v1.2-zh.html) / [English HTML](model-onboarding-lab-v1.2-en.html)
- **Supersedes**：`agentic_onboarding_capability_arena_design_v1_1`（2026-10-28）
- **Companion**：[model-onboarding-lab-inputs.md](model-onboarding-lab-inputs.md)（外部输入、来源、证据强度）
- **定位**：不是“再设计一个多 Agent 平台”，而是把 v1.1 的实验场升级成**可搜索、可归因、可晋级**的优化系统。

---

## 0. v1.1 → v1.2 改了什么

| # | 变化 | 影响章节 |
| --- | --- | --- |
| 1 | 新增**四类搜索空间**：解空间、工作流、指令、实现 | §4 |
| 2 | 新增**L0–L4 多 Agent 层级**，把“多 Agent”从架构选择变成实验因子 | §5 |
| 3 | 推荐架构从“角色团队”改为 **Owner + Scouts + Critic + Diagnostician** 的单决策脊柱 | §6 |
| 4 | 任务集补 **T09 profile-guided、T10 coordination** | §7 |
| 5 | 指标补 **pass@k / pass^k、cost per verified success、coordination failures、groundedness** | §9 |
| 6 | 失败分类补 **MAST 协作失败**，归因补 **Who&When 思路 + 消融 + 反事实 replay** | §10 |
| 7 | 优化闭环从“改 Skill”扩展为 **按搜索空间选优化器**（GEPA/AFlow/MaAS/AIDE/AgentHPO） | §11 |
| 8 | 5 次实验改为 **screening（5–10）+ confirmation（10–20 或配对）** | §9、§14 |
| 9 | 新增 **action space schema** 与 **“可演化 vs 冻结”清单** | §11、§12、附录 B |
| 10 | 新增 **4 阶段实验矩阵**、停止规则、反证条件 | §9、§14、§16 |

**一句话**：v1.1 回答“怎么测”；v1.2 回答“测完之后，改哪一层、用什么搜索、怎么证明它真的有用”。

---

## 1. Executive decision

### 1.1 目标

提高**新 onboarding 任务首次生成“可执行、通过设备验证、满足质量约束”的 Recipe 的概率**，并且不靠隐藏失败、人工补救、反复重试或昂贵全量运行来美化结果。

### 1.2 两个必须分开的记分板

| 记分板 | 问题 | 主指标 |
| --- | --- | --- |
| **A. 工程可靠性** | agent 能不能发现能力、组出合法 Recipe、过预检、跑通、上设备？ | 首次验证成功率 |
| **B. 量化优化质量** | 在合法候选里，谁的质量/延迟/内存/大小权衡更好？ | 可行解的 Pareto 前沿 |

**不要合成一个 0–100 分。** 一个合法但质量差的 Recipe，和一个质量好但靠人工反复修补才得到的 Recipe，是两种不同的问题。

### 1.3 v1.2 的核心判断

1. **多 Agent 不是目标，是拓扑选择。** 它可能是 L1 独立重复、L2 角色协作、L3 流水线、L4 种群演化；四者回答不同问题。
2. **优化对象决定优化器。** 解空间、工作流、指令、实现是四个不同的搜索空间；用错优化器，比不优化更糟。
3. **onboarding 是强耦合串行链路，不适合全 peer 多 Agent。** 推荐“单 owner + 只读 scout + 独立 critic + 并行 diagnostician”。
4. **先有可信 oracle，再谈多 Agent。** 没有真实 `run(config)` 和 device/KPI oracle，Arena 只能测模拟器。
5. **没有归因，就没有优化。** 每次失败必须落到“最早因果边界 + 协作失败模式 + 责任 agent/step”。

---

## 2. Problem reframing

### 2.1 不要问“哪个 Agent 赢了”

要问：**在受控条件下，哪个改变能稳定提升任务完成率，机制是什么？**

- 单次获胜可能只是抽样运气；
- 重复出现的失败模式才是可行动的工程证据；
- 一个“更聪明的 Agent”可能只是更会猜评测集，而不是更懂 onboarding。

### 2.2 待验证假设

| 假设 | 内容 | 对应干预 |
| --- | --- | --- |
| H1 Skill 歧义 | 必选约束与建议没区分，触发条件不清 | Skill 改写 / GEPA |
| H2 能力不透明 | 函数存在，但签名、默认值、适用范围、前置条件、失败语义藏在实现里 | Repo map / capability contract |
| H3 验证缺口 | 错误配置到昂贵执行才暴露 | Preflight |
| H4 编排噪声 | Skill 输出不一致、工具太多、证据冲突 | 拓扑简化 / owner 决策 |
| H5 成功定义混乱 | 生成 JSON、执行成功、设备跑通、质量达标不是一回事 | Gate 序列 |
| H6 量化波动 | 校准、设备、runtime、种子、硬件竞争影响结果 | 固定协议 / 重复测量 |
| **H7 搜索空间错配**（v1.2 新增） | 团队在优化 prompt，真正瓶颈在工作流或参数 | 四类搜索空间分流 |

### 2.3 不做什么

- 不先发明 Agent 框架、共享记忆、自修改 Skill、新 MCP 层或复杂编排图；
- 不在基线测量前引入多 Agent 协作；
- 不把“多 Agent”当成组织架构图来设计。
- 不在同一个实验里同时改 Skill、契约、预检和工作流。

---

## 3. System under test

### 3.1 评估单位

一次真实 onboarding 任务：从用户请求，到经过验证的产物（Recipe + artifact + device/KPI 结果）。

Agent 的自然语言输出只是中间产物；**最终以 gate 结果为准**。

### 3.2 端到端边界

```text
01 Request
   ↓
02 Expert evidence（Skills / repo / dataset / device profile）
   ↓
03 Recipe（完整 JSON）
   ↓
04 Preflight（schema / capability / compatibility / resource）
   ↓
05 Execute（run(config)）
   ↓
06 Device eval（runtime / accuracy / latency / memory / power）
   ↓
07 Register（版本 / 审批 / lineage）
```

每一阶段输出带时间戳、机器可读的事件。

### 3.3 边界责任

| 边界 | Agent 负责 | 确定性系统负责 | 必须记录 |
| --- | --- | --- | --- |
| 证据 → Recipe | 整合证据、选支持选项、解释权衡 | 暴露版本/约束、校验必填项 | 证据 ID、选择/拒绝理由、provenance |
| Recipe → preflight | 根据诊断修复；不得发明 API | schema、能力查询、兼容性、dry-run | 错误/警告、耗时、修复次数 |
| Preflight → execute | 调用受支持的入口 | 隔离 workspace、锁依赖、资源限制 | 命令/API、退出码、stdout/stderr、artifact hash |
| Execute → device | 解读指标、决定是否受控调整 | 固定 evaluator、固定设备协议 | 质量、延迟、内存、兼容性 |
| Device → register | 总结适用条件与限制 | 只晋级已批准产物 | Recipe 版本、commit、数据版本、审批 |

### 3.4 被测系统必须是“真”的

v1.2 明确要求：

- **真实 `run(config)`**：不是 mock，不是随机数；
- **真实 device/KPI oracle**：至少一个可重复的 target；
- **真实 repo/API**：agent 能发现、能调用、能失败。

如果只用模拟器，Arena 可以验证 harness 本身，但不能得出“多 Agent 是否提升 onboarding”的结论。

---

## 4. 四类搜索空间（v1.2 新增）

### 4.1 为什么要拆

“优化 onboarding”可能指四件完全不同的事。把它们混在一个 loop 里，实验无法解释，优化器也会互相打架。

| 搜索空间 | 优化什么 | 典型动作 | 优化器 | 产物 | 评估 |
| --- | --- | --- | --- | --- | --- |
| **S1 解空间** | Recipe 参数 | bits、group size、calibration、mixed precision、exclusions、backend | AIDE / AgentHPO / Optuna | `recipe.json` 候选 | 质量/延迟/内存 Pareto |
| **S2 工作流** | stage、工具、顺序、分支 | 加/删/换 stage，重排，条件分支 | AFlow（MCTS） | workflow JSON | gate 序列 + 成本 |
| **S3 指令** | Skill、prompt、context playbook | 触发条件、步骤、证据要求、停止条件 | GEPA / ACE | `SKILL.md` / playbook 版本 | 成功率 + 成本 + groundedness |
| **S4 实现** | pipeline 代码 | runner、adapter、诊断器、缓存 | DGM / AlphaEvolve（后置） | code patch | 全量回归 + 沙箱 |

### 4.2 规则

1. **一次只动一个空间。** 不要在同一轮同时改 Skill 和工作流。
2. **先便宜后昂贵**：S3（指令）→ S2（工作流）→ S1（参数）→ S4（实现）。
3. **contract/evaluator 不在任何搜索空间里。** 事实和验收标准必须冻结。
4. **每个空间都有自己的回归集**；S3 的 patch 不能直接改 S1 的评估标准。

### 4.3 方法映射

| 如果失败主要来自 | 先试 | 不要先试 |
| --- | --- | --- |
| 找不到已有函数 / 不理解 API | repo map、capability contract | 换更大的模型 |
| 参数组合错 / 跨字段冲突 | preflight、typed contract | 多 Agent 辩论 |
| 流程顺序不对 / 少一步 | AFlow、workflow patch | GEPA 改 Skill |
| Skill 触发/步骤不清 | GEPA、Skill patch | 拓扑搜索 |
| 拓扑不对（该并行/该串行） | MaAS、L0–L4 对照 | 继续加 Agent |
| 参数没调好 | AIDE / AgentHPO / Optuna | 改 prompt |
| 实现有 bug | DGM / 人工 patch | 让 Agent 自由改代码 |

---

## 5. L0–L4 多 Agent 层级（v1.2 新增）

### 5.1 五个层级

| 层 | 定义 | 回答的问题 | 度量 | 主要风险 |
| --- | --- | --- | --- | --- |
| **L0** | 单 Agent | 任务本身难不难？ | 首次成功率 | 能力上限 |
| **L1** | 同配置独立 replicas | 方差多大？pass@k / pass^k？ | 方差、pass^k | 不是协作 |
| **L2** | 角色协作：owner + scouts + critic + diagnostician | 分工是否降低失败率？ | 首次成功率、coordination 失败 | handoff 丢信息 |
| **L3** | 流水线多 Agent：每阶段一个 Agent | 专业化/并行是否值得？ | gate 转化、wall-clock | context 分裂 |
| **L4** | 种群/演化：多配置竞争 | 哪种配置/工作流/技能更好？ | 相对 baseline 的效应 + 成本 | 过拟合、评估器被利用 |

### 5.2 关键区分

- **L1 不是“多 Agent 协作”**：它测的是采样方差，不能证明协作更好。
- **L4 不是“更多 Agent”**：它是离线搜索，不应该和在线任务混在一起。
- **L3 不是默认目标**：只有阶段间接口清晰、可以并行/独立验收时才值得。

### 5.3 onboarding 的推荐

| 场景 | 推荐层级 | 理由 |
| --- | --- | --- |
| 先测基线 | L0 + L1 | 先知道任务难不难、方差多大 |
| 证据收集（repo/API、dataset、device） | L2 scouts | 读操作可并行，且不改变决策 |
| 关键路径（recipe → compile → device） | 单 owner | 串行耦合，避免 context 分裂 |
| 失败诊断 | L2 diagnosticians | 多假设并行，owner 决策 |
| 质量参数搜索 | L4（离线） | 搜索 recipe 参数，不参与在线决策 |
| 技能/工作流优化 | L4（离线） | GEPA/AFlow 在 trace 上搜索 |

### 5.4 什么时候不该用多 Agent

- 任务强串行、上下文高度耦合（recipe → compile → device）；
- 失败主要来自工具/基础设施，而不是分工；
- 协调成本（token、延迟、handoff 错误）大于收益；
- 没有可信 evaluator，无法判断协作是否真的更好；
- 团队还没有 L0/L1 基线。

> 外部证据：Anthropic 的多 Agent 研究系统在 breadth-first 研究任务上报告显著提升，但 token 成本约 15×；Cognition 的实践文章警告 coding/长上下文任务的全 peer 多 Agent 会造成 context 碎片化。结论不是“多 Agent 无用”，而是“用错地方会更差”。

---

## 6. Arena 架构（v1.2 更新）

### 6.1 推荐拓扑：单决策脊柱 + 并行外围

```text
                 ┌─────────────────────────────┐
                 │ Owner / Orchestrator        │  唯一决策脊柱
                 │ - 持有 task + recipe 状态    │
                 │ - 分配预算                   │
                 │ - 选候选 / 签字              │
                 └───────┬─────────┬───────────┘
       并行证据（只读）  │         │  并行诊断
        ┌───────────────┘         └───────────────┐
        │ Scout team                              │ Diagnostician team
        │ - repo/API scout                        │ - log/trace analyst
        │ - model inspector                       │ - calibration analyst
        │ - dataset scout                         │ - compiler/device analyst
        │ - device/profile scout                  │ （每人只提 1 个 mutation）
        └───────────────┬─────────────────────────┘
                        │ evidence cards（typed, cited）
                 ┌──────▼─────────┐
                 │ Author          │  组 recipe（owner 或独立）
                 └──────┬──────────┘
                        │ recipe.json
                 ┌──────▼─────────┐
                 │ Critic/Preflight│  冻结 rubric，无修改权
                 └──────┬──────────┘
                        │ pass/fail + diagnostics
                 ┌──────▼─────────┐
                 │ Executor        │  run(config), logs, artifacts
                 └──────┬──────────┘
                        │ result
                 ┌──────▼─────────┐
                 │ Evaluator       │  冻结 oracle（device/KPI）
                 └─────────────────┘
```

### 6.2 决策权

| 角色 | 可以写 | 不可以写 |
| --- | --- | --- |
| Owner | task 状态、候选选择、最终 recipe | evaluator、测试数据 |
| Scout | evidence card、只读缓存 | recipe、共享状态 |
| Author | recipe 草稿（在 owner 授权下） | evaluator、其他 run |
| Critic | 诊断、pass/fail | recipe、阈值 |
| Executor | 运行日志、产物 | recipe、评估器 |
| Diagnostician | 失败假设、一个 mutation 建议 | 直接改 recipe |
| Evaluator | 指标、gate 结果 | 被任何 Agent 修改 |

### 6.3 为什么不是全 peer

- onboarding 是串行耦合；全 peer 会产生隐式决策冲突、重复工作、context 丢失；
- 多 Agent 的收益主要在“广度”（并行搜索/证据），不在“串行决策”；
- 单 owner 保留完整上下文，scout/diagnostician 只返回结构化证据，减少 context 污染。

### 6.4 如何验证这个架构

在同一批任务、同一 evaluator、同一预算下比较：

- **C0**：单 Agent
- **M1**：owner + scouts
- **M2**：owner + scouts + critic
- **M3**：pipeline-of-specialists
- **M4**：peer team（对照，预期更差/更贵）

用 MAST 编码协作失败，用 Who&When 思路归因。

---

## 7. 任务集（v1.2 更新）

### 7.1 基础任务（沿用 v1.1）

| ID | 任务原型 | 测什么 | Oracle |
| --- | --- | --- | --- |
| T01 | 已知正确的参考接入 | 能否复现已验证路径 | Recipe + 执行 + 设备容差 |
| T02 | 发现已有函数 | 是否调用库能力而非重写 | 预期 API 家族 |
| T03 | 不支持的配置 | 能否尽早拒绝 | 早停 + 有依据的解释 |
| T04 | 缺失/歧义证据 | 能否提问或选安全默认 | 阻塞字段识别 |
| T05 | 非直观参数组合 | 能否映射到真实支持空间 | Schema + 跨字段约束 |
| T06 | 执行失败恢复 | 能否做最小、有证据的修复 | 一次受控修复 |
| T07 | 质量约束量化 | 能否在约束下优化质量 | Pareto |
| T08 | 未见过模型/设备 | 是否泛化 | held-out 通过 |

### 7.2 v1.2 新增

| ID | 任务原型 | 测什么 | Oracle |
| --- | --- | --- | --- |
| **T09** | profile-guided | 给 device profile，选优化动作并复测 | 指标改善 + 无回归 |
| **T10** | coordination | 需要 repo/API、dataset、device 三源证据才能组 Recipe | 正确 handoff + 首次成功 |

### 7.3 Oracle 类型

- 精确 Recipe（已知参考）；
- 合法参数范围 / 跨字段约束；
- 确定性 predicate（schema + preflight + execution）；
- 设备 KPI 阈值（质量/延迟/内存/热）；
- 人工评审（仅用于歧义样本，盲评）。

### 7.4 划分

- **discovery**：3 个任务，用于发现失败模式；
- **validation**：2 个任务，用于确认干预；
- **held-out**：2–3 个任务，只在最后用；
- 任务、数据、设备、评测协议冻结版本。

---

## 8. Run protocol（v1.2 更新）

### 8.1 五个阶段

| 阶段 | 做什么 | 退出条件 |
| --- | --- | --- |
| **P0 Prepare** | 冻结 commit/Skills/依赖/模型/评估器；选任务；定预算 | 另一位工程师能复现 |
| **P1 Baseline** | L0 + L1，5–10 reps；不共享结果 | 能识别主要失败模式与方差 |
| **P2 Diagnose** | 按最早边界 + MAST 分类；Who&When 归因 | 前 3 个失败类有证据 |
| **P3 Intervene** | 一次改一个空间/一个变量；held-out 检查 | 能量化效应与成本 |
| **P4 Promote** | 只晋级可复现、无回归的改动 | 更新回归集与版本 |

### 8.2 实验清单（manifest）

每次 run 必须记录：

```json
{
  "experiment_id": "exp-2026-11-01-T01-L2-S3",
  "run_id": "run-03",
  "task_id": "T01",
  "search_space": "S3",
  "topology": "L2",
  "baseline": {
    "repo_commit": "sha",
    "skills_hash": "sha256:...",
    "contract_version": "v...",
    "model_endpoint": "...",
    "evaluator_version": "..."
  },
  "budget": {"tokens": 0, "gpu_minutes": 0, "wall_clock_min": 0},
  "held_out": false,
  "events": "events.jsonl",
  "recipe": "recipe.json",
  "result": "evaluation.json"
}
```

### 8.3 纪律

- 同一 task / assets / hardware；
- 随机化 run 顺序；
- 不共享可变输出；
- 不自动改共享 Skills；
- 不让候选自己评分；
- 记录每次 retry、参数变化、人工介入。

---

## 9. 指标、统计与实验矩阵（v1.2 新增）

### 9.1 Gate 序列

| Gate | 检查 | 失败含义 |
| --- | --- | --- |
| **G1** | Recipe schema / 必填字段 | 结构化输出失败 |
| **G2** | 跨字段 + 能力 + 兼容性 preflight | 领域约束失败 |
| **G3** | `run(config)` 执行成功、产物存在 | 实现/环境失败 |
| **G4** | 目标设备加载/运行 | 部署失败 |
| **G5** | 质量/延迟/内存/热达标 | 优化质量失败 |

**主指标**：first-attempt verified success = G5 且无人工修复、无第二次 Recipe。

### 9.2 指标

| 类别 | 指标 |
| --- | --- |
| 可靠性 | 首次成功率、G1–G5 转化率、pass@1、pass@k、pass^k |
| 成本 | tokens、GPU-min、wall-clock、人工介入、**cost per verified success** |
| 协作 | handoff 错误、重复工作、证据冲突、决策反复（MAST） |
| 可信度 | 关键参数有证据引用的比例（groundedness） |
| 泛化 | held-out 任务通过率 |
| 质量 | 质量、延迟、内存、大小、Pareto |

### 9.3 统计

- **Screening**：3 tasks × 5 reps；只用于发现粗粒度差异；
- **Confirmation**：2 tasks × 10–20 reps 或配对任务；
- 配对 bootstrap 95% CI；mixed-effects（task/run 随机效应）；
- 预注册 primary metric + 2–3 个假设；FDR 控制；
- 报告 effect size + CI，不只 p 值；
- 不把 best-of-n 当 pass@1；同时报 pass@k 与 pass^k。

### 9.4 实验矩阵

**Stage 1：拓扑（先回答“多 Agent 有没有用”）**

| ID | 因子 | 水平 | 任务 × reps | 主指标 | 决策 |
| --- | --- | --- | --- | --- | --- |
| E1 | topology | L0, L1, L2, L3（L4 只做离线对照，不参与在线任务） | T01/T02/T03 × 5 | 首次成功率、coordination、成本 | 是否继续多 Agent |

**Stage 2：知识（在胜者上逐项加）**

| ID | 因子 | 水平 | 任务 × reps | 主指标 | 决策 |
| --- | --- | --- | --- | --- | --- |
| E2 | knowledge | baseline, repo map, contract, preflight | 3 × 10 | G1–G5、修复负担 | 是否值得建契约层 |

**Stage 3：搜索（离线优化）**

| ID | 因子 | 水平 | 任务 × reps | 主指标 | 决策 |
| --- | --- | --- | --- | --- | --- |
| E3 | instruction | baseline vs GEPA | 3 × 10 + held-out | 成功率、成本 | 是否晋级 Skill patch |
| E4 | workflow | baseline vs AFlow | 3 × 10 + held-out | gate 转化、成本 | 是否采用 workflow |
| E5 | topology | best fixed vs MaAS | 3 × 10 + held-out | 成功率、成本 | 是否动态路由 |
| E6 | params | baseline vs AIDE/AgentHPO | 2 × 20 | Pareto | 是否进入质量轨 |

**Stage 4：实现（后置）**

| ID | 因子 | 水平 | 任务 × reps | 主指标 | 决策 |
| --- | --- | --- | --- | --- | --- |
| E7 | implementation | baseline vs DGM/AlphaEvolve | 2 × 20 | 全量回归 | 是否值得自修改 |

**规则**：E1 不通过，不进入 E2；E2 没有明确瓶颈，不进入 E3；E3–E6 必须用 held-out 确认；E7 只在沙箱、可回滚、人工审批下做。

---

## 10. 失败分类与归因（v1.2 更新）

### 10.1 两套标签

**领域失败（F01–F10）**：最早因果边界。

| 代码 | 失败类 | 典型信号 | 候选干预 |
| --- | --- | --- | --- |
| F01 | 任务理解 | 模型/设备/目标错 | 任务 schema / 澄清策略 |
| F02 | Skill 路由 | 该用的 Skill 没触发 | 触发条件 |
| F03 | API 发现 | 找不到已有函数/重复实现 | repo map / 索引 |
| F04 | 契约不匹配 | 类型、默认值、组合错 | typed contract |
| F05 | Recipe 组合 | 单字段合法但整体冲突 | schema + preflight |
| F06 | 执行/runtime | 配置看起来对但跑挂 | 诊断/环境锁 |
| F07 | 设备部署 | 产物加载/约束失败 | 兼容性矩阵 |
| F08 | 质量回归 | 跑通但质量/性能不达标 | 搜索协议 / guardrail |
| F09 | 评估噪声 | 指标随环境漂移 | 固定协议/重复测量 |
| F10 | 安全/权限 | 越权、数据边界 | 策略/审批 |

**协作失败（MAST）**：多 Agent 特有。

- specification：任务、角色、边界没定义清楚；
- inter-agent misalignment：handoff 丢信息、忽略输入、重复工作、决策冲突；
- task verification：过早结束、验证不完整、绕过评估器。

每个失败 trace 打两个标签：`F0x` + `MAST 模式`。

### 10.2 归因

1. **Who&When 思路**：预测“责任 agent / step”；
2. **消融**：去掉一个 role/tool，观察结果变化；
3. **反事实 replay**：用 oracle 修正失败 step，观察下游是否恢复；
4. **人工抽检**：歧义样本盲评；
5. **禁止**：让 agent 自己写“我没问题”的复盘作为唯一证据。

### 10.3 归因输出

```json
{
  "trace_id": "...",
  "earliest_boundary": "F04",
  "mast": ["inter_agent_misalignment:handoff"],
  "responsible": {"agent": "repo-scout", "step": 7},
  "evidence": ["events/00042.json", "events/00057.json"],
  "confidence": 0.72,
  "candidate_intervention": "contract:add_precondition"
}
```

---

## 11. 优化闭环：从 trace 到 patch（v1.2 更新）

### 11.1 闭环

```text
Trace collection
  → classify (F0x + MAST)
  → attribute (Who&When + ablation + replay)
  → propose one patch
  → choose optimizer by search space
  → evaluate on regression + held-out
  → promote / rollback
  → update regression suite
```

### 11.2 Patch 格式

每个 patch 必须包含：

1. 失败事件 ID 与证据；
2. 根因假设；
3. 最小 diff（改了哪些文件）；
4. 预期指标变化；
5. 潜在回归/成本；
6. 回滚方式；
7. 验证任务（至少一个 held-out）。

### 11.3 按搜索空间选优化器

| 空间 | 优化器 | 输入 | 产物 | 晋级条件 |
| --- | --- | --- | --- | --- |
| S3 指令 | **GEPA** | 失败 trace + reflection | Skill patch | held-out 提升、成本不恶化 |
| S3 指令 | ACE | context playbook | context 版本 | 长期记忆有效、无膨胀 |
| S2 工作流 | **AFlow** | stage 图 + gate | workflow JSON | gate 转化提升、成本可控 |
| L4 拓扑 | **MaAS** | 任务分布 + 候选拓扑 | 路由策略 | 平均提升、成本下降/持平 |
| S1 参数 | **AIDE / AgentHPO / Optuna** | recipe 空间 + oracle | 候选 Pareto | 质量/延迟/内存改进 |
| S4 实现 | **DGM / AlphaEvolve** | 代码 + 全量回归 | code patch | 沙箱、回滚、人工审批 |

### 11.4 可演化 vs 冻结

| 资产 | 状态 | 理由 |
| --- | --- | --- |
| `SKILL.md` / prompt | **可演化** | 流程知识，允许 GEPA/ACE |
| workflow 图 | **可演化** | 允许 AFlow |
| 拓扑/路由 | **可演化** | 允许 MaAS |
| recipe 候选 | **可演化** | 允许 AIDE/AgentHPO |
| capability contract | **冻结（从源码生成）** | 事实不能由 LLM 发明 |
| evaluator / acceptance | **冻结** | 防止自评分/篡改 |
| 测试数据 / held-out | **冻结** | 防止泄漏 |

### 11.5 晋级规则

一个 patch 只有在以下条件全部满足时才晋级：

- 在 regression 集上不退化；
- 在至少一个 held-out 上有提升；
- effect size + 95% CI 支持；
- cost per verified success 不恶化；
- 有人类可读的决策记录与回滚方案；
- 通过安全/权限检查。

---

## 12. 量化质量轨（v1.2 更新）

### 12.1 和工程轨分开

- 工程轨问“能不能跑通、能不能上设备”；
- 质量轨问“在可行解里，哪个质量/延迟/内存权衡更好”；
- 不要用工程轨的 GPU 预算跑质量搜索。

### 12.2 Action space

| 层 | 可优化字段 | 约束来源 | 验证 |
| --- | --- | --- | --- |
| model | model_uri、task、architecture、context | registry/license | inspect |
| calibration | dataset、samples、seq_len、sampling | dataset card/privacy | validate |
| quantization | method、bits、group_size、act_quant、mixed precision、exclusions | library schema / platform profile | preflight |
| runtime | backend、version、compiler flags | runtime env / SDK | compatibility |
| device | pool、matrix、OS、KPI thresholds | device profile | device test |
| acceptance | max drop、latency、memory、thermal | business | KPI report |

### 12.3 两阶段评估

1. **Cheap screen**：schema、兼容性、校准数据、静态资源估算、小规模代表评估、提前终止；
2. **Expensive confirm**：入围候选，固定设备/runtime、预热、重复、输入、版本、artifact hash。

### 12.4 搜索方法

- **AIDE**：树搜索，适合“代码/实验空间”；
- **AgentHPO**：LLM agent 迭代 propose/evaluate；
- **Optuna**：成熟 BO，适合低维参数；
- **AutoQuant / FlexQuant / UDP**：量化算法/混合精度搜索的参考，不是 agent 框架。

### 12.5 输出

- 可行候选的 Pareto 前沿；
- 每个候选的 metric vector（质量、延迟、内存、大小）；
- provenance（recipe hash、model hash、calibration set hash、evaluator version）；
- 人工选择依据（部署优先级）。

---

## 13. 隔离与安全（v1.2 更新）

### 13.1 不变量

- 源码/数据不出公司批准边界；
- 模型路由、CLI 遥测、插件、日志、归档全部核验；
- 每个 run 独立 workspace；
- evaluator 对 worker 只读；
- 不共享可变输出；
- 预算/租约/超时/清理。

### 13.2 威胁模型

| 威胁 | 防护 |
| --- | --- |
| Agent 读无关文件 | 只读 repo、最小 workspace、路径白名单 |
| CLI 外发上下文 | 内网模型端点、网络策略、遥测审计 |
| 并发覆盖共享配置 | 每 run 独立目录、无共享写 |
| 复用旧产物 | artifact hash + 运行 ID |
| 不可信 Skill/仓库内容诱导越权 | 工具权限、命令白名单、评审 |
| Agent 改 evaluator/阈值 | 评估器外部化、只读、版本校验 |
| GPU 竞争导致指标失真 | 租约、独占、固定协议 |
| 日志泄密 | 脱敏、保留期、访问控制 |

### 13.3 执行前提

Codex/Claude Code 是候选 worker，不是自动批准。必须先核验企业配置、模型路由、遥测、扩展策略、网络路径；不符合时使用已批准的内网 CLI/模型端点或最小内部封装。

---

## 14. 实施计划（v1.2 更新）

### 14.1 四周计划

| 时间 | 阶段 | 内容 | 退出条件 |
| --- | --- | --- | --- |
| **Day 1–2** | P0 | 冻结 baseline；选 T01–T03；定义 oracle；建 manifest/workspace | 另一位工程师能复现 |
| **Day 3–6** | P1 | L0 + L1，5 reps；跑通 trace/evaluator | 能得到基线成功率与方差 |
| **Week 2** | P2 + E1 | 失败分类 + 拓扑筛选（L0–L3） | 知道多 Agent 是否有用 |
| **Week 3** | E2 | 在胜者上加 repo map/contract/preflight | 知道瓶颈在“知识”还是“执行” |
| **Week 4** | E3–E6 | GEPA/AFlow/MaAS/AIDE 各做一个小实验 | 至少一个可复现改进，或明确证伪 |
| **可选 Week 5–6** | E7 + 质量轨 | DGM/AlphaEvolve 沙箱；Pareto | 有/无继续投资证据 |

### 14.2 资源

| 资源 | 建议 | 扩展规则 |
| --- | --- | --- |
| 并行 agent | 3–5 | 只在硬件/API 配额允许时增加 |
| 任务 | 2–3 个诊断任务 | 稳定后扩到 6–8 |
| 全量量化 | 1 个参考任务 + shortlist | cheap screen 广，expensive 窄 |
| 人工评审 | 每个失败 + 所有晋级 | 先自动化明确 predicate |

### 14.3 停止规则

- held-out 无提升；
- coordination 成本 > 收益；
- cost per verified success 变差；
- 失败主要来自基础设施/评估器；
- 单因素干预无法复现。

---

## 15. Deliverables（v1.2 更新）

| # | 交付物 | 内容 |
| --- | --- | --- |
| 1 | Run manifest + leaderboard | 任务、条件、run ID、版本 hash、gate、成本、原始指标 |
| 2 | Trace bundle | 事件流、Recipe、日志、校验、artifact hash、决策记录 |
| 3 | Failure taxonomy | F0x + MAST + 归因 + 复现次数 + 候选干预 |
| 4 | **Topology comparison**（新增） | L0–L4 的成功率、协调失败、成本 |
| 5 | **Credit assignment**（新增） | 责任 agent/step + 证据 + 置信度 |
| 6 | Patch candidates | Skill diff、contract、validator、workflow JSON |
| 7 | Optimization frontier | Pareto + provenance |
| 8 | Decision record | 改了什么、为什么、证据、回归、回滚 |

---

## 16. 风险与反证（v1.2 更新）

| 风险 | 信号 | 响应 |
| --- | --- | --- |
| 赢家只是采样噪声 | 排名随重复变化 | 增加配对重复；优先确定性约束 |
| 过拟合参考任务 | 基线提升但 held-out 退化 | 保留 held-out；限制单变量 |
| 多 Agent 协调成本 > 收益 | token/延迟上升、handoff 错误多 | 退回 L0/L2；减少角色 |
| 拓扑搜索过拟合 | 只在已见任务上路由正确 | 留出任务 + 成本约束 |
| 契约 stale | 元数据与源码签名漂移 | 源码生成 + 版本绑定 + 一致性测试 |
| Workflow 搜索利用 evaluator | gate 通过但质量差 | 冻结 evaluator + 人工抽检 |
| 质量排序受环境噪声影响 | 延迟/质量随负载漂移 | 固定协议、重复测量 |
| CLI 不合规 | 无法证明数据边界 | 停止该 runtime；换内网端点 |

**反证条件**：

1. 如果当前系统在代表性任务上首次成功率已经很高，Arena 只应做回归测试，不是平台项目；
2. 如果失败几乎都来自基础设施/硬件，先修基础设施，Skill/契约杠杆有限；
3. 如果单因素干预无法在 held-out 上复现，不要上多 Agent 或自演化；
4. 如果多 Agent 的协调失败率高于收益，保持单 Agent；
5. 如果 evaluator 不可信，停止优化，先修评估。

---

## 17. Prompts（v1.2 更新）

### 17.1 Baseline worker

```text
你正在执行一次受控的端侧模型 Onboarding 基准任务。

目标：使用当前隔离工作区中的仓库、Skills 与批准工具，严格满足任务验收条件。

规则：
1. 不要假设 API 存在；先检查仓库与可用 Skills。
2. 优先使用已有且受支持的库能力；无法验证时说明证据缺口，不要编造函数或参数。
3. 生成要求的 Recipe JSON；所有输出写入指定 run 目录。
4. 只使用批准工具和配置的内网模型端点；不访问外部服务或无关文件。
5. 昂贵执行前运行可用的验证/预检；若不存在，记录已检查内容与剩余不确定性。
6. 不得修改评估器、验收条件、基线源码、共享 Skills 或其他 run 的文件。
7. 失败时根据真实日志分类，只做有证据支持的修改，并记录每次重试与参数变化。
8. 没有机器可验证证据就不能宣称成功；必须区分 Recipe 生成、Schema 有效、执行成功、设备验证与质量达标。

交付：recipe.json、简短运行报告（API/函数、证据引用、参数决策、校验、重试、未解决问题）、必要日志与产物 hash。
```

### 17.2 Owner

```text
你是本次 onboarding 任务的唯一决策者。

职责：
- 维护 task / recipe 状态与预算；
- 向 scouts 请求证据，向 diagnosticians 请求失败假设；
- 只选择有证据支持的 Recipe；
- 在 preflight/executor/evaluator 返回失败时，决定“修、换候选、停止”；
- 不做没有证据的猜测；不修改 evaluator/验收标准。

输出：决策记录（候选、证据、拒绝理由、预算、下一步）。
```

### 17.3 Scout

```text
你是只读证据 scout。只返回结构化 evidence card，不做最终决策。

Evidence card：
- claim：一句话结论；
- evidence：文件/函数/文档/指标 + 引用；
- confidence：high/medium/low；
- applicability：模型/平台/版本范围；
- open_questions：还缺什么。
```

### 17.4 Critic

```text
你是独立 critic。使用冻结 rubric 检查 Recipe：
- schema / 必填字段；
- 跨字段约束；
- 能力/兼容性；
- 资源估算；
- 风险与回滚。

只返回 pass/fail + 具体诊断；不得修改 Recipe 或阈值。
```

### 17.5 Diagnostician

```text
你是失败诊断者。基于日志、trace、指标提出一个最可能的根因，并只给一个最小 mutation 建议。

输出：
- earliest_boundary（F0x）；
- MAST 模式（如适用）；
- 证据；
- 根因假设；
- 一个 mutation；
- 预期效果与风险。
```

### 17.6 Improvement proposal

```text
Review the supplied traces and failure taxonomy. Propose one narrowly scoped change.

You may propose a Skill patch, repo map/API index, contract metadata, preflight check, workflow change, or diagnostic improvement. Do not modify the baseline directly.

Include: failure event IDs, evidence, smallest diff, falsifiable prediction, regression/cost, test plan incl. held-out, rollback.
```

---

## 18. Decision gates（v1.2 更新）

| 观察到的证据 | 决策 | 不要做 |
| --- | --- | --- |
| 反复发现不了已有函数 | 做 repo map/API 索引/契约 | 再加一个通用 Agent |
| 找到函数但组合错误 | typed precondition + preflight | 只堆示例 |
| Recipe 合法但执行错误难定位 | 诊断/失败分类/重试边界 | 盲目改参数 |
| 执行成功但质量不达标 | 单独质量搜索（AIDE/AgentHPO） | 先重写 Skills |
| Skill-only 改动在 held-out 上低成本提升 | 晋级 Skill patch + 回归 | 先建 registry |
| 契约+预检相对 Skill-only 有可重复收益 | 投资轻量契约层 | 默认上 MCP |
| 多 Agent 协调失败多、成本高 | 回到 L0/L2，减少角色 | 继续加 Agent |
| Workflow 搜索稳定提升 | 采用 AFlow 产物 + 回归 | 手工拍脑袋 |
| 拓扑路由有稳定收益 | 采用 MaAS 路由 | 全任务强制多 Agent |
| 所有干预都无改善 | 检查模型/runtime、任务歧义、评估器 | 推导“需要更多 Agent” |

---

## 19. 一句话

**不要先问“用几个 Agent”，先问“我要搜索的是解空间、工作流、指令，还是实现”。** 四类问题对应四种优化器；多 Agent 只是其中一种搜索算子。对 onboarding 这种强耦合链路，最稳的起点是“单 owner + 并行只读 scout + 独立 critic + 并行 diagnostician”，再用 GEPA/AFlow/MaAS 离线演化，最后才考虑 DGM/AlphaEvolve 这类自修改系统。

---

## 附录 A：方法选择矩阵

| 方法 | 搜索空间 | 契合度 | 成熟度 | 成本 | 现在用？ |
| --- | --- | --- | --- | --- | --- |
| **GEPA** | S3 指令 | 高 | 高 | 中 | ✅ |
| **AFlow** | S2 工作流 | 高 | 高 | 中高 | ✅ |
| **MaAS** | L4 拓扑 | 高 | 中 | 中高 | ✅（小规模） |
| **MAST** | 诊断 | 高 | 高 | 低 | ✅ |
| **Who&When** | 归因 | 高 | 中 | 中 | ✅ |
| **AIDE** | S1 解空间 | 高 | 高 | 中 | ✅ |
| **AgentHPO** | S1 解空间 | 高 | 中 | 中 | ✅ |
| **ProfilingAgent** | S1/S2 领域闭环 | 高 | 早期 | 中 | 试点 |
| **ShrinkLLM** | 压缩流水线 | 高 | 早期 | 中 | 参考 |
| **LLM-Guided Toolbox** | 边缘优化 | 高 | 早期 | 中 | 参考 |
| **ML-Master / R&D-Agent** | 长程 ML | 中高 | 高 | 高 | 参考 |
| **Anthropic / Cognition** | 多 Agent 设计 | 高 | 实践 | 低 | ✅（设计原则） |
| **DGM / AlphaEvolve** | S4 实现 | 中 | 高 SOTA | 很高 | 后置 |
| **Agent Lightning** | 训练 | 中 | 中 | 高 | 后置 |

---

## 附录 B：Action space schema（示例）

```json
{
  "model": {
    "model_uri": {"type": "string", "required": true, "source": "registry"},
    "task_type": {"type": "string", "enum": ["text-generation", "classification"]},
    "context_length": {"type": "integer", "max_source": "model_config"}
  },
  "calibration": {
    "dataset_id": {"type": "string", "required": true},
    "samples": {"type": "integer", "range": [128, 4096]},
    "seq_len": {"type": "integer", "range": [128, 8192]},
    "sampling": {"type": "string", "enum": ["random", "diverse", "business-weighted"]}
  },
  "quantization": {
    "method": {"type": "string", "enum": ["awq", "gptq", "int8_weight_only", "fp8", "mixed"]},
    "bits": {"type": "integer", "enum": [4, 8]},
    "group_size": {"type": "integer", "enum": [32, 64, 128, null]},
    "activation_quant": {"type": "boolean"},
    "exclude_layers": {"type": "array", "items": "string"}
  },
  "runtime": {
    "backend": {"type": "string", "enum": ["vllm", "tensorrt-llm", "qnn", "neuron"]},
    "version": {"type": "string", "pinned": true},
    "compiler_flags": {"type": "object"}
  },
  "device": {
    "pool_id": {"type": "string"},
    "matrix": {"type": "array"},
    "kpi": {"type": "object"}
  },
  "acceptance": {
    "max_accuracy_drop": {"type": "number", "default": 0.01},
    "latency_p95_ms": {"type": "number"},
    "max_memory_mb": {"type": "integer"},
    "thermal_limit_c": {"type": "number"}
  }
}
```

**规则**：每个字段必须有 `source`、`constraint`、`preflight`；agent 只能改允许字段。

---

## 附录 C：来源

外部方法/证据见 [model-onboarding-lab-inputs.md](model-onboarding-lab-inputs.md)。关键来源：

- GEPA（ICLR 2026）、AFlow（ICLR 2025）、MaAS（ICML 2025）
- MAST（NeurIPS 2025 D&B）、Who&When（ICML 2025）
- ProfilingAgent、ShrinkLLM（IEEE MDM 2026）、LLM-Guided Agentic Optimization Toolbox
- ML-Master、R&D-Agent、AIDE、AgentHPO、AutoML-Agent
- MLE-bench（ICLR 2025）、MLAgentBench（ICML 2024）、Agentless
- Anthropic 多 Agent 研究系统、Cognition 多 Agent 实践
- DGM（ICLR 2026）、AlphaEvolve、Agent Lightning
- AutoQuant、FlexQuant、UDP

> 数字与结论以原文为准；本文是设计输入，不是独立复现。
