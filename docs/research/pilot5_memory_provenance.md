# Pilot #5 expectation provenance

执行前核对。预注册阻止按结果改尺子；它不证明尺子本来就是对的。

Commit：`f46d9578190b476b3501923ea8977d899e8db2cb`。包 `@modelcontextprotocol/server-memory` 0.6.3。

## 入口

`package.json` 的 bin 是 `dist/index.js`。`main` 调用 `ensureMemoryFilePath()`。声明的启动在 `start.sh` 里先设置 `MEMORY_FILE_PATH=/tmp/ve-pilot-5.jsonl`，再执行该文件。

沙箱的 `env -i` 作用在 `/app/start.sh` 之前。脚本自己的 `export` 发生在那之后，所以这个变量能到达 node。`/tmp` 是 ADR-008-amendment-3 已有的隔离 tmpfs，不是新的挂载，也不是宿主目录。

没有这个变量时，默认文件在编译产物旁边的 `memory.jsonl`，位于只读根上。那条路径不是本主张。本主张只覆盖声明的 `/tmp/ve-pilot-5.jsonl`。

## S1

只核对 `protocolVersion` 2025-03-26。源码把服务器构造为 `name: "memory-server"`，版本来自旁边 `package.json` 的 `0.6.3`。这一版不把 SDK 是否原样转发写成主张。

## S2

`registerTool("create_entities")` 注册这个名字。其余工具允许出现。

## R1

参数是一个实体：

- `name`: `ve-pilot-5`
- `entityType`: `fixture`
- `observations`: `["fixed"]`

`createEntities` 在图里没有同名实体时把该实体放进返回数组。空文件或文件不存在时，`loadGraph` 得到空图。处理函数用 `JSON.stringify(result, null, 2)` 放进一条 `type=text`。

主张比较的是解析后的值，不是某一种键顺序或空白。预期值就是这一个实体。键顺序没有单独证明，所以不把整段格式化文本写成唯一合法字节。

不主张 `read_graph`、关系、删除、搜索，也不主张默认路径。

## 规则互斥

- P5-M1 是 protocolVersion 符合。P5-M3 是 initialize 可解析但版本不符。P5-M2 是没有可解析响应。
- P5-M4 是名单里有 `create_entities`。P5-M5 是有名单但没有这个名字。
- P5-M7 是 tool result 可解析、`isError` 不是 true、文本解析后的值等于预注册实体数组。P5-M8 是有可解析 result，但这条不成立。
- P5-M9 只表示超时。P5-M10 只表示启动前被边界拒绝。P5-M11 只表示前置不是 match，所以没有发送。

没有占位规则。
