# Methodology Lineage

这个文件回答思想从哪来。它不是文献综述，也不是认证映射。

哲学可以继承。机制需要适配。细节必须经过现实验证。

VeriEnvelope 不主张发明了验证、符合性、Assurance、V&V 或计量。如果它有价值，价值在于把这些成熟原则重新组合，适配到现代 Tool、MCP、Skill 以及其他可执行软件组件，并让结果低维、可读、可追溯、可复现、可质疑、可修正。

权威体系是高价值参考。Authority is evidence, not truth。现实反例仍然可以否决我们。

内部记号 L0、L1、L2 保留。正式名称是三个验证维度，不是成熟度，不是认证等级，不是高低层。

## NIST Conformance / TEVV

informed by / adapted from。VeriEnvelope 不是 NIST framework。

| | |
| --- | --- |
| Inherited | 原子化、可测试的 Claim。测试条件要写明。结果要可复现、可追溯。没有观察到错误，不能推出没有错误。方法和工具自己也要被审计。运行条件和适用范围要留下。 |
| Adapted | Capability Claim、Method、Observation、Evidence、Envelope、Revalidation。 |
| Not Adopted | 不把 NIST 的完整项目体系、评分或机构流程搬进来。 |

## Common Criteria

| | |
| --- | --- |
| Inherited | 功能要求与 Assurance 分开。被测对象边界要明确。运行环境和假设属于结论的一部分。变化之后先看影响，再决定重验什么。这后一条叫 Assurance Continuity。 |
| Adapted | L0 Capability、L1 Assurance、L2 Applicability Envelope、Revalidation。 |
| Not Adopted | 不采用 EAL、PP、ST 那套完整认证机器。 |

Pilot 阶段的规则仍然是：change → revalidation required。等真实记录积累之后，才可能变成：change → impact analysis → affected claims → selective revalidation。现在不建 impact graph，也不建选择性重跑引擎。

## ETSI / TTCN-3 / ICS

| | |
| --- | --- |
| Inherited | Test Purpose 与可执行测试分开。实现方的声明与验证结果分开。对象可以先声明自己支持什么，验证方再决定测哪一部分。 |
| Adapted | Declared Capability 不等于 Verified Capability。Project / Vendor Claim 不等于 VeriEnvelope Result。Method 不等于 Runner。`source_type=vendor_claim` 已经能记下声明，不能单独打开准入。 |
| Not Adopted | 不新建完整的 ICS / PICS 系统。 |

## NASA Verification / Validation

| | |
| --- | --- |
| Inherited | Verification 不等于 Validation，也不等于适合预定用途。 |
| Adapted | 当前只验证：声明的 Claim 在声明条件下是否得到支持。 |
| Not Adopted | 不判断这个组件是否适合某个用户、业务、公司或任务。Verified 或 Admitted 不等于 Suitable for your use。用户是否采用，不在验证职责里。 |

## JCGM / ISO Metrology

| | |
| --- | --- |
| Inherited | Observation 不等于符合性决定。中间必须有 Decision Rule。 |
| Adapted | Raw Observation → Interpretation Rule → Claim Result → Admission Rule。现有 `classification_rules` 和 admission policy 就是这两步，不是新层。 |
| Not Adopted | 不把 ±σ、连续误差传播或置信区间搬进当前的软件行为测试。只有真实对象确实需要量化不确定度时再考虑。 |

## SACM / Assurance Case

| | |
| --- | --- |
| Inherited | Claim 连到 Evidence，再说明理由和限制。 |
| Adapted | L1 与 Claim / Evidence 的关系跟 assurance case 相容：Claim、Evidence、Reason、Limitation。 |
| Not Adopted | 不实现完整 SACM 元模型。 |

## 仍然只是当前工作模型

下面这些还没有被多个外部组件反复检验。它们是 Pilot 的工作规则，不是继承来的定律。

- 三个真实外部组件才讨论正式网站。
- 一次预检只授权一次 planned run。
- 空的 Observed Limits 只表示当前没有主动实验观察到限制。
- 组合能力必须单独验证。当前不做组合测试。
