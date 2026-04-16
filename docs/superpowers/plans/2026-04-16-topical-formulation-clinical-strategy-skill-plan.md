# Implementation Plan: 外用制剂临床开发策略 SKILL

## Overview

本计划基于已确认的设计文档，目标是在当前项目目录下交付一个最小可用的 SKILL 骨架，使其能够围绕中国与 FDA 场景，为皮肤外用、局部起效的小分子制剂输出可解释的临床开发策略。

首版实现不追求一开始就把全部法规、案例和适应症资料塞满，而是先把以下三件事做扎实：

- 固定工作流
- 固定输入与输出结构
- 固定四个优先适应症模块入口

## Linked Specification

- 设计文档：`/Users/huanglu/Projects/球探冷门/docs/superpowers/specs/2026-04-16-topical-formulation-clinical-strategy-skill-design.md`

## Requirements Summary

### Functional Requirements

- 在品种信息输入后，输出中国 / FDA / 中美双报场景下的临床开发策略。
- 同时覆盖创新药与改良型新药，第一版重点支持改良型新药。
- 默认输出保守路径与激进路径，并说明推荐路径。
- 对每条关键建议给出依据类型、依据要点和适用前提。
- 优先支持痤疮、玫瑰痤疮、浅表真菌感染和 AGA。

### Non-Functional Requirements

- **可解释性**：所有关键建议都必须带依据说明。
- **可扩展性**：后续新增适应症或案例时不推翻当前结构。
- **时效性**：FDA、PSG、公开 review 在需要时可运行时检索。
- **稳健性**：信息不全时仍可输出初版策略，但需标记不确定项。

### Acceptance Criteria

- [x] 技能目录完成初始化并通过基础校验。
- [x] `SKILL.md` 明确触发条件、工作流和输出边界。
- [x] `references/` 下具备输入模板、输出模板、资料层地图和四个优先适应症模块。
- [x] 技能默认要求输出保守/激进双路径。
- [x] 技能明确要求 FDA/最新/PSG/具体品种场景触发联网检索。
- [x] 第二轮补充法规依据卡、FDA 审评案例卡和中美差异卡。
- [x] 仓库层面对该技能目录解除 `.gitignore` 阻断，便于后续上传 GitHub。

## Technical Approach

### Architecture

首版按“先固化结构，再补充深度”的顺序推进：

1. 搭建技能骨架与 UI 元数据
2. 写入主工作流和输入/输出模板
3. 建立资料层地图，明确本地资料与运行时检索边界
4. 建立 4 个优先适应症模块
5. 进行结构校验

### Proposed Repository Structure

```text
/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/
└── topical-clinical-strategy/
    ├── SKILL.md
    ├── agents/
    │   └── openai.yaml
    └── references/
        ├── cde-fda-differences.md
        ├── workflow.md
        ├── source-map.md
        ├── input-template.md
        ├── output-template.md
        ├── regulatory/
        │   ├── china-core.md
        │   └── fda-core.md
        ├── review-cases/
        │   └── topical-fda-cases.md
        └── indications/
            ├── acne.md
            ├── rosacea.md
            ├── superficial-fungal.md
            └── aga.md
```

### Key Design Decisions

1. **先做规则入口，不先做大而全资料库**：避免一开始就被资料堆积拖慢可用性。
2. **把“静态资料层 + 运行时检索层”写入技能流程**：保证输出既稳又不过时。
3. **把双路径输出做成默认行为**：不把保守/激进作为额外功能。
4. **把优先适应症拆成独立 reference 文件**：后续扩容时更容易维护。
5. **把浓度依据不足改为非阻断风险提示**：适应口服改外用等真实场景。

## Implementation Phases

### Phase 1: 初始化技能骨架

**Goal**: 创建标准 skill 目录和基础元数据

**Tasks**:

- [x] 使用 `init_skill.py` 初始化 skill 目录
- [x] 创建 `agents/openai.yaml`
- [x] 建立 `references/` 基础目录

**Deliverables**:

- 可识别的技能目录
- 可继续编辑的初始文件结构

### Phase 2: 固化主工作流

**Goal**: 让技能具备稳定的使用方式

**Tasks**:

- [x] 完成 `SKILL.md`
- [x] 写入资料层、决策流程、联网触发条件
- [x] 写入输入不足时的处理规则

**Deliverables**:

- 一份完整的技能主说明

### Phase 3: 固化输入与输出模板

**Goal**: 让技能有稳定的问法和稳定的答案形态

**Tasks**:

- [x] 编写输入模板
- [x] 编写输出模板
- [x] 在工作流中引用模板文件

**Deliverables**:

- `input-template.md`
- `output-template.md`

### Phase 4: 建立资料层地图

**Goal**: 明确静态资料、动态检索和证据分级

**Tasks**:

- [x] 编写本地资料与官方资料地图
- [x] 明确中国指导原则、FDA guidance、PSG、公开 review 的层级关系
- [x] 明确何时必须联网

**Deliverables**:

- `source-map.md`

### Phase 5: 建立四个优先适应症模块

**Goal**: 让技能对优先适应症具备更高质量的专属判断

**Tasks**:

- [x] 编写痤疮模块
- [x] 编写玫瑰痤疮模块
- [x] 编写浅表真菌感染模块
- [x] 编写 AGA 模块

**Deliverables**:

- `references/indications/` 下的 4 个文件

### Phase 6: 校验与后续迭代入口

**Goal**: 确保骨架可用，并为后续规则卡扩展预留空间

**Tasks**:

- [x] 运行 `quick_validate.py`
- [x] 检查文件层级、frontmatter 和元数据
- [x] 记录下一轮需要补充的法规卡、案例卡和 PSG 清单

