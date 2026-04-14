# Titan007 全联赛扩展与投注结论输出设计

## 1. 背景

当前仓库已经具备以下能力：

- 基于 Titan007 公开页面抓取未来赛程、欧赔、亚盘、大小球
- 将抓取结果标准化为训练行并训练主冷门模型与冷平模型
- 对指定日期范围输出 `predictions / combined_rankings / draw_rankings`
- 通过 `scripts/titan007_skill_entry.py` 提供统一入口

但当前链路还有两个明显缺口：

- 默认只围绕五大联赛工作，导致 Titan007 页面上其他联赛会被过滤掉，无法形成“全联赛”工作流
- 运行 SKILL 后只给概率和榜单，缺少最终可直接执行的投注结论，用户仍需手动解读概率、阈值和盘口说明

本设计的目标是在不推翻现有主链路的前提下，同时补齐这两个缺口。

## 2. 目标

本阶段交付两个直接可用的结果：

### 2.1 全联赛工作流打通

- `predict-range` 与 `predict-excel` 默认覆盖 Titan007 当页可识别的全部联赛
- `backfill_titan007_history.py` 与 `refresh-models` 默认覆盖 Titan007 可回填的全部联赛
- 现有 `--competitions` 仍可用于按联赛过滤
- 五大联赛之外的联赛也能进入标准化、训练和预测流程

### 2.2 直接输出投注结论

每场比赛除了原始概率字段外，还要新增：

- `建议方向`：`主冷 / 客冷 / 冷平 / 不投注`
- `置信度`：`强 / 中 / 弱 / 不投注`
- `为什么下这个结论`：由模型阈值、方向优势、盘口变化共同生成的解释
- `是否建议投注`：布尔或等价文本字段

最终要求是：用户运行 SKILL 后可以直接看到投注结论，而不是再自己分析数据。

## 3. 范围与非目标

### 3.1 范围

- Titan007 未来比赛抓取
- Titan007 历史回填
- 训练集标准化
- 主冷门模型与冷平模型预测
- Excel / CSV / JSON 输出增强
- SKILL 文档更新

### 3.2 非目标

- 不引入新的第三方商业数据源
- 不重写现有 softmax 模型为新算法
- 不在本阶段做联赛分层阈值
- 不做可视化 BI 面板
- 不做自动定时调度

## 4. 方案概述

本阶段采用：

- `现有 Titan007 主链路 + 联赛通用化层 + 投注结论汇总层`

不采用：

- `只改 SKILL 文案，不改代码`
  原因：无法真正实现全联赛和自动投注结论。
- `为每个联赛单独训练阈值`
  原因：样本尚不稳定，规则过早复杂化会增加维护成本。
- `移除现有五大联赛特征并整体重训新结构`
  原因：风险偏高，不符合“小步可审查 diff”的原则。

## 5. 当前限制分析

当前全联赛无法打通的原因主要有三类：

### 5.1 联赛识别限制

`src/upset_model/collectors/titan007_public.py` 中的 `parse_schedule_matches` 依赖固定的：

- `TITAN007_COMPETITION_NAME_TO_CODE`
- `FOOTBALL_DATA_COMPETITIONS`

因此只有映射里的联赛会被保留，其他联赛会被直接过滤。

### 5.2 标准化限制

`src/upset_model/standardize.py` 中的 `row_to_training_row` 依赖：

- `FOOTBALL_DATA_COMPETITIONS`

如果联赛 code 不在五大联赛映射里，训练行会返回 `None`，无法进入训练和预测。

### 5.3 输出层限制

当前输出只停留在：

- `combined_candidate_label`
- `combined_candidate_probability`
- `secondary_candidate_label`
- `secondary_candidate_probability`
- `draw_upset_probability`
- `explanation`

这些字段需要用户自己再结合阈值、方向差距与盘口说明做二次判断，缺少“最终建议”。

## 6. 目标架构

### 6.1 保持主链路不变

继续复用：

- `scripts/predict_titan007_range.py`
- `scripts/backfill_titan007_history.py`
- `scripts/titan007_skill_entry.py`
- `src/upset_model/modeling.py`
- `src/upset_model/draw_model.py`
- `src/upset_model/excel_report.py`

### 6.2 增加两个薄层

#### A. 联赛通用化层

职责：

- Titan007 联赛名归一化
- 全联赛默认放行
- 支持按 code 或名称过滤
- 为未知联赛生成稳定 code，并保留原始名称

#### B. 投注结论汇总层

职责：

