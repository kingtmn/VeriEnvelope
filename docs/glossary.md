# 术语

这些词只在本仓库里使用。一句话能说清的，不拆成两个词。

**Identity**
到底测的是谁。它是验证的前提，不是第四个验证维度。

**Source Identity**
源码这一边：repository、commit、component path、package metadata、lockfile。

**Execution Artifact Identity**
实际执行的工件：origin、build recipe、toolchain、base image、local image id。它不等于 Source Identity。

**Subject**
被测对象。当前就是某个组件的某个版本。

**Component**
Subject 的登记身份：谁、什么类型、来源、版本、commit。`status` 是登记生命周期，不是验证结论。

**Measurement object**
一次测量实际绑定的东西：哪个 subject、哪条能力陈述、哪个方法版本、哪个仪器版本、哪个环境、哪次交互或 fixture。它是结果上这些字段的合取，不是单独的 schema。

**Method**
公开的测量规格，在 `methods/`。它定义规则编号和每条规则对应的解释，不执行自己。

**Instrument**
按方法去观察的工具。当前唯一的仪器是参考 runner。Fixture 是仪器这次使用的固定输入，不是另一个结论。

**Runner**
参考仪器的名字。它是方法的一种实现，不是方法本身。

**Fixture**
方法目录里预先固定的输入和预期输出。

**Observation**
运行直接留下的事实，例如退出码、stdout 是否与预期字节一致、是否超时。字段名是 `observation`。

**Outcome**
对观察的解释，字段名是 `outcome_class`。解释可以错，观察记录仍应保留。

**Capability Claim**
一条可测试的陈述，外加这次运行给它的状态。状态不是分数，也不是组件总分。

**三个验证维度**
L0、L1、L2 的正式名称。它们是三个问题，不是成熟度，不是认证等级，也不是高低层。

**L0 Capability Conformance**
在声明条件下，这条 Claim 有没有被实际观察到。单位是 Claim，不是组件质量。

**L1 Assurance**
为什么暂时相信这次测量。对象是测量链，不是另一条 Claim。L1 更强不会自动加宽 L2。当前不因只有一个 Runner 而分等级。

**L2 Applicability Envelope**
这个结论到哪里停止有资格被声称。它是声明范围、已观察限制、未知区域和重新验证边界。

**Decision Rule**
从原始观察到 Claim 结果的公开规则。观察本身不是符合性决定。

**Declared Capability**
项目方或供应商声称支持的能力。它不是 Verified Capability。

**Verified Capability**
经过方法和 Decision Rule 之后的 Claim 结果。

**Declared Scope**
这条 Claim 明确覆盖的条件。字段名是 `tested_conditions`。

**Observed Limit**
实验已经观察到的限制。字段名是 `known_limits`。空值写作 None empirically established：当前没有主动实验观察到限制。这不等于不存在限制。

**Unknown Region**
没有测试、因此不能外推的区域。字段名是 `untested_areas`。没测不是失败。

**Revalidation Boundary**
哪些变化一发生，旧结论就不能自动代表新状态。字段名是 `revalidation_triggers`。

**Evidence**
一次运行的原始文件、清单和最终封存。清单哈希的是结论写入前的材料。`seal.json` 哈希写完后的关键文件，并且不哈希自己。它不是解释。新版本不会让旧 evidence 消失。

**Verification Result**
把观察、解释、Claim 状态和 envelope 绑在一次 `run_id` 上的 `result.json`。它不是原始字节本身。

**History**
后来追加的变化。它不涂改旧证据。

**Revalidation**
判断旧的验证结果现在还能不能代表目标对象。它不修改历史 evidence。

**Applicability**
旧结果对当前对象是 `current`，还是 `revalidation_required`。

**candidate**
组件登记生命周期的一态。身份被记下。它不是 `admitted`，也不是推荐。

**Admission**
验证政策决定，字段是 `result.admission`。取值是 `admitted`、`insufficient`、`withheld`。`admitted` 不是发布状态，不是质量，不是推荐，也不是认证。

**Fitness for use**
某个用户、业务或组织是否应该采用这个对象。这不在 VeriEnvelope 的职责里。

**Pilot Preflight**
这一次计划中的外部运行能不能开始。READY 只授权这一次，不是组件状态。

**Project Gate**
项目能不能进入下一阶段。Project GATE 1 要至少 3 个真实外部组件跑完最小链。一个 Pilot 完成不等于这道门通过。

**Composition Boundary**
几条 Claim 分别 demonstrated，不能推出它们的组合 demonstrated。组合要单独验证。当前没有组合测试。

**Defect**
已记录的方法、runner 或评估错误。当前历史还不能按条关闭。

**Method defect**
规格本身把观察解释错了，或规格无法让两个评估者做同一件事。

**Runner defect**
参考实现没有按当时的方法规格执行。

**Evaluation defect**
VeriEnvelope 自己把证据读成了错误结论。

**External report**
别人的报告。`source_type=external_report`。它可以促使复现，不能单独准入。

**Unknown**
没有足够材料作判断。页面上的 UNKNOWN 表示字段缺失，不是零。

**Insufficient**
材料不够，或这次记录根本不是准入决定，或证据文件对不上。

**Out of envelope**
请求或结果落在这次声明的执行边界外面。它不是“这个对象很差”。

**Withheld**
材料够作判断，但收录条件不满足。Pilot 阶段不把这公开成否定名单。

**L0 / L1 / L2**
三个验证维度的内部记号，不是三级，也不是字段。L0 问能力是否被观察到，L1 问为何暂时相信，L2 问结论能声称到哪里。
