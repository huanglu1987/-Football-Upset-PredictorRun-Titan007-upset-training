# Implementation Plan: 球探浏览器自动抓取预测

## Overview

本计划对应球探浏览器自动抓取预测子设计，目标是在不引入新 API Key 的前提下，基于真实浏览器会话打通：

- 日期范围 -> 球探赛程页抓取
- 比赛列表 -> 欧赔 / 亚盘 / 大小球页面抓取
- 页面解析 -> 标准快照
- 标准快照 -> 现有模型预测

首版重点是把自动抓取与自动预测主链跑通，不做自动重训。

## Linked Specification

- 设计文档：`/Users/huanglu/Projects/球探冷门/docs/superpowers/specs/2026-04-13-titan007-browser-auto-prediction-design.md`

## Requirements Summary

### Functional Requirements

- 支持输入 `start_date`、`end_date` 批量抓取未来比赛
- 自动抓取比赛列表以及每场的 `1X2 / 亚盘 / 大小球` 页面
- 将页面解析成现有模型可消费的标准快照
- 复用现有预测逻辑，输出逐场概率和 `Top-N` 排行
- 保存原始 HTML、中间结构化结果和失败清单

### Non-Functional Requirements

- **小改动**：尽量复用现有 `chrome_session`、`standardize` 和 `predict_snapshot_csv` 逻辑
- **可复现**：所有抓取页面必须落盘缓存
- **可排错**：失败时能定位到列表页、赔率页或解析器
- **可降级**：缺失亚盘/大小球时允许部分预测

### Acceptance Criteria

- [ ] 能自动抓到指定日期范围内的比赛列表
- [ ] 能为大部分比赛抓到至少 `1X2` 快照
- [ ] 能输出带完整度标记的预测结果
- [ ] 能生成失败报告和缓存原始 HTML
- [ ] 关键解析逻辑有样本测试覆盖

## Technical Approach

### Architecture

实现按“先列表页、再欧赔页、再补盘口页”的顺序推进：

1. 先打通赛程页抓取与比赛列表解析
2. 再打通单场 `1X2` 页面抓取与快照生成
3. 然后补亚盘与大小球
4. 最后串联现有预测主链和失败报告

### Proposed File Changes

- `src/upset_model/config.py`
  新增球探浏览器抓取相关目录、浏览器等待时间和页面路由配置
- `src/upset_model/collectors/chrome_session.py`
  扩展打开 URL、定位标签页、抓取指定 URL 源码等能力
- `src/upset_model/collectors/`
  新增球探浏览器抓取器和解析器模块
- `src/upset_model/standardize.py`
  新增球探结构化结果 -> 标准快照行转换
- `scripts/`
  新增按日期范围自动抓取并预测的 CLI
- `tests/`
  新增 HTML 样本解析测试和最小流程测试

### Key Design Decisions

1. **真实浏览器优先**
   复用当前用户可访问球探的浏览器会话，不额外引入无头浏览器框架。

2. **先抓源码，再做解析**
   所有页面先缓存 HTML，解析器只吃本地样本，便于调试和回归测试。

3. **先满足 `1X2`**
   `1X2` 是预测必需字段，亚盘和大小球作为增强项分阶段补齐。

4. **现有预测链不重写**
   尽量把新功能做成“自动生成快照 CSV / 训练行”的前置层。

## Implementation Phases

### Phase 1: 浏览器抓取基础能力

**Goal**: 让程序能自动打开球探页面并抓取指定页面源码

**Tasks**:

- [ ] 扩展 `chrome_session` 支持打开指定 URL
- [ ] 支持按 URL 等待页面加载并抓源码
- [ ] 设计缓存路径和运行 ID
- [ ] 明确浏览器不可用时的报错

**Deliverables**:

- 可复用的页面抓取函数
- 原始 HTML 缓存目录结构

### Phase 2: 赛程页抓取与比赛列表解析

**Goal**: 从日期页拿到比赛列表与比赛详情入口

**Tasks**:

- [ ] 确认球探日期页 URL 规则
- [ ] 抓取单日赛程页 HTML
- [ ] 解析联赛、时间、主客队、比赛链接或比赛 ID
- [ ] 保存结构化比赛列表

**Deliverables**:

- 单日比赛列表解析器
- 比赛列表 JSON 缓存

### Phase 3: 单场赔率页解析

**Goal**: 至少拿到 `1X2` 必需字段

**Tasks**:

- [ ] 抓取单场欧赔页 HTML
- [ ] 解析初赔、即时赔
- [ ] 映射到标准快照核心字段
- [ ] 评估亚盘 / 大小球页面的字段可得性

**Deliverables**:

- 单场欧赔解析器
- 核心快照生成逻辑

### Phase 4: 自动预测串联

**Goal**: 给日期范围直接出预测结果

**Tasks**:

- [ ] 批量抓取日期范围比赛
- [ ] 生成标准快照
- [ ] 调用现有模型输出预测
- [ ] 生成失败报告和运行摘要

**Deliverables**:

- 新的日期范围自动预测 CLI
- 预测报告和失败清单

### Phase 5: 回归测试与文档

**Goal**: 确保页面解析和最小预测流程可回归

**Tasks**:

- [ ] 固定 HTML 样本
- [ ] 增加解析器单测
- [ ] 增加自动预测最小流程测试
- [ ] 补充运行说明

**Deliverables**:

- 解析器测试
- 最小使用说明

## Risks & Mitigation

### Risk 1: 日期页 URL 规则不稳定

- **Probability**: Medium
- **Impact**: High
- **Mitigation**: 先做单页样本探针，再把 URL 模板固化到配置层

### Risk 2: 页面由脚本动态生成，源码中无目标数据

- **Probability**: Medium
- **Impact**: High
- **Mitigation**: 同时验证 `view-source` 和 DOM 抓取两条路径，必要时增加复制 DOM 能力

### Risk 3: 单场详情页入口依赖页面交互

- **Probability**: Medium
- **Impact**: Medium
- **Mitigation**: 优先解析可直接构造的比赛 ID / 链接，不依赖坐标点击

### Risk 4: 盘口页字段口径与现有标准化字段不匹配

- **Probability**: High
- **Impact**: Medium
- **Mitigation**: 先确保 `1X2` 主链可用，其他盘口按增强字段单独接入

## Immediate Next Step

先用一个真实球探页面样本确认两件事：

1. 日期页和单场赔率页的 URL 规则
2. `view-source` 抓到的源码里是否已经包含可解析的比赛列表和赔率表
