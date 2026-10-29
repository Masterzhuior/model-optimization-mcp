# Capability Arena 多 Agent 输入包

> 目的：给 `agentic_onboarding_capability_arena_design_v1_1` 补三类输入：
> 1. 真正契合、或当前 SOTA、或近期被验证“确实好用”的方法；
> 2. 多 Agent 在 model onboarding 链路里的正确用法（以及不该用的地方）；
> 3. 一套可以直接排期的实验、指标、统计和防作弊方案。
>
> 证据说明：以下内容基于论文标题/摘要、官方博客和搜索片段整理。标注“报告”的数字请以原文为准；仅标题/摘要的来源已单独标注。本文是设计输入，不是对 SOTA 的独立复现。

---

## 0. 先对齐：“多 Agent 尝试”要拆成 5 层

这两份设计稿里“multi-agent”有时指“多个独立 agent 跑同一个任务”，有时指“多个角色协作”。这两个东西回答的问题完全不同，必须拆开。下表中 L1–L4 才是四种不同的“多 agent”用法，L0 是对照基线：

| 层 | 是什么 | 回答什么问题 | 典型做法 | 不该和谁混 |
| --- | --- | --- | --- | --- |
| **L0** | 单 agent 多次尝试 | 任务本身难不难、模型能力够不够 | 单 agent + 重试 | 不要叫“多 agent” |
| **L1** | 同一配置的独立 replicas | 方差多大、pass@k / pass^k | 独立 workspace、冻结基线 | 不是协作，不能证明“多 agent 更好” |
| **L2** | 角色协作（owner + scouts + critic） | 分工是否降低失败率 | orchestrator-worker、author-critic | 不要和 L4 的“种群”混 |
| **L3** | 流水线多 agent（每阶段一个 agent） | 专业化/并行是否值得 | pipeline-of-specialists | 串行耦合任务容易 context 分裂 |
| **L4** | 种群/演化（多配置竞争） | 哪种配置/工作流/技能更好 | GEPA、AFlow、MaAS、DGM | 不是“更多 agent”，是搜索 |

**设计含义**：Arena 的第一层实验应该只测 L0/L1（基线 + 方差）；第二层再测 L2/L3（协作是否值得）；L4 是离线优化器，不要和在线任务混在一起。

---

## 1. 结论先行（给设计负责人）

1. **onboarding 是强耦合、长上下文、串行决策的链路，不适合全 peer 多 agent。** 推荐“单 owner + 只读 scout + 独立 critic + 并行 diagnostician”的 hub-and-spoke：多 agent 用在探索宽度（证据、失败假设、候选 recipe），不用在串行决策耦合（recipe → compile → device）。
2. **最值得先接的优化器只有 4 个**：GEPA（技能/提示演化）、AFlow（工作流搜索）、MaAS（拓扑搜索）、AIDE/AgentHPO（recipe 参数搜索）。前三个优化“流程/指令”，最后一个优化“参数”。
3. **评估/归因补两个**：MAST（多 agent 协作失败分类）+ Who&When（失败归因到 agent/step）。这解决“多 agent 到底哪里坏了、该改谁”。
4. **领域内最接近的三篇**：ProfilingAgent、ShrinkLLM、LLM-Guided Agentic Optimization Toolbox。它们把“profile → 诊断 → 选优化动作 → 复测”做成 agent 闭环，和 onboarding 的设备反馈最贴。
5. **5 次只够发现失败模式，不够给干预排名。** screening 用 5–10 次，confirmation 用 10–20 次或配对任务；报 pass@1 / pass^k / 成本每成功，不要只报 best-of-n。
6. **先有可信 oracle，再谈多 agent。** 没有真实 `run(config)` 和 device/KPI oracle，Arena 测的是模拟器。

---

## 2. 契合度 × 成熟度：先看这张矩阵

