# 架构

VeriEnvelope 是测量记录系统。Git 仓库里的方法、schema 和证据包是事实来源。查看器只是人读界面。

## 三条链

一次完整测量应当能向下追：

结论 → 测量对象 → 方法版本 → 参考实现版本 → 环境 → fixture → 原始输出 → 边界 → 是否有人复现 → 后来有没有被反例改写

管线自审仍然只覆盖本仓库的 fixture。外部候选 Everything 另有自己的证据包。一个组件把 C1、C2、C3 跑完，只可能完成 Pilot #1，不能通过 Project GATE 1。责任分工见 [architecture/responsibility_model.md](architecture/responsibility_model.md)。

## 三层分离

```text
methods/VE-METHOD-001/method.yaml     方法规格
        │
        │  规则编号与结果类别写在这里
        ▼
runner/verienvelope/                  参考实现
        │  只决定“这次命中哪条规则”
        │  不改写规则对应的结论类别
        ▼
evidence/<id>/<version>/<run-id>/     一次测量的原始包
        result.json                   这次的结论
```

方法文件不 import runner。runner 读取方法文件。第三方可以只读 `methods/` 和 `methodology/`，自己写执行器。

官方验证结论不会由第三方结果自动生成。将来如果要接收外部结果，路径是：

Third Party Result → Evidence Review → Auxiliary Reproduction → Registry

这条路径现在只有文档位置，没有提交系统。

## 数据怎么放

一次运行在内存里组装结果，先做一致性检查和 schema 校验，通过后才写入证据包。校验失败不会写成通过。

证据包目录：

```text
evidence/<component-id>/<version>/<run-id>/
  manifest.json
  environment.json
  input/
  stdout.log
  stderr.log
  result.json
  notes.md
  seal.json
```

不另放空的 `output/`。标准输出和标准错误就是这次的原始输出。

`run_id` 每次不同。同一 fixture、同一方法版本下，观察类别、规则编号、能力状态和准入状态应当相同。比较两次运行时忽略 `run_id` 和时间戳。

环境编号是本次捕获事实的短哈希（操作系统、架构、Python、runner 版本）。它不是预先登记的认证环境名。不记录用户名和主机名。

## 结论模型

一次运行同时写下这些，而不是一个 PASS：

- `observation`：这次看到了什么（match、mismatch、execution_error、blocked、not_run）
- `outcome_class`：如何归类。超时这类无法归因的情况用 `unclassified`，不强行写成 runner 或组件的错
- `capabilities[].status`：可测试陈述是否被这次运行证明
- `admission`：能不能进入公开收录。取值只有 `admitted`、`insufficient`、`withheld`

`withheld` 表示门栓已经能判断“不满足收录条件”，但 Pilot 阶段不把这变成公开否定。`insufficient` 表示还不能做这个判断。

自审记录的 `record_purpose` 固定为 `pipeline_self_test`，准入固定为 `insufficient`。

作者声明的 `source_type` 是 `vendor_claim`。它可以被保存，但不能单独满足“能力已被复现”。当前准入只承认带 `ve_test` 证据的复现，并且自审记录在那之前就会停住。

## 准入

对人读的定义是：

Admit = IdentityLocked AND CoreCapabilityReproduced AND EvidenceTraceable AND EnvelopeDefined AND NoCriticalUnresolvedContradiction

实现里还有两条当前阶段的硬条件：

- 记录用途必须是 `component_verification`。自审永远不够。
- 每个被标成 demonstrated 的能力，至少要有一条 `source_type=ve_test` 的证据。`vendor_claim`、`external_report`、`independent_test` 都不能单独打开门。独立测试不能自动变成官方结论。
- 证据包目录、清单和最终封存都要交给完整性检查。关键文件缺失、路径逃出包外、清单哈希不一致，或封存对不上时，结果是 `insufficient`，不能保持 `admitted`。

任一必要材料缺失时，结果是 `insufficient`，即使同时存在失败迹象。材料齐全但门栓不满足时，才是 `withheld`。

runner 不回写组件文件的 `status`。组件 `status` 不能是 `admitted`。验证结果可以写下 `admission=admitted`，那是政策决定，不是发布状态。详见 ADR-010。

## 历史

历史只追加。`append_history` 保留原前缀。Git 历史是另一层：静默改旧提交仍然违反宪法，代码挡不住有人改 Git，所以证据包要能单独阅读。

