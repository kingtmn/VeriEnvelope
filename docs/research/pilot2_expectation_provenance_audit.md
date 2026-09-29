# P2-C1 预期来源审计

对象只限于冻结工件。源码 commit `e87bb897e15a6f2af402afb0f10b45eced9e1f9b`。镜像 `sha256:cc8221f580a2ff7cdecac250da533250ef12e03a4101c13363056039072544cd` 里的 `playwright-core` 是 `1.64.0-alpha-1789764292000`。没有用后来的 main，也没有重新构建。

这一页审计的是预期本身，不是把 Run #2 的输出写成正确值。

Source pinned 不等于 semantic mapping established。Pre-registered 不等于 correctly specified。

## Critical assertions

| Assertion | Expected | Source | Commit / artifact | File / symbol | 语义 | 为什么映射到响应字段 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| protocolVersion | `2025-03-26` | bundled MCP SDK 的支持列表，以及方法自己提供的客户端版本 | 同一镜像内 `utilsBundle.js` | `SUPPORTED_PROTOCOL_VERSIONS`，`Server._oninitialize` | 客户端提供的协议版本；若该字符串在支持列表里，响应回这个版本 | `utilsBundle.js` 76689 列出它。81681–81689：请求版本在列表中时，`protocolVersion` 等于请求版本 | supported |
| serverInfo.name | `api` | `createConnection` 里的工厂名 | 同一 `coreBundle.js` | `packages/playwright-core/src/tools/mcp/index.ts` 的 `backendFactory.name` | 进程内库函数的连接工厂名。该函数会把它传给 `createServer` | 方法把这个字符串当成 CLI 启动后的 `serverInfo.name`。CLI 不调用 `createConnection` | incorrect_mapping |
| serverInfo.version | `1.64.0-alpha-1789764292000` | `playwright-core` 的 `package.json` `version` | 镜像内该文件，version 字段就是这个字符串 | `packages/playwright-core/src/package.ts` 的 `packageJSON`；CLI 工厂的 `version: version2` | 这个 playwright-core 包的版本 | CLI 工厂把该版本交给 `createServer`，再交给 `new Server({ version })`，SDK 把它放进 `serverInfo` | supported |
| request id | 响应 id 等于请求 id | JSON-RPC 对应关系，方法的 expected observation | 方法 0.1.0 / 0.2.0 的 C1 文字 | runner 按 id 匹配 | 哪一条响应属于哪一条请求 | 这是协议对应，不是组件元数据 | supported |
| error absence | 响应没有 `error` | 方法 C1 陈述 | 方法文字 | C1 statement | 有结果，而不是 JSON-RPC error | 方法把“没有 error”写成主张的一部分 | supported |

## `api` 从哪里来

镜像内 `/app/node_modules/playwright-core/lib/coreBundle.js`，对应源路径 `packages/playwright-core/src/tools/mcp/index.ts`，函数 `createConnection`。

工厂对象是：

- `name: "api"`
- `nameInConfig: "api"`
- `version: packageJSON.version`

紧接着调用 `createServer("api", packageJSON.version, backendFactory, ...)`。

`packageJSON` 来自 `packages/playwright-core/src/package.ts`：`require(packageRoot + "/package.json")`。`packageRoot` 是 `playwright-core` 目录。镜像里该文件的 `name` 是 `playwright-core`，`version` 是 `1.64.0-alpha-1789764292000`。

`api` 的语义是这个库函数的 backend factory 名。同一函数确实把它作为 `Server` 的 Implementation `name`。所以在调用 `createConnection` 时，它会成为 `serverInfo.name`。

它不是：

- `@playwright/mcp` 的 `package.json` `name`（那是 `@playwright/mcp`）
- `mcpName`（那是 `io.github.microsoft/playwright-mcp`）
- CLI 的 commander 程序名（那是 `Playwright MCP`）
- 配置键 `nameInConfig` 在另一条路径上的值（CLI 路径上是小写 `playwright`）

`tools` 导出同时包含 `createConnection` 和 `decorateMCPCommand`。它们是两个入口。

## `Playwright` 从哪里来

