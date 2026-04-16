# 外用制剂临床开发策略 SKILL 使用说明

这份说明面向后续从 GitHub 下载仓库的同事，目标是让大家在本机快速安装并开始试用 `topical-clinical-strategy`。

## 1. 技能位置

仓库中的技能源码位于：

`/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy`

如果只是阅读技能结构，可以直接查看：

- [SKILL.md](/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/SKILL.md)
- [workflow.md](/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/workflow.md)

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

- [validation-prompts.md](/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/validation-prompts.md)

如果想快速理解“好答案大致应该长什么样”，先看这些示范案例：

- [worked-examples/index.md](/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/worked-examples/index.md)

## 5. 建议的试用顺序

1. 先看 `SKILL.md`
2. 再看 `worked-examples/index.md`
3. 然后用 `validation-prompts.md` 里的场景测试
4. 最后再用自己的真实品种信息试跑

## 6. 试用时重点观察什么

建议重点看这几件事：

- 是否明确区分了 `中国 / FDA / 双区域`
- 是否同时给了 `保守路径` 和 `激进路径`
- 是否能讲清楚关键缺口，而不是只给结论
- 是否把 `PSG` 放在合适的位置，没有被过度放大
- 在输入很少时，是否明确进入“第一轮策略判断”模式

## 7. 常用参考文件

法规层：

- [china-core.md](/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/regulatory/china-core.md)
- [fda-core.md](/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/regulatory/fda-core.md)

稳定性与质控：

- [failure-patterns.md](/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/failure-patterns.md)
- [output-self-check.md](/Users/huanglu/Projects/球探冷门/飞书文档审核/莫匹罗星资料核对/盐酸特比奈芬数据资料/ZYG25001/外用制剂临床方案设计SKILL/topical-clinical-strategy/references/output-self-check.md)

## 8. 当前状态

当前版本已经具备：

- 技能主工作流
- 中美法规卡
- FDA 审评案例卡
- 失败模式与输出自检
- 示例 prompts
- worked examples

在正式对外发布到 GitHub 前，仍建议继续用真实品种做 1 到 2 轮业务内测。
