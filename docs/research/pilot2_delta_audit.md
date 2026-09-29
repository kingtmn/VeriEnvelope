# Pilot #2 Full Audit 与 Pilot #1 Delta

日期：2026-09-27。Pilot #2 在第一条 primary claim 与预期冲突后停止。没有第二次运行。C2 和 C3 没有发送。

## 这次运行

- 对象：`mcp.playwright-mcp`，commit `e87bb897e15a6f2af402afb0f10b45eced9e1f9b`
- 方法：`VE-METHOD-MCP-002` 0.1.0。运行后没有改。
- 执行前基线：`5aa3ed999aa0b3f8cfbd8416954f4d4e96fee719`
- 授权：`external-run-p2-1`，primary C1。启动时追加了 `authorization_consumed`。授权文件里的 `authorized: true` 没有改。
- 证据：`evidence/mcp.playwright-mcp/0.0.82/run-47f9611e16544d998d983bfa4d7c1b43/`
- 镜像：`sha256:cc8221f580a2ff7cdecac250da533250ef12e03a4101c13363056039072544cd`
- sandbox：ADR-008-amendment-1。user 65532:65532，network none，read-only root，cap-drop ALL，no-new-privileges，pids 64，memory 512m。没有宿主挂载。

## Observation

进程在 initialize 响应之前退出，exit code 1。stdout 只有发出的 initialize 请求。stderr 是 Node `SystemError`：`uv_os_homedir returned ENOENT`，栈在 `playwright-core` 的 `chromiumChannels.ts`，发生在加载 `coreBundle.js` 时。

没有 JSON-RPC 响应。

## Claim Status

- C1：`not_demonstrated`。规则 P2-M2。observation `execution_error`。outcome `unclassified`。
- C2：没有发送。status `insufficient`。
- C3：没有发送。status `insufficient`。

## Diagnosis

状态：未确认。

stderr 与“进程在导入时调用 `os.homedir()`，而这次环境没有 home 目录”相一致。可能相关的层次包括：sandbox 的 `env -i` 不传 HOME、uid 65532 在镜像里没有 passwd home、组件在握手前就读取 home、启动脚本没有在镜像内设置 HOME。

这些只是候选。这次记录没有把它们写成原因。没有改 sandbox，没有重跑。

## 规则重叠，未改判

方法里 P2-M10 的文字也包括“进程在响应前退出”，并写成 `blocked` / `out_of_envelope`。实际用的是 P2-M2：没有可解析响应，所以 `execution_error` / `not_demonstrated`。

不在看见输出之后改 0.1.0 来挑选更顺眼的规则。若要分开这两条规则，必须是新方法版本，并且不能改这个证据包。

## L0 / L1 / L2

L0：只有 C1 被测量，结果是没有 demonstrated。C2、C3 未测。

L1：身份和镜像在运行前钉住。证据已封存。只有一个 runner，不评独立性。没有为了复现再跑一次。

L2：声明范围仍是方法里的 tested conditions。封存结果的 `known_limits` 是空的，意思是这个字段里没有写成已确立的限制。stderr 是一条 Observed Limit 候选，没有升成普遍规律，也没有写回证据包。未知区域仍包括真实网站、其他 commit、宿主文件系统。改 sandbox、HOME 或方法版本都需要重新验证。

## Admission

`insufficient`。理由是有能力未执行，并且有能力 `not_demonstrated`。组件文件仍是 `candidate`。这不是认证，也不是对 Playwright 的否定。

## Pilot #2 状态

complete。完成的意思是：对象、方法和工件已固定，C1 有一次真实执行和封存证据，C2/C3 因停止规则没有测量，结论停在 unclassified。不是三条都 demonstrated。

## 与 Pilot #1 的差

1. 继续有效的结构：预注册、一次一个 primary claim、按 id 等响应、sandbox 边界记录、证据封存、admission 与 component status 分开、冲突后停止后续 claim、方法版本不按输出回改。
2. 第一次被真正触发的：进程在握手前崩溃；stderr 成为主要证据；`blocked` 与 `execution_error` 的规则文字重叠；浏览器服务器在现有 `env -i` 下还没进入工具调用。
3. 新问题：home 目录缺失使进程起不来。这是 Applicability / 环境边界的候选，不是已经证明的组件缺陷，也不是 VeriEnvelope 已经失败的证明。
4. 信息增益弱的字段：这次 `known_limits` 仍为空，增益在 stderr，不在那个数组。`case.json` 里同时有 `C1` 和 `initialize` 两条相同判断，是 runner 把消息名也写进了 judgments。不为此重跑。
5. 方法：0.1.0 不改。以后如果要区分 P2-M2 和 P2-M10，另起版本。
6. 骨架：六个区块够用。不增加 L3，不改 L0/L1/L2 的定义，不因为这一次崩溃去改 Everything 的方法。

## GATE

Pilot #1 和 Pilot #2 都走完了“身份 → 声明 → 方法 → 一次测量或有理由的停止 → 证据 → 结果 → envelope → 历史 / admission”。所以 GATE 1 的进度是 2/3。Project GATE 1 仍未通过。GATE 2 仍锁定。Pilot #3 没有执行。

## 预期来源

后来的来源审计见 `pilot2_expectation_provenance_audit.md`。`external-run-p2-2` 暴露的不是组件缺陷，而是测量预期的来源映射错误：冻结的 `serverInfo.name = api` 来自没有被声明启动器调用的 `createConnection`。

A frozen ruler can still be wrong.

Pre-registration controls outcome-driven change; it does not establish correctness of the measuring rule.

上面的 2/3 是这次停止当时的计数说法。后来的门计数改成语义 Tool，不回写这一段。
