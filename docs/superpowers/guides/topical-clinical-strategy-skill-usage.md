# 外用制剂临床开发策略 SKILL 使用说明

这份说明面向后续从 GitHub 下载仓库的同事，目标是让大家在本机快速安装并开始试用 `topical-clinical-strategy`。

## 1. 技能位置

仓库中的技能源码位于：

`飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy`

如果只是阅读技能结构，可以直接查看：

- [SKILL.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/SKILL.md)
- [workflow.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/workflow.md)

## 2. 安装到本机 Codex

仓库根目录已经准备了安装脚本：

```bash
bash scripts/install_topical_clinical_strategy_skill.sh
```

默认会安装到：

```bash
${CODEX_HOME:-$HOME/.codex}/skills/topical-clinical-strategy
```

如果你需要安装到自定义 `CODEX_HOME`，先设置环境变量再执行：

```bash
export CODEX_HOME=/your/custom/codex/home
bash scripts/install_topical_clinical_strategy_skill.sh
```

## 3. 更新技能

当仓库里的技能有新版本时，拉取最新代码后重新执行安装脚本即可：

```bash
git pull
bash scripts/install_topical_clinical_strategy_skill.sh
```

## 4. 建议的试用方式

初次试用建议直接用已经整理好的验证 prompt：

- [validation-prompts.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/validation-prompts.md)

如果想快速理解“好答案大致应该长什么样”，先看这些示范案例：

- [worked-examples/index.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/worked-examples/index.md)
- [case-library/index.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/case-library/index.md)

## 5. 建议的试用顺序

1. 先看 `SKILL.md`
2. 再看 `worked-examples/index.md`
3. 然后用 `validation-prompts.md` 里的场景测试
4. 最后再用自己的真实品种信息试跑

## 6. 输出模式怎么选

当前这套技能支持两种模式：

- `策略版`
- `方案纲要版（synopsis）`

建议这样使用：

- 如果你还在判断注册路径、证据缺口、保守/激进路线，默认用`策略版`
- 如果你已经有较明确的候选品种，想让技能把研究顺序、SAD/MAD、患者 PK、转段门槛写得更细，要求它输出`方案纲要版（synopsis）`

可直接这样提问：

```text
请用策略版输出该项目的中国临床开发路径。
```

```text
请用方案纲要版（synopsis）输出该项目的早期研究设计，重点写清楚健康人/患者、SAD/MAD 和转段门槛。
```

## 7. 试用时重点观察什么

建议重点看这几件事：

- 是否明确区分了 `中国 / FDA / 双区域`
- 是否同时给了 `保守路径` 和 `激进路径`
- 是否能讲清楚关键缺口，而不是只给结论
- 是否把 `PSG` 放在合适的位置，没有被过度放大
- 在输入很少时，是否明确进入“第一轮策略判断”模式
- 如果要求了 `synopsis`，是否真的给出研究级别架构，而不是继续停留在结论陈述

## 8. 常用参考文件

法规层：

- [china-core.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/regulatory/china-core.md)
- [china-innovative-methods.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/regulatory/china-innovative-methods.md)
- [fda-core.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/regulatory/fda-core.md)

输出层：

- [output-template.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/output-template.md)
- [synopsis-template.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/synopsis-template.md)

稳定性与质控：

- [failure-patterns.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/failure-patterns.md)
- [output-self-check.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/output-self-check.md)
- [known-boundaries.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/known-boundaries.md)
- [clinicaltrials-strategy.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/clinicaltrials-strategy.md)

案例导航：

- [case-library/index.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/case-library/index.md)
- [worked-examples/index.md](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/worked-examples/index.md)

发布准备：

- [GitHub 发布前检查清单](./topical-clinical-strategy-github-release-checklist.md)
- [China 官方来源索引](../../../飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/regulatory/china-official-source-index.md)

## 9. 当前状态

当前版本已经具备：

- 技能主工作流
- 中美法规卡
- FDA 审评案例卡
- 外用创新药规则层
- 中国创新药方法学卡
- 失败模式与输出自检
- 示例 prompts
- worked examples
- case library
- 10 个当前适应症模块：
  - 痤疮
  - 玫瑰痤疮
  - 浅表真菌感染
  - AGA
  - AD
  - 银屑病
  - 脂溢性皮炎
  - 白癜风
  - 斑秃
  - 放射性皮炎

在正式对外发布到 GitHub 前，仍建议继续用真实品种做 1 到 2 轮业务内测。

同时建议先阅读 `known-boundaries.md`，因为当前版本虽然已经去掉了正常使用所需的本地原始资料依赖，但 GitHub 文档可移植性和公开分发策略仍值得在发布前再检查一轮。

对于 public GitHub 场景，当前推荐做法是：

- 直接使用仓库内摘要卡和规则卡
- 需要中国原始指导原则时，再按 `china-official-source-index.md` 去官方站点检索
- 不默认依赖作者本机上的 PDF 或 CSV 路径
