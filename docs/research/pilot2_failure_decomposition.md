# Pilot #2 第一次失败的分解

`external-run-p2-1` 保持原样。这里不改证据包，不改 `VE-METHOD-MCP-002` 0.1.0 的原文（见 `versions/0.1.0.yaml`），也不把假设写成那次运行的原因。

## Problem A — Observation

- 进程启动了
- initialize 请求已发送
- 没有 JSON-RPC 响应
- 进程 exit code 1
- stderr 是 `uv_os_homedir` ENOENT
- 栈进入 `playwright-core` 的 `chromiumChannels.ts`，发生在 MCP 握手完成之前

## Problem B — Classification

见 `pilot2_decision_rule_audit.md`。结论：两条规则的字面条件有交集，方法没有 precedence。这是 method defect。0.1.0 的结果不重算。缺陷记录在 `registry/history/method-defects.jsonl`，不在证据包里。

## Problem C — Environment hypotheses

这些不是 cause。

| Hypothesis | 内容 | 状态 |
| --- | --- | --- |
| H1 | `env -i` 去掉 HOME，Node 的 home 查找因此走失败路径 | supported |
| H2 | uid 65532 在镜像里没有 passwd home，所以没有 HOME 时系统无法解析 home | supported |
| H3 | playwright-core 在 MCP 握手前无条件读取 homedir | supported |
| H4 | 启动脚本或镜像配方本应提供 HOME，但是构建时漏了 | contradicted |
| H5 | HOME 只是第一个显影的环境假设，不是全部问题 | unresolved |

静态和诊断细节在下面。D2 没有做：D0 和 D1 已经把“没有 HOME”和“只有隔离 HOME”分开，不需要再加 passwd。

## Problem D — Governance

Pilot #2 = complete 保持不变。

若 Project GATE 1 只数完成的 Pilot，那么三个 Tool 都在启动或 initialize 前停下，仍可能被数成 3/3。这个定义过宽。

修正后的计数条件：一个 Pilot 要贡献 Project GATE 1，必须实际到达并测量一条组件自身的语义主张。结果可以是 demonstrated、not_demonstrated 或 out_of_envelope。initialize 和 tools/list 不够。

Everything 的 echo 是这样一条主张，所以 Pilot #1 贡献 1。Playwright 还没有到 `browser_navigate`，所以 Pilot #2 complete，但还不贡献。

Completed pilots: 2

Gate-qualified semantic Tool cases: 1 / 3

没有新的 Gate。

## 静态路径

对象是镜像里的 `playwright-core` 1.64.0-alpha-1789764292000，不是后来的 main。

1. Node 22.23.3 的 `src/node_os.cc` `GetHomeDirectory` 调用 `uv_os_homedir`。失败时 `lib/os.js` 抛出 `ERR_SYSTEM_ERROR`。
2. 是 `os.homedir()`。绑定名是 `getHomeDirectory`，底层是 `uv_os_homedir`。
3. 调用发生在模块初始化。`coreBundle.js` 第 77273 行调用 `init_coreBundle()`。它调用 `init_utils()`，再调用 `init_chromiumChannels()`。Map 字面量在初始化时执行 `os.homedir()`。不是第一次 tool call，也不是 browser launch。
4. initialize 请求没有进入 MCP handler。崩溃在 `require` 这个 bundle 的时候。
5. 调用在 `playwright-core`。`cli.js` 只是在加载时 `require` 了这个 bundle。
6. 目的是拼 Chrome / Edge channel 的默认用户数据目录，例如 `homedir()` 加上 `.config/google-chrome`。
7. 无条件。即使用 `--browser chromium`，这个 Map 仍会在导入时建出来。同一 Node 版本带的 libuv 先读 HOME；HOME 不存在才查 passwd，查不到就返回 ENOENT。

## 镜像里的 HOME 事实

diagnostic_only。不是 registry evidence。记录在 `diagnostics/pilot2_home/results/facts.json`。

