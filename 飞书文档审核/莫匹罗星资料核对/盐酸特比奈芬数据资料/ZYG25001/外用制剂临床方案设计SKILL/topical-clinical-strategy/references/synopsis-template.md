# Synopsis Template

## Purpose

Use this template when the user wants more than a strategy memo and expects a study-architecture answer close to protocol-synopsis depth.

This template is still not full protocol authoring.

It should stop before full operational detail such as:

- exact schedule of assessments tables
- full inclusion and exclusion criteria lists
- full statistical-analysis-plan text
- complete protocol boilerplate

## When To Use

Use synopsis mode when one or more of the following is true:

- the user asks for a more detailed plan design
- the user asks how Phase 1 or early studies should actually be run
- the project has moved beyond portfolio triage into candidate-level planning
- the team needs a draft internal study architecture for discussion

## Required Output Header

Start by naming the mode:

- `当前输出模式：方案纲要版（synopsis）`

Then state:

- 产品定位
- 当前推荐主路径
- 当前判断级别
- 主要未决假设

## Required Sections

### 1. 项目定位与开发主张

State:

- 创新药 / 改良型新药判断
- 目标临床优势或核心开发主张
- 当前最关键的监管问题

### 2. 总体研究架构

State:

- 研究总顺序
- 哪一步解决什么问题
- 哪一步是 Go/No-Go 节点

For example:

- `研究 1：健康人单次给药 PK/耐受`
- `研究 2：患者重复给药 PK/耐受`
- `研究 3：剂量探索/POC`

### 3. 早期研究综述

Explicitly answer:

- 健康受试者 / 患者 / 先健康受试者后患者
- SAD 是否需要
- MAD 是否需要
- 患者 PK 是否需要
- max-use PK 或 MUsT 是否需要
- 给药强度、面积、频次哪个是主要递增维度

### 4. 单项研究纲要

For each planned study, write a concise synopsis with the following fields:

- `研究名称`
- `研究目的`
- `设计类型`
- `受试人群`
- `关键入组方向`
- `分组/队列框架`
- `给药方案`
- `主要评估指标`
- `关键次要评估指标`
- `风险控制点`
- `升级或转段门槛`

### 5. 剂量与频次决策逻辑

State:

- 候选浓度或规格来源
- 是否需要多浓度并行
- 是否先做 `qd` 再看 `bid`
- 暴露-效应如何帮助收缩方案

### 6. 后续探索或关键研究框架

State:

- 探索研究如何承接早期研究
- 关键研究前必须具备的证据
- 长期安全如何布局

### 7. 当前证据缺口与补强动作

Split into:

- `进入下一研究前必须补`
- `可在下一研究中同步补`
- `后续申报前需补`

### 8. 依据说明

For each major design choice, include:

- `依据类型`
- `依据要点`
- `适用前提`

## Output Style Rules

- Default to Chinese.
- Keep the answer concise but operationally useful.
- Prefer study architecture and decision logic over verbose prose.
- Do not fake protocol-level precision when the evidence is not mature enough.