- 读取主模型和冷平模型结果
- 根据固定规则输出投注建议
- 给出 `方向 + 置信度 + 理由`
- 产出排序后的推荐榜单

## 7. 联赛通用化设计

### 7.1 配置层拆分

当前 `FOOTBALL_DATA_COMPETITIONS` 实际承担了两种职责：

- football-data 原始历史数据集的五大联赛定义
- Titan007 在线抓取允许的联赛定义

本阶段将其职责拆开：

- 保留 `FOOTBALL_DATA_COMPETITIONS`
  继续表示 football-data 五大联赛集合
- 新增 Titan007 联赛归一化辅助逻辑
  用于在线抓取和历史回填

新增能力应满足：

- 已知五大联赛继续映射到现有 code：`E0 / SP1 / D1 / I1 / F1`
- 其他 Titan007 联赛根据原始名称生成稳定 code
- 原始联赛中文名始终保留到 `competition_name`

### 7.2 Titan007 联赛 code 规则

对 Titan007 联赛新增一个稳定 code 生成方法，建议格式：

- 已知五大联赛：保留原 code
- 未知联赛：使用 ASCII 安全的稳定格式，如 `T7_<normalized_code>`

例如：

- `中乙` -> `T7_U4E2D_U4E59`
- `瑞典超` -> `T7_U745E_U5178_U8D85`

约束：

- 结果必须稳定，不因单次运行变化
- 同名联赛始终产生相同 code
- code 尽量保持 ASCII 安全，便于 CSV、缓存键和命令行过滤
- 不需要额外联网查询外部标准联赛码

### 7.3 过滤规则

当命令行不传 `--competitions` 时：

- 不再默认限制为五大联赛
- 默认保留 Titan007 页面中全部可识别联赛

当命令行传 `--competitions` 时：

- 继续支持旧 code，如 `E0 SP1`
- 新增支持 Titan007 原始联赛名，如 `英超 中乙 瑞典超`
- 匹配规则应同时接受：
  - 已知 code
  - 原始名称
  - 归一化后 code

### 7.4 标准化兼容策略

`row_to_training_row` 目前会在联赛 code 不属于五大联赛时返回 `None`。

本阶段改为：

- 五大联赛：
  - `competition_name` 使用现有 display name
  - 保留五大联赛 one-hot 特征
- 其他联赛：
  - `competition_code` 保留通用化后的 stable code
  - `competition_name` 使用 Titan007 原始联赛名
  - 五大联赛 one-hot 特征全部置 `0`

这样做的原因：

- 不破坏现有模型特征结构
- 不需要修改模型文件结构
- 让模型主要依赖赔率、亚盘、大小球等通用盘口特征泛化到其他联赛

## 8. 历史回填与重训设计

### 8.1 默认行为变化

`scripts/backfill_titan007_history.py`

- 当前默认 `--competitions` 为五大联赛
- 修改后默认不再限制联赛

`scripts/titan007_skill_entry.py refresh-models`

- 当前窗口组中若未显式指定联赛，默认退回五大联赛
- 修改后窗口组未指定联赛时，默认表示“全联赛”

### 8.2 缓存复用逻辑

现有 refresh 缓存是否可复用，依赖：

- `selected_competitions`
- `training_row_count`
- `failure_count`

修改后需要兼容“全联赛默认模式”：

- 对于显式指定联赛的窗口组，仍按具体列表比较
- 对于未指定联赛的窗口组，缓存摘要中应记为全联赛模式
- 避免因为 “空列表 vs 五大联赛列表” 导致错误复用或重复抓取

### 8.3 训练兼容性

训练逻辑不新增新的联赛特征列，也不改变模型 artifact 结构。

优点：

- 现有模型加载逻辑无需改动
- 历史模型与新模型的 JSON 结构保持兼容
- diff 小，风险可控

风险：

- 非五大联赛没有专属联赛特征

对应处理：

- 在投注结论层加入更严格的“是否建议投注”门槛
- 明确允许输出 `不投注`

## 9. 投注结论设计

### 9.1 结论字段

新增统一结论字段，建议命名如下：

- `bet_direction`
  可选值：`主冷 / 客冷 / 冷平 / 不投注`
- `bet_confidence`
  可选值：`强 / 中 / 弱 / 不投注`
- `bet_recommendation`
  可选值：`建议投注 / 谨慎关注 / 不投注`
- `bet_reason`
  中文短句，直接解释为什么形成该结论
- `direction_probability`
  主方向概率
- `direction_gap`
  主方向概率减去次方向概率

必要时可补充机器可读字段：

