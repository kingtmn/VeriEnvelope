# ADR-011：Pilot #2 选择 Playwright MCP

## 状态

在第一次 Pilot #2 进程之前接受。选择日期使用候选池快照 `2026-09-27T01:33:44Z`。

## 范围

当前研究范围是 Tool。Pilot #1、#2、#3 保持 MCP 暴露的 Tool，用来固定协议族。Playwright 的浏览器是这个 MCP server 里面的执行边界，不是新的 CLI、REST 或浏览器扩展协议族。

Skill、Agent、Multi-Agent、Workflow、Model、Prompt package、完整应用和企业系统仍在范围外。

## 决定

Pilot #2 的对象是 `microsoft/playwright-mcp`，commit `e87bb897e15a6f2af402afb0f10b45eced9e1f9b`，package metadata `@playwright/mcp` 0.0.82。

方法是新的 `VE-METHOD-MCP-002`。不修改 `VE-METHOD-MCP-001` 0.3.0。

## 理由

Stage A：独立仓库，快照时 37593 stars、3196 forks，微软维护，2026-09-25 仍有提交。这只说明值得花验证成本。

Stage B：Apache-2.0，commit 和 lockfile 可以固定，不需要生产 secret。可以在镜像里放一个静态 HTML，把 `browser_navigate` 的标题文本写成运行前的预期观察。

和 Pilot #1 的差异是 browser / runtime 边界，不是再选一个 echo 式 reference server。

没有把它选进来是因为预计它会通过，也没有因为它可能失败。

## 不是什么

Star 不是能力证据。这个 ADR 不预测 PASS 或 FAIL。如果现有 sandbox 无法安全执行，记录 `blocked_before_measurement`，不放宽 user、network、read-only 或 cap-drop。

## 后果

执行前要有方法、固定 claim、执行工件和单独的 run authorization。一次运行只有一个 primary claim。第一次与预期冲突就停止后面的 primary claim。