**Deliverables**:

- 通过校验的最小可用技能
- 下一轮扩展方向

### Phase 7: 第二轮资料充实与 GitHub 友好化

**Goal**: 把骨架扩展为更适合团队复用和仓库分发的版本

**Tasks**:

- [x] 补充中国核心法规依据卡
- [x] 补充 FDA 核心法规依据卡
- [x] 补充 CDE vs FDA 差异卡
- [x] 补充 FDA 公开审评案例卡
- [x] 解除该技能目录在 `.gitignore` 中的阻断

**Deliverables**:

- `references/regulatory/` 目录
- `references/review-cases/` 目录
- `references/cde-fda-differences.md`
- GitHub 友好的版本控制配置

### Phase 8: 第三轮稳健性增强

**Goal**: 提升技能在团队试用阶段的稳定性、可解释性和可验证性

**Tasks**:

- [x] 增加 PSG 使用策略说明
- [x] 增加常见失败模式清单
- [x] 增加验证用 prompts 集
- [x] 把以上内容接入主技能工作流

**Deliverables**:

- `references/psg-strategy.md`
- `references/failure-patterns.md`
- `references/validation-prompts.md`
- 更稳健的 `SKILL.md` / `workflow.md` / `source-map.md`

### Phase 9: 第四轮实战验证修正

**Goal**: 通过首轮人工回测发现输出层缺口，并把这些缺口固化进技能自身

**Tasks**:

- [x] 记录首轮人工验证结果
- [x] 增加输出自检清单
- [x] 强化“第一轮策略判断”模式
- [x] 修正单区域输出时不应机械强制中美对照的问题

**Deliverables**:

- `references/output-self-check.md`
- `references/validation-results-round4.md`
- 更稳健的 `output-template.md`

### Phase 10: 第五轮示范案例沉淀

**Goal**: 为团队试用和后续发布准备可直接参考的代表性示范输出

**Tasks**:

- [x] 选择四个高代表性场景
- [x] 为每个场景编写示范输入与示范输出骨架
- [x] 增加示范案例索引并接入主工作流

**Deliverables**:

- `references/worked-examples/index.md`
- `references/worked-examples/acne-combination-dual-region.md`
- `references/worked-examples/rosacea-us-chronic.md`
- `references/worked-examples/superficial-fungal-short-course.md`
- `references/worked-examples/aga-topical-finasteride-risk.md`

### Phase 11: 第六轮内测分发准备

**Goal**: 在不正式发布 GitHub 的前提下，先把同事下载后的安装和试用路径整理清楚

**Tasks**:

- [x] 增加专用安装脚本
- [x] 增加同事可读的安装/试用说明
- [x] 补充两个更贴近业务语境的示范案例
- [x] 把业务近邻案例接入 worked examples 和 validation prompts

**Deliverables**:

- `scripts/install_topical_clinical_strategy_skill.sh`
- `docs/superpowers/guides/topical-clinical-strategy-skill-usage.md`
- `references/worked-examples/terbinafine-topical-dual-region.md`
- `references/worked-examples/minoxidil-optimization-dual-region.md`

### Phase 12: 第七轮封版前验收与发布准备

**Goal**: 在不实际发布 GitHub 的前提下，把业务验收、已知边界、ClinicalTrials 先例层和发布前检查项补齐

**Tasks**:

- [x] 记录第七轮业务验收与发布准备结论
- [x] 增加已知边界/不适用场景说明
- [x] 增加 `ClinicalTrials.gov` 设计先例层说明
- [x] 增加 GitHub 发布前检查清单
- [x] 把以上入口接回主技能工作流和使用说明

**Deliverables**:

- `references/validation-results-round7.md`
- `references/known-boundaries.md`
- `references/clinicaltrials-strategy.md`
- `docs/superpowers/guides/topical-clinical-strategy-github-release-checklist.md`

### Phase 13: 第八轮适应症扩展与创新药细化

**Goal**: 在保持当前结构稳定的前提下，先扩展 3 个常见适应症模块，再把外用创新药逻辑从改良型新药逻辑中单独做细

**Tasks**:

- [x] 增加 AD 模块
- [x] 增加银屑病模块
- [x] 增加脂溢性皮炎模块
- [x] 增加外用创新药规则文件
- [x] 把新模块和新规则接回主工作流、资料地图和边界说明
- [x] 增加对应验证 prompts

**Deliverables**:

- `references/indications/ad.md`
- `references/indications/psoriasis.md`
- `references/indications/seborrheic-dermatitis.md`
- `references/innovative-topical-rules.md`

## Risks and Mitigations

- **风险：资料层过重，技能说明过长**
  - 处理：把详细内容放入 `references/`，`SKILL.md` 只保留工作流
- **风险：FDA 资料时效性不够**
  - 处理：把 FDA/PSG/具体品种设为联网触发场景
- **风险：AGA 等模块依据不如痤疮充分**
  - 处理：在模块中显式标记高不确定性和高风险点
- **风险：把 PSG 误当成创新药或 505(b)(2) 硬要求**
  - 处理：在资料层地图和主工作流中明确 PSG 仅为辅助层

## Next Iteration Candidates

- 补充更细的 PSG 清单和适应症映射
- 按适应症增加更多法规卡和失败案例卡
- 增加 AD、银屑病、脂溢性皮炎等扩展模块
- 视团队需要把 China-side public registry 也做成独立资料层
- 决定本地原始 PDF / CSV 是否需要生成 repo-safe 摘要或索引文件
- 当你确定 GitHub 仓库后，执行最后的发布动作
