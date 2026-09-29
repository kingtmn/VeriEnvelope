# 重新验证

旧的通过只描述旧的绑定：组件版本、方法版本、runner 版本、环境、fixture。它不自动迁移。

## 版本

组件版本字符串只要变化，就不得复用旧准入。不解析语义化版本，也不把 minor 或 patch 当成“显然无影响”。

## 触发种类

下列变化至少要求重新验证。名单以代码中的 `TRIGGER_KINDS` 为准，并必须与 `methods/VE-METHOD-001/method.yaml` 里的 `envelope.revalidation_triggers` 相同：

- `major_version`
- `relevant_dependency`
- `permission`
- `runtime`
- `protocol`
- `method_revision`
- `runner_bug`
- `external_counterexample`
- `security_or_capability_change`

未列入名单的变化种类同样要求重新验证。调用方如果认为某个改动无关，应传入空列表，并自行准备理由。空列表只表示“没有申报变化”，不表示已经审核过上游差异。

## 系统不做什么

runner 没有复制旧 `admission` 的功能。`admission_reuse_allowed` 只回答政策上是否禁止复用。返回真也不等于已经复用。

`verification_applicability` 只比较 source commit、execution artifact、method version、runner version 和 protocol。不一致时返回 `revalidation_required`。它不打开、不改写、不删除 evidence 文件。旧 evidence 仍是当时的观察。

重新验证的新运行是一条新的 `run_id`。旧证据包保留。新历史事件使用 `revalidated`，`previous_state` 指向旧状态。

Pilot 阶段保持保守规则：变化发生，就要求重新验证。以后若真实记录够用，可以演化成：变化 → 影响分析 → 受影响的 Claim → 选择性重验。这借鉴 Assurance Continuity，见 [METHODOLOGY_LINEAGE.md](../METHODOLOGY_LINEAGE.md)。现在不实现 change graph、dependency graph 或选择性重跑。