- `bet_direction_code`
- `bet_confidence_score`
- `bet_recommendation_rank`

### 9.2 主方向判定

主方向来自现有的 `combined_candidate_label`：

- `home_upset_win` -> `主冷`
- `away_upset_win` -> `客冷`
- `draw_upset` -> `冷平`

若不满足最低下注门槛，则直接改判为：

- `不投注`

### 9.3 最低下注门槛

首版采用固定阈值规则，不做联赛分层。

建议规则：

- 对 `主冷 / 客冷`
  - 要求 `upset_score >= main_model.decision_threshold`
- 对 `冷平`
  - 要求 `draw_upset_probability >= draw_model.decision_threshold`
- 对所有方向
  - 要求 `direction_gap >= 0.06`

任何一条不满足时：

- `bet_direction = 不投注`
- `bet_confidence = 不投注`
- `bet_recommendation = 不投注`

### 9.4 置信度分级

首版用统一规则：

- `强`
  - 主方向概率至少高于对应阈值 `0.08`
  - 且 `direction_gap >= 0.10`
- `中`
  - 主方向概率至少高于对应阈值 `0.03`
  - 且 `direction_gap >= 0.06`
- `弱`
  - 达到最低下注门槛，但未达到 `中`
- `不投注`
  - 未达到最低门槛

说明：

- 对 `主冷 / 客冷`，“主方向概率”使用 `combined_candidate_probability`
- 对 `冷平`，同样使用 `combined_candidate_probability`，其来源即 `draw_upset_probability`

### 9.5 最终推荐文案

将 `方向` 与 `置信度` 转换为更直观的推荐：

- `强` -> `建议投注`
- `中` -> `建议投注`
- `弱` -> `谨慎关注`
- `不投注` -> `不投注`

### 9.6 理由生成

理由分两层：

#### A. 决策理由

直接解释为什么给出该建议，优先包含：

- 主方向概率是否超过模型阈值
- 主方向领先次方向多少
- `upset_score` 是否达到主模型阈值
- 若不投注，则明确写出哪条门槛未满足

示例：

- `冷平概率 0.48，达到冷平模型门槛 0.48`
- `主方向领先次方向 0.12，方向更明确`
- `综合冷门分 0.61，高于主模型门槛 0.58`
- `主次方向差仅 0.03，信号不够集中，建议观望`

#### B. 盘口理由

复用并增强现有 explanation：

- 主胜/客胜赔率变化
- 平赔变化
- 最低赔与次低赔差距变化
- 亚盘变化
- 大小球赔率变化

#### C. 最终输出

`bet_reason` 由 2 到 4 个短句组成，顺序为：

1. 是否达到门槛
2. 方向差距是否清晰
3. 盘口变化支持点

## 10. 推荐榜单设计

### 10.1 新增推荐榜单

在现有：

- `combined_rankings.csv`
- `draw_rankings.csv`

之外，新增：

- `betting_recommendations.csv`
- `betting_recommendations.json`

每行至少包含：

- 基本比赛信息
- 主次方向概率
- `bet_direction`
- `bet_confidence`
- `bet_recommendation`
- `bet_reason`

### 10.2 排序规则

推荐榜单按以下优先级排序：

1. 是否建议投注
2. 置信度等级
3. 主方向概率
4. 主次方向差
5. `upset_score`

目的：

- Top 区域更接近“今日可操作场次”
- 避免仅按原始概率排序而忽略方向模糊场次

## 11. 终端输出设计

### 11.1 `predict-range`

保留现有：

- Combined leaderboard
- Draw leaderboard

新增：

- `Betting recommendations`

每条摘要建议输出：

- 比赛日期
- 联赛
- 对阵
- 建议方向
- 置信度
- 是否建议投注
- 核心理由

示例格式：

```text
2026-04-17 I1 萨索洛 vs 科莫 建议=冷平 置信度=中 建议投注
原因=冷平概率 0.48 达到门槛；领先次方向 0.17；平赔与盘口变化支持冷平
```

### 11.2 `predict-excel`

保留现有输出路径打印，并补充：

- 推荐榜单文件路径
- 终端 Top 建议摘要

## 12. Excel 设计

### 12.1 新增 sheet

在原有：

- `summary`
- `combined_rankings`
- `draw_rankings`
- `all_predictions`

之外新增：

- `betting_recommendations`

### 12.2 推荐 sheet 字段

建议字段：

