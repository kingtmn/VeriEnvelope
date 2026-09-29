# Publication Audit v0.1

审计只回答：Tool-only VeriEnvelope v0.1 现在能不能诚实公开。结果是 READY。没有打分。

GATE 2 仍然锁定。这一页不是 Publication Authorization。不创建 GitHub Release，不 push，不扩大 registry。

## 检查

1. 五个 semantic cases 都真正调用了组件自己的行为。结果不必全部 demonstrated。
2. 边界至少三类：protocol / deterministic Tool behavior、browser / runtime、filesystem / permission。Time 实际是 timezone conversion。Memory 实际是 process-local knowledge graph。这两类是记录，不是为了凑数造出来的。
3. 现行方法 `VE-METHOD-MCP-001` 0.3.0、`002` 0.4.0、`003` 0.2.0、`004` 0.1.0、`005` 0.1.0 的每条 classification rule 都有 `when`、`observation`、`outcome_class`、`capability_status`、`run_note`。`003` 0.1.0 的不完整规则留在 `versions/`，不是现行结论。
4. `003` 0.2.0、`004`、`005` 的 Runner 选择 rule id，规范字段从方法复制。测试会改写 `capability_status` 并确认 Runner 跟着走。`001` 和 `002` 的 Runner 仍在代码里重复方法已经写下的同一组标签，没有补上方法里没有的状态。这不改变已经封存的结论。把这两支 Runner 改成从 YAML 读取，留到以后，不作为本版 blocker。
5. Release set 的正式证据包经过 schema、manifest、seal 和 result consistency。本审计不改旧包。
6. 历史缺陷还在：Filesystem 0.1.0 的 Decision Rule 不完整，对应证据包不改。方法修订从 0.1.0 到 0.2.0 可追溯。
7. 重测是真实的：缺陷，方法与 Runner 修复，新版本，新授权 `external-run-p3-2`，新测量 `run-a030ab0bf2ee40faaf0b22cf003147ce`，结论恢复为方法授权的 demonstrated。
8. Blind independent calibration 已经发生，并且发现了上面这条缺陷。不另做一次凑数。
9. 每条现行主张的 L2 都写出 tested conditions、未测区域和 revalidation triggers。`known_limits` 为空表示这条记录没有把未归类现象写成已证实的组件限制。
10. Admission 只表示声明范围内能否进入当前 registry。组件登记状态仍是 `candidate`。
11. 没有一条已知事实会直接推翻上面五条现行主张却还没处理。
12. 公开用词不说 certification、security guarantee、production readiness、overall quality ranking 或 fitness-for-use。

## 现行 semantic cases

| 对象 | 主张 | 现行证据 | 规则 | 结果 | 表面 |
| --- | --- | --- | --- | --- | --- |
| Everything | echo | `run-244a13b788824422bad65fb9b195ee93` | 方法 0.3.0 | demonstrated | protocol / deterministic Tool behavior |
| Playwright MCP | browser_navigate | `run-d22d4d1928204029b8d2e45e82f749ad` | P2-M8 | not_demonstrated | browser / runtime |
| Filesystem | read_text_file | `run-a030ab0bf2ee40faaf0b22cf003147ce` | P3-M7 | demonstrated | filesystem / permission |
| Time | convert_time | `run-f4ba0e8b9d3243f7b42f103a9624fb19` | P4-M7 | demonstrated | timezone conversion |
| Memory | create_entities | `run-21d1582275e347ee9389bc241b6756dd` | P5-M7 | demonstrated | process-local knowledge graph |

Filesystem 的 `run-605485ecb4594a0d9fabd0002ca19899` 是缺陷被发现之前的记录。现行读取结论是后面那一次。

## 继续延期

下面这些不推翻现行五条主张，所以不在本版打开：

- transcript 方向混写
- artifact provenance 较薄
- runtime OS / architecture 记录不完整
- seal 没有签名
- Playwright 的 DBus、pthread / pids、`/dev/shm`、fonts / GPU
- `001` 与 `002` Runner 仍在代码里重复方法标签
- 构建日志里的依赖公告

## 结果

READY。

没有 blocker。Release candidate 写在 `docs/release/V0_1_RELEASE_CANDIDATE.md`。下一步只剩人类的 Publication Authorization。
