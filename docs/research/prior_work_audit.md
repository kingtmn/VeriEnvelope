# 前期工作审计

本文件是内部证据，不是产品说明。2026-09-26 只读查看，没有修改旧项目，也没有运行旧项目里的未知代码。

搜索范围：`~/Desktop` 上名称相关的项目目录、`~/Documents/Codex`、`~/Documents/GitHub`、`~/Architect-R1`。没有扫描整盘。

`~/Documents/Codex` 的日期目录和 `~/Documents/GitHub/phl-risk-dashboard` 里，没有命中“三检、能力无关、验证债务、标准件”。`~/Desktop/方法论` 是空目录。名为 TEVV 的项目没有找到。

目录名 `whitebox_learning:` 带冒号，路径按实际名字引用。

## 1. ADRA 宪法

1. Source：`/Users/<user>/Desktop/Agent 方向鲁棒性审计`
2. Artifact：`docs/CONSTITUTION.md`
3. Original idea：0 个观察到的错误只覆盖当前版本、任务、包络和观察窗口。未观察不是通过。失败账本不是待办。观察、推断和未知分开。审计器自己会失败。外部框架不能规定实验结果。
4. Evidence level：已有真实验证的研究约束。`docs/FAILURE_LEDGER.md` 的 F-BUILD-001 记录了审计器错误制造虚假安全结论。这不是对 MCP 组件的验证。
5. Relevance：直接约束 VeriEnvelope 怎样说话，以及为什么 runner 不能当终审。
6. Difference：ADRA 的测量对象是任务条件下的 Agent 行为包络。VeriEnvelope 当前对象是低层组件的一条陈述。ADRA 有 C-1 到 C-15；VeriEnvelope 宪法更短。
7. Recommendation：adapt
8. Reason：解决的具体问题是防止把“这次没看到失败”写成安全。已写入宪法第 2 条和 `methodology/epistemic_limits.md`。不把 ADRA 的十五条款和 Agent 窗口模型搬进来，因为当前没有 Agent 实验，GATE 2 也锁着。

## 2. ADRA 测量语义

1. Source：同上
2. Artifact：`docs/MEASUREMENT_SEMANTICS.md`
3. Original idea：窗口判定有 PASS / FAIL / UNKNOWN / N/A。UNKNOWN 不是 PASS。多个窗口失败是多次越界，不是多个独立漏洞。语义冻结只覆盖有限的确定性一致性检查。
4. Evidence level：已有测试。文件写明证据在 `docs/experiments/M1/`。本轮没有重跑 M1。
5. Relevance：和 observation / outcome 分离、以及“一致不等于独立”是同一类问题。
6. Difference：ADRA 的窗口是 Agent 轨迹投影。VeriEnvelope 用一次运行的 observation 和 outcome class，没有多窗口计数器。
7. Recommendation：adapt
8. Reason：解决“缺证据被记成通过”和“重复投影被当成独立证据”。当前 schema 的 `source_type` 加上认识论文档已经表达后者。不增加窗口判定枚举，避免和现有 observation 重复。

## 3. ADRA 失败账本

1. Source：同上
2. Artifact：`docs/FAILURE_LEDGER.md`
3. Original idea：设计和搭建中的失败保留，已修复的条目仍留着。审计器失败是一等类别。
4. Evidence level：已有真实验证，对象是 ADRA 自己的搭建错误，不是外部组件能力。
5. Relevance：对应 History 和 evaluation/runner/method defect。
6. Difference：ADRA 账本是人写的研究日志，另有运行时 JSONL。VeriEnvelope 的 History 是结果上的追加事件，还不能按条关闭。
7. Recommendation：defer
8. Reason：按条关闭要等真实 Pilot 出现两条并存的缺陷。触发条件在 ADR-007。现在加账本格式没有第二条缺陷可记。

## 4. ADRA 准入策略

