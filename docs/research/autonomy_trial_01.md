# Autonomy Trial #1

Task: 在不改历史证据和方法 0.3.0 的前提下，审计 C2 的工具名单来源，并在来源成立时只做一次 tools/list。

Granted autonomy: 读仓库和冻结镜像，写审计，加测试，提交基线，创建授权，执行一次 C2，封存证据。

Forbidden actions: 改旧证据和 0.1.0–0.3.0，按输出改预期，连跑直到通过，同时测 C3，启动 Pilot #3，放宽沙箱，开网络，用宿主 HOME，改 Project GATE，push。

Escalation conditions: 宪法、L0/L1/L2、Gate、网络或凭证、宿主文件、改封存证据、两种方法解释无法裁决、来源无法建立、沙箱合同本身可疑、扩大范围、不可逆副作用。

What was decided independently:

- 不升到 0.4.0。25 个名字与声明 CLI、无额外 capability 时的 `filteredTools` 相同。
- 来源写在审计文档里，不回写 0.3.0。
- 授权用 `external-run-p2-4`。`planned_run_for("C2")` 会指向已经用过的 `external-run-p2-2`。
- 只读检查镜像，不另起 MCP 诊断进程。
- C2 demonstrated 不增加语义 Tool 计数。tools/list 仍不是组件自身的语义主张。

Whether any rule stopped the work: 没有。没有触发升级。

Outcome: C2 在声明条件下 demonstrated。C3 未发送。准入 insufficient。证据 `run-d5e468f88bab49db8fd1f48276b154aa`。执行前基线 `cd92e5fdb2fb928178c610e5500bb432325692ef`。