- 进程环境里 HOME 为空
- uid 是 65532:65532
- `/etc/passwd` 没有 uid 65532。有 `node:x:1000:1000::/home/node`
- 因此没有 65532 的 home 字段
- `/work` 是 `drwxrwxrwt`，`touch` 成功
- 镜像配方和 `start.sh` 没有写 HOME。沙箱当时的 `env -i` 只放 PATH 和 LANG

## D0 / D1 / import

同一镜像，同一 uid，同一 amendment-1 边界。D1 只增加 `HOME=/work/home`，并由同一 uid 在 tmpfs 上创建该目录。

| Case | 结果 |
| --- | --- |
| D0 `os.homedir()` | exit 1，`uv_os_homedir` ENOENT |
| D1 `os.homedir()` | exit 0，打印 `/work/home`。目录属主 65532:65532 |
| import D0 | exit 1，栈与 Run #1 相同，停在 `chromiumChannels.ts` |
| import D1 | exit 0，打印 `import-ok`。没有启动 MCP，没有发送 initialize |

## 责任

Decision A：通用 sandbox baseline。

一个普通 Node 进程调用 `os.homedir()` 是合理的。uid 65532、`env -i`、没有 passwd home、也没有 HOME，会让这个标准 API 抛 ENOENT。这是 VeriEnvelope 自己制造的过贫环境，不是“十个普通工具都应如此”的安全基线。

隔离 HOME 放在 tmpfs，空、非宿主、不持久、属 sandbox uid。不增加网络、能力或宿主挂载。

H4 不成立：配方没有承诺过 HOME。镜像里的 `/home/node` 属于 uid 1000，沙箱不用那个用户。

H5 仍 unresolved。导入在 D1 下过去了，不表示后面的 MCP 或浏览器没有别的环境假设。

## Revalidation question

Under the newly declared environment contract, does P2-C1 initialize now produce the preregistered response?

镜像 id 不变。变化的是 sandbox 合同：amendment-1 没有 HOME 保证，amendment-2 保证隔离 HOME。其他关键边界不变。这不是再试一次 0.1.0。

## external-run-p2-2

问题的答案是：没有。在方法 0.2.0 和 ADR-008-amendment-2 下，initialize 返回了可解析响应，但 `serverInfo.name` 是 `Playwright`，预注册字符串是 `api`。`protocolVersion` 是 `2025-03-26`，`serverInfo.version` 与预注册相同。规则是 P2-M3，observation `mismatch`，outcome `unclassified`，C1 `not_demonstrated`。stderr 为空，exit code 0。C2 和 C3 没有发送。

证据：`evidence/mcp.playwright-mcp/0.0.82/run-d46735b07c1c434b9461370aca6a7268`。预注册的 `api` 不按这次输出改掉。

这把 H1–H3 留在 supported：隔离 HOME 与“导入时 ENOENT”的消失同时出现。它不支持“HOME 使 C1 demonstrated”。H5 仍 unresolved，因为工具调用还没测。新的观察是名字不一致，不是再调 HOME。

## 这次运行的 L0 / L1 / L2

L0：C1 被测量，结果 `not_demonstrated`。C2、C3 仍是 `insufficient`。

L1：同一镜像 id。进程包装改成 amendment-2，并写在 `runtime.json`。执行前基线是 `efb2582`。包的 seal 和 manifest 核对为空。Run #1 的包没有改。

L2：C1 的 tested conditions 仍含预注册的 `serverInfo.name api`。这次结果信封里的 `known_limits` 只写了这条窄观察：在该镜像和 amendment-1 下，没有可解析 HOME 与 ENOENT 同时出现；只加隔离 `/work/home` 时，导入不再出现该错误。这不表示所有部署里的 Playwright 都需要 HOME，也不表示 C1 已经符合。未知区域仍包括真实网站和其他 commit。