| | 早期 / 需验证 | 成熟 / 可直接借 |
| --- | --- | --- |
| **高契合** | MaAS、Who&When、ProfilingAgent、ShrinkLLM、LLM-Guided Toolbox | GEPA、AFlow、MAST、AIDE、AgentHPO、MLE-bench、MLAgentBench、Agentless |
| **高 SOTA / 低即用** | DGM、AlphaEvolve、Agent Lightning | — |
| **低契合** | 通用多 agent 框架（AutoGen/CrewAI 等）只当编排层，不构成实验证据 | — |

读法：先从右上角拿“现在就能用”的；右下没有，是因为真正高契合的方法大多还在早期；左下不是不能碰，而是不要拿它当第一周的 PoC。

---

## 3. 最契合的输入（Tier 1：现在就能用）

### 3.1 GEPA — 用 trace 演化 SKILL.md，而不是让 agent 自由改系统

- **是什么**：Reflective Prompt Evolution，用自然语言反馈 + Pareto 选择演化 prompt；ICLR 2026。
- **为什么契合**：你的核心资产是 13 个 `SKILL.md` 和 agent 指令；GEPA 正好把“失败轨迹 + 反馈”变成“下一版指令”，且比 RL 更省 rollout（论文报告在部分任务上优于 GRPO，且所需 rollout 少一个数量级；具体数字以原文为准）。
- **怎么用**：
  - 每个失败 trace 生成一段 reflection（失败边界、证据、建议）；
  - 候选 patch **只改 skill 文本**；
  - 在固定回归集 + 至少一个 held-out 上评估；
  - 保留 Pareto 前沿（成功率 vs 成本），不要只留最高分。
