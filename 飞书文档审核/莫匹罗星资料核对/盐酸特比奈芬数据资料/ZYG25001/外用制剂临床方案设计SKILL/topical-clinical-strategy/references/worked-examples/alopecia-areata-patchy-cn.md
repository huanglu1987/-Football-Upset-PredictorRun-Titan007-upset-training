# Worked Example: Localized Patchy Alopecia Areata, China

## Representative Input

```text
项目代号 AA-301。某外用小分子溶液拟用于局灶性斑秃，计划先在中国开展临床研究。已有非临床药效和基础局部安全数据，尚无人体 PK。团队希望尽快进入患者研究，并重点看局部斑片再生发信号。请输出保守路径与激进路径，并重点说明早期临床应先做健康人还是患者，以及重复给药研究应如何设计。
```

## Why This Example Matters

This example is useful for:

- newly added alopecia areata indication work
- patchy localized disease rather than broad scalp disease
- cases where the team wants patient-first development logic

## What a Strong Answer Should Include

- 明确指出 `局灶性 / patchy AA` 应与广泛头皮受累或系统性 AA 逻辑分开
- 解释为什么 AA 不能直接套用 AGA 的疗程、终点和人群分层
- 说明在 AA 里，患者早期研究通常比长健康受试者包更有决策价值
- 对中国路径说明：
  - 应把创新药或改良型新药的整体临床进入依据讲清楚
  - 需要强调斑片选择、摄影标准化和背景治疗控制

## Example Output Shape

### 项目结论摘要

- 当前更接近：外用创新药第一轮策略判断
- 推荐主路径：中度偏激进，但前提是局限于 localized patchy AA
- 最大监管风险：如果一开始把患者范围放得过宽，或没有标准化病灶选择和成像，早期信号会非常难解释

### 判断级别与关键假设

- 当前判断级别：正式策略判断前期
- 关键假设：该外用产品可以在局灶性病灶中产生足够的局部药效，而系统暴露仍可控
- 高优先级缺口：
  - 人体系统暴露与重复给药可耐受性
  - patch-level objective assessment 的标准化
  - spontaneous fluctuation 对早期信号的干扰控制

### 保守路径

- 先用简短健康受试者或极小样本首人体研究回答 PK 和基本耐受
- 再进入局灶性 AA 患者短期重复给药研究
- 逐步放大到更正式的探索性有效性研究

### 激进路径

- 若系统暴露担忧不高且局部给药逻辑强，可更早进入患者重复给药研究
- 但必须收窄到 `localized patchy AA`，并强化病灶选择和摄影质控

### 关键依据类型

- alopecia areata indication module
- China local-acting, innovation-method, and exposure-response guidance
- ClinicalTrials.gov localized or topical AA precedent

## Example Early-Stage Design Detail

### 早期研究总体判断

- 对这个项目，我不建议机械地沿用“先完整健康人 SAD/MAD，再患者”的传统口服药路径。
- 更合理的思路通常是：`必要时极简 HV 首人体 + 尽早进入患者重复给药研究`，甚至在系统暴露担忧较低时可以 `patient-first`。
- 原因：
  - AA 的 PD 和临床信号主要发生在患者病灶上，健康受试者几乎无法提供真正决策性信息
  - 局灶性 patch 选择是否合理，比长健康受试者包更影响后续成败
  - 斑秃存在自发波动，早期研究更需要“可解释性”，而不是形式上完整

### 单次给药研究建议

- 若分子机制存在系统安全担忧，建议做一个极简的首人体单次给药研究。
- 推荐人群：
  - 优先健康受试者，样本不必大
  - 若暴露可预期极低，也可考虑直接并入患者早期重复给药方案中
- 目标：
  - 回答单次外用后的局部耐受
  - 获取基础系统 PK
  - 设定后续患者研究的安全边界

### 重复给药研究建议

- 真正的早期主研究更建议放在 `localized patchy AA` 患者中。
- 推荐设计：
  - 小样本、随机、双盲、载体对照
  - 重复给药 `8-12 周`
  - 固定 1-2 个 index patch 或明确的评估区域
- 关键设计点：
  - 明确局灶性入组标准，不宜过早纳入广泛头皮受累
  - 统一摄影、光照、角度和 dermoscopy 方案
  - 控制背景治疗和近期自然波动因素

### 患者早期信号建议

- 早期患者研究应重点收集：
  - patch-level regrowth trend
  - dermoscopic markers
  - standardized photography
  - investigator/patient global impression
- 不建议过早把终点写成“大范围 scalp hair response”，否则局灶性信号容易被稀释。

### 转段门槛

- 只有当以下条件基本成立时，才建议进入更正式的探索或关键研究：
  - 患者局部耐受和系统暴露可接受
  - 至少 1 个 patch-level 评估方法稳定可解释
  - 已观察到相对载体更有说服力的再生发趋势
  - 局灶性人群边界已清楚，不需要过早扩展到更广泛 AA

## Main Teaching Point

In localized patchy alopecia areata, a good answer earns patient-relevant early signal quickly and resists drifting into broad-scalp AGA-like development logic.
