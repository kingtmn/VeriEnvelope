# Current State

日期：2026-09-28。本文件描述仓库事实。它过时时应被改正，而不是被宣传文案覆盖。

## 已有

- 宪法、方法论文档、架构说明和 ADR。
- 四个 JSON Schema：组件身份、测试用例、证据清单、验证结果。
- 方法 `VE-METHOD-001` v0.1.0，用途是管线自审。
- 方法 `VE-METHOD-MCP-001` v0.3.0，用途是第一个外部 MCP。0.1.0 留在 Git `87bd0ad`。C1 现在同时观察 `protocolVersion`。C2、C3 的预期没有改。第一次观察仍不写成原因。规格在第一次外部运行前固定，运行后不得为了匹配输出而改它。
- 候选 `mcp.server-everything`，commit `f46d9578190b476b3501923ea8977d899e8db2cb`。`candidate` 是登记状态，不是推荐，也不是 `admitted`。
- 参考 runner：允许名单、超时上限、清洗后的子进程环境、证据包、schema 校验、历史追加、准入判断、重新验证触发条件。
- 证据清单列出结论写入前的文件 SHA-256。整包写完后另有 `seal.json`，覆盖 manifest、环境、输入、日志、result 和 notes。准入同时检查这两层。对不上就不是 admitted。
- 本地 HTML 查看器，只渲染结果文件。
- 测试覆盖 schema、证据包、确定性观察、历史追加、重新验证，以及“自审不得准入”。

## 没有

