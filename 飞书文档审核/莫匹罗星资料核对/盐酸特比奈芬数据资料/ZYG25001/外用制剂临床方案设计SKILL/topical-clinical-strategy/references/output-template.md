# Output Template

## Usage

This file is the default output router.

The skill now supports two output modes:

- `策略版`
- `方案纲要版（synopsis）`

Default to `策略版` unless the user explicitly asks for more design detail.

If the user asks for a study-architecture answer, use:

- `references/synopsis-template.md`

This file continues to define the default `策略版` structure.

## Mode Selection

### Use `策略版` when

- the user is still at portfolio or early candidate triage stage
- the inputs are sparse
- the main task is path judgment, not study drafting

### Use `方案纲要版（synopsis）` when

- the user asks for more detailed study design
- the user asks how a Phase 1 or exploratory package should actually be run
- the team needs an internal near-synopsis architecture

In synopsis mode, still keep:

- path judgment
- evidence labeling
- conservative versus aggressive framing

## Strategy-Mode Required Sections

### 1. 项目结论摘要

State:

- 产品定位
- 地区与注册路径判断
- 当前推荐主路径
- 最大监管风险

### 2. 判断级别与关键假设

State:

- 当前判断级别：正式策略判断 / 第一轮策略判断
- 关键假设
- 最影响路径变化的高优先级缺口

Use this section especially when the prompt is sparse.

### 3. 开发前提判断

State:

- 创新药 / 改良型新药判断及理由
- 可桥接基础及理由
- 系统暴露关注程度及理由
- 当前最影响路径选择的前提条件

### 4. 保守路径 vs 激进路径

For each path, state:

- 核心思路
- 适用前提
- 主要优点
- 主要缺点
- 关键监管风险

Then state:

- 当前更推荐哪一路径
- 为什么

### 5. 分期开发策略

For each stage, state:

- 研究目的
- 推荐研究类型
- 推荐受试人群
- 受试人群选择理由
- 推荐对照方式
- 主要终点与关键次要终点
- 给药设计要点
- 关键评估项目
- 样本量思路
- 是否可跳过或合并
- 进入下一阶段的门槛

For early-stage work, do not stop at generic labels such as “开展 I 期研究”.

When Phase 1 or early exploratory work is in scope, explicitly state:

- 健康受试者 / 患者 / 先健康受试者后患者
- 是否需要 SAD
- 是否需要 MAD
- 是否需要患者 PK、max-use PK 或 MUsT
- 递增维度是浓度、给药面积、给药量还是频次
- 关键安全性和 PK 观察点
- 触发升级或转段的核心门槛

Suggested detail level for early-stage output:

- `早期总体目标`
- `先入组人群与理由`
- `SAD 设计建议`
- `MAD 或重复给药研究设计建议`
- `患者 PK / MUsT / 早期信号整合建议`
- `转入后续探索或确证研究的门槛`

### 6. 关键专项研究建议

Address when relevant:

- 最大使用 PK / MUsT
- 局部刺激 / 致敏 / 光安全
- 暴露-效应分析
- 长期安全
- PK bridge / relative BA
- 剂量探索 / 成分贡献

### 7. CDE vs FDA 差异提示

Only use this as a full section when:

- both regions are in scope
- or the user explicitly asks for a comparison

If the user asks for a single-region strategy, this can be reduced to a short note about why the other region might differ.

Compare at least:

- 注册属性判断
- 临床优势要求
- 桥接受受度
- 系统暴露研究要求
- 长期安全要求
- 终点与证据强度
- 沟通建议

### 8. 当前证据缺口清单

Split into:

- `必须补`
- `强烈建议补`
- `可选增强`

For each gap, explain what decision it affects.

### 9. 依据说明

For each key recommendation, include:

- `依据类型`
- `依据要点`
- `适用前提`

## Output Style Rules

- Default to Chinese.
- Keep the answer structured and strategy-level.
- If the user asks for more detailed design, expand the early-stage section to strategy-design level rather than staying at slogan level.
- Do not silently imply certainty that the evidence does not support.
- If evidence is mixed, say so directly.
- If the conservative and aggressive paths differ because of one key assumption, name that assumption explicitly.
- If synopsis mode is selected, switch to `references/synopsis-template.md` instead of stretching this file beyond its intended depth.