1. Source：同上
2. Artifact：`docs/ADMISSION_EVIDENCE_STRATEGY.md`
3. Original idea：使用测量项目不等于通过认证。外部框架决定该测什么，不决定必须出现什么结果。
4. Evidence level：架构猜想，带有已执行实验的上下文，但商业链 A–F 大多未做。
5. Relevance：和“candidate 不是认可、admitted 不是认证”相同。
6. Difference：ADRA 把后续出口写到发表和商业证据。VeriEnvelope 明确不做这些。
7. Recommendation：adapt
8. Reason：只保留“收录不是认证”。不引入 ADRA 的 A–F 漏斗，那些出口没有当前消费者。

## 5. d_an 总规则

1. Source：`/Users/<user>/Desktop/黑盒学习系统/d_an`
2. Artifact：`core_directives/TOTAL_RULES_V0_1.md`，索引在 `RULE_INDEX.md`
3. Original idea：路径正确高于数字更好。没有日志就没有学习主张。提议不是批准，批准不是部署。失败可以留下，失败不可见才危险。思想、实验室和论文等级必须分开。
4. Evidence level：纯思想，旁边的 `mox` 有实验目录。本轮没有重跑，也不把那些实验当成组件证据。
5. Relevance：证据先于结论、失败保留、自审不能当批准。
6. Difference：d_an 是学习系统的策略层级。VeriEnvelope 不学习、不更新策略。
7. Recommendation：adapt
8. Reason：解决“好看的数字或一次通过代替可追溯运行”。现有证据包和准入已经做这件事。不引入 ParentStrategy / Child Strategy 层级。

## 6. d_an 父子冗余

1. Source：同上
2. Artifact：`sections/28_parent_child_strategy_architecture.tex`
3. Original idea：父子冗余是以后的策略审查原则，原文写明当前不实现代码。
4. Evidence level：纯思想
5. Relevance：和“一个缺陷是否派生出另一个”有关。
6. Difference：原文讨论的是学习策略，不是测试缺陷。
7. Recommendation：defer
8. Reason：原文自己都推迟实现。VeriEnvelope 在 ADR-007 的触发出现前也不做缺陷图。提前做会把未验证的策略架构当成测试模型。

## 7. d_an 主张登记

1. Source：同上
2. Artifact：`revision_log/2026-05-12.md`
3. Original idea：不采用正式预注册，而用主张登记加运行前后记录，避免事后改口，也避免探索阶段的重流程。
4. Evidence level：纯思想，附有当时的主张编号更新记录
5. Relevance：registry 的 candidate 应表示“身份和陈述被记下”，不是被认可。
6. Difference：d_an 登记的是研究主张。VeriEnvelope 登记的是组件身份和一次测量。
7. Recommendation：adapt
8. Reason：`candidate` / `admitted` / `withdrawn` 已经够用。术语表写明 candidate 不是认可。不再加一套主张编号。

## 8. 白盒策略规则

1. Source：`/Users/<user>/Desktop/黑盒学习系统/whitebox_learning:`
2. Artifact：`CORE_RULES.md`，`README.md` 写明 scaffolded，parent-approved false，experiment-running false
3. Original idea：看得见内部过程也不等于批准。执行前要有入口约束，结束后的通过不等于策略批准。验证结构不等于验证策略。追踪要包含输入、检查、错误和上报。黑盒推断不能冒充白盒证据。
4. Evidence level：toy。脚手架，没有被批准的实验。
5. Relevance：VeriEnvelope 需要的是结构可追踪，不是打开被测组件的全部源码。
6. Difference：白盒项目把 white-box 定义成“内部过程可见的学习策略”。那会误导 VeriEnvelope 去要求阅读组件实现。
7. Recommendation：adapt
8. Reason：保留“可见不等于批准”和“结构可追溯”。不新增 whitebox 模块。组件源码是否可读，是另一维，当前方法不依赖它。

## 9. E0 链路审计

