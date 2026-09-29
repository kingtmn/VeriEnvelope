# P2-C3 预期来源

对象是方法 0.3.0 和镜像 `sha256:cc8221f580a2ff7cdecac250da533250ef12e03a4101c13363056039072544cd`。没有启动浏览器，也没有改方法。

## 最小主张

在该 commit、该镜像、ADR-008-amendment-2、声明的启动参数，以及镜像内这份固定 HTML 下，调用 `browser_navigate`，参数 URL 为 `file:///app/fixture/ve-pilot-2.html`。返回的 MCP tool result 里，至少有一条 `type=text` 的文本包含 `- Page Title: ve-pilot-2`。不断言整份 snapshot，不断言标题以外的节点。

## 执行链

`browser_navigate` 在 `navigate.ts`。capability 是 `core-navigation`，没有 `skillOnly`。它属于当前 C2 的 25 个名字。

handler：`context.ensureTab()`，然后 `tab.checkUrlAndNavigate(params.url)`，然后 `response.setIncludeSnapshot()`。

`checkUrlAndNavigate` 只在 URL 无法解析时才补 `http://` 或 `https://`。`file:///app/fixture/ve-pilot-2.html` 可以解析，协议保持 `file:`。接着 `page.goto`，`waitUntil` 是 `domcontentloaded`，然后再等 `load`，上限 5 秒。

`checkUrlAllowed`：`allowUnrestrictedFileAccess` 为真时直接返回。否则 `file:` 会抛出 `Access to "file:" protocol is blocked`。声明的 `--allow-unrestricted-file-access` 关掉的是服务器自己的这道检查。它不增加容器能力，也不挂载宿主目录。方法里已经写了这个开关。

标题来自 `headerSnapshot` 里的 `page.title()`。`renderTabMarkdown` 在 `tab.title` 非空时写入 `` `- Page Title: ${tab2.title}` ``。`serialize` 把这一节放进 `### Page`，再放进唯一的 `type=text` 文本。默认不是 JSON。没有单独的 title 字段。子串断言对应的就是这个 formatter，不是 README。

`setIncludeSnapshot` 在没有 snapshot 配置时用 `full`。声明参数没有改 snapshot mode，所以 Page 节会写出来。snapshot 正文不在这次断言里。

## Fixture

仓库文件 `methods/VE-METHOD-MCP-002/fixtures/ve-pilot-2.html`。镜像路径 `/app/fixture/ve-pilot-2.html`。两边 SHA-256 都是 `1e546c583185e6d1ea5066acf30cf05176ded4f1c88d3aff4d489ffdd1a290a1`。它在第一次 Pilot #2 运行前的提交 `2822e851` 里已经固定。

内容是一张静态 HTML。`<title>ve-pilot-2</title>`。没有脚本，没有外链，不读时间，不写宿主数据。

## 结论

`- Page Title: ve-pilot-2` 有源码和 fixture 依据。不需要 0.4.0。0.3.0 不改。

## external-run-p2-5

同一会话里 C1 和 C2 的判断是 match。然后发送了一次 `browser_navigate`。响应 id 是 3。文本是：

`### Error`

`Error: async initializeServer: EROFS: read-only file system, mkdtemp '/tmp/playwright-artifacts-lDzUZ9'`

没有 `- Page Title: ve-pilot-2`。规则 P2-M8，observation `mismatch`，C3 `not_demonstrated`。stderr 为空，exit code 0。预期字符串没有按这次文本修改。

这是主张已经执行后的观察。`/tmp` 上的 `mkdtemp` 只是错误文本里的字，还不是经过单变量实验的原因。没有为它加挂载，也没有再跑。
