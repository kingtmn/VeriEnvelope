# Pilot #3 预期来源

对象是 `modelcontextprotocol/servers` commit `f46d9578190b476b3501923ea8977d899e8db2cb`，路径 `src/filesystem`。package metadata 是 `@modelcontextprotocol/server-filesystem` 0.6.3。没有启动 MCP。

`server.registerTool("read_text_file", ...)` 的处理函数是 `readTextFileHandler`。不传 head 或 tail 时，它调用 `readFileContent`，也就是 `fs.readFile(path, "utf-8")`，再放进 `{ type: "text", text: content }`。

启动参数只给出 `/app/fixture`。源码在客户端没有 roots capability 时保留命令行允许目录。本方法的 initialize 发送空 capabilities。

fixture 文件是 `methods/VE-METHOD-MCP-003/fixtures/ve-pilot-3.txt`，sha256 `dae4e9d957af7c3ddb7fdb92e84de8ef6fb305648d9dc0f559fd27c6acb0b354`。容器内路径是 `/app/fixture/ve-pilot-3.txt`。预期文本就是这些字节。

`new McpServer` 的字面量是 `secure-filesystem-server` 和 `0.2.0`。这一版不把 SDK 转发写成主张。

允许目录之外的路径、写入和删除不在这次主张里。