- `match_date`
- `kickoff_time`
- `competition_code`
- `competition_name`
- `home_team`
- `away_team`
- `bet_direction`
- `bet_confidence`
- `bet_recommendation`
- `combined_candidate_label`
- `combined_candidate_probability`
- `secondary_candidate_label`
- `secondary_candidate_probability`
- `direction_gap`
- `upset_score`
- `draw_upset_probability`
- `bet_reason`

### 12.3 Summary 预览

`summary` 页新增 `betting_top_preview` 区域，展示前 10 条推荐。

### 12.4 呈现要求

- 概率列使用百分比格式
- `bet_confidence` 使用固定颜色区分
- `bet_direction` 使用固定颜色区分
- `不投注` 行使用弱化颜色，便于人工快速略过

## 13. SKILL 更新设计

更新 `/Users/huanglu/.codex/skills/football-upset-predictor/SKILL.md`，明确：

- 默认覆盖 Titan007 全联赛
- `predict-excel` 不再只返回 Excel 路径和排行榜
- 返回时优先总结投注建议榜
- 如果 draw model 缺失，要说明冷平建议会退化

建议更新后的输出契约：

- 优先返回 Excel 路径
- 同时返回投注推荐前几名
- 每条推荐包含：方向、置信度、理由

## 14. 兼容策略

### 14.1 命令兼容

以下命令形式保持可用：

```bash
PYTHONPATH=src python3 scripts/titan007_skill_entry.py predict-range --start-date 2026-04-18 --end-date 2026-04-20
PYTHONPATH=src python3 scripts/titan007_skill_entry.py predict-excel --start-date 2026-04-18 --end-date 2026-04-20
PYTHONPATH=src python3 scripts/titan007_skill_entry.py refresh-models --validation-season 2526
```

### 14.2 参数兼容

- 旧 code 过滤继续支持，如 `E0 SP1`
- Titan007 原始联赛名过滤新增支持
- 未传 `--competitions` 时的默认行为从“五大联赛”切换为“全联赛”

### 14.3 模型文件兼容

- 不改变 `SoftmaxModelArtifact` 结构
- 不改变现有 feature list 的基本框架
- 老模型仍可被加载

## 15. 测试设计

### 15.1 单元测试

补充以下测试：

- 未知联赛在 `parse_schedule_matches` 中可被保留
- 未知联赛可生成稳定 code
- 未知联赛可进入 `snapshot_row_to_training_row`
- 五大联赛原行为不回归
- 投注结论规则输出 `主冷 / 客冷 / 冷平 / 不投注`
- 置信度规则输出 `强 / 中 / 弱 / 不投注`
- `bet_reason` 能覆盖门槛不足与方向明确两类情况

### 15.2 Excel 测试

- 新 sheet `betting_recommendations` 存在
- summary 中存在推荐预览
- 推荐字段正确落盘

### 15.3 入口测试

- `predict-excel` 运行后写出推荐文件路径
- `refresh-models` 在全联赛默认下能正确写出摘要
- 缓存复用逻辑对“全联赛模式”有效

## 16. 风险与缓解

### 16.1 非五大联赛泛化不稳定

风险：

- 非五大联赛缺少联赛专属特征，模型效果可能不如五大联赛稳定

缓解：

- 保留“不投注”作为一等结论
- 首版强调门槛与方向差距

### 16.2 Titan007 联赛名不稳定

风险：

- 同一联赛在页面上可能出现别名或不同写法

缓解：

- 先做基础归一化与稳定 code 规则
- 保留原始 `competition_name`，便于后续修正规则

### 16.3 训练样本结构变化

风险：

- 全联赛进入后，训练集规模和分布变化会影响现有阈值

缓解：

- 重训后继续使用已有阈值推荐逻辑重新生成 `decision_threshold`
- 在 refresh 摘要中保留核心指标，便于比较

## 17. 实施顺序

建议按以下顺序落地：

1. 配置与 Titan007 联赛通用化
2. 标准化兼容未知联赛
3. 预测链路默认全联赛
4. 历史回填与 refresh 全联赛
5. 投注结论汇总层
6. Excel / CSV / JSON 输出增强
7. SKILL 文档更新
8. 测试补齐

## 18. 验收标准

满足以下条件视为完成：

- 不传 `--competitions` 时，Titan007 预测和历史回填默认覆盖全联赛
- 非五大联赛不会在解析或标准化时被静默丢弃
- 运行 `predict-excel` 后，能直接看到投注推荐，而不是只看到概率榜
- 推荐结果至少包含：`方向 + 置信度 + 原因`
- Excel、CSV、JSON、终端输出都能看到统一口径的投注建议
- SKILL 文档明确新的默认行为和输出契约
