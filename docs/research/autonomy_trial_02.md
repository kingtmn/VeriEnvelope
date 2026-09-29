# Autonomy Trial #2

Goal: 审计并只测量一次 Playwright 的 C3 页面标题主张。

Frozen governance: 宪法、Tool 范围、L0/L1/L2、旧证据、append-only 历史、一个 run 一个主测量、不 retry-until-pass、GATE 按语义 Tool 计数、GATE 2 锁定、不挂宿主 HOME、不开网络、不使用凭证、不 push。

Granted autonomy: 来源审计、方法版本、测试、基线、授权、一次 C3、封存、提交。

Independent decisions:

- 不升 0.4.0。标题行来自 `renderTabMarkdown` 和静态 `<title>`。
- 授权用 `external-run-p2-5`，不用会撞上旧运行的 `planned_run_for("C3")`。
- 不预加 `/dev/shm`、字体、额外 tmpfs 或能力。
- 看到 `EROFS` 之后不改沙箱、不改预期、不再跑。
- 这次 `not_demonstrated` 计入语义 Tool，因为 `browser_navigate` 已经发出并被判定。计数从 1/3 记为 2/3。Project GATE 1 仍不通过。

Method revisions: 无。

Hard gate interventions: 无。没有放宽沙箱。

Escalations: 无。

Outcome: C3 `mismatch` / `not_demonstrated`。证据 `run-a554d6a9f8fc4d41b1f3764e5cbc1476`。执行前基线 `43a8d2a2c87841c47771a84879301ff90d85c819`。

Could the work finish without human process supervision? 可以。人没有再批中间步骤。

Did autonomy create any evidence-hygiene violation? 没有。旧包、0.3.0 和预期字符串都没改。诊断没有写进 registry evidence。