## 重新验证

版本字符串一旦变化，旧准入不得沿用。依赖、权限、运行时、协议、方法、runner 缺陷、外部反例、安全或能力相关变化，也会要求重新验证。

未识别的变化种类同样要求重新验证，不把“没见过的变更”当成无影响。

源码 commit、execution artifact、method version、runner version 或声明的 protocol 与记录不一致时，适用性是 `revalidation_required`。这个判断不改写、不删除旧 evidence。旧文件仍是当时的观察。

runner 没有“把旧 PASS 抄到新版本”的代码路径。

## 安全边界

当前实现：

- 只执行方法目录内的相对路径，拒绝绝对路径和 `..`
- 子进程不使用 shell
- 工作目录是临时目录，不是仓库根
- 超时必须在 0 到 30 秒之间
- 子进程环境只保留 PATH、语言、时区和平台启动所需的少量变量，加上 `PYTHONNOUSERSITE` 和 `PYTHONHASHSEED`
- 方法用途不是 `pipeline_self_test` 时，直接拒绝，不启动子进程

`run_case` 仍然只跑管线自审。容器边界在 `sandbox.py`。无害进程测过它。2026-09-26 又用它发送过一次 Everything 的 initialize。细节和证据在 ADR-008 的 Amendment 1。

- 一次性容器，结束时删除
- 运行时 `--network none`
- 非 root、只读根文件系统、丢弃全部 capabilities、no-new-privileges
- 不挂载宿主家目录、docker socket 或仓库写入区
- 唯一可写位置是容器内的临时目录
- 宿主环境不继承。目标进程经 `env -i` 后只有 PATH 和 LANG
- 镜像自己声明的 ENV 留在容器配置里，必须记下来。它不是进程环境，也不是宿主 secret
- CPU、内存和 PID 有上限，超时后清理
- 镜像 id 和 inspect 返回的 repo digest 被记下

构建阶段如果要联网，只能走 `pull_image`。运行阶段不拉取。宿主上的 npm、npx、pip、uvx 被拒绝。

因此：还不能用 `run_case` 验证外部 MCP。不要在 GitHub Actions 里执行未知第三方代码。清洗环境变量仍然不是沙箱；沙箱是上面的容器边界。

## 测量怎么读

一次结果里已经分开这些角色，没有再加一层类型：

- Subject：`component_id`、版本、commit
- Method：`method_id`、`method_version`
- Instrument：`runner_name`、`runner_version`；fixture 是这次仪器使用的固定输入
- Observation：`observation`，以及 stdout / stderr
- Interpretation：`outcome_class` 和 `rule_id`
- Conclusion：能力状态、envelope、`admission`

多个 `source_type` 可以并存。它们一致只提高核对价值，不自动变成真理。共享同一 runner、同一 fixture 或同一模型的记录不是独立仪表。

组件各自满足一条陈述，不能推出它们组合之后仍满足。组合需要单独的测量对象。当前没有组合验证，也不从单组件结论继承。

通过某条陈述，也不能推出这个组件最适合某个用户。那是另一件事。

## 三个验证维度

L0、L1、L2 是内部记号。正式名称是三个验证维度：能力是否被观察到、为什么暂时相信这次测量、结论能声称到哪里。它们不是成熟度，不是认证等级，也不是 schema 里的层级。以后如果真实记录证明这个问法没用，可以删掉，不必保留。

L0 通过并且 L1 更强，不会自动加宽 L2。每条 Claim 的边界写在该 Claim 上，字段仍是 `tested_conditions`、`known_limits`、`untested_areas`、`revalidation_triggers`。`known_limits` 允许为空。空的显示是 None empirically established，不是“没有限制”。

## Project GATE 1 与 Pilot

Project GATE 1 计数的是到达过一条组件自身语义主张的真实 Tool，不是完成了几份 Pilot。initialize 或 tools/list 不够。Pilot 可以在启动失败时 complete，同时不给这道门加一。`project_gate_1(semantic_tool_cases=...)` 与 `pilot_status` 分开。GATE 2 继续锁定，不增加 L3。

## 查看器

`verienvelope view` 读取 `result.json`，确认它符合 schema，然后写出一个自包含 HTML 文件。它不访问网络，不补全缺失字段。缺失的 commit 显示为 UNKNOWN。
