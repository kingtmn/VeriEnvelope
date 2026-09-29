# Pilot #2 HOME diagnostics

diagnostic_only

not_registry_evidence

这些进程不是 component verification，不进入 `evidence/`，也不能当作 C1。

它们使用与 `external-run-p2-1` 相同的镜像和 ADR-008-amendment-1 边界。D1 只增加一个条件：`HOME=/work/home`，并且该目录在 tmpfs `/work` 上由同一 uid 创建。
