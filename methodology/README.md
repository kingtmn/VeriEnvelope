# 方法论

这里说明 VeriEnvelope 怎样做判断。具体步骤和规则编号在 `methods/`。参考实现在 `runner/`，它不是本目录的一部分。

阅读顺序：

1. [../METHODOLOGY_LINEAGE.md](../METHODOLOGY_LINEAGE.md) — 继承了哪些原则，没有照搬什么
2. [core_method.md](core_method.md) — 三个验证维度、判断链，以及规格 / 实现 / 结果
3. [measurement_audit.md](measurement_audit.md) — 怎样审计测量工具自己
4. [revalidation.md](revalidation.md) — 什么变化使旧结论失效
5. [epistemic_limits.md](epistemic_limits.md) — 观察和解释怎么分开，哪些话不能说
6. [pilot_preflight.md](pilot_preflight.md) — 某一次外部运行前的检查单

原则列表在 [docs/design_principles.md](../docs/design_principles.md)。
