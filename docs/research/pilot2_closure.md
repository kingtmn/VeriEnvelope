# Pilot #2 关闭审计

日期：2026-09-26。对象是 Playwright MCP，commit `e87bb897e15a6f2af402afb0f10b45eced9e1f9b`，方法现用 `VE-METHOD-MCP-002` 0.4.0。

## 当前可用记录

- C1：`run-d22d4d1928204029b8d2e45e82f749ad` 里的前置观察是 match，P2-M1，demonstrated。更早的独立记录 `run-b93181d9aee447d1ad4328d15a8363dc` 在方法 0.3.0、amendment-2 下也是 match。
- C2：同一新包里的前置观察是 match，P2-M5，demonstrated。更早的独立记录 `run-d5e468f88bab49db8fd1f48276b154aa` 在方法 0.3.0、amendment-2 下也是 match。
- C3：当前合同下的记录是 `run-d22d4d1928204029b8d2e45e82f749ad`。`browser_navigate` 已发送。文本没有 `- Page Title: ve-pilot-2`。规则 P2-M8，observation `mismatch`，outcome `unclassified`，C3 `not_demonstrated`。准入 `withheld`。

## 被后续合同取代的结果

`run-a554d6a9f8fc4d41b1f3764e5cbc1476` 是 amendment-2、方法 0.3.0 下的 C3。它不再是当前环境身份下的 C3 记录。包本身不改，也不重算。

`run-47f9611e16544d998d983bfa4d7c1b43` 属于 amendment-1。`run-d46735b07c1c434b9461370aca6a7268` 属于方法 0.2.0 的名字映射。它们都只作为当时的证据保留。

## 只属于历史的证据

上述旧包，以及 `diagnostics/pilot2_home/`、`diagnostics/pilot2_tmp/`。诊断不是组件 Capability evidence。

## 准入

组件状态仍是 `candidate`。最新 C3 记录的准入是 `withheld`：证据完整，主主张 `not_demonstrated`。这不是认证，也不是“组件不可用”的判决。

## L2

已测条件是方法 0.4.0 写出的条件：固定 commit、固定镜像、stdio、amendment-3、隔离 HOME、空 tmpfs `/tmp`、声明的启动参数、镜像内静态 HTML。`known_limits` 为空，因为浏览器退出的原因还没有用单变量诊断建立。未测区域包括其余工具、真实网站、宿主文件系统，以及这次日志里出现但没有单独改变的 DBus 和线程上限。重新验证的触发条件仍是方法里写的那些：commit、镜像、sandbox、启动参数或预期字符串变化。

## 结果聚合

缺陷在 `assemble_capabilities` 之前的两处改写：主主张不是 match 时，已 match 的前置主张被写成 insufficient。`case.json` 保留了真实判断。旧包不改。以后的包保留 demonstrated。一致性检查也改为：结果级 observation 只约束 `tested_under` 里点名的主主张。回归测试在 `tests/unit/test_mcp_p2.py` 和 `tests/unit/test_consistency.py`。

## /tmp

D0：只读根，`mkdtemp('/tmp/...')` 为 EROFS。D1：只增加空 tmpfs `/tmp`，mkdtemp 成功。责任是通用 sandbox 合同。ADR-008-amendment-3 只增加这一条。方法 0.4.0 只改 sandbox 引用。

## Deferred

DBus socket 缺失，以及 `pthread_create: Resource temporarily unavailable` 后浏览器被 SIGKILL。

Reason: outside current VeriEnvelope decision boundary

## 人工裁决

没有。原因未归类，不需要把这次失败写成组件缺陷或环境缺陷。
