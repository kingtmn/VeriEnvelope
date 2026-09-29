# VE-METHOD-001

版本 0.1.0。用途：`pipeline_self_test`。

这是测量管线的自审方法，不是组件验证方法。规格在 [method.yaml](method.yaml)。参考 runner 是一种实现，不是这份规格本身。

## 预测

同一 fixture 多次运行，应得到相同的 observation、rule_id 和能力状态。证据包里必须有 stdout。

如果未改 fixture 而观察类别变化，或自审被写成 admitted，就该修改方法或 runner，而不是改预期去迎合输出。

## 规则

| 规则 | 何时 | 能力状态 |
| --- | --- | --- |
| R1 | 退出码和 stdout 都符合预期 | demonstrated |
| R2 | 退出码符合，stdout 不符 | not_demonstrated |
| R3 | 退出码不符 | not_demonstrated |
| R4 | 超时 | insufficient |
| R5 | 路径被拒绝或文件不存在 | insufficient |

R3 不进一步判断是组件、环境还是 fixture 作者的失误。陈述本身包含预期退出码，所以陈述未被满足。R4 连这个判断都不做。

## Fixture

`fixtures/` 里的脚本只服务上表。它们不是待收录组件。
