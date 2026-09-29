# P2-M2 与 P2-M10

读的是 `VE-METHOD-MCP-002` 0.1.0 原文，文件 `versions/0.1.0.yaml`。0.2.0 不改写这次判断。

## 各自想解决什么

P2-M2：initialize 没有可解析的对应响应，或返回了 error。结果是 `execution_error` / `unclassified` / `not_demonstrated`。它想表示主张没有被 demonstrated，同时不指认原因。

P2-M10：容器边界拒绝启动，或进程在响应前退出。结果是 `blocked` / `out_of_envelope` / `insufficient`。它想表示观察没有在方法边界内完成，并且这不是组件失败判定。

## 条件有没有交集

有。`external-run-p2-1` 同时满足：

- P2-M2 的“没有可解析的对应响应”
- P2-M10 的“进程在响应前退出”

它不满足 P2-M10 的前半句。边界检查通过了，进程启动了，initialize 也发出去了。

两条规则给出不同的 observation、outcome 和 capability status。0.1.0 没有写谁优先。实现走了 `_send` 的“没有匹配响应 → P2-M2”。那是代码路径，不是方法里的 precedence。

## 这是哪一种重叠

不只是措辞重复。两条规则想管的阶段不同，但 0.1.0 把“响应前退出”写进了 P2-M10，又让 P2-M2 覆盖一切没有响应的情况。阶段不同，字面条件却相交。没有 precedence。因此是 method defect，不是一条已经写明、只是实现选错的规则。

## 0.2.0 的互斥分支

先问边界或策略是否在测量开始前拒绝。是则 P2-M10：`blocked` / `out_of_envelope` / `insufficient`。

否则，进程已经启动，但预期 id 没有可解析响应。则 P2-M2：`execution_error` / `unclassified` / `not_demonstrated`。

Run #1 若按这个分支重读，会落在 P2-M2，而不是 P2-M10。这只是事后的阅读。封存结果仍是当时的 P2-M2，不重算。

没有为这个区分增加新的 outcome。

## case.json 里的两条判断

`C1` 和 `initialize` 是同一判断的两个键。`_send` 用消息名存了一次，主测量再用 claim id 存了一次。这是 runner bookkeeping，不是两个不同结论。

0.1.0 的 `case.json` 不改。以后的记录只保留 C1、C2、C3。不为这件事重跑。
