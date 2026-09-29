# VE-METHOD-MCP-001

这是第一个外部 MCP 的测量规格，版本 0.3.0。0.1.0 留在 Git `87bd0ad`。规格在 [method.yaml](method.yaml)。0.3.0 在第一次外部运行前把 `protocolVersion` 加进 C1 的预期观察。C2、C3 没有改。`package_version` 2.0.0 是源码 metadata。执行工件是本地隔离构建镜像，不是 npm 发布包。

选择 Everything 不是因为它质量最好，也不是 VeriEnvelope 推荐它。它是 MCP 客户端的参考测试服务器。Pilot #1 要看的是这条链能不能走完：身份、陈述、方法、固定输入、执行、证据、结论、边界。对象本身应尽量少带生产系统的复杂度。

## 测量对象落在现有六块里

没有新增第七块 schema。

| 问题 | 放在哪里 |
| --- | --- |
| Subject | 组件身份：`mcp.server-everything`，版本 2.0.0，commit 见方法文件 |
| Capability | 方法里的 C1、C2、C3。运行后才会写进 result 的 capabilities |
| Assurance | 方法的 assurance。运行后抄进结果 |
| Envelope | 方法的 envelope，包含“不声明”列表 |
| Evidence | 外部组件的证据尚未产生。量具自检不记在这个组件名下 |
| History | 尚未产生 |

方法版本、传输、握手和预期观察是这次测量的条件，写在方法文件里。它们不是新的数据块。

## 还没有执行

通过条件以本版本方法文件为准。看到运行结果之后再改这些条件，必须升版本，并记为方法修订。
