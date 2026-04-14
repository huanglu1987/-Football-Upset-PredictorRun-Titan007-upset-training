# 球探 Excel 报告技能与历史扩窗重训设计

## 1. 背景

当前工程已经具备以下能力：

- 基于球探公开页自动抓取未来比赛的 `1X2 / 亚盘 / 大小球`
- 生成逐场预测结果、联合榜和冷平榜
- 训练主模型与冷平模型
- 通过统一入口脚本运行 `predict-range` 与 `train-models`

离“最终可用”的状态还差两段关键能力：

- 给定日期范围后，直接产出一份适合人工查看和筛选的 Excel 报告
- 继续扩充球探同源历史窗口，提升 `Top-20` 冷门筛选表现，以及主冷/客冷分向稳定性

本子项目在不推翻现有主链路的前提下，补齐这两段能力。

## 2. 子项目目标

本阶段同时交付两类能力：

### 2.1 Excel 报告版预测技能

- 输入 `start_date / end_date`
- 自动抓取球探未来比赛
- 自动生成主模型与冷平模型预测
- 自动写出 `.xlsx` 报告
- 返回 Excel 路径和关键榜单摘要

### 2.2 历史扩窗重训能力

- 通过一份固定窗口清单，批量回填球探同源历史样本
- 自动合并训练集
- 自动重训主模型与冷平模型
- 输出训练摘要，重点展示：
  - `Top-10 / Top-20 upset precision`
  - `Top-20 home_upset_win precision`
  - `Top-20 away_upset_win precision`
  - `Top-20 draw_upset precision`

## 3. 范围与非目标

### 3.1 范围

- 数据来源：球探公开页
- 预测对象：
  - `home_upset_win`
  - `away_upset_win`
  - `draw_upset`
- 输出形式：
  - Excel 报告
  - 预测 JSON/CSV
  - 训练摘要 JSON
  - 历史窗口回填摘要

### 3.2 非目标

- 不引入新的商业 API
- 不建设实时轮询盘口数据库
- 不做图表型 BI 面板
- 不在本阶段重写模型算法
- 不做自动定时调度

## 4. 方案选择

本阶段采用以下方案：

- `现有预测主链路 + Excel 导出层 + 历史窗口编排层`

不采用以下方案作为本阶段主路径：

- `只导出 CSV`
  原因：不满足“给日期就直接出 Excel 报告”的最终使用形态。
- `直接做复杂可视化图表工作簿`
  原因：增加实现和维护成本，首版收益有限。
- `手工维护历史窗口命令`
  原因：可复现性差，后续不便比较模型版本。

## 5. 系统边界

本阶段新增两个薄层，复用现有主链路。

### 5.1 `excel_reporter`

职责：

- 读取预测结果与运行摘要
- 生成结构化 Excel 报告
- 提供清晰、稳定的 sheet 布局
- 保留适合二次筛选和人工看盘的字段

### 5.2 `history_expander`

职责：

- 读取固定窗口清单
- 调用现有历史回填脚本批量抓取
- 合并多个窗口的 `training_rows.csv`
- 调用现有训练脚本重训双模型
- 输出训练对比摘要

### 5.3 现有主链路保持不变

继续复用：

- `scripts/backfill_titan007_history.py`
- `scripts/train_upset_model.py`
- `scripts/train_draw_model.py`
- `scripts/predict_titan007_range.py`
- `scripts/titan007_skill_entry.py`

新增逻辑尽量作为编排层和导出层，不侵入抓取与建模主干。

## 6. Excel 报告设计

首版固定生成一个工作簿，包含四个 sheet。

### 6.1 `summary`

作用：提供一眼可读的运行概览。

建议内容：

- 报告生成时间
- 请求日期范围
- 选定联赛范围
- 主模型路径
- 冷平模型路径
- 抓取比赛数
- 成功打分数
- 失败数
- 当前主模型指标：
  - `accuracy`
  - `top_10_upset_precision`
  - `top_20_upset_precision`
  - `top_20_home_upset_win_precision`
  - `top_20_away_upset_win_precision`
- 当前冷平模型指标：
  - `top_20_draw_upset_precision`
  - `draw_precision`
  - `draw_recall`
- 当次联合榜 Top 场次摘要

### 6.2 `combined_rankings`

作用：作为日常主用榜单。

建议字段：

- `match_date`
- `kickoff_time`
- `competition_code`
- `competition_name`
- `home_team`
- `away_team`
- `combined_candidate_label`
- `combined_candidate_probability`
- `secondary_candidate_label`
- `secondary_candidate_probability`
- `home_upset_probability`
- `draw_upset_probability`
- `away_upset_probability`
- `upset_score`
- `predicted_label`
- `explanation`

### 6.3 `draw_rankings`

作用：单独看冷平信号。

建议字段：

- `match_date`
- `kickoff_time`
- `competition_code`
- `competition_name`
- `home_team`
- `away_team`
- `draw_upset_probability`
- `combined_candidate_label`
- `secondary_candidate_label`
- `explanation`

### 6.4 `all_predictions`

作用：保留全部比赛完整明细，便于用户自行筛选、透视和归档。

直接写入完整预测字段，包含：

- 所有概率列
- 主次方向列
- 当前判定标签
- 原始解释字段

### 6.5 Excel 呈现要求

首版不做图表，但应具备以下可用性增强：

- 冻结首行
- 全列自动筛选
- 概率列使用百分比格式
- 列宽按内容自动调整到可读范围
- `combined_candidate_label` 使用固定颜色区分：
  - `home_upset_win`
  - `draw_upset`
  - `away_upset_win`
- `failure_count > 0` 时，在 `summary` 中醒目标记

## 7. 统一入口设计

统一入口扩展成两个更贴近最终用户心智的动作：

