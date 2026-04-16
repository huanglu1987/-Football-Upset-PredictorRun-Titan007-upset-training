# Validation Prompts

## Purpose

Use these prompts for manual testing, team trial runs, or future forward-testing. They are designed to probe both the normal path and the failure path of the skill.

## What Good Output Should Show

A good answer should usually include:

- clear region and path framing
- conservative and aggressive routes
- explicit evidence type and applicability
- indication-specific endpoint logic
- meaningful uncertainty marking

## Prompt 1: Minimal-Input Acne Case

```text
请帮我设计一个外用痤疮改良型新药的临床开发路径。活性成分是某已上市口服小分子，拟开发成外用凝胶，目标浓度 1%，适应症是中重度痤疮，开发地区先美国。现阶段只有口服上市经验和少量非临床药效数据。
```

Why this test matters:

- tests oral-to-topical logic
- tests whether weak strength rationale becomes a risk signal instead of a hard stop
- tests FDA-side bridge reasoning

## Prompt 2: Rich-Input Acne Combination Case

```text
请基于以下信息输出中国和 FDA 的临床开发策略，并比较保守路径与激进路径：三联外用痤疮凝胶，三个活性成分均已有外用先例，目标人群为 12 岁及以上，已有局部耐受、贴敷致敏和最大使用 PK 数据，拟主打提高依从性和疗效。
```

Why this test matters:

- tests component-contribution awareness
- tests dual-region comparison
- tests whether existing max-use PK changes path aggressiveness

## Prompt 3: Rosacea Chronic-Use Case

```text
我要做一个玫瑰痤疮外用泡沫剂，美国路径优先。活性成分已有其他剂型上市经验，但新剂型可能改善局部刺激。请输出保守和激进两条开发路径。
```

Why this test matters:

- tests chronic-use safety logic
- tests whether public review precedent is used appropriately

## Prompt 4: Superficial Fungal Short-Course Case

```text
某外用抗真菌乳膏计划做浅表真菌感染，想把疗程做得比现有治疗更短，先美国后中国。请判断这种开发路径的关键风险和建议的临床研究框架。
```

Why this test matters:

- tests follow-up cure logic
- tests whether the model separates mycological and clinical endpoints
- tests whether PSG is used as support rather than as a final answer

## Prompt 5: AGA Finasteride-Risk Case

```text
请设计一个 topical finasteride 用于 AGA 的临床开发策略，目标市场为美国。希望尽可能走激进路径，缩短开发时间。
```

Why this test matters:

- tests whether the skill resists over-aggressive FDA logic
- tests whether FDA safety signals are surfaced
- tests whether systemic and transfer exposure stay visible

## Prompt 6: AGA Minoxidil-Optimization Case

```text
已有外用 minoxidil 类经验，拟做一个改良剂型提高依从性并降低刺激，请给出中国和 FDA 双路径开发建议。
```

Why this test matters:

- tests whether the skill can become relatively pragmatic when precedent is strong
- tests whether the aggressive path is allowed but still bounded

## Prompt 7: China-Only Improved New Drug Case

```text
请从中国改良型新药角度评估一个口服已上市小分子改为外用乳膏治疗脂溢性皮炎的开发路径，重点说明为什么这样设计能够体现临床优势。
```

Why this test matters:

- tests whether China-side clinical-advantage logic is explicit
- useful later when the indication set expands beyond the current four deep modules

## Prompt 8: Dual-Region Uncertain Path Case

```text
某皮肤外用喷雾剂项目想同时考虑中国和 FDA，但目前只有有限非临床数据，没有人体 PK，也不确定是创新药还是改良型新药。请给出一个第一轮开发策略判断。
```

Why this test matters:

- tests whether the skill can still produce a usable first-pass answer
- tests uncertainty marking and gap prioritization

## Prompt 9: Terbinafine Dual-Region Case

```text
请为盐酸特比奈芬外用乳膏设计中国和 FDA 的临床开发策略。项目希望兼顾开发效率，但也要有一条更稳妥的保守路径。适应症是浅表真菌感染，现有基础主要来自口服和既往外用临床经验。
```

Why this test matters:

- tests a business-near superficial fungal scenario
- tests whether same-ingredient familiarity is used properly
- tests whether the answer avoids collapsing into generic-only logic

## Prompt 10: Minoxidil Optimization Case

```text
已有外用 minoxidil 使用基础，拟开发一个改良剂型以提高依从性并降低刺激，请给出中国和 FDA 双路径开发建议。
```

Why this test matters:

- tests a business-near AGA optimization scenario
- tests whether the aggressive path is allowed in a bounded way
- tests whether long-horizon AGA logic remains intact

## Prompt 11: AD Nonsteroidal Innovation Case

```text
请评估一个外用非甾体小分子创新药用于轻中度特应性皮炎的中美临床开发路径。当前仅有非临床药效和一定局部耐受数据，没有人体 PK。希望知道早期临床应如何设计，以及保守和激进路径分别怎么走。
```

Why this test matters:

- tests innovative-topical rather than bridge-heavy logic
- tests AD itch and chronic-use reasoning
- tests whether the answer avoids pretending the program is already pivotal-ready

## Prompt 12: Psoriasis Limited-BSA Topical Case

```text
某外用小分子乳膏拟用于斑块状银屑病，目标人群是轻中度、有限 BSA 人群。请给出中国和 FDA 双路径开发建议，并重点说明是否需要最大使用 PK、长期安全和剂量探索。
```

Why this test matters:

- tests limited-BSA topical psoriasis logic
- tests whether the answer separates topical from systemic psoriasis expectations
- tests how long-term safety and maximal-use PK are balanced

## Prompt 13: Seborrheic Dermatitis Foam Case

```text
请设计一个外用泡沫剂用于脂溢性皮炎的临床开发策略，先美国后中国。项目希望覆盖头皮和面部，强调起效快和依从性提升。请输出保守路径和激进路径。
```

Why this test matters:

- tests scalp and face usability logic
- tests chronic relapsing dermatitis reasoning
- tests whether the answer avoids borrowing fungal cure logic

## Prompt 14: Innovative Oral-to-Topical Uncertain Path Case

```text
某口服已进入临床的小分子拟改为外用喷雾开发新适应症，目前还不能确定按创新药还是改良型新药更合适。请输出第一轮策略判断，并说明外用创新药和改良型新药路径在早期研究设计上的关键差异。
```

Why this test matters:

- tests the new innovative-topical rule layer
- tests path-uncertain reasoning
- tests whether the answer clearly distinguishes proof-of-concept logic from bridge logic

## Manual Review Checklist

When testing these prompts, check:

- Did the answer stay at strategy level?
- Did it produce both conservative and aggressive paths?
- Did it anchor China and FDA differently when needed?
- Did it name the most important missing evidence?
- Did it avoid claiming that PSG or one FDA case controls the whole strategy?
