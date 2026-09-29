# 核心方法

## 测量链

真实组件，或当前阶段的本地 fixture，按一份固定方法运行。运行产生原始证据。能力结论、置信理由和适用范围都引用这份证据。历史只追加。

没有原始证据的句子，不是本项目意义上的结论。

思想来源在仓库根目录的 [METHODOLOGY_LINEAGE.md](../METHODOLOGY_LINEAGE.md)。哲学可以继承，机制需要适配，细节必须经过现实验证。

## 三个验证维度

L0、L1、L2 是内部记号。正式名称是三个验证维度。它们不是成熟度，不是认证等级，也不是高低层。

L0 Capability Conformance 问：在声明条件下，这条 Claim 是否被实际观察到？链是 Claim → Preconditions → Method → Observation → Decision Rule → Claim Result。单位是 Claim，不是整个组件。

L1 Assurance 问：为什么暂时相信这个测量？当前包括 Provenance、Instrument Validity、Reproducibility、Evidence Integrity。只有一个 Runner，也不因此新设 Assurance 等级。Independence 以后可以加，现在不加。

L2 Applicability Envelope 问：这个结论到哪里停止有资格被声称？它是 Declared Scope、Observed Limits、Unknown Region、Revalidation Boundary。Observed Limits 可以为空。空表示 None empirically established，不是不存在限制。Unknown 是合法结果。没测不是失败。已知限制不是已经观察到的失败。主动探测边界只是取得 L2 材料的一种手段，不是 L2 本身。

L0 被观察到，并且 L1 更强，不会自动加宽 L2。

## 判断链

观察本身不能直接变成“符合”。中间是公开的 Decision Rule。完整顺序是：

Measurement Object → Method → Raw Observation → Interpretation / Decision Rule → Claim Result → Claim Envelope → Admission Rule → Registry Decision

`VE-METHOD-MCP-001` 0.3.0 的 `classification_rules` 就是 Claim 的 Decision Rule。admission policy 是后面的 Registry Decision。这一轮不改 C1、C2、C3 的规则。

## 声明与验证

对象以后可以带 Declared Capability Profile，例如声称支持 tools、resources 或 sampling。那只是 Project / Vendor Claim。VeriEnvelope 可以记下声明，从中选出可测试的 Claim，再给出 demonstrated、not_demonstrated 或 insufficient。现在不新增 Profile schema。

Vendor Claim 不等于 Verified Claim。Method 不等于 Runner。

## 验证不决定用途

VeriEnvelope 描述对象、Claim、方法、证据、Claim Result 和 Applicability Envelope，并按公开政策做 registry admission。

它不推荐用户必须选哪个组件，不判断该不该部署，不判断是否适合某个公司，也不做成本、生态、偏好或组织条件下的最终选择，更不替用户接受风险。

We verify declared claims. We do not decide fitness for your use.

## 不能推出的关系

- Vendor Claim 不等于 Verified Claim
- Observation 不等于 Interpretation，也不等于原因，也不等于符合性决定
- L0 通过加上 L1 更强，不等于 L2 更宽
- A demonstrated 加上 B demonstrated，不等于 A+B demonstrated
- Verification 不等于推荐，也不等于适合用途
- Admitted 不等于 Certified，不等于 Production Ready，也不等于 Best Choice
- 没有观察到错误，不等于不存在错误

## 三层

下面这三层是规格、实现和结果。它们不是上面的三个验证维度。

方法规格写清：对象范围、预测、非目标、分类规则，以及每条规则对应的观察、结果类别和能力状态。

参考实现负责把一次具体执行对应到规则编号，并原样采用方法里写的类别。实现可以有缺陷。缺陷应被记成 `runner_defect`，而不是去改方法文件让旧结果看起来合理。

验证结论是某一次绑定了版本、环境、fixture 和时间的记录。另一份实现跑出的结果，先是别人的结果。

## 预测

对 `VE-METHOD-001`：

- 支持当前做法的结果：同一 fixture 连续运行，观察类别、规则编号和能力状态一致；读者能从证据包打开 stdout。
- 需要修改方法或 runner 的结果：两次运行的观察类别不一致；输出其实不同却被标成 demonstrated；证据包里找不到原始输出；自审记录被标成 admitted。

这些预测写在方法文件里。runner 不解释自然语言预测，测试检查行为。

## 反例

下面的情况应留下记录，而不是丢弃：

- 输出与预期不一致
- 退出码与预期不一致
- 超时
- 路径不在允许名单内
- 后来发现是 runner 或方法写错了

超时不自动归因为组件失败或 runner 失败。归不了因，就保持 `unclassified`，能力状态为 `insufficient`。

## 现在不测量什么

`VE-METHOD-001` 不测量外部工具，不测量 MCP，不产生准入。`VE-METHOD-MCP-001` 0.3.0 是第一次外部运行前的规格，不是空的 `VE-METHOD-002`。执行工件是本地隔离构建的镜像。package version 不是 npm 发布包的验证结论。
