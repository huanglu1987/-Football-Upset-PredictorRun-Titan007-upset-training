# Input Template

## Usage

Use this template when the user provides incomplete product information or when you need to normalize the request before building strategy.

## Minimum Input Set

- `分子/活性成分`
- `作用机制（如已知）`
- `剂型`
- `目标浓度/规格`
- `目标适应症`
- `目标人群`
- `开发地区`
- `注册路径初判`
- `已有前期数据概况`

## Strongly Recommended Inputs

- `既往上市基础`
- `拟定临床优势`
- `给药频次与疗程设想`
- `CMC/制剂关键点`
- `主要监管担忧`
- `计划对照方式`

## Optional Enrichment

- `非临床药效细节`
- `局部耐受/致敏/光安全细节`
- `系统毒理/毒代细节`
- `人体PK或最大使用PK信息`
- `竞品/同类品种`
- `时间或预算约束`

## Suggested Collection Template

```md
分子/活性成分：
作用机制（如已知）：
剂型：
目标浓度/规格：
目标适应症：
目标人群：
开发地区：中国 / 美国 / 中美双报
注册路径初判：创新药 / 改良型新药 / 待判断

既往上市基础：
拟定临床优势：
给药频次与疗程设想：

已有前期数据：
- 非临床药效：
- 局部耐受/刺激/致敏/光安全：
- 系统毒理/毒代：
- 人体PK或最大使用PK：
- 早期疗效信号：

CMC/制剂关键点：
主要监管担忧：
计划对照方式：
时间或预算约束：
```

## Missing-Data Rule

If the user only supplies the minimum set:

- still generate a first-pass strategy
- mark high-uncertainty items clearly
- explain what additional inputs would materially change the recommendation

Do not reject the task solely because the target strength lacks prior topical precedent.
