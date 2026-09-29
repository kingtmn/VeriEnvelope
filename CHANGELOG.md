# Changelog

## Unreleased

五个 semantic case 之后停止加样本。Publication Audit 结果是 READY。本地 v0.1 release candidate 已写好，等待人类的 Publication Authorization。没有公开，没有 push。

`external-run-p5-1` 在方法 0.1.0 下调用了一次 `create_entities`。返回的实体与预注册值一致。规则 P5-M7。证据在 `run-21d1582275e347ee9389bc241b6756dd`。方法没有按输出回改。

Pilot #5 选定同一 commit 的 Memory server。方法 `VE-METHOD-MCP-005` 0.1.0 在执行前固定。主主张是 `create_entities` 返回一个预注册实体。

`external-run-p4-1` 在方法 0.1.0 下调用了一次 `convert_time`。文本包含预注册的 `time_difference` `+9.0h`。规则 P4-M7。证据在 `run-f4ba0e8b9d3243f7b42f103a9624fb19`。方法没有按输出回改。

Publication Gate v0.1 写在 `docs/release/PUBLICATION_GATE_V0_1.md`。Pilot #4 选定 Time server 的 `convert_time`，方法 `VE-METHOD-MCP-004` 0.1.0 在执行前固定。更高关注度但需要网络或凭证的候选记为延期，不记为失败。

`external-run-p3-2` 在方法 0.2.0 下重测 R1。文本仍与 fixture 字节一致。P3-M7 给出 match、confirmed、demonstrated。证据在 `run-a030ab0bf2ee40faaf0b22cf003147ce`。0.1.0 和旧包不改。Historical Project GATE 1 PASS 保留。现行适用性在这次重测后重新成立。GATE 2 仍锁定。到这里停止。

`VE-METHOD-MCP-003` 0.1.0 的 Decision Rule 不完整：P3-M1、P3-M4、P3-M7 没有 capability_status，P3-M6 只是占位。Runner 当时自行写入 capability_status。

`external-run-p3-1` 在方法 0.1.0 下读取了镜像内 fixture。文本与预注册字节一致。证据在 `run-605485ecb4594a0d9fabd0002ca19899`。Project GATE 1 通过。GATE 2 仍锁定。到这里停止。

`external-run-p2-6` 在方法 0.4.0 和 ADR-008-amendment-3 下重测 C3。同一会话的 C1、C2 保持 demonstrated，C3 仍是 `not_demonstrated`。证据在 `run-d22d4d1928204029b8d2e45e82f749ad`。没有再改环境。方法 0.4.0 只改 sandbox 引用。依据是 diagnostic_only 的 mkdtemp。旧方法和旧证据不改。结果聚合不再把已测过的前置主张改成 insufficient。

`external-run-p2-5` 在方法 0.3.0 下把 C3 当作主测量。`browser_navigate` 返回的文本没有预注册标题，而是只读根上创建临时目录失败。C3 是 `mismatch`。证据在 `run-a554d6a9f8fc4d41b1f3764e5cbc1476`。方法没有改，也没有再跑。

`external-run-p2-4` 在方法 0.3.0 下把 C2 当作主测量。同一容器里先核对 initialize，再发送 tools/list。名字集合与预注册的 25 个 core tool 一致。C3 没有发送。证据在 `run-d5e468f88bab49db8fd1f48276b154aa`。方法 0.3.0 没有改。

`external-run-p2-3` 在方法 0.3.0 下只发送了一次 initialize。C1 的观察是 match。C2 和 C3 没有发送。证据在 `run-b93181d9aee447d1ad4328d15a8363dc`。0.3.0 把 `serverInfo.name` 从 `api` 改为 `Playwright`，依据是 CLI 工厂的静态源码链，不是为了迎合上一次输出。0.1.0 和 0.2.0 的结果没有重算。

`external-run-p2-2` 在方法 0.2.0 和 ADR-008-amendment-2 下只发送了一次 initialize。响应里的 `serverInfo.name` 是 `Playwright`，预注册是 `api`。C1 是 `mismatch`。C2 和 C3 没有发送。证据在 `run-d46735b07c1c434b9461370aca6a7268`。第一次运行的包和方法 0.1.0 没有改。

研究范围锁定为 Tool。Pilot #1 到 #3 保持 MCP。实验卫生写在 `EXPERIMENT_HYGIENE.md`。候选池快照在 `docs/research/candidate_pool_snapshot.md`。Pilot #2 预选 Playwright MCP，Pilot #3 预选 Filesystem server，都在执行前固定。

Pilot #2 只发送了一次 initialize。进程在响应前退出。C1 没有被 demonstrated。C2 和 C3 没有发送。证据在 `run-47f9611e16544d998d983bfa4d7c1b43`。没有重跑。

证据包在写完后增加 `seal.json`。准入同时核对原始清单和最终封存。

固定 Everything 为第一个外部候选。VE-METHOD-MCP-001 修订到 0.3.0：第一次观察不自动写成组件原因，并且 C1 在运行前增加 protocolVersion。执行工件标明为本地隔离构建，不是 npm 发布包。

基线提交 `1d68d37` 之后，对本地 image id 只发送了一次 initialize。C1 的观察是 match，记在 `8bd33d8`。C2 和 C3 当时没有发送。组件没有准入。

随后在新容器里做了 external run #2，主测量是 C2。前置 initialize 再次 match。tools/list 的名字集合与预注册的 13 个名字一致。C3 没有发送。方法 0.3.0 没有改。这次观察记在 `e71dea5`。

责任模型把 Identity、L0、L1、L2、Evidence、History、Revalidation、Admission、Pilot Preflight 和 Project GATE 1 分开。一条 Claim 可以带自己的 envelope。已观察到的限制允许为空。一个 Pilot 完成不等于 Project GATE 1 通过。这个模型记在 `016a56a`。

external run #3 在新容器里重做了 initialize 和 tools/list，然后只调用了一次 echo。C3 的观察是 match。准入是 `admitted`，含义只限声明范围内的 registry 收录。方法 0.3.0 没有改。Project GATE 1 仍然未通过。

方法论写明三个验证维度、判断链和思想来源。`candidate` 是登记状态，`admitted` 是验证决定。已经发生的 Run #2 和 Run #3 用追加事件标成授权已消耗。没有重跑外部组件，也没有改 C1、C2、C3 的观察。

增加最小 OCI 运行边界，以及只覆盖四条消息的 MCP stdio 执行器。量具自检使用本仓库控制的 fixture，记录用途是 `instrument_self_test`。

在隔离构建中生成 Everything 本地镜像，并记下 image id。没有启动，也没有推送。PILOT PREFLIGHT GATE 为 READY，这不是一次测量通过。

## 0.1.0 - 2026-09-26

建立实验性测量骨架：宪法、方法 `VE-METHOD-001`、schema、只跑本地 fixture 的参考 runner、证据包和本地查看器。

没有外部组件验证。GATE 1 未通过。
