# VeriEnvelope v0.1 release candidate

这是本地候选，不是已经公开的版本。没有 GitHub Release，没有 push。要公开，还需要一次人类的 Publication Authorization。

VeriEnvelope verifies specific claims under declared conditions. It does not decide overall product quality or fitness for use.

公开位置可以叫 Evidence-bound Tool Verification。它不是认证平台，不是排行榜，不是安全扫描器，也不是工具质量排名。

## 这一版包含什么

- 宪法：[CONSTITUTION.md](../../CONSTITUTION.md)
- 方法论：[methodology/core_method.md](../../methodology/core_method.md)
- 参考 Runner：`runner/verienvelope/`
- 证据 schema：`schemas/`
- 发布标准：[PUBLICATION_GATE_V0_1.md](PUBLICATION_GATE_V0_1.md)
- 审计：[PUBLICATION_AUDIT_V0_1.md](PUBLICATION_AUDIT_V0_1.md)

## 选入公开说明的五条主张

1. Everything，`echo`，方法 `VE-METHOD-MCP-001` 0.3.0，`run-244a13b788824422bad65fb9b195ee93`，demonstrated。
2. Playwright MCP，`browser_navigate`，方法 `VE-METHOD-MCP-002` 0.4.0，`run-d22d4d1928204029b8d2e45e82f749ad`，not_demonstrated。
3. Filesystem，`read_text_file`，方法 `VE-METHOD-MCP-003` 0.2.0，`run-a030ab0bf2ee40faaf0b22cf003147ce`，demonstrated。
4. Time，`convert_time`，方法 `VE-METHOD-MCP-004` 0.1.0，`run-f4ba0e8b9d3243f7b42f103a9624fb19`，demonstrated。
5. Memory，`create_entities`，方法 `VE-METHOD-MCP-005` 0.1.0，`run-21d1582275e347ee9389bc241b6756dd`，demonstrated。

标题可以写“某个热门 MCP 的这条主张没有 demonstrated”。正文必须同时给出方法、证据和 Envelope。关注度只解释为什么选它，不进入判断。

## 历史和重测

Filesystem 方法 0.1.0 的 Decision Rule 不完整。旧包 `run-605485ecb4594a0d9fabd0002ca19899` 保留。0.2.0 补全规则之后，`external-run-p3-2` 重新测量，现行结论改为方法授权的 demonstrated。这是一条真实的缺陷到重测链条，不是把旧记录涂掉。

## 明确不主张

- 不认证组件，不保证安全，不表示可以用于生产。
- 不给整体质量排名，不判断是否适合某个用途。
- `admission=admitted` 只表示这条记录可以进入当前声明范围。组件状态仍是 `candidate`。
- 五条主张都不覆盖未写进各自方法的工具、路径、网络或凭证。
- GATE 2 锁定。这一版没有 Skill、Agent、Multi-Agent 或 Workflow。

## 已知限制

审计里延期的事项仍然延期。seal 是内容哈希，不是签名。跨操作系统矩阵、供应链证明和形式化验证不是这一版的条件。

## Verification Request

以后可以接受维护者申请、厂商申请、用户提名，或由 VeriEnvelope 自己选题。请求来自谁，不改变验证。

以后可以为人付费购买优先级、服务速度、测试范围或报告形式。不能购买 demonstrated、更宽的 Envelope，或隐藏负结果。

这一版只记下这个原则，不实现申请系统，也不实现付费。