- **不要做**：不要让 GEPA 改契约/评估器。契约是事实，必须从源码生成；GEPA 只演化“procedure”。
- **来源**：[GEPA (ICLR 2026)](https://proceedings.iclr.cc/paper_files/paper/2026/hash/0e9e708b6f48e14fd0ac29e167413f76-Abstract-Conference.html)

### 3.2 AFlow — 搜索 onboarding 工作流图

- **是什么**：把 agentic workflow 表示成代码，用 MCTS 搜索“用哪些节点、怎么连”；ICLR 2025。论文报告在多个基准上优于手工工作流（平均约 5.7%，以原文为准）。
- **为什么契合**：你的 pipeline 有明确 stage 和分支（是否 device farm、是否 mixed precision、是否 compile），天然是 workflow 搜索空间。
- **怎么用**：
  - 节点 = 现有 tool / skill；边 = 依赖；
  - 评估 = Arena 的 gate 序列；
  - 搜索预算固定，产出可读的 workflow JSON（不是黑盒）；
  - 只在“有稳定 evaluator”后跑，否则 MCTS 会过拟合噪声。
- **来源**：[AFlow (ICLR 2025)](https://proceedings.iclr.cc/paper_files/paper/2025/hash/5492ecbce4439401798dcd2c90be94cd-Abstract-Conference.html)

### 3.3 MaAS — 搜索多 agent 拓扑，而不是手拍

- **是什么**：Agentic Supernet，按 query 采样不同多 agent 架构；ICML 2025。
- **为什么契合**：你正要从“单 agent”走向“多 agent”，但不知道该用哪种拓扑；MaAS 把拓扑当搜索空间，按任务难度/类型路由，并考虑推理成本。
- **怎么用**：
  - 先定义 5–8 个候选拓扑（single、owner+scouts、author-critic、pipeline、population）；
  - 用 MaAS 的思路做 cost-aware 选择；
  - 不要一开始就上全量搜索，先在 2–3 个任务上验证路由是否有意义。
- **风险**：拓扑搜索容易过拟合任务集；必须留出任务 + 成本约束。
- **来源**：[MaAS (ICML 2025)](https://arxiv.org/abs/2502.04180)

### 3.4 MAST — 多 agent 失败的 14 种模式

- **是什么**：Multi-Agent System Failure Taxonomy；3 大类（specification、inter-agent misalignment、task verification）、14 个失败模式；NeurIPS 2025 D&B。
- **为什么契合**：你的 F01–F10 是“任务链路”分类；MAST 补的是“协作”分类。两者正交，应该一起用。
- **怎么用**：
  - 每个失败 trace 打两个标签：最早因果边界（F0x）+ MAST 模式；
  - 统计哪类协作失败最常见；
  - 再决定加 critic、改 handoff、还是减少 agent。
- **来源**：[MAST (NeurIPS 2025)](https://arxiv.org/abs/2503.13657)

### 3.5 Who&When — 把失败归因到 agent/step

- **是什么**：自动失败归因 benchmark/方法，回答“哪个 agent、在哪一步导致失败”；ICML 2025。
- **为什么契合**：多 agent 最大的坑是“大家都觉得自己没错”；没有归因，就无法做 credit assignment，也无法决定删谁/加谁。
- **怎么用**：
  - trace 做 step-level 标注；
  - 用 Who&When 的思路预测“责任 agent/step”；
  - 人工抽检；
  - 把归因结果作为 patch 的证据，而不是让 agent 自己写复盘。
- **来源**：[Who&When (ICML 2025)](https://arxiv.org/abs/2505.00212)

### 3.6 ProfilingAgent — 用 profiling 指导优化动作

- **是什么**：Profiling-Guided Agentic Reasoning for Adaptive Model Optimization（2025）。
- **为什么契合**：你的 device farm 已经有 latency/memory/power/thermal；ProfilingAgent 的思路是把这些指标变成 agent 的 observation，指导下一轮优化，而不是只出一张 KPI 报告。
- **怎么用**：
  - 把 profile 结果转成结构化 evidence card（bottleneck、affected ops、device constraints）；
  - agent 只从允许的 action space 选下一步；
  - 复测确认，未改善则回滚。
- **来源**：[ProfilingAgent](https://arxiv.org/abs/2509.05584)（标题/摘要级证据）

### 3.7 ShrinkLLM — agent 化压缩流水线

- **是什么**：Automated LLM Compression via AI Agents（IEEE MDM 2026）。
- **为什么契合**：和你的“量化/压缩 → 评测 → 反馈”最接近；可借鉴它的 agent 分工、工具调用和停止条件。
- **怎么用**：作为 pipeline 设计的对照；重点看它如何决定“下一步压缩动作”和“何时停止”，而不是照搬模型。
- **来源**：[ShrinkLLM (IEEE MDM 2026)](https://www.computer.org/csdl/proceedings-article/mdm/2026/331000a363/2izmGoIOKaI)（标题/摘要级证据）

### 3.8 LLM-Guided Agentic Optimization Toolbox — 边缘部署工具箱

- **是什么**：面向 edge-deployable NN 的 LLM 引导 agentic 优化工具箱。
- **为什么契合**：你的目标就是 edge/端侧；它把“优化 pass 选择 + 部署约束”做成工具箱，和你的 compile/device 阶段对应。
- **怎么用**：借鉴它的 tool schema 和 action space；不要让 agent 直接写 shell。
- **来源**：[LLM-Guided Toolbox](https://www.iitis.pl/pl/bibcite/reference/16243)（标题/摘要级证据）

---

## 4. 可借的 SOTA/参考（Tier 2）

| 方法 | 是什么 | 借什么 | 来源 |
| --- | --- | --- | --- |
| **ACE** | Agentic Context Engineering，演化 context playbook；ICLR 2026 | 把 skill/context 当可演化资产；和 GEPA 互补 | [ACE](https://arxiv.org/abs/2510.04618) |
| **AIDE** | 把 ML 工程建模为代码空间树搜索 | recipe/实验树搜索；MLE-bench 强基线 | [AIDE](https://arxiv.org/abs/2502.13138) |
| **AgentHPO** | LLM agent 做超参优化 | recipe 参数（bits/group size/calibration）搜索 | [AgentHPO](https://arxiv.org/abs/2402.01881) |
| **AutoML-Agent** | 全流水线 AutoML 多 agent；ICML 2025 | stage 分解、检索增强规划、多阶段验证 | [AutoML-Agent](https://arxiv.org/abs/2410.02958) |
| **ML-Master** | 探索+推理+认知积累；报告 MLE-bench 29.3% medal rate，曾登顶 | 长程 ML 工程的 memory/loop 设计 | [ML-Master](https://arxiv.org/abs/2506.16499) |
| **R&D-Agent** | 微软的 research/development/evolution 循环 | pipeline 的 R&D loop 与演进 | [R&D-Agent](https://arxiv.org/abs/2505.14738) |
| **MLE-bench** | 75 个 Kaggle 竞赛，medal 阈值；ICLR 2025 | 任务/评分/防泄漏设计 | [MLE-bench](https://arxiv.org/abs/2410.07095) |
| **MLAgentBench** | 13 个 ML 实验任务；ICML 2024 | 任务 brief 与 baseline 设计 | [MLAgentBench](https://arxiv.org/abs/2310.03302) |
| **Agentless** | 简单三阶段 pipeline，强 SWE-bench 基线 | 必须有的“简单基线”；防过度 agent 化 | [Agentless](https://arxiv.org/abs/2407.01489) |
| **Anthropic 多 agent 研究系统** | orchestrator-worker；报告内部研究 eval 超单 agent 90.2%，token 约 15× | 何时用多 agent：breadth-first 研究；强耦合任务不适合 | [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system) |
| **Cognition 多 agent 反思** | 代码/长上下文任务的多 agent 陷阱；后续“what's actually working” | 不要全 peer；保持单线程决策/上下文压缩 | [Cognition](https://cognition.ai/blog/multi-agents-working) |

---

## 5. 后置的高风险/高成本（Tier 3）

| 方法 | 是什么 | 为什么后置 | 来源 |
| --- | --- | --- | --- |
| **DGM** | 自修改 agent 代码，开放演化；报告 SWE-bench 20→50、Polyglot 14.9→30.7 | 强，但会改自己的代码/评估边界；需要强沙箱、回滚、审计 | [DGM (ICLR 2026)](https://arxiv.org/abs/2505.22954) |
| **AlphaEvolve** | Gemini 驱动的演化编码 agent；报告 4×4 矩阵乘法 48 次乘法，并在 50+ 开放问题中约 20% 取得改进（最高约 0.7%） | 更适合算法/启发式搜索，不是流程编排；成本高 | [AlphaEvolve](https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/) |
| **Agent Lightning** | 用 RL 训练 agent，复用现有 harness | 需要训练基础设施；先证明 prompt/skill 优化不够 | [Agent Lightning](https://microsoft.github.io/agent-lightning/) |
| **AutoQuant / FlexQuant / UDP** | 自动发现量化算法 / 弹性量化 / 进化混合精度 | 不是 agent 框架；作为 action space / 搜索基线参考，不占多 agent 实验的主线 | [AutoQuant](https://github.com/yandex-research/AutoQuant) · [FlexQuant](https://arxiv.org/abs/2501.07139) · [UDP](https://ieeexplore.ieee.org/document/11471740) |

---

## 6. 领域专用：onboarding 的 action space

如果 agent 只能改 prompt，不叫优化 onboarding；它必须能改这些**受支持**的字段：

| 层 | 可优化字段 | 约束来源 | 验证 |
| --- | --- | --- | --- |
| model | model_uri, task, architecture, context | registry / license | inspect |
| calibration | dataset, samples, seq_len, sampling | dataset card / privacy | validate |
| quantization | method, bits, group_size, act_quant, mixed precision, exclusions | library schema / platform profile | preflight |
| runtime | backend, version, compiler flags | runtime env / SDK | compatibility |
| device | pool, matrix, OS, KPI thresholds | device profile | device test |
| acceptance | max drop, latency, memory, thermal | business | KPI report |

原则：

- 只允许库真正支持的组合；用 typed contract + preflight 拦截。
- 一次只改一个动作：profile → diagnose → choose one action → re-evaluate；不要一次改 5 个参数。
- 参数搜索优先用 AIDE / AgentHPO / Optuna；提示词/技能演化用 GEPA；**不要把两者混在一个 loop**。
- 现有工具（NVIDIA ModelOpt、llm-compressor、Intel Neural Compressor、AIMET）已经提供 accuracy-aware 的局部搜索；agent 的职责是“选择和排序”，不是重新发明量化算法。

---

## 7. 推荐架构：Owner + Scouts + Critic + Diagnostician

```text
                 ┌─────────────────────────────┐
                 │ Owner / Orchestrator agent  │  唯一决策脊柱
                 │ - 持有 task + recipe 状态    │
                 │ - 分配预算                   │
                 │ - 最终 recipe / 签字         │
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
                 │ Author agent    │  组 recipe
                 │ （或 owner）     │
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

**为什么不是全 peer：**

- onboarding 是串行耦合（recipe → compile → device），全 peer 会造成 context 分裂、隐式决策冲突、重复工作。
- Anthropic 的多 agent 在 breadth-first research 上强，但 token 成本约 15×；Cognition 明确警告 coding/长上下文任务的全 peer 多 agent。
- 把并行放在“读/诊断”，把串行放在“决策/执行”。

**如何验证这个架构：**

- C0 单 agent；
- M1 owner + scouts；
- M2 owner + scouts + critic；
- M3 pipeline-of-specialists；
- M4 peer team（预期更差/更贵，作为对照）。

同一批任务、同一 evaluator、同一预算；用 MAST 编码协作失败，用 Who&When 归因。

---

## 8. 优化闭环：从 trace 到 patch

1. **收集**：每次 attempt 的 manifest、events、recipe、logs、metrics、artifact hashes。
2. **分类**：最早因果边界（F01–F10）+ MAST 模式。
3. **归因**：Who&When 思路 + 消融（去掉一个 role/tool）+ 反事实 replay。
4. **提案**：只针对一个失败类；格式 = 证据 / 假设 / 改动文件 / 预期指标 / 风险 / 回滚 / 验证任务。
5. **选择优化器**：
   - skill / instruction → **GEPA**
   - workflow → **AFlow**
   - topology → **MaAS**
   - recipe params → **AIDE / AgentHPO**
   - pipeline code → **DGM / AlphaEvolve**（后置）
6. **评估**：冻结回归集 + 至少一个 held-out；成本调整；显著性。
7. **晋级/回滚**：版本化；只保留可复现的改动；更新回归集。

**关键边界：**

- **可演化**：SKILL.md、workflow 图、拓扑、recipe 候选。
- **不可演化**：evaluator、acceptance 阈值、contract 事实、测试数据。
- contract 应从源码/平台 profile 生成（Griffe/源码扫描），版本绑定；LLM 只补“人工业务约束”，且要标注来源。

---

## 9. 实验设计（可直接排期）

### 9.1 任务

沿用 v1.1 的 T01–T08，补两个：

- **T09 profile-guided**：给一个 device profile，要求选优化动作并复测。
- **T10 coordination**：一个需要 3 个证据源（repo/API、dataset、device）才能组 recipe 的任务，专门测 handoff。

### 9.2 条件（分阶段，不要全因子）

**Stage 1（拓扑，2 周）**

- C0 单 agent
- M1 owner + scouts
- M2 owner + scouts + critic
- M3 pipeline-of-specialists
- M4 peer team（对照）

**Stage 2（知识，2 周）**

在 Stage 1 胜者上，加：

- C1 repo map / API index
- C2 capability contracts
- C4 preflight
- 一次只加一个。

**Stage 3（搜索，可选 2 周）**

- GEPA 改 skill
- AFlow 改 workflow
- MaAS 改 topology
- 在 held-out 上比较，成本调整。

**Stage 4（质量，单独）**

- AIDE / AgentHPO / Optuna 搜 recipe；
- Pareto 前沿；
- 不和工程可靠性混分。

### 9.3 指标

- **Gates**：G1 valid recipe、G2 preflight、G3 execution、G4 device、G5 quality。
- **Primary**：first-attempt verified success（G5，无人工修复）。
- **Reliability**：pass@1、pass@k、pass^k。
- **Cost**：tokens、GPU-min、wall-clock、human interventions、cost per verified success。
- **Coordination**：handoff errors、duplicate work、conflicting evidence、decision churn（MAST）。
- **Groundedness**：关键参数有证据引用的比例。
- **Generalization**：held-out tasks。

### 9.4 统计

- 5–10 reps 用于 screening；10–20 或配对任务用于 confirmation。
- 同一 task / assets / hardware；随机顺序；paired bootstrap 95% CI；mixed-effects（task/run 随机效应）。
- 预先注册 primary metric + 2–3 个假设；FDR 控制。
- 报告 effect size + CI，不只 p 值。
- 停止规则：held-out 无提升、协调成本 > 收益、cost per success 变差。

### 9.5 预算

- 每个 run 设 token/GPU/时间上限；超时即失败，不让人工续命。
- 先 3 tasks × 5 reps × 5 条件（C0 + M1–M4）≈ 75 runs 做 screening；再 2 tasks × 20 reps 做 confirmation。
- 质量轨单独预算；不要用工程轨的 GPU 预算跑搜索。

---

## 10. 对 v1.1 的 10 个具体修改

1. 增加 **L0–L4“多 agent 层级”** 作为独立因子，不要混在 C0–C5 里。
2. 把“优化对象”分成 **solution / workflow / instruction / implementation** 四类，各配优化器。
3. 把 **5 次**改为“5–10 次 screening；10–20 次/配对 confirmation”。
4. 增加 **MAST 协作失败编码 + Who&When 归因**。
5. 增加 **coordination metrics**（handoff / duplicate / conflict / churn）。
6. 把架构从“peer team”改成 **“owner + scouts + critic + diagnostician”**。
7. 增加 **“可演化 vs 冻结”清单**：skill/workflow 可演化；contract 从源码生成；evaluator 冻结。
8. 增加 **action space schema + preflight**；agent 只能改支持字段。
9. 增加 **cost-adjusted score**（cost per verified success）。
10. 增加 **“何时不该用多 agent”** 的停止规则。

---

## 11. 失败模式与防作弊

**MAST 三类：**

- specification：任务/角色/边界没定义清楚；
- inter-agent misalignment：handoff 丢信息、忽略输入、重复工作、决策冲突；
- task verification：过早结束、验证不完整、评估器被绕过。

**常见坑：**

- 任务歧义、角色重叠、handoff 丢信息、忽略 critic；
- executor 跑错 config、evaluator 被改；
- best-of-n 当 pass@1、test leakage、stale contract；
- 用同一个任务既设计 patch 又验收 patch。

**防护：**

- 冻结 evaluator、只读 repo、每 run 独立 workspace；
- budget cap、pipeline patch 审批、rollback；
- 人工抽检 + 自动化一致性测试；
- contract 版本绑定 commit/源码/测试，变更触发重验。

---

## 12. 来源与证据强度

| 来源 | 类型 | 本 memo 中的用法 | 强度 |
| --- | --- | --- | --- |
| [GEPA](https://proceedings.iclr.cc/paper_files/paper/2026/hash/0e9e708b6f48e14fd0ac29e167413f76-Abstract-Conference.html) | ICLR 2026 论文 | 技能/提示演化 | 方法可靠；数字待原文核对 |
| [AFlow](https://proceedings.iclr.cc/paper_files/paper/2025/hash/5492ecbce4439401798dcd2c90be94cd-Abstract-Conference.html) | ICLR 2025 论文 | 工作流搜索 | 方法可靠；5.7% 待原文核对 |
| [MaAS](https://arxiv.org/abs/2502.04180) | ICML 2025 论文 | 拓扑搜索 | 方法可靠 |
| [MAST](https://arxiv.org/abs/2503.13657) | NeurIPS 2025 D&B | 协作失败分类 | 方法可靠 |
| [Who&When](https://arxiv.org/abs/2505.00212) | ICML 2025 论文 | 失败归因 | 方法可靠 |
| [ProfilingAgent](https://arxiv.org/abs/2509.05584) | arXiv 2025 | profile-guided 优化 | 标题/摘要级 |
| [ShrinkLLM](https://www.computer.org/csdl/proceedings-article/mdm/2026/331000a363/2izmGoIOKaI) | IEEE MDM 2026 | agent 化压缩 | 标题/摘要级 |
| [LLM-Guided Toolbox](https://www.iitis.pl/pl/bibcite/reference/16243) | 论文/工具箱 | 边缘优化 action space | 标题/摘要级 |
| [DGM](https://arxiv.org/abs/2505.22954) | ICLR 2026 论文 | 自修改代码 | 方法可靠；数字待原文核对 |
| [AlphaEvolve](https://deepmind.google/discover/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/) | DeepMind 官方博客 | 演化编码 | 官方来源 |
| [ML-Master](https://arxiv.org/abs/2506.16499) | arXiv 2025 | 长程 ML agent | 29.3% 来自搜索片段，待原文核对 |
| [R&D-Agent](https://arxiv.org/abs/2505.14738) | arXiv 2025 + GitHub | R&D loop | 方法可靠 |
| [AIDE](https://arxiv.org/abs/2502.13138) | arXiv 2025 | 树搜索 | 方法可靠 |
| [AgentHPO](https://arxiv.org/abs/2402.01881) | arXiv 2024 | HPO | 方法可靠 |
| [AutoML-Agent](https://arxiv.org/abs/2410.02958) | ICML 2025 | 全流水线多 agent | 方法可靠 |
| [MLE-bench](https://arxiv.org/abs/2410.07095) | ICLR 2025 | 任务/评分 | 方法可靠 |
| [MLAgentBench](https://arxiv.org/abs/2310.03302) | ICML 2024 | 任务设计 | 方法可靠 |
| [Agentless](https://arxiv.org/abs/2407.01489) | arXiv 2024 | 简单基线 | 方法可靠 |
| [Anthropic 多 agent](https://www.anthropic.com/engineering/multi-agent-research-system) | 官方工程博客 | 何时用多 agent | 官方来源；90.2%/15× 为文中报告 |
| [Cognition](https://cognition.ai/blog/multi-agents-working) | 官方博客 | 多 agent 陷阱 | 官方来源 |
| [Agent Lightning](https://microsoft.github.io/agent-lightning/) | 微软文档 | RL 训练 | 官方来源 |
| [ACE](https://arxiv.org/abs/2510.04618) | ICLR 2026 论文 | context 演化 | 方法可靠 |
| [AutoQuant](https://github.com/yandex-research/AutoQuant) / [FlexQuant](https://arxiv.org/abs/2501.07139) / [UDP](https://ieeexplore.ieee.org/document/11471740) | 开源/论文 | 量化 action space | 参考级 |

---

## 13. 一句话

**不要先问“用几个 agent”，先问“我要搜索的是解空间、工作流、指令，还是实现”。** 四类问题对应四种优化器；多 agent 只是其中一种搜索算子。对 onboarding 这种强耦合链路，最稳的起点是“单 owner + 并行只读 scout + 独立 critic + 并行 diagnostician”，再用 GEPA/AFlow/MaAS 离线演化，最后才考虑 DGM/AlphaEvolve 这类自修改系统。
