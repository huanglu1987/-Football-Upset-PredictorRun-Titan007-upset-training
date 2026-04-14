# Implementation Plan: 球探冷胜预测模型

## Overview

本计划基于已确认的设计文档，目标是在可稳定访问的赔率数据源前提下，交付两个可复用入口：

- 训练入口：完成历史回填、特征生成、模型训练与回测
- 预测入口：输入比赛日期范围，输出逐场冷胜概率与每日排行榜

首版不追求大而全，而是先把“可稳定抓取、可复现训练、可按日期区间预测”这三件事做扎实。

## Linked Specification

- 设计文档：`/Users/huanglu/Projects/球探冷门/docs/superpowers/specs/2026-04-13-win007-upset-model-design.md`

## Requirements Summary

### Functional Requirements

- 使用可稳定访问的数据源抓取五大联赛近 3 赛季比赛与赔率数据
- 只预测 `home_upset_win`、`away_upset_win`、`non_upset`
- 训练入口能够完成历史数据回填、特征生成、模型训练、回测报告输出
- 预测入口能够接收日期范围并输出逐场冷胜概率、每日 Top N、简短赔率解释
- 当历史赔率波动轨迹不可得时，系统能够自动降级为“初赔 vs 临场”的双时点模型

### Non-Functional Requirements

- **可复现性**：原始抓取结果必须缓存，训练结果可重跑
- **可解释性**：预测输出必须带简短赔率解释
- **容错性**：字段缺失时要有显式降级与日志
- **可扩展性**：后续可在不推翻结构的情况下加入平局冷门和更多特征

### Acceptance Criteria

- [ ] 能在单联赛样本上稳定完成抓取与解析
- [ ] 能扩展到五大联赛近 3 赛季并产出标准化数据
- [ ] 能完成至少一轮时间切分训练与回测
- [ ] 能按日期范围输出预测结果和 Top N 排行
- [ ] 预测结果在数据不完整时有明确标记而非静默失败

## Technical Approach

### Architecture

实现按“先验证，再扩量”的顺序推进：

1. 先验证候选数据源的可访问性、字段完整性和自动化稳定性
2. 再做历史回填与标准化数据落盘
3. 然后构建特征、训练模型、生成回测报告
4. 最后提供按日期区间预测的统一入口，并封装成双技能工作流

### Proposed Repository Structure

以下是建议的首版目录结构：

```text
/Users/huanglu/Projects/球探冷门/
├── docs/
│   └── superpowers/
│       ├── specs/
│       └── plans/
├── data/
│   ├── raw/
│   ├── interim/
│   ├── features/
│   └── models/
├── src/
│   └── upset_model/
│       ├── collectors/
│       ├── parsers/
│       ├── datasets/
│       ├── features/
│       ├── training/
│       ├── prediction/
│       └── utils/
├── scripts/
└── tests/
```

### Key Design Decisions

1. **先做抓取探针再铺全量管线**：因为最大风险在数据源稳定性，不应先写完整训练系统再发现页面字段拿不到。
2. **原始数据与特征数据分层存储**：保证后续重训不依赖重复抓取。
3. **训练和预测入口分离**：与你的最终使用方式一致，也能降低单个入口复杂度。
4. **优先双时点模型**：先把 `初赔 -> 临场` 的净变化做稳，再视球探页面能力决定是否加入完整波动轨迹特征。
5. **优先稳定源而不是页面抓取**：如果公开网页反爬或连接层不稳定，优先切到 CSV/API 源，减少工程噪音。

### Preferred Data Sources

- `football-data.co.uk`
  - 用途：历史训练、回测、基线模型
  - 优点：现成 CSV，覆盖多年历史，适合快速建训练集
  - 局限：不一定有完整盘口波动轨迹，盘口深度受字段限制

- `API-Football`
  - 用途：自动化预测入口、赛前抓取
  - 优点：有官方 API 形态，适合日期区间查询和程序化调用
  - 局限：额度与历史深度依赖套餐，需要 API Key

## Implementation Phases

### Phase 1: 抓取探针与项目骨架

**Goal**: 确认候选数据源可抓取、可解析，并搭起最小工程骨架

**Tasks**:

- [ ] 初始化 Python 项目骨架与基础依赖
- [ ] 选定一个联赛、一个赛季做源站探针
- [ ] 验证历史文件或 API 是否能稳定取到比赛 ID、开赛时间、对阵、赛果
- [ ] 验证 `1X2`、亚盘、大小球的初赔与临场字段是否稳定存在
- [ ] 确认原始响应缓存格式与目录结构

**Deliverables**:

- 一套可运行的数据源探针
- 一份字段可得性清单
- 一份数据源风险记录

**Estimated effort**: 1-2 天

### Phase 2: 历史回填与标准化

**Goal**: 回填五大联赛近 3 赛季数据，并落成统一标准化表

**Tasks**:

- [ ] 扩展比赛列表抓取到五大联赛近 3 赛季
- [ ] 按比赛 ID 或联赛赛季批量获取 `1X2`、亚盘、大小球数据
- [ ] 设计并实现 `raw_matches` 与 `raw_odds_snapshots` 落盘逻辑
- [ ] 增加重试、限速、字段缺失日志
- [ ] 输出历史回填覆盖率统计

