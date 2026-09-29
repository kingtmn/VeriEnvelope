# ADR-008 第一个外部进程的最低隔离

## Context

参考 runner 今天只跑仓库内 fixture。它清洗了一部分环境变量，使用临时目录和超时。它不断网，不限制 CPU、内存和进程数，也不阻止 PATH 被污染。这不够执行第三方 MCP Server。

这一决定只定义最低边界。它不实现该边界，也不授权现在运行外部代码。

## Decision

第一个外部组件运行使用一个一次性容器，而不是继续在宿主机子进程里执行。不自研沙箱平台。运行时选本地已有的 OCI 容器（Docker 或兼容实现）。如果机器上没有它，Pilot 继续停着，不用“小心一点”代替。

每次运行：

- 一个容器，结束即删除，失败路径也删除
- 网络默认关闭。方法文件若要求网络，必须事先写出允许的目的地；没有这句话就拒绝启动
- 输入目录只读挂载。容器内只有一个可写临时目录。不挂载宿主家目录、仓库写入区和 docker socket
- 不继承宿主环境变量。密钥只有方法点名的文件能进去，默认没有密钥
- CPU 限制为 1，内存 512 MiB，进程数 64，超时取方法里的值且不超过 30 秒
- 标准输出和标准错误进入证据包。容器销毁前把它们拷出
- 环境捕获包含镜像摘要，不只是镜像标签，以及容器内的系统、架构和 runner 版本

这些数字是第一条 Pilot 的上限，不是容量规划。方法若证明 512 MiB 使目标无法完成启动，应改方法里的声明并重新评审，而不是悄悄拿掉限制。

## Reason

外部 MCP 进程是任意代码。协议边界不能代替隔离。一次性容器覆盖文件系统、网络、资源上限和清理，已经回答“最低到哪可以跑一次”。再做编排、镜像仓库策略或多租户，没有当前运行可以消费。

## Trade-offs

容器不是完整的安全证明。内核共享、镜像来源和运行时漏洞仍在。证据包必须记下镜像摘要，这样以后能知道当时跑的是哪一个镜像。没有容器时，预检第 9 条保持失败。

## Status

Accepted. The runtime boundary is implemented in `runner/verienvelope/sandbox.py`. `run_case` does not call it.

构建和运行分开。`pull_image` 可以联网，并且不把宿主密钥放进该子进程。`run_command` 不拉取镜像，运行时网络关闭。宿主上的 npm、npx、pip、uvx 直接拒绝。Everything 自带的 Dockerfile 不代替这道边界。

接受这条决定时，外部 MCP 还没有启动。2026-09-26 的 Run #1 对固定本地镜像发送了一次 initialize。下面的修正不改写当时的决定，只把后来看见的环境事实写清楚。

## Amendment 1 — 2026-09-26

策略版本：`ADR-008-amendment-1`。

Run #1 的 `runtime.json` 里，容器 `Config.Env` 含有 `NODE_VERSION=22.12.0` 和 `YARN_VERSION=1.22.22`。它们来自 Node 基础镜像的 ENV，不是宿主变量。

当时的文字分成两层，实现也是两层，但证据字段把它们记在了一起：

- ADR 写的是不继承宿主环境。这一点仍然成立。`env -i` 不复制宿主变量。
- 架构说明写的是目标进程只有 PATH 和 LANG。同一条启动命令在基础镜像上执行 `printenv`，进程输出只有 `PATH` 和 `LANG`。`NODE_VERSION` 和 `YARN_VERSION` 留在镜像声明和容器 `Config.Env` 里，没有进入该进程。

因此这不是 sandbox failure。C1 的证据包保持原样，不因为这次澄清而失效。`boundary.env` 记录的是容器配置环境，不是进程环境。

以后的运行分开记录：

- Host-derived environment：不继承。进程包装仍然是 `env -i`，只放入 PATH 和 LANG。
- Image-defined environment：允许出现在镜像和容器配置里，必须记入该次运行，不得夹带宿主 secret。它是执行工件的环境事实，不是进程环境。

`VE-METHOD-MCP-001` 0.3.0 的 tested conditions 没有把“进程里只能有 PATH 和 LANG”写成 C1、C2 或 C3 的测量条件。这次修正的是边界记录，不是那三条陈述。方法保持 0.3.0，不升版本。

## Amendment 2 — 2026-09-27

策略版本：`ADR-008-amendment-2`。

Amendment 1 的进程包装是 `env -i`，只放入 PATH 和 LANG，并且以 uid 65532 运行。这个镜像的 `/etc/passwd` 没有 65532。Node 22.23.3 的 `os.homedir()` 调用 `uv_os_homedir`：先看 HOME，没有 HOME 再查 passwd。两条都没有时，返回 ENOENT。

这不是把宿主 home 挂进去。新的进程合同只多一件事：在现有 tmpfs `/work` 上创建空目录 `/work/home`，并让目标进程的 `env -i` 包含 `HOME=/work/home`。目录属于 sandbox uid，不持久，没有 secret。

仍然保持：network none、只读根、cap-drop ALL、no-new-privileges、非 root、不挂载宿主 home、原有的 CPU、内存和 pids 上限。

Pilot #1 和 `external-run-p2-1` 仍属于 amendment-1。它们的证据不改写，也不因为这条修正而重跑。

## Amendment 3

一次只改变 `/tmp` 的诊断（`diagnostics/pilot2_tmp/`，diagnostic_only）表明：在同一镜像、同一 uid 65532、同一 amendment-2 其余边界下，`mkdtemp('/tmp/...')` 得到 `EROFS`。只增加空的 tmpfs `/tmp` 之后，`mkdtemp` 成功，路径仍在 `/tmp` 下。这不是宿主目录，容器销毁后不保留。

因此最小运行时合同增加一条：隔离、非持久、非宿主的可写临时目录，实现为

```text
--tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m
```

仍然保持 network none、非 root、只读根、cap-drop ALL、no-new-privileges、不挂载宿主 HOME、不挂载宿主文件系统、既有资源上限。`/work` 上的隔离 HOME 保持不变。这不是放宽宿主或外部权限。

amendment-1 与 amendment-2 的原文不改。那些环境下已经产生的 evidence 保持原环境身份。只有新 run 使用 amendment-3。
