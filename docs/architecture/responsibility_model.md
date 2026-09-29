# 责任模型

这些名字已经够用。这一页只规定谁回答什么，不增加验证层。

可以压成一条链：Identity → Claim → L0 → L1 → L2 → Admission。Evidence 纵向穿过这些环节。History 和 Revalidation 纵向穿过时间。用户是否采用，在这条链外面。

Identity 固定对象。Claim 固定被声称的那一句。L0 问这条 Claim 是否被观察到。L1 问为什么暂时相信这次测量。L2 问结论能被声称到哪里。Admission 问当前 registry 政策是否允许收录。Evidence 回答当时发生了什么。History 回答后来变了什么。Revalidation 问旧结论现在还能不能代表当前对象。Pilot Preflight 只授权一次 planned run。Project Gate 控制项目能不能扩大。

这三个验证维度不是成熟度，不是认证等级，也不是高低层。思想来源见仓库根目录的 METHODOLOGY_LINEAGE.md。

严谨度不等于覆盖范围。不知道就写 Unknown。没有观察到的限制留空。

## Identity

回答：到底测的是谁？

它是验证的前提，不是第四个验证维度。

Source Identity 是源码：repository、commit、component path、package metadata、lockfile。Execution Artifact Identity 是实际跑起来的工件：artifact origin、build recipe、toolchain、base image、local image id。两者不相等。

`package version 2.0.0` 只是源码 metadata。当前执行对象的 origin 是 `locally_built_from_pinned_source`。这不是“VeriEnvelope 验证了 npm registry artifact 2.0.0”。

`component.json` 与 `artifact.json` 已经分开存放这两边，并且被 evidence seal 覆盖。不再另写 `identity.json`。`identity_reference` 只对这两份材料做稳定哈希，不复制字段。

## L0 Capability Conformance

回答：在声明条件下，这条 Claim 是否被实际观察到？

Claim → Preconditions → Method → Observation → Decision Rule → Claim Result。观察本身不是符合性决定。

单位是 Capability Claim，不是组件，也不是整体质量。C1、C2、C3 各自是一条 L0 Claim。状态只使用 `demonstrated`、`not_demonstrated`、`insufficient`、`unknown`、`out_of_envelope`。

三条都 demonstrated，不能推出 secure、reliable、production ready、bug-free 或 best choice。

## L1 Assurance

回答：为什么暂时相信这个 L0 结果？

对象是测量结果和测量链，不是另一条 Capability Claim。当前材料是：source commit、lockfile、build provenance、sandbox、executor self-test、方法与 runner 的 conformance、golden、执行前 Git baseline、原始 stdout / stderr、Evidence Package、SHA-256、`seal.json`。

L0 被观察到，并且 L1 更强，不会自动加宽 L2。

## L2 Applicability Envelope

回答：这个结论到哪里停止有资格被声称？

L2 是四类信息，不是四个新层级。主动探测边界只是取得材料的一种手段，不是 L2 本身。不另设 Confidence、Risk 或 Operational 边界：

- Declared Scope：这条 Claim 明确覆盖的条件。字段名是 `tested_conditions`。
- Observed Limits：实验已经观察到的限制。字段名是 `known_limits`。允许为空。空的含义是 None empirically established：当前没有通过主动实验观察到限制。这不等于不存在限制。没有做过改变条件的实验，就保持空。
- Unknown Region：没测，因此不能外推。字段名是 `untested_areas`。Unknown 是合法结果。没测不是失败。
- Revalidation Boundary：哪些变化一发生，当前结论就不能自动代表新状态。字段名是 `revalidation_triggers`。它是随时间变化的边界，包括 source identity、execution artifact、method、相关 runner、协议条件、相关依赖、权限、环境边界，以及已确认的外部反例。

每条 Claim 有自己的 envelope。组件总页上的一段通用边界不能代替 C1、C2、C3 各自的边界。

## Evidence

回答：当时实际上发生了什么？