1. Source：`/Users/<user>/Desktop/链路审计/E0-v0.1`
2. Artifact：`README.md`
3. Original idea：确定性 toy。多个审计器（N0、N1、L1、J1）比较同一批故障是否被不同方法定位。原文禁止把 toy 说成电池物理或工业噪声。
4. Evidence level：已有测试的 toy。README 给出 pytest 和冻结后的确认运行。本轮没有重跑。
5. Relevance：多仪器，以及“玩具成功不是真实对象成功”。
6. Difference：E0 比较的是故障定位器，不是软件组件能力。J1 被标成仅供解释。
7. Recommendation：adapt
8. Reason：强化“fixture 自审不是组件验证”，这已经是 VE-METHOD-001 的 purpose。不引入多审计器模型或电池链数学。多个仪器的位置留给 `source_type`，等第二个真实仪器出现再用。

## 10. OPC 行动空间用语

1. Source：`/Users/<user>/Desktop/链路审计/opc方法论`
2. Artifact：`docs/opc-control-rules.md`
3. Original idea：不要把某次案例里的“可达行动空间”写成全局规则。
4. Evidence level：纯思想，领域是一人公司方法，不是软件测量
5. Relevance：提醒不要把路由或行动空间缩减写成 VeriEnvelope 的总架构
6. Difference：问题域不同
7. Recommendation：reject
8. Reason：它解决的是另一套方法论的过度概括。VeriEnvelope 当前不做路由器。只在认识论文档里写明“符合测试不是最适合用户”。不引用 OPC 的状态机。

## 11. d_an 多维路由

1. Source：`/Users/<user>/Desktop/黑盒学习系统/d_an`
2. Artifact：`docs/14_dimension_interface_and_routing_framework.md`
3. Original idea：多维输入如何进入模型而不塌成一段 token。文件自标为理论候选，未实现。
4. Evidence level：架构猜想
5. Relevance：标题里的 routing 容易被误接到“工具太多所以要路由”
6. Difference：这是神经网络接口设计，不是组件符合性
7. Recommendation：reject
8. Reason：它不解决“一条组件陈述是否在给定条件下成立”。放进来会把未实现的模型架构当成测量标准。

## 12. 蜂群错误边界

1. Source：`/Users/<user>/Desktop/fengqun`
2. Artifact：`governance/error_registry.py`
3. Original idea：错误日志被实现成投影空间里会扩张或收缩的动态边界，带衰减和严重度。
4. Evidence level：已有代码的仿真治理，不是组件验证
5. Relevance：名字像 error ledger 和 dynamic boundary
6. Difference：边界是数值几何。VeriEnvelope 的边界是版本、环境和未测区域
7. Recommendation：reject
8. Reason：它解决蜂群仿真里的几何约束，不解决证据是否支持一句能力陈述。现有 Envelope 加重新验证已经表达“边界会变”。引入半径和衰减没有可观察的软件行为对应物。

## 13. 半开环用语

1. Source：`/Users/<user>/Desktop/黑盒学习系统/d_an/docs/12_experimental_methodology_protocol.md` 等
2. Artifact：上述协议
3. Original idea：半开环判定用于 token 接口实验，避免塌成单一分数。
4. Evidence level：纯思想，附实验计划
5. Relevance：用户后来把强闭环 / 半闭环 / 开环用于“对象可验证程度”
6. Difference：d_an 的半开环是模型输入实验术语，不是组件 Pilot 分类
7. Recommendation：reject
8. Reason：两套“闭环”不是同一个概念。Pilot 选择继续用 ADR-004 的理由：协议边界固定、结果可观察。不把 d_an 的开环分级写成组件类型。

## 没有找到独立文件的说法

以下说法在本次搜索范围内没有独立规格或实验：

- 三检制度这个名字
- 能力无关验收或止通规这个名字
- validation debt 这个术语
- 标准件 / 非标件 / 探索件的三分法
- 名为 TEVV 的项目

它们仍在 `architecture_delta.md` 里按问题而不是按出处判断。没有出处，就不能写成“过去已经验证”。
