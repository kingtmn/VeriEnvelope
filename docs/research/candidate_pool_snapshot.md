# Candidate Pool Snapshot

检索时间：2026-09-27T01:33:44Z。计数来自当时的 GitHub REST API `repos/{owner}/{repo}`。这是选择时点的快照，不是质量分，也不是排序。

官方 registry 页面没有被用作排名。某仓库里的 `server.json` 只说明它声明了 registry 名称，不增加热门权重。

第三方榜单的综合分没有采用。

Star 和 Fork 只用于 Stage A：值不值得花验证成本。它们不进入 Capability、Assurance 或 Admission。

## Stage A 与 Stage B

Stage A 看现实影响力：GitHub stars、官方或主流维护者、当前仍在更新、被常见客户端当作 MCP server 使用。通过 Stage A 只表示值得测。

Stage B 看现在能不能测：source 和 version/commit 可以固定，许可证足够做本地实验，能在受控环境执行或能说明为什么不能，至少能写一条非宣传式 Capability Claim，不需要生产 secret，没有不可接受的真实副作用，能保留原始 evidence，当前基础设施有机会测量。

没有总分。

## 快照

| 对象 | 仓库 | Stars | Forks | pushed_at | License SPDX | 语言 |
| --- | --- | --- | --- | --- | --- | --- |
| MCP servers monorepo | modelcontextprotocol/servers | 90611 | 11694 | 2026-09-26T23:13:19Z | NOASSERTION | TypeScript |
| Context7 | upstash/context7 | 62452 | 3033 | 2026-09-26T07:27:34Z | MIT | TypeScript |
| Chrome DevTools MCP | ChromeDevTools/chrome-devtools-mcp | 52641 | 4926 | 2026-09-27T00:06:19Z | Apache-2.0 | TypeScript |
| Playwright MCP | microsoft/playwright-mcp | 37593 | 3196 | 2026-09-25T22:43:50Z | Apache-2.0 | TypeScript |
| GitHub MCP Server | github/github-mcp-server | 33222 | 5051 | 2026-09-25T17:44:17Z | MIT | Go |
| Firecrawl MCP | firecrawl/firecrawl-mcp-server | 7517 | 896 | 2026-09-26T23:12:54Z | MIT | JavaScript |
| Supabase MCP | supabase/mcp | 2924 | 410 | 2026-09-26T06:22:12Z | Apache-2.0 | TypeScript |
| Brave Search MCP | brave/brave-search-mcp-server | 1473 | 208 | 2026-09-26T02:54:37Z | MIT | TypeScript |
| Sentry MCP | getsentry/sentry-mcp | 864 | 149 | 2026-09-26T16:11:34Z | NOASSERTION | TypeScript |

`modelcontextprotocol/servers` 的 star 属于整个 monorepo。不能把它写成 Everything、Filesystem、Fetch 或 Time 各自的 star。

下面每个对象只记事实和两道门的结论。不写“可靠”“最好”或“安全”。

## 1. Everything（已完成，不进入下一轮选择）

- 仓库：https://github.com/modelcontextprotocol/servers ，路径 `src/everything`
- 维护：Model Context Protocol
- 固定 commit：`f46d9578190b476b3501923ea8977d899e8db2cb`（2026-09-22T14:30:15Z）
- package metadata：`@modelcontextprotocol/server-everything` 2.0.0
- 传输：stdio。本地进程。运行时网络在 Pilot #1 中关闭。
- 鉴权：这条 reference server 的已测路径不需要生产 secret。
- 外部服务：已测路径没有。
- 边界：低业务复杂度的 reference / test server。
- 本快照的角色：Pilot #1。不再当作 Pilot #2 或 #3。

## 2. Playwright MCP

- 仓库：https://github.com/microsoft/playwright-mcp
- 维护：Microsoft
- 本快照时 main 的 tip：`e87bb897e15a6f2af402afb0f10b45eced9e1f9b`（2026-09-25T21:21:17Z，subject 涉及 docker 下用 tini 回收浏览器进程）
- package metadata：`@playwright/mcp` 0.0.82，Apache-2.0
- `server.json` 名称：`io.github.microsoft/playwright-mcp`。声明的传输是 stdio。
- 依赖锁定：`playwright-core` 1.64.0-alpha-1789764292000，integrity `sha512-ZgRaybFv4rRy7QMGnYprEGFdNJnvapNqcaER2w96bDQA+40BWIle1el1Yh9KHD3E6XYmieMB+r+UxFTCauTGGQ==`
- 本地 / 远程：服务器进程可以本地启动。浏览器在该进程内启动。
- 网络：测量一条本地 `file:` 页面时，不需要访问外部网站。运行时仍按现有 sandbox 关闭网络。
- 鉴权：这条路径不需要生产 secret。
- 外部服务：本地 fixture 路径没有。
- 声明的工具：核心、非 skillOnly 的名字集合在方法里预注册。这里不把 README 功能列表当成已验证能力。
- 构建：源码 commit 可固定。npm 依赖由 lockfile 固定。浏览器二进制要在镜像构建时下载，运行时不再下载。
- artifact：可以做成本地 OCI image。没有 registry digest，除非以后单独记录。
- 可写的语义陈述：对镜像内固定 HTML 做 `browser_navigate`，观察返回文本里的页面标题。`file:` 在默认配置下会被服务器拒绝，源码里的开关是 `--allow-unrestricted-file-access`。
- sandbox：现有边界是非 root、只读根、cap-drop ALL、no-new-privileges、network none、pids 64、memory 512m。浏览器进程是否放得下，要等执行，不在这里预测。
- 主要执行边界：browser / runtime。这是 MCP server 内部的执行边界，不是新的协议族。

