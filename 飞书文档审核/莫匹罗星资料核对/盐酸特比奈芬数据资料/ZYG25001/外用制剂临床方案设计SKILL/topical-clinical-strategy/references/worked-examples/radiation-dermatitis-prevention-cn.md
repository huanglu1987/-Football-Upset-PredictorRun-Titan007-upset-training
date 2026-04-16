# Worked Example: Radiation Dermatitis Prevention, China

## Representative Input

```text
某外用凝胶拟用于放射性皮炎预防，计划先在中国开展临床研究。团队希望作为肿瘤支持治疗产品开发，优先聚焦单一放疗场景。已有基础局部安全和非临床支持数据，但尚无人体临床经验。请输出保守路径与激进路径，并重点说明 prevention 项目早期研究应如何设计。
```

## Why This Example Matters

This example is useful for:

- newly added radiation dermatitis indication work
- prevention rather than treatment positioning
- oncology supportive-care integration rather than classic dermatology outpatient logic

## What a Strong Answer Should Include

- 明确先把项目定义为 `prevention`，不要和 `treatment` 混写
- 说明放射性皮炎项目的关键不是传统皮肤病自然病程，而是放疗工作流和背景支持治疗控制
- 解释为什么这类项目里长健康受试者包通常不是核心
- 对中国路径说明：
  - 要把单一放疗场景、背景标准护理和终点评分体系说清楚
  - 需强调临床进入合理性和局部用药安全边界

## Example Output Shape

### 项目结论摘要

- 当前更接近：局部起效支持治疗产品的正式策略判断
- 推荐主路径：偏保守，但可在单一放疗场景下做适度压缩
- 最大监管风险：如果 prevention 与 treatment、或多个放疗场景混在一个首轮程序里，研究会很难解释

### 判断级别与关键假设

- 当前判断级别：第一轮正式策略判断
- 关键假设：产品可在不影响放疗流程和背景护理的前提下，降低 clinically meaningful dermatitis burden
- 高优先级缺口：
  - 单一放疗场景选择
  - 背景 supportive care 标准化
  - irradiated field 条件下的局部耐受和实际可用性

### 保守路径

- 先收窄到单一放疗场景和 prevention 主张
- 先做较真实临床场景下的耐受和可操作性确认
- 再进入较正式的随机对照 prevention 研究

### 激进路径

- 若场景单一、标准护理统一、局部耐受明确，可更快进入患者预防性随机研究
- 但仍不建议把 prevention 与 treatment 合并开发

### 关键依据类型

- radiation dermatitis indication module
- China local-acting and clinical-entry guidance
- ClinicalTrials.gov prevention-setting precedent

## Example Early-Stage Design Detail

### 早期研究总体判断

- 对这个项目，我不建议花很大力气先做传统健康受试者 SAD/MAD。
- 更合理的思路通常是：`有限首人体耐受确认 + 尽早进入放疗患者场景研究`。
- 原因：
  - 真正的问题发生在 irradiated skin 和 oncology workflow 中
  - prevention 价值取决于开始时点、给药依从性和背景护理控制
  - 健康受试者对 irradiated-field tolerability 和真实使用可操作性的代表性有限

### 单次给药或极简首人体研究建议

- 若配方存在明显新辅料或局部刺激担忧，可做一个极简首人体耐受研究。
- 目标：
  - 回答未照射皮肤条件下的基本局部耐受
  - 排除明显不适合进入患者场景的刺激问题
- 但这一步不应成为主研究，更不建议为了形式完整而拉长开发。

### 患者早期研究建议

- 更关键的早期研究应放在 `单一放疗场景` 的患者中。
- 推荐先聚焦一种相对一致的人群，例如某一类实体瘤放疗场景，而不是同时混合多个 irradiation field。
- 研究重点：
  - 给药开始时点与放疗开始的衔接
  - 背景 supportive care 的统一
  - 局部耐受、依从性和实际可操作性
  - dermatitis grading 的一致性

### prevention 主研究框架建议

- 早期患者研究可以设计为随机、对照、前瞻性 prevention 研究的前置版本。
- 关键设计点：
  - 明确是 `预防 grade 达到某一阈值的皮炎`，还是 `降低 worst grade`
  - 统一评分体系，例如 CTCAE-like grading
  - 控制合并使用的保湿剂、激素或其他支持治疗
  - 把 oncology site training 当作研究质量的一部分，而不是附属事项

### 转段门槛

- 只有当以下条件基本成立时，才建议进入更正式的 prevention 随机研究：
  - 单一放疗场景可稳定执行
  - 背景标准护理变异可控
  - irradiated-field 条件下局部耐受可接受
  - 终点定义和评分训练已足够标准化

## Main Teaching Point

Radiation dermatitis prevention programs become much stronger when the answer treats oncology workflow control as core trial design, not operational detail.
