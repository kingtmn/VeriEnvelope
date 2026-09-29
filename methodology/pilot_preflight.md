# Pilot 前检查单

这张表回答：现在能不能执行第一个外部组件。全部条件满足时，门是 READY。READY 只表示可以开始第一次真实运行，不表示那个组件通过了。

少任何一项，门就是 NOT READY。不另拆一层门。

自审方法 `VE-METHOD-001` 不走这张表。量具自检的记录是 `instrument_self_test`，不是外部验证。

当前候选是 Everything，commit `f46d9578190b476b3501923ea8977d899e8db2cb`。方法是 `VE-METHOD-MCP-001` 0.3.0。执行工件是 locally_built_from_pinned_source，不是 npm 发布包。

| # | 条件 | 现在 |
| --- | --- | --- |
| 1 | Candidate identity pinned | 满足 |
| 2 | Commit pinned | 满足 |
| 3 | Claims written before execution | 满足。C1、C2、C3 的预期观察没有因为归类修订而改写 |
| 4 | Method version fixed | 满足。`VE-METHOD-MCP-001` 0.3.0。0.1.0 留在 Git 87bd0ad。0.2.0 的修订原因留在方法文件里 |
| 5 | Expected observations fixed | 满足 |
| 6 | Interpretation rules fixed | 满足。M2、M4、M6、M9、M10 不把第一次观察写成原因 |
| 7 | Explicit non-claims fixed | 满足 |
| 8 | Evidence package ready | 满足 |
| 9 | Final package seal ready | 满足 |
| 10 | Runtime sandbox implemented | 满足。`run_case` 仍不启动外部进程 |
| 11 | Build/acquisition isolation defined | 满足。宿主 npm、npx、pip、uvx 被拒绝 |
| 12 | Network policy explicit | 满足。运行时网络关闭 |
| 13 | Secret isolation tested | 满足。无害进程，不是外部证据 |
| 14 | Resource limits tested | 满足 |
| 15 | Container cleanup tested | 满足 |
| 16 | Revalidation triggers declared | 满足 |
| 17 | MCP protocol executor implemented | 满足。只实现 initialize、notifications/initialized、tools/list、tools/call |
| 18 | MCP executor validated against a controlled local fixture | 满足。记录用途是 instrument_self_test，不是外部验证 |
| 19 | Full sandbox → MCP executor → evidence → seal path validated | 满足。只在受控 fixture 上走过 |
| 20 | Candidate image built from pinned source in isolated build | 满足。镜像已构建。Run #1 已经用这个 image id 做过一次 C1，那次运行已经结束 |
| 21 | Candidate image digest recorded | 满足。`sha256:5f1784c80a95be56091a16ac8f6955b32eb170dcf89ee3b9d2cb86c0b26fe1d6`。这是本地 image id，没有推送 |
| 22 | No unresolved execution-path contradiction | 满足。镜像 CMD 与方法 argv 一致。Node 基础镜像的 ENTRYPOINT 只是执行该 CMD 的包装 |

机器可读表在 `runner/verienvelope/pilot_preflight.py`。事实文件是 `registry/candidates/everything-build.json`。没有这份文件时，执行条件不成立。

上面 22 项不是一张永久通行证，也不是组件状态。Run #1 / C1 和 Run #2 / C2 的授权都已经用完。当前只授权这一次：

| 字段 | 值 |
| --- | --- |
| planned_run | external-run-3 |
| primary_claim | C3 |
| method_version | VE-METHOD-MCP-001 0.3.0 |
| execution_artifact | sha256:5f1784c80a95be56091a16ac8f6955b32eb170dcf89ee3b9d2cb86c0b26fe1d6 |
| sandbox_policy | ADR-008-amendment-1 |
| timestamp | 2026-09-26T14:45:00Z |

记录在 `registry/runs/external-run-3.json`。Run #2 的记录不能拿来开始这一次。工件、方法或主张对不上，就不能开始。Pilot #1 即使之后跑完，也不等于 Project GATE 1。

PILOT PREFLIGHT GATE：READY for external run #3 / C3。这一次已经执行。`registry/runs/external-run-3.json` 里 authorized 仍为真，那是当时的授权事实。`registry/runs/authorization-events.jsonl` 追加了 `authorization_consumed`。下一次外部运行必须另写授权，不能沿用本行。这一行不授权 Pilot #2。
