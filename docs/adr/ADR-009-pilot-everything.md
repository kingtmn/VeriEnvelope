# ADR-009 第一个外部候选用 Everything，但现在不跑

## Context

Pilot #1 要验证的是 VeriEnvelope 能不能对第一个外部对象走完：

身份 → 陈述 → 方法 → 固定输入 → 执行 → 证据 → 结论 → 边界

它不是为了找一个最复杂的真实 MCP，也不是为了给那个服务器打分。

## Decision

候选定为 `modelcontextprotocol/servers` 里的 Everything，commit `f46d9578190b476b3501923ea8977d899e8db2cb`，路径 `src/everything`，包 `@modelcontextprotocol/server-everything` 2.0.0，传输候选 stdio。

该目录的 README 写明：这是给 MCP 客户端作者用的测试服务器，不是一个有用的业务服务器。因此被测对象自己的业务复杂度较低。

选择它不是因为它质量最好，也不是 VeriEnvelope 推荐它。`candidate` 只表示身份已固定。

本轮只读了仓库文件。没有安装，没有 npx，没有 npm install，没有执行其中任何代码。

三条陈述和明确不声明的范围写在 `methods/VE-METHOD-MCP-001`，并且写在任何执行之前。

C3 选用 `echo`。同一 commit 的源码把输入字符串原样放进 `Echo: ${message}`。`get-env` 会倒出环境变量，`gzip-file-as-resource` 会取 URL，所以不用它们充数。

## Reason

协议窗口固定：initialize、tools/list、一次工具调用。这正好是测量链要走的最短外部路径。更复杂的服务器会把“方法还没写清”和“对象自己很复杂”混在同一次失败里。

## Trade-offs

许可证不是单一 SPDX 结论。包字段、目录 README 和仓库根 LICENSE 说法不一致，身份记录保留这个分歧，不把它收成 MIT。

`tools/list` 依赖客户端能力。空能力下的预期名单已经写死。如果源码读错了，正确做法是方法修订，不是对着第一次输出改预期。

他们自带的 Dockerfile 和 README 里的 `docker run mcp/everything` 不满足 ADR-008。运行时必须走本仓库的容器边界。构建如果需要网络，是单独的获取阶段，不能在宿主上执行 npm。

## Status

Accepted as the first candidate. Not executed.
