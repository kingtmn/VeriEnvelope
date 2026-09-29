# ADR-007 缺陷编号等到两条缺陷并存再引入

## Context

历史里的 `fixed` 或 `revalidated` 会把“当前有开放缺陷”这个标记清掉。它不记住是哪一条被修好。一条修好、另一条仍在时，这个标记会说谎。

白盒学习和 ADRA 的失败账本都强调错误不能删，并且失败可以有父子或同一根因。那些项目没有给 VeriEnvelope 一个已经验证过的图结构。

## Decision

现在不实现缺陷图，也不增加 `defect_id`。

升级触发条件只有一个：第一次真实 Pilot 里出现下面任一情况。

- 两个互不包含的 defect 同时开着
- 一个 defect 已经被标记修复或重新验证，另一个仍然开着

到那时再加：

- Defect ID
- Fixed by（指向关闭它的历史事件）
- Revalidated by（指向新的运行）

在触发条件出现之前，现有历史事件够用。提前加编号没有记录可指。

## Reason

一条开放标记的错误，要等真实的第二条缺陷才会发生。用想象中的图去改写入路径，会在没有消费者时扩大 schema。

## Trade-offs

在触发之前，连续的“缺陷然后修复”不能表达部分修复。这个限制写在 `CURRENT_STATE.md`，避免读历史的人以为每条缺陷都被单独关闭了。

## Status

Accepted. Implementation deferred until the trigger fires.
