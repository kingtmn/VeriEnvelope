# ADR

- [ADR-001](ADR-001-source-of-truth.md) 事实放在 Git 和证据包里
- [ADR-002](ADR-002-method-vs-runner.md) 方法、参考实现、验证结论分开
- [ADR-003](ADR-003-no-global-score.md) 不设总分
- [ADR-004](ADR-004-pilot-object.md) Pilot 对象选 MCP Server，但现在不跑
- [ADR-005](ADR-005-pipeline-self-test.md) 第一份方法只审计管线
- [ADR-006](ADR-006-runner-stack.md) 参考实现的技术选择
- [ADR-007](ADR-007-defect-ledger-trigger.md) 多条缺陷并存时才引入缺陷编号
- [ADR-008](ADR-008-pilot-safety-boundary.md) 第一个外部进程的最低隔离。运行时边界已实现，还没有用来启动外部组件
- [ADR-009](ADR-009-pilot-everything.md) 第一个候选是 Everything。身份已固定，没有执行
- [ADR-010](ADR-010-admission-is-not-publication.md) `admitted` 是验证决定，`candidate` 是登记状态
- [ADR-011](ADR-011-pilot-2-selection.md) Pilot #2 选择 Playwright MCP。选择发生在执行之前
- [ADR-012](ADR-012-pilot-3-preselection.md) Pilot #3 预选 Filesystem server。这一轮不执行
