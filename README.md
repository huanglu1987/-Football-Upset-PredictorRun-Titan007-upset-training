# Football Upset Predictor

Titan007 足球冷门预测仓库，支持：
- Titan007 历史窗口回填
- 主冷 / 客冷 / 冷平模型训练
- 指定日期范围预测
- 输出最终下注清单

仓库默认不提交运行数据、模型产物和抓取缓存，所以换设备后需要先做一次初始化。

## 环境要求

- Python `3.11+`
- 能访问 GitHub 和 Titan007
- 首次训练/刷新模型时，预留一定抓取和训练时间

## 快速开始

```bash
git clone https://github.com/huanglu1987/-Football-Upset-PredictorRun-Titan007-upset-training.git
cd -Football-Upset-PredictorRun-Titan007-upset-training
bash scripts/bootstrap_repo.sh
```

`bootstrap_repo.sh` 会做这些事：
- 创建 `.venv`
- 安装仓库依赖
- 创建 `data/raw`、`data/interim`、`data/features`、`data/models`
- 把仓库内的 `football-upset-predictor` SKILL 安装到本机 Codex 技能目录

## 首次初始化模型

新设备第一次运行预测前，先生成模型：

```bash
source .venv/bin/activate
PYTHONPATH=src python3 scripts/titan007_skill_entry.py refresh-models --validation-season 2526
```

这一步会：
- 回填默认历史窗口
- 合并训练样本
- 训练主模型和冷平模型
- 把模型写到 `data/models/`

## 运行预测

```bash
source .venv/bin/activate
PYTHONPATH=src python3 scripts/titan007_skill_entry.py predict-excel --start-date YYYY-MM-DD --end-date YYYY-MM-DD --top-n 20
```

默认行为：
- 覆盖 Titan007 全联赛
- 最终清单保留 `强 / 中 / 弱`
- 排除 `不投注`
- 按 `强 -> 中 -> 弱` 排序
- 输出字段为 `比赛时间 / 对阵 / 等级 / 建议方向 / 原因`

## 常用命令

初始化环境：

```bash
bash scripts/bootstrap_repo.sh
```

只安装 Codex 技能：

```bash
bash scripts/install_codex_skill.sh
```

刷新模型：

```bash
source .venv/bin/activate
PYTHONPATH=src python3 scripts/titan007_skill_entry.py refresh-models --validation-season 2526
```

导出 Excel：

```bash
source .venv/bin/activate
PYTHONPATH=src python3 scripts/titan007_skill_entry.py predict-excel --start-date 2026-04-14 --end-date 2026-04-15 --top-n 20
```

## 数据说明

仓库不会提交这些目录：
- `data/raw/`
- `data/interim/`
- `data/features/`
- `data/models/`

这意味着：
- GitHub 仓库保持轻量
- 新设备需要自己初始化模型
- 本地训练和预测结果不会污染源码仓库

## 测试

```bash
source .venv/bin/activate
PYTHONPATH=src python3 -m unittest discover -s tests -p 'test_*.py'
```
