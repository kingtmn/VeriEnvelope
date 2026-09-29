# ADR-006 参考实现用 Python 标准库和两个成熟库

## Context

第一阶段需要：schema 校验、读取方法文件、固定子进程、写证据包、生成一个本地页面。不需要网站框架。

## Decision

- Python 3.11+
- `jsonschema` 校验 JSON Schema
- `PyYAML` 只负责把方法规格读成数据
- 子进程、路径、哈希、UUID 使用标准库
- 查看器由 Python 写出单个 HTML 文件，不引入前端框架，也不起长期服务
- 测试用 pytest

命令行只有 `run` 和 `view`。不使用单独的 CLI 框架。

## Reason

这些步骤用标准库已经能做完。方法文件用 YAML，是因为规格需要给人读，同时让 runner 读取规则的结论类别，避免在 Python 里再抄一张结论表。YAML 不承载可执行逻辑。

静态 HTML 足够回答八个阅读问题。引入 React 或常驻 Web 服务不能改善证据的可追溯性。

## Trade-offs

条件判断仍在 Python 中，见 ADR-002。没有容器运行时；隔离缺口见架构文档，不靠再加一个依赖假装已经隔离。

## Status

Accepted
