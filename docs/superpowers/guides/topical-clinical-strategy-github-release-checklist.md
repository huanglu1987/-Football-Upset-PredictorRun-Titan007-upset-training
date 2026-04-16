# 外用制剂临床开发策略 SKILL GitHub 发布前检查清单

这份清单用于正式发布 `topical-clinical-strategy` 到 GitHub 之前的最后一轮人工检查。当前目标是“先准备好”，不是现在就发布。

## 1. 结构校验

先确认技能目录仍能通过基础校验：

```bash
python3 /Users/huanglu/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  "/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy"
```

建议同时确认安装脚本语法无误：

```bash
bash -n /Users/huanglu/Projects/球探冷门/scripts/install_topical_clinical_strategy_skill.sh
```

## 2. 本地原始资料依赖检查

当前技能在资料地图中仍引用了作者本机上的原始 PDF / CSV 路径，例如：

- `/Users/huanglu/Desktop/临床/...`

发布前要明确这几件事：

- 这些原始文件是否允许入仓
- 如果不允许入仓，是否已经有足够的 repo 内摘要卡可以替代
- 团队成员在没有这些本地原件时，技能是否仍能靠 `references/regulatory/*.md` 和官方检索正常工作

可先快速扫一遍本地路径引用：

```bash
rg -n "/Users/huanglu/Desktop/临床/" \
  "/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy"
```

## 3. 文档可移植性检查

当前部分文档最初是按本地 Codex 使用场景写的，发布前要确认是否仍存在机器本地绝对路径或只在本机有效的文件链接。

建议检查：

```bash
rg -n "/Users/huanglu/" \
  "/Users/huanglu/Projects/球探冷门/docs/superpowers" \
  "/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy"
```

重点判断：

- 这是必须保留的本地资料路径说明，还是应该改成相对链接
- 这是给 Codex 本机看的路径，还是给 GitHub 同事看的路径

## 4. 技能内容完整性检查

发布前至少人工复核以下入口是否都还在：

- `SKILL.md`
- `references/workflow.md`
- `references/source-map.md`
- `references/input-template.md`
- `references/output-template.md`
- `references/known-boundaries.md`
- `references/clinicaltrials-strategy.md`
- `references/worked-examples/index.md`

## 5. 业务验收样例复查

建议至少用以下 3 个场景再人工过一遍：

- 痤疮口服改外用、美国优先
- 盐酸特比奈芬双区域浅表真菌感染
- minoxidil 改良剂型双区域 AGA

发布前重点确认：

- 是否明确给出保守路径和激进路径
- 是否说明推荐路径
- 是否标出关键缺口和关键假设
- 是否把 `ClinicalTrials.gov` 说成“设计先例层”，而不是“监管要求层”

## 6. Git 工作区检查

确认工作区里没有把无关内容一起带入发布：

```bash
git -C /Users/huanglu/Projects/球探冷门 status --short
```

当前已知有一个无关未跟踪目录：

- `docs/news/`

发布前请继续确认它是否仍与本技能无关。

## 7. 发布前结论

只有当以下问题都回答清楚时，才建议进入真正的 GitHub 发布动作：

- 本地原始资料缺失时，技能是否仍可工作
- 面向 GitHub 的文档是否已经去掉不必要的本地绝对链接
- 业务近邻样例是否再次人工验收通过
- 当前仓库是否只包含准备发布的相关改动