**Deliverables**:

- `data/raw/` 下的原始页面缓存
- `data/interim/` 下的标准化比赛与赔率数据
- 覆盖率与缺失率报告

**Estimated effort**: 2-4 天

### Phase 3: 特征工程与训练集构建

**Goal**: 形成可训练的数据集，并明确降级逻辑

**Tasks**:

- [ ] 实现冷胜标签生成逻辑
- [ ] 构建 `1X2` 静态与变化特征
- [ ] 构建亚盘联动与大小球联动特征
- [ ] 实现缺失特征策略与数据完整度标记
- [ ] 生成 `model_features` 数据表

**Deliverables**:

- `data/features/` 下的训练特征表
- 特征字典与字段说明
- 样本分布报告

**Estimated effort**: 2-3 天

### Phase 4: 模型训练与回测

**Goal**: 产出第一版可用模型，并完成严格时间切分回测

**Tasks**:

- [ ] 建立基线模型与主模型
- [ ] 实现时间切分训练流程
- [ ] 输出 precision、recall、Top N 命中率与校准结果
- [ ] 对比不同联赛表现
- [ ] 将模型与元数据落盘

**Deliverables**:

- `data/models/` 下的模型文件与元数据
- 回测结果表
- 一份简洁回测报告

**Estimated effort**: 2-3 天

### Phase 5: 日期区间预测入口

**Goal**: 输入日期范围即可出预测结果

**Tasks**:

- [ ] 实现待预测比赛抓取逻辑
- [ ] 复用训练期特征流程构建预测特征
- [ ] 载入模型并输出主冷胜/客冷胜概率
- [ ] 生成每日 Top N 排行
- [ ] 生成简短赔率解释与数据完整度提示

**Deliverables**:

- 一个可按日期范围运行的预测入口
- 逐场结果表
- 每日排行榜输出

**Estimated effort**: 1-2 天

### Phase 6: 双技能封装与使用文档

**Goal**: 把训练与预测统一成可复用的技能式入口

**Tasks**:

- [ ] 梳理训练入口参数与输出约定
- [ ] 梳理预测入口参数与输出约定
- [ ] 编写运行说明与示例命令
- [ ] 补充最关键的集成测试

**Deliverables**:

- 训练入口说明
- 预测入口说明
- 最小使用手册

**Estimated effort**: 1 天

## Dependencies

### External Dependencies

- 候选数据源可稳定访问：`待验证`
- Python 运行环境与基础科学计算库：`可控`

### Internal Dependencies

- 当前仓库为空目录，需要从零建立项目结构

### Blockers

- 历史数据源是否提供足够深度的盘口字段：`高风险未验证`
- API 额度、限流或商业授权限制：`高风险未验证`

## Risks & Mitigation

### Risk 1: 历史盘口波动轨迹不可得

- **Probability**: High
- **Impact**: High
- **Mitigation**: 首版默认按双时点模型设计，先不依赖完整时间序列

### Risk 2: 数据源字段命名或返回结构不稳定

- **Probability**: Medium
- **Impact**: High
- **Mitigation**: 原始响应缓存 + 解析日志 + 字段探针测试

### Risk 3: 大规模回填时触发限流

- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: 限速、重试、断点续跑、缓存复用

### Risk 4: 类别不平衡导致冷胜概率失真

- **Probability**: High
- **Impact**: Medium
- **Mitigation**: 使用时间切分评估、校准概率、重点看 Top N 命中率而不是整体准确率

## Timeline

| Milestone | Target | Status |
|-----------|--------|--------|
| 抓取探针完成 | 2026-04-14 | Planned |
| 历史回填完成 | 2026-04-17 | Planned |
| 特征与训练完成 | 2026-04-20 | Planned |
| 预测入口完成 | 2026-04-21 | Planned |
| 双技能封装完成 | 2026-04-22 | Planned |

## Success Criteria

### Technical Success

- [ ] 原始页面可缓存并重复解析
- [ ] 标准化表可稳定生成
- [ ] 模型训练与回测可重复运行
- [ ] 预测入口可按日期范围稳定出结果

### Product Success

- [ ] 你可以输入日期范围直接拿到逐场结果
- [ ] 输出同时包含概率、排行榜和简短赔率解释
- [ ] 在数据不完整时系统行为仍可理解

## Minimal First Build

为了最快进入代码实现，建议第一个可开工范围只包括：

- 先搭 Python 项目骨架
- 只验证一个联赛、一个赛季的抓取探针
- 先只打通 `比赛列表 -> 1X2/亚盘/大小球 -> 标准化落盘`
- 暂不在第一轮就写完整训练和预测入口

只要这个最小链路通了，后面扩到五大联赛和双入口就会快很多。

## Next Action

下一步直接进入 Phase 1，优先创建以下内容：

- 项目基础目录
- 抓取探针脚本
- 原始页面缓存逻辑
- 第一版字段解析器