包括 request、response、stdout、stderr、environment、runtime、artifact identity、fixture、时间、manifest、seal。Evidence 被 L0、L1、L2 引用，但它自己不是新的验证层。

Evidence 不是解释。以后出现新版本，旧 evidence 也不失效。它仍是不可改写的历史观察。Declared Scope、Unknown Region、Revalidation Boundary 写在验证结果的 envelope 里，不装扮成原始观察。

## History

回答：后来发生了什么？

只追加新观察、更正、方法修订、runner defect、method defect、evaluation defect、revalidation、withdrawal、supersession。不静默删掉旧错误或旧结论。

## Revalidation

不修改历史 Evidence。它判断旧的 Verification Result 现在还能不能代表目标对象。

因此不把旧 evidence 标成 stale。evidence 保持 historical and immutable。适用性只用两个现有判断就够：`current`，或 `revalidation_required`。不为此新增四个状态名。源码 commit、execution artifact、method version、runner version、声明的 protocol 任一变化，旧结论不得继续当作当前对象的现行结论。历史文件留在原地。

## Admission

这是 registry 决定，不是 Capability 结果，不是质量分，也不是认证。

只有 required claims 满足既有准入条件、evidence 可追溯、envelope 写明了范围和未知区域、并且没有未解决的关键矛盾时，才可能是 `admitted`。材料不够是 `insufficient`。材料够但条件不满足是 `withheld`。

`component.status` 是登记生命周期：`candidate` 或 `withdrawn`。`candidate` 只表示身份被记下。`result.admission` 才是验证政策决定。`admitted` 只表示当前政策允许在声明范围内收录。它不是发布动作，不是推荐，不是安全认证，不是整体优质，也不是生产级。详见 ADR-010。

## Pilot Preflight

回答：这一次 planned external run 能不能执行？

必须同时绑定 planned_run、primary_claim、method_version、execution_artifact、sandbox policy、timestamp。一次授权经过 planned、authorized，运行之后追加 `authorization_consumed`。当时 authorized 为真的记录不改写。被消耗的授权不能再被读成“还能再跑一次”。

## Project GATE 1

项目级 GATE 1 仍是：至少 3 个真实外部 Tool 各自到达过一条组件自身的语义主张之前，不进入正式公开网站。结果可以是 demonstrated、not_demonstrated 或 out_of_envelope。没到达那条主张的完成 Pilot 不加进这个计数。

Pilot 完成只表示这一份链可以审完。它不等于 Project GATE 1 通过。代码里的 `pilot_status` 与 `project_gate_1(semantic_tool_cases=...)` 分开返回。

## GATE 2

第一阶段不增加 L3，也不扩展到 Agent 或 Multi-Agent。保持锁定。

## 组合与选择

A demonstrated 加上 B demonstrated，不能推出 A+B demonstrated。C1、C2、C3 都 demonstrated，只表示三条独立 Claim 在各自条件下被观察到。组合、Workflow、Agent 必须单独验证。当前不做组合测试。

验证也不等于推荐，也不等于适合某个用途。成本、速度、生态、部署偏好、接口习惯和业务要求由用户自己决定。当前不做推荐，也不做路由。We verify declared claims. We do not decide fitness for your use.

## 一致性核对

1. Identity 的哈希引用已有的 source 与 artifact 材料，不承担 L0 结论。
2. request、response、stdout、stderr 仍然是原始文件。范围和未知区域在 result 的 envelope。
3. 适用性函数不删除、不改写 evidence 文件。
4. Admission 的取值仍是 `admitted`、`insufficient`、`withheld`，没有质量分。
5. demonstrated 在查看器里和该 Claim 的声明范围放在同一节。
6. `revalidation_required` 只拒绝把旧结论当成现行结论。
7. Run #2 的授权文件不能授权 Run #3。
8. 一个完整 Pilot 不能让 `project_gate_1` 返回 passed。
9. L0、L1、L2 是三个验证维度，不是低中高。
10. 查看器在没有 claim envelope 的旧记录上，会写明必须同时看本次运行的边界，不能只读状态。
