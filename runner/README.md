# 参考实现

这里是 VeriEnvelope 参考 runner，不是方法规格，也不是官方裁判。

方法在 `methods/`。即使删除本目录，方法文件仍然应当能被人读懂并另行实现。

## 现在实际会做的事

```bash
python -m verienvelope run \
  --method methods/VE-METHOD-001 \
  --case methods/VE-METHOD-001/cases/echo_match.json \
  --out evidence/_scratch
```

只接受 `purpose: pipeline_self_test`。其他用途在启动子进程之前拒绝。`sandbox.py` 是另一条入口，目前只给无害进程的边界测试使用，不执行外部 MCP。

进程退出码：

| 码 | 含义 |
| --- | --- |
| 0 | observation 为 match |
| 1 | 陈述未被证明（输出或退出码不符） |
| 2 | 被拒绝、超时，或其他不足以判断的执行结果 |
| 3 | schema 或方法规格错误 |

退出码 0 不是准入。

## 查看

```bash
python -m verienvelope view --result <result.json> --out viewer/preview/index.html
```

查看器位于 `viewer/` 所述的人读界面。生成逻辑在 `verienvelope/view.py`，避免两份模板各写一套结论。