### 7.1 `predict-excel`

建议命令形态：

```bash
PYTHONPATH=src python3 scripts/titan007_skill_entry.py predict-excel \
  --start-date 2026-04-18 \
  --end-date 2026-04-20 \
  --top-n 20
```

内部流程：

1. 调用现有 `predict_titan007_range.py`
2. 获取本次运行目录和预测 CSV/JSON
3. 读取主模型与冷平模型摘要
4. 生成 Excel 报告
5. 打印 Excel 路径和榜单摘要

### 7.2 `refresh-models`

建议命令形态：

```bash
PYTHONPATH=src python3 scripts/titan007_skill_entry.py refresh-models \
  --validation-season 2526
```

内部流程：

1. 读取默认窗口清单
2. 批量回填历史窗口
3. 合并成统一 `training_rows.csv`
4. 重训主模型
5. 重训冷平模型
6. 输出训练摘要 JSON
7. 更新默认模型文件

## 8. 历史窗口扩充策略

本阶段不再依赖手工拼接多个命令，而是改为固定窗口清单。

### 8.1 窗口选择原则

- 优先覆盖五大联赛比赛密集的周末
- 尽量覆盖赛季早期、中期、后期
- 尽量分布在不同赛季，避免单赛季过度集中
- 避开国际比赛日和明显稀疏赛程周

### 8.2 目标扩充范围

建议在现有基础上继续补：

- `2324`：新增 `3-4` 个周末窗口
- `2425`：新增 `3-4` 个周末窗口
- `2526`：新增 `2-3` 个已完赛窗口

目标不是一次性覆盖整赛季，而是先把样本增厚到足够稳定比较 `Top-20` 指标。

### 8.3 编排方式

建议新增一个窗口清单文件，例如：

- `data/interim/titan007/default_history_windows.json`

内容包括：

- `date_ranges`
- 适用联赛
- 可选备注

历史扩窗编排脚本负责：

1. 逐窗口调用回填脚本
2. 收集成功窗口与失败窗口
3. 合并所有成功窗口的 `training_rows.csv`
4. 输出合并后的训练集

## 9. 训练与评估输出

本阶段训练输出重点从“单一 accuracy”转向“筛选稳定性”。

### 9.1 主模型重点指标

- `top_10_upset_precision`
- `top_20_upset_precision`
- `top_20_home_upset_win_precision`
- `top_20_away_upset_win_precision`
- `decision_threshold`
- `decision_metrics.accuracy`
- `decision_metrics.upset_precision`
- `decision_metrics.upset_recall`

### 9.2 冷平模型重点指标

- `top_20_draw_upset_precision`
- `decision_threshold`
- `decision_metrics.draw_precision`
- `decision_metrics.draw_recall`

### 9.3 对比输出

训练摘要中应明确展示：

- 上一版默认模型指标
- 本次重训模型指标
- 是否提升 `Top-20`
- 主冷/客冷方向是否更平衡

## 10. 失败处理

系统必须允许部分成功，但不能静默忽略问题。

### 10.1 预测失败处理

- 如果赛程页抓取失败且无比赛数据，则不生成伪 Excel
- 如果仅部分比赛失败，仍生成 Excel，但在 `summary` 标记失败数
- 如果主模型缺失，则阻断预测并提示先重训
- 如果冷平模型缺失，则继续生成 Excel，但 `draw_rankings` 需明确写明“未加载冷平模型”

### 10.2 重训失败处理

- 某些历史窗口回填失败时，不影响其他窗口继续执行
- 合并训练集时只纳入成功窗口
- 最终训练摘要必须列出失败窗口和失败原因
- 若成功窗口太少导致无法切分训练/验证，则终止重训并显式报错

## 11. 测试策略

本阶段建议补充以下测试：

### 11.1 Excel 导出测试

- 能成功写出 `.xlsx`
- `summary / combined_rankings / draw_rankings / all_predictions` 四个 sheet 均存在
- 关键列名正确
- 没有冷平模型时，`draw_rankings` sheet 仍可生成说明或空表

### 11.2 统一入口测试

- `predict-excel` 参数能正确转发
- `refresh-models` 能正确串联回填与训练
- 缺少模型文件或训练集文件时，错误提示可读

### 11.3 历史扩窗测试

- 能加载窗口清单
- 能合并多个 `training_rows.csv`
- 能正确输出成功窗口与失败窗口摘要

## 12. 验收标准

本阶段完成的判定标准如下：

- 给一个日期范围后，统一入口能直接生成 Excel 报告
- Excel 至少包含 `summary / combined_rankings / draw_rankings / all_predictions`
- 历史窗口能通过固定清单批量回填并合并训练集
- 主模型与冷平模型能通过统一入口完成重训
- 训练摘要能直接展示 `Top-20`、`主冷 Top-20`、`客冷 Top-20`、`冷平 Top-20`
- 扩样本后，可明确比较“本次 vs 上次”的 `Top-20` 与主冷/客冷方向稳定性

## 13. 风险与缓解

### 风险 1：扩窗后指标短期回落

- 影响：中到高
- 原因：样本增厚后验证更真实，过去的小样本高指标可能回落
- 缓解：保留每次重训摘要，重点看趋势和稳定性，而不是只看单次最佳值

### 风险 2：Excel 报告字段过多导致难看

- 影响：中
- 缓解：联合榜和冷平榜保留核心字段，完整字段只放在 `all_predictions`

### 风险 3：历史窗口回填耗时增长

- 影响：中
- 缓解：窗口清单可分批执行，并缓存每次回填的原始页面与 `training_rows.csv`

### 风险 4：球探页面结构调整影响回填

- 影响：高
- 缓解：保留原始缓存、失败日志和解析测试样本，优先修复解析器而不是推翻主链路