- Run #1 的 C1 与 Run #2 的 C2 已提交，观察都是 match，准入都是 `insufficient`。Run #3 的主测量是 C3，观察是 match。这次运行里的前置 C1、C2 也是 match。准入按现有政策是 `admitted`。这只表示声明范围内可以进入当前 registry，不是认证、推荐或生产级。Pilot #1 的证据和方法收敛已经提交。最终提交是 `471b1f796d4866ff637930ec3b8a239fbad63b6a`。没有 push。
- 当前范围是 Tool。Pilot #1 到 #3 保持 MCP。Pilot #2 是 Playwright MCP。Pilot #3 是 Filesystem server，读文件测量已经执行一次。
- Pilot #2 的第一次 C1 仍是 `run-47f9611e16544d998d983bfa4d7c1b43`，方法 0.1.0，observation `execution_error`。该包不改。方法 0.1.0 的原文在 `methods/VE-METHOD-MCP-002/versions/0.1.0.yaml`。
- `VE-METHOD-MCP-002` 现用 0.4.0。0.1.0–0.3.0 留在 `versions/`。0.4.0 只把 sandbox 引用改成 ADR-008-amendment-3：在 amendment-2 的隔离 HOME 之外，增加空的 tmpfs `/tmp`。网络、只读根、能力、非 root 和资源上限没有放宽。Pilot #1 不因此重跑。
- 在这个新合同下的第一次 C1 是 `run-d46735b07c1c434b9461370aca6a7268`。initialize 有响应。`serverInfo.name` 是 `Playwright`，当时预注册是 `api`。规则 P2-M3，observation `mismatch`。该包不改。来源审计在 `docs/research/pilot2_expectation_provenance_audit.md`：`api` 属于 `createConnection`，声明的 CLI 使用 `decorateMCPCommand` 的字面量 `Playwright`。
- 方法 0.3.0 只改了这个名字映射。在同一镜像和 amendment-2 下又做了一次 C1：`run-b93181d9aee447d1ad4328d15a8363dc`。observation `match`，规则 P2-M1，C1 `demonstrated`。
- C2 的 25 个名字在运行前对上了 CLI 的 `filteredTools`。`external-run-p2-4` 是 `run-d5e468f88bab49db8fd1f48276b154aa`。同一会话里 C1 前置观察是 match，tools/list 与预注册集合一致，规则 P2-M5，C2 `demonstrated`。这只覆盖当前声明条件下的工具发现集合。
- C3 在 amendment-2 下的记录是 `run-a554d6a9f8fc4d41b1f3764e5cbc1476`。该包不改。`external-run-p2-6` 在方法 0.4.0 和 amendment-3 下重测了一次：`run-d22d4d1928204029b8d2e45e82f749ad`。同一会话里 C1、C2 是 demonstrated，C3 是 `mismatch` / P2-M8 / `not_demonstrated`。返回文本没有标题，而是浏览器进程已关闭。准入按现有政策是 `withheld`：材料齐全，但有一条主张没有被 demonstrated。没有再补环境。关闭审计在 `docs/research/pilot2_closure.md`。
- Pilot #3 在方法 0.1.0 下执行过一次：`run-605485ecb4594a0d9fabd0002ca19899`。原始观察仍是文本与 fixture 字节一致，observation `match`，outcome `confirmed`。该包不改。0.1.0 的 P3-M7 没有写出 capability_status，当时的 demonstrated 由 Runner 填入，所以这条正式能力状态不再作为现行结论。
- `VE-METHOD-MCP-003` 现用 0.2.0。`external-run-p3-2` 是 `run-a030ab0bf2ee40faaf0b22cf003147ce`。同一会话里 S1、S2 是前置 match。R1 选择 P3-M7。capability_status `demonstrated` 来自方法规则，不是 Runner 自填。准入 `admitted`，只限声明范围。
- Historical Project GATE 1 decision 仍是 PASS。现行适用性在方法补全后重新成立：三条语义 Tool 都有方法授权的测量，证据链、方法修订、错误保留、Envelope 和重测都在。这是 Gate revalidated after Filesystem Method repair。GATE 2 仍锁定。不开始 Skill、Agent，不扩大 registry，不 push。
- 当前阶段是 Pre-release Calibration。发布标准写在 `docs/release/PUBLICATION_GATE_V0_1.md`。它不是新的验证层。`external-run-p4-1` 是 `run-f4ba0e8b9d3243f7b42f103a9624fb19`。方法 `VE-METHOD-MCP-004` 0.1.0。`convert_time` 的文本包含预注册的 `+9.0h`，规则 P4-M7，`demonstrated`。准入 `admitted`，只限声明范围。`external-run-p5-1` 是 `run-21d1582275e347ee9389bc241b6756dd`。方法 `VE-METHOD-MCP-005` 0.1.0。`create_entities` 返回的实体与预注册值一致，规则 P5-M7，`demonstrated`。准入 `admitted`，只限声明范围。语义 Tool case 现在是 5 个。Publication Audit 是 READY，写在 `docs/release/PUBLICATION_AUDIT_V0_1.md`。本地候选在 `docs/release/V0_1_RELEASE_CANDIDATE.md`。没有 Publication Authorization，没有 GitHub Release，没有 push。GATE 2 仍锁定。
- 没有第三方提交、注册服务或账号。`site/` 已准备一个从五个现行结果生成的只读静态网站；尚未 push，也尚未部署。
- 没有总分，没有公开的未通过名单。
- 容器运行时边界已实现。受控 MCP fixture 的量具自检是 `instrument_self_test`，不是外部验证。`run_case` 仍然拒绝外部方法。
- Everything 镜像的本地 image id 是 `sha256:5f1784c80a95be56091a16ac8f6955b32eb170dcf89ee3b9d2cb86c0b26fe1d6`。镜像没有推送。三次外部运行都已结束，方法 0.3.0 没有按输出回改。Run #3 的授权已经用完，不能再当作下一轮的通行证。责任分工写在 `docs/architecture/responsibility_model.md`。C1、C2、C3 各自的 observed limits 为空。
- 历史里的 `fixed` 或 `revalidated` 会关掉当前打开的缺陷标记，不会按每一条缺陷分别关闭。升级条件写在 ADR-007，现在不实现缺陷图。
- 两个独立评估者尚未对同一外部组件做 P3 对照。

## 如何阅读一次自审运行

`admission=insufficient` 且 `record_purpose=pipeline_self_test` 表示：这次只检查了测量管线。即使观察为 match，也没有组件被准入。
