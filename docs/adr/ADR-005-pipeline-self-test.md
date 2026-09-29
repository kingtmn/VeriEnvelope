# ADR-005 第一份方法只做管线自审

## Context

如果第一份方法假装在验证一个外部组件，而实际只跑了仓库里的 echo 脚本，记录会形成一个假闭环：看起来有 PASS，其实没有组件被测量。

## Decision

`VE-METHOD-001` 的 purpose 是 `pipeline_self_test`。它检查参考 runner 能否执行允许名单内的 fixture、分类，并写出合法证据包。

结果里的 `record_purpose` 取自方法文件。该用途的准入永远是 `insufficient`。

runner 拒绝执行其他用途，包括 `component_verification`。

## Reason

宪法要求测量工具本身可被审计，也要求未知不要包装成已验证。自审是前者，禁止把它写成组件结论是后者。

## Trade-offs

架构目前不能端到端验证一个真实 MCP Server。这是故意留下的缺口。数据模型已经能表示那样的结果，执行被安全边界挡住。

## Status

Accepted
