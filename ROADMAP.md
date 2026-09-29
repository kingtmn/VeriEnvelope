# Roadmap

当前阶段只建立可运行、可验证、可修改的测量骨架。不建公开网站。

当前范围是 Tool。Skill、Agent、Multi-Agent、Workflow、Model、Prompt package、完整应用和企业系统不在范围内。Pilot #1 到 #3 保持 MCP 暴露的 Tool，用来固定协议族。没有证据说明 MCP 测量模型回答不了 Tool 的问题之前，不加入 CLI、REST 或浏览器扩展。

## GATE 1

3 个真实组件各自跑通下面整条链之前，不建立正式公开网站：

Method → Test → Evidence → Capability / Assurance / Envelope → History

这 3 个组件必须是外部真实软件，不能是本仓库的 fixture。fixture 跑通只说明管线能记录自己，不能当作 GATE 1。

历史决定：通过，记在 `02b4ce2`。Filesystem 方法 0.1.0 的正式能力状态后来失去现行资格，适用性曾是 `revalidation_required`。`run-a030ab0bf2ee40faaf0b22cf003147ce` 在方法 0.2.0 下重新完成读取测量之后，现行适用性再次通过。计数规则不变。

## GATE 2

第一版锁定：

- 不增加 L3 或更后的层级。
- 不把范围扩到 Agent 或 Multi-Agent。

要打开这道门，必须先有真实 Pilot 证据说明现有结构为什么不够。感觉上“以后可能用到”不算证据。

当前：锁定。

## 安全前提

不在宿主机上安装或执行第三方代码。运行时边界写在 [docs/adr/ADR-008-pilot-safety-boundary.md](docs/adr/ADR-008-pilot-safety-boundary.md)。检查单在 [methodology/pilot_preflight.md](methodology/pilot_preflight.md)。当前 PILOT PREFLIGHT GATE 只对 external run #3 / C3 为 READY。READY 不替代 Project GATE 1，也不是组件状态。镜像只在本地构建，没有推送。

## Pilot 要检验的是 VeriEnvelope

第一批真实组件同时是对测量体系的实验，不是对外公布的成绩单。

- P1. 这种结构是否降低了理解一个组件的成本？
- P2. Identity、Capability、Assurance、Envelope、Evidence、History 是否够描述低层组件？
- P3. 两个评估者按同一方法，能否得到高度接近的结论？如果不能，方法还没有离开作者个人习惯。
- P4. 外部反例和版本变化能否被追加吸收，而不是把旧记录涂掉？

P3 的权重最高。未通过的组件只保留内部证据，不建公开黑榜。

## 推迟

第三方提交、Evidence Review 工作流、注册表服务、正式证据强度等级（不要把草稿中的 E0–E3 写成标准）、自动发现项目、公开网站、总分。

## 选择真实 Pilot 的标准

下一阶段只准备 3–5 个候选，并且先只做一类对象。当前建议的类别是 MCP Server，理由见 [docs/adr/ADR-004-pilot-object.md](docs/adr/ADR-004-pilot-object.md)。

候选要同时满足：

- 开源，许可证允许阅读和本地运行
- 能固定版本和 commit
- 安装方式写得清楚
- 能在本地或受控环境运行
- 功能声明可以写成可测试陈述
- 不需要高风险权限
- 不需要昂贵基础设施
- 有真实使用，但使用量不是入选理由，Star 数量也不是

Skill 不进入第一阶段 Pilot。

## 下一步

Historical Project GATE 1 decision 是 PASS。现行适用性在 Filesystem 方法修复后的重测里重新成立。GATE 2 仍锁定。

Pre-release Calibration 的发布标准在 `docs/release/PUBLICATION_GATE_V0_1.md`。选题可以记录关注度；关注度不进入主张、方法或准入。五个 semantic case 已经封存。Publication Audit 是 READY。下一步只剩人类的 Publication Authorization。不是网站、Skill、Agent、扩大 registry、GitHub Release 或 push。GATE 2 仍锁定。