Stage A：通过。独立仓库，stars 37593，微软维护，2026-09-25 仍有提交。

Stage B：通过到“可以预注册并尝试”。source、commit、lockfile、许可证和一条本地语义 claim 都写得出来。不需要生产 token。sandbox 是否真能跑，留给一次真实执行。

## 3. Filesystem server

- 仓库：https://github.com/modelcontextprotocol/servers ，路径 `src/filesystem`
- 维护：Model Context Protocol
- 同一 main tip：`f46d9578190b476b3501923ea8977d899e8db2cb`
- package metadata：`@modelcontextprotocol/server-filesystem` 0.6.3
- 传输：该包是 MCP server，预期 stdio。本快照没有启动它。
- 本地。语义 claim 可以写成：只允许一个镜像内或 tmpfs 目录，读写一个预先放好的文件并核对内容。
- 鉴权：这条路径不需要生产 secret。
- 外部服务：没有。
- 构建：与 Everything 同一 monorepo，可以用类似的隔离构建固定 commit。
- sandbox：文件系统权限是主要边界。不能把宿主 home 挂进去。
- star：只有 monorepo 的 90611，不是这个目录自己的 star。

Stage A：通过，但是热度证据弱于独立仓库。它的影响力来自官方 reference servers 集合，不来自单独 star。

Stage B：通过到“以后可以预注册”。这一轮不执行。

## 4. Chrome DevTools MCP

- 仓库：https://github.com/ChromeDevTools/chrome-devtools-mcp
- 维护：ChromeDevTools
- 传输：MCP。浏览器是本机 Chrome / DevTools。
- 主要边界：browser / runtime，并且和容器 sandbox 可能冲突，因为 Chrome 自己也有 sandbox。
- 鉴权：连接本机浏览器，不一定是生产 token，但会碰到宿主机浏览器。

Stage A：通过。

Stage B：这一轮不选。若 Pilot #2 已经是 Playwright，再选它会重复 browser/runtime 这一类边界。不是因为它会失败。

## 5. Context7

- 仓库：https://github.com/upstash/context7
- 维护：Upstash
- 服务器源码是 MIT，commit 可以固定。文档内容来自远程服务，backend 不能随这个仓库一起钉死。
- 网络和外部服务是主要边界。

Stage A：通过。

Stage B：语义结果依赖不可固定的远程 backend。当前方法不能把那次响应写成可复现的组件能力。延后。不是组件失败。

## 6. GitHub MCP Server

- 仓库：https://github.com/github/github-mcp-server
- 维护：GitHub
- 语言 Go。MIT。stdio 或远程都可能，实际调用 GitHub API。
- 鉴权：需要 GitHub token。网络：需要。外部服务：GitHub。

Stage A：通过。

Stage B：不使用用户的生产 token。当前方法不能安全测量它。这不等于该服务器不合格。延后。

## 7. Firecrawl MCP

- 仓库：https://github.com/firecrawl/firecrawl-mcp-server
- 外部抓取服务。通常需要 API key 和网络。
- Stage A：热度低于前几名，但仍是真实产品服务器。
- Stage B：外部服务加凭证。延后。

## 8. Supabase MCP

- 仓库：https://github.com/supabase/mcp
- 外部项目与凭证。
- Stage B：需要真实项目权限。延后。

## 9. Brave Search MCP

- 仓库：https://github.com/brave/brave-search-mcp-server
- 搜索 API。通常需要 API key 和网络。
- Stage B：外部服务加凭证。延后。

## 10. Sentry MCP

- 仓库：https://github.com/getsentry/sentry-mcp
- 外部 Sentry 账号。License SPDX 为 NOASSERTION。
- Stage A：低于上面的独立仓库。
- Stage B：鉴权和外部服务。延后。

## 11. Fetch（monorepo 内）

- 路径：`modelcontextprotocol/servers` 的 fetch server。
- 主要边界：出站网络和不可固定的网页。
- Stage B：要测语义就会碰到外部网站。这一轮不选。star 仍是 monorepo 的。

## 12. Time（monorepo 内）

- 路径：`modelcontextprotocol/servers` 的 time server。
- 行为依赖时钟。可以写 claim，但结果随时间变化。
- 这一轮不选。不是因为会失败，而是它和 Playwright、Filesystem 相比，新增的主要是时间依赖，信息类型更窄。

## 这一轮没有做的事

没有给候选打 0–100 分。没有按“谁更容易通过”或“谁更容易失败”排序。Pilot #3 只预选，不执行。
