# Output Template

## Usage

Use this structure for the final strategy output unless the user explicitly asks for a different format.

## Required Sections

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
- 推荐对照方式
- 主要终点与关键次要终点
- 样本量思路
- 是否可跳过或合并
- 进入下一阶段的门槛

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
- Do not silently imply certainty that the evidence does not support.
- If evidence is mixed, say so directly.
- If the conservative and aggressive paths differ because of one key assumption, name that assumption explicitly.
