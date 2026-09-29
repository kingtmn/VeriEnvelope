# ADR-003 不设总分

## Context

单一分数会把能力、置信和适用范围压成一个高低。热度指标也很容易滑进这个分数。

## Decision

不设 0–100 分，也不设星级。公开收录是门栓：`admitted`、`insufficient` 或 `withheld`。

组件 schema 拒绝 popularity、stars、downloads 等额外字段。若将来展示生态信息，必须放在与能力结论分离的结构里。现在没有这个结构，因为没有展示需求。

未通过收录的结果不进入公开黑榜。

## Reason

Pilot 的第一批运行同时在检验 VeriEnvelope。此时公布“某项目不合格”，会把未稳定的测量说成裁决。

## Trade-offs

没有总分，就不能按“好坏”排序。这是目标，不是缺功能。人需要自己读边界和证据。

## Status

Accepted
