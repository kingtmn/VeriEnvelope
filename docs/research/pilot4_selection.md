# Pilot #4 / #5 selection

选择时点使用 `docs/research/candidate_pool_snapshot.md`，检索时间 2026-09-27T01:33:44Z。没有按更新后的 GitHub 排名重做候选池。下面的关注度只解释为什么先消耗验证成本。它不进入主张、方法、L0、L1 或 Admission。没有打分，也没有排行榜。没有把“预计它会暴露问题”写成测试目标。

## 本轮不测的更高关注度候选

这些对象的关注度高于下面选定的 Time。不测它们是因为当前执行边界，不是因为它们失败。

Deferred:
semantic verification requires external network or credentials

Reason:
outside current v0.1 execution boundary

- Context7，`upstash/context7`，快照 62452 stars。远程文档后端，语义调用离开本地。
- Chrome DevTools MCP，`ChromeDevTools/chrome-devtools-mcp`，快照 52641 stars。需要宿主 Chrome / DevTools，并且重复 browser/runtime。
- GitHub MCP Server，`github/github-mcp-server`，快照 33222 stars。需要 token 和 GitHub API。
- Firecrawl MCP，快照 7517 stars。外部抓取服务。
- Supabase MCP，快照 2924 stars。外部项目和凭证。
- Brave Search MCP，快照 1473 stars。搜索 API。
- Sentry MCP，快照 864 stars。外部账号。
- Fetch，同一 monorepo。快照已经写明：要测语义就会碰到外部网站。

## Pilot #4

- candidate identity：Time server，`mcp-server-time` 0.6.2，路径 `src/time`
- source：https://github.com/modelcontextprotocol/servers
- commit：`f46d9578190b476b3501923ea8977d899e8db2cb`
- popularity / impact reason：它在官方 MCP servers monorepo 里。快照把该仓库记为 90611 stars。star 属于整个仓库，不属于 Time 自己。快照把它列为第 12 项。
- public-interest reason：时区换算是这个服务器对外提供的具体能力。官方仓库里的参考实现，读者可以对照同一份源码。
- measurability reason：`convert_time` 在两个固定偏移的时区之间计算 `time_difference`。这一字段由两端的 UTC 偏移和源码里的格式化决定，不读取外部网络，也不需要凭证。不把会随时钟变化的日期和 `get_current_time` 写成主张。
- why now：快照里更高关注度的候选都停在网络、凭证或宿主浏览器上。Time 是快照中还能在 $0、network none 里做一条窄语义主张的下一项。上一轮不选它，是因为整份结果随时间变化；这一轮只测偏移字段。
- known execution dependencies：本地 Python OCI，构建时获取该 commit 和锁文件里的依赖。运行时 network none、无凭证、无宿主数据、sandbox ADR-008-amendment-3。`--local-timezone UTC` 避免读取宿主时区。不安装发行版 tzdata，时区库使用锁文件里的 Python `tzdata` 2024.2。
- boundary class：timezone conversion。这是记录它实际属于的表面，不是为了再造一类。

具体主张、预期字符串和镜像 id 在执行前另写进方法和 provenance。本文件不记录运行结果。

## Pilot #5

快照表格里没有第二个还能留在当前边界内的候选。同一份已经冻结的 commit 里还有 `src/memory`，包名 `@modelcontextprotocol/server-memory` 0.6.3。它不在快照的逐项名单里；当时的名单也没有因为它需要网络或凭证而排除它。star 仍然只属于整个 monorepo，不另做排名。

- candidate identity：Memory server，`@modelcontextprotocol/server-memory` 0.6.3，路径 `src/memory`
- source：https://github.com/modelcontextprotocol/servers
- commit：`f46d9578190b476b3501923ea8977d899e8db2cb`
- popularity / impact reason：与 Everything、Filesystem、Time 相同的官方 monorepo。没有单独的 star 计数。
- public-interest reason：这是官方参考服务器里的进程内知识图，和已经测过的回声、浏览器、文件系统、时区不是同一类调用。
- measurability reason：源码在本地，运行不需要账号。封存 Pilot #4 之后从源码确定主主张：`create_entities` 写入一个预注册实体，图文件放在已有隔离 tmpfs 的 `/tmp/ve-pilot-5.jsonl`。不需要外部网络或凭证。默认的安装目录路径不测，因为它在只读根上，而且那不是这条主张。
- why now：需要第五个 semantic case，而快照里其余高关注度对象都在执行边界之外。
- known execution dependencies：本地 Node OCI，同一 commit，运行时 network none，sandbox ADR-008-amendment-3。图的存放位置必须在容器内部，不能挂载宿主家目录。

Pilot #5 等 Pilot #4 完成后再设计主张和执行。不并行。