镜像入口是 `/app/cli.js`。`start.sh` 执行的是这个文件，参数里没有 `--port`。

`cli.js` 第 30 行调用 `tools.decorateMCPCommand(p, packageJSON.version)`。这里的 `packageJSON` 是 `/app/package.json`，版本 `0.0.82`。`decorateMCPCommand` 的定义只接收 `command`。第二个参数没有被读。

`p` 的 `.name('Playwright MCP')` 是 commander 显示名。它没有传入 `Server`。

`decorateMCPCommand` 在 `packages/playwright-core/src/tools/mcp/program.ts`。动作里构造：

- `name: "Playwright"`
- `nameInConfig: "playwright"`
- `version: version2`

`version2` 在同文件初始化时等于上面的 playwright-core `packageJSON.version`。

然后 `await start(factory, config.server)`。

`start` 在 `packages/playwright-core/src/tools/utils/mcp/server.ts`。`options.port` 未定义时创建 `StdioServerTransport`，并 `connect(factory, ...)`。

`connect` 调用 `createServer(factory.name, factory.version, factory, ...)`。

`createServer` 执行 `new Server({ name, version }, { capabilities: { tools: { listChanged: true } } })`。

`Server` 在同一镜像的 `utilsBundle.js`，注释路径是 `node_modules/@modelcontextprotocol/sdk/dist/esm/server/index.js`。构造函数把第一个参数存为 `this._serverInfo`。`_oninitialize` 返回 `serverInfo: this._serverInfo`。

因此 CLI 这条链是：

字面量 `"Playwright"` → CLI factory.name → `createServer` 的 name → `new Server({ name })` → `_serverInfo` → initialize 结果的 `serverInfo.name`。

同一 bundle 里还有别的 `"Playwright"` 字符串：dashboard 的 `title`、浏览器对象的类名、commander 的 `Playwright MCP`。那些不进入这条 `Server` 构造。小写 `playwright` 是 `nameInConfig`，用于 HTTP 配置键，不是 `serverInfo.name`。

## 两条链的关系

两条链都在同一个 `coreBundle.js` 里，都最终可以调用 `createServer`，但入口不同。

- `createConnection`：工厂名 `api`。导出给进程内调用。`/app/cli.js` 不调用它。
- `decorateMCPCommand`：工厂名 `Playwright`。`/app/cli.js` 调用它。方法声明的启动器就是这个 CLI。

构建没有把 `api` 改写成 `Playwright`。Dockerfile 只做 `npm ci`，不编译这段 bundle。两个字面量都还在冻结文件里。镜像里没有单独安装的 `@modelcontextprotocol/sdk` 目录。`package-lock.json` 里的 SDK `1.30.0` 是 `@playwright/mcp` 的 devDependency，`npm ci --omit=dev` 没有装它。运行时用的是 bundle 里面的那份 SDK。

这是 source expectation mapping 问题，不是 build/runtime 把一个身份字符串变换成另一个。

## 结论

Case A：`expectation_semantic_mapping_defect`。

`api` 这个字符串存在，并且在 `createConnection` 上会成为 Implementation name。方法测量的进程不走那个函数。声明的 CLI 把字面量 `Playwright` 传进 MCP `Server`，SDK 把它作为 `serverInfo.name` 返回。

这不是 Playwright 的缺陷。0.1.0 和 0.2.0 的结果不重算。当时按冻结方法得到的 `mismatch` / `not_demonstrated` 仍是历史事实。以后的测量要用修正后的映射，所以需要新的方法版本。

Case C 不成立为这次的分类：方法已经绑定了 CLI 启动器。缺的不是配置条件，而是把另一个函数的名字抄到了这个启动器上。

## diagnostic_only 与 known_limits

HOME 的 D0、D1 和 import-only 仍是 diagnostic_only，不是 registry capability evidence。

`run-d46735b07c1c434b9461370aca6a7268` 的结果信封 `known_limits` 引用了这些诊断。该包不改。诊断可以指导方法、沙箱和后续实验设计。它不能自动变成已验证的组件属性。以后的正式结果不再把这段诊断写进 Claim Envelope。

## amendment-2

保持。这次名字映射错误不反驳隔离 HOME。
