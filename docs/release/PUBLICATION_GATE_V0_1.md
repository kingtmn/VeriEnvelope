# Publication Gate v0.1

这是 Tool-only VeriEnvelope v0.1 的发布标准。它属于治理，不是 L3，不是新的验证层，也不是成熟度模型。验证骨架仍是 L0 Capability Conformance、L1 Assurance、L2 Applicability Envelope。

Publication Readiness 不等于把已知问题做完。Unknown、Deferred issue 和 Known limitation 可以很多。会直接推翻一条公开核心主张、而且项目已经知道却没有处理的矛盾，不能留下。

达到下面的条件之后停止加样本，进入 Publication Audit。不要把 10 个 Tool、统计显著性、跨操作系统矩阵、供应链证明、签名体系、形式化验证、企业 SLA 或完整安全审计写成 v0.1 的必选项，除非没有它就无法诚实发布当前主张。

## PG-1 Semantic cases

至少 5 个真实 Tool semantic cases。每个都要真正调用该组件自己的语义行为。结果可以是 `demonstrated` 或 `not_demonstrated`。不要求全部通过。协议握手和 tool discovery 只能做前置，不能代替语义 case。

## PG-2 Boundary diversity

至少 3 类明显不同的 failure / capability surface。现有记录是：

- protocol / deterministic Tool behavior
- browser / runtime
- filesystem / permission

新 Pilot 只记录它实际属于哪一类。不为了凑类别去制造第四类或第五类。

## PG-3 Decision Rule completeness

正式使用的每条 classification rule 都写出 `when`、`observation`、`outcome_class`、`capability_status`。Runner 不得补上方法没有声明的规范语义。Release set 必须 100% 满足。历史版本里已经冻结的不完整规则留在原处，不回改；现行结论只使用补全后的版本。

## PG-4 Evidence consistency

Release set 里每个正式 Evidence package 的 schema、manifest、seal 和 result consistency 都通过。不能留下已知的、会改变公开结论的证据矛盾。

## PG-5 Independent calibration

至少一次真正的 blind independent evaluation。Filesystem 方法与 Runner 的 Decision Rule 缺陷已经由这次评估发现。不重复做一次来凑数。

## PG-6 Revalidation

至少一条真实链条：缺陷，到方法或 Runner 修复，到冻结的新版本，到新的授权，到新的测量，到新的证据，到被恢复或被改变的结论。Filesystem 的 `VE-METHOD-MCP-003` 0.1.0 到 0.2.0 已经满足。不重复做一次来凑数。

## PG-7 Critical contradictions

发布时，critical unresolved contradiction 的数量是 0。

## 选题和验证分开

Selection Strategy 可以因为影响力、用户量、关注度、维护者、社区讨论或传播价值决定先测谁。这些理由只留在 selection record。它们不进入主张、方法、预期观察、Decision Rule、sandbox、证据解释、L0、L1 或 Admission。

Verification 不因为对象是大厂、有争议、或希望文章有流量，而改变尺子。也不因为希望某个对象失败而改尺子。更可能失败不是方法设计的依据。

## 执行边界

增量预算目标是 $0。默认运行时网络关闭，不使用真实凭证，不使用宿主私人数据。语义只有在外部网络或凭证下才成立的候选，记为：

Deferred:
semantic verification requires external network or credentials

Reason:
outside current v0.1 execution boundary

这不是 Tool failure。

## 达到 5 个之后

Semantic Tool Cases 到达 5 个就停止继续选第 6 个。先做 Publication Audit。审计结果只写 READY，或 NOT READY 并列出真正的 blocker。READY 之后可以在本地准备 v0.1 release candidate，然后停止，等待人类的 Publication Authorization。不自动创建 GitHub Release，不 push，不扩大 registry。GATE 2 保持锁定。
