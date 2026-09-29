# P2-C2 预期来源

对象是方法 0.3.0 里已经冻结的 25 个 `core_tools`，以及镜像 `sha256:cc8221f580a2ff7cdecac250da533250ef12e03a4101c13363056039072544cd` 里的 `playwright-core` `1.64.0-alpha-1789764292000`。没有重新构建，也没有启动 MCP。

## 注册链

`/app/start.sh` 执行 `/app/cli.js`，参数是 `--headless --browser chromium --no-sandbox --isolated --allow-unrestricted-file-access --no-webmcp`。没有 `--caps`，没有 `--config`，没有 `--port`。

`cli.js` 调用 `decorateMCPCommand`。该动作先 `resolveCLIConfigForMCP`，再 `filteredTools(config)`，把结果的 schema 放进 CLI 工厂的 `toolSchemas`，然后 `start(factory)`。

`filteredTools` 在 `packages/playwright-core/src/tools/backend/tools.ts`：

保留 `capability` 以 `core` 开头的工具，或者 `config.capabilities` 点名的 capability；然后去掉 `skillOnly`。

`defaultConfig` 没有 `capabilities`。`--caps` 不在声明参数里。沙箱是 `env -i`，不传入 `PLAYWRIGHT_MCP_CAPS`。因此 `config.capabilities` 不存在，OR 分支不增加工具。

`browserTools` 由各 `*_default` 数组无条件展开。从这些数组抽出、且通过上面谓词的名字，与方法 0.3.0 的 `core_tools` 逐个相同，共 25 个，没有重复。

`tools/list` 的处理函数先返回这些 schema，再追加 `backend.dynamicTools()`。`backendPromise` 只在 `tools/call` 里创建。本方法的 C2 在任何 tool call 之前发送 `tools/list`，所以这一次列表不包含 dynamic tools。

## 不在这次列表里的工具

源码里还有工具，但当前入口不注册它们：

- `skillOnly: true` 且 capability 以 `core` 开头：`browser_check`、`browser_uncheck`、`browser_press_sequentially`、`browser_keydown`、`browser_keyup`、`browser_navigate_forward`、`browser_reload`、`browser_console_clear`、`browser_network_clear`、`browser_webmcp_list`、`browser_webmcp_call`。过滤函数丢掉它们。
- capability 不是 `core*`：`config`、`devtools`、`network`、`pdf`、`storage`、`testing`、`vision`。只有 `--caps` 或对应环境变量点名时才会进入 `filteredTools`。当前声明没有这些条件。
- 页面通过 WebMCP 注册的工具走 `dynamicTools`。`--no-webmcp` 把 `config.webmcp` 设为 false，并且这次 `tools/list` 发生在 backend 创建之前。

这些工具不是 hidden 的第二套 MCP 名字。它们要么被同一过滤函数排除，要么属于另一次调用才会出现的动态列表。

浏览器种类不参与 `filteredTools`。声明的 chromium 不改变这 25 个名字是否注册。

## 和 `api` 那次的差别

`api` 是另一个函数里的工厂名，被错映射到 CLI 的 `serverInfo.name`。

C2 的名字来自 CLI 实际调用的 `filteredTools`，不是来自另一条入口，也不是来自 README。集合级映射成立。

`tools/list` 的集合会随 `--caps`、`PLAYWRIGHT_MCP_CAPS` 或配置文件改变。本方法的启动参数和 `env -i` 把这些条件固定为未设置。预期集合有资格作为这次 C2 的断言。不需要新的方法版本。

## 非主张

这次不断言工具能完成操作，不断言 dynamic tools 在 `tools/call` 之后仍为空，不断言其他 capability 组合。

## external-run-p2-4

同一会话里，initialize 的前置观察是 match。随后 `notifications/initialized`，然后 id 为 2 的 `tools/list`。响应 id 是 2。没有夹杂通知。名字集合与 `core_tools` 相同，missing 和 unexpected 都是空。规则 P2-M5。C3 没有发送。stderr 为空。没有 `unmatched.json`。
