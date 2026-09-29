# ADR-012：Pilot #3 预选 Filesystem server

## 状态

在 Pilot #2 第一次执行之前接受。这一轮不执行 Pilot #3。

## 决定

预选对象是 `modelcontextprotocol/servers` 里的 `src/filesystem`，commit `f46d9578190b476b3501923ea8977d899e8db2cb`，package metadata `@modelcontextprotocol/server-filesystem` 0.6.3。

它和 Pilot #2 不是同一类边界。Pilot #2 是 browser / runtime。Pilot #3 预选的是 filesystem / permission：只对一个受控目录做可观察的读写，不挂载用户 home。

## 理由

提前固定，是为了避免看见 Pilot #2 的结果之后，再挑一个更容易把现有方法说成正确的对象。

Stage A 的热度证据是官方 reference servers 集合，不是这个目录自己的 star。monorepo 的 90611 stars 不能记到 Filesystem 头上。

Stage B 在纸面上可以成立：source 能钉住，不需要生产 token，语义 claim 可以写成固定文件的精确内容。真正的方法要等 Pilot #3 开跑前另写，不能复用 Playwright 的方法。

## 更换

如果后来不能执行，保留本候选、阻塞原因和更换原因。不能静默换成另一个对象。

## 明确不预选的对象

- Chrome DevTools MCP：和 Playwright 同属 browser/runtime，不适合作为下一个不同边界。
- GitHub MCP：需要真实鉴权。不用生产 token。当前方法不能安全测量，不是该服务器不合格。
- Context7：服务器仓库可以固定，文档 backend 不能固定。
- Firecrawl、Brave Search、Supabase、Sentry：外部服务或凭证。
- Fetch：语义会依赖外部网页。
- Time：主要新增的是时钟依赖。

这些都留在候选池里。延后不是失败，也不是 Not demonstrated。
