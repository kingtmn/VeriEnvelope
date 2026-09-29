# 证据

一次测量对应一个目录：

```text
evidence/<component-id>/<version>/<run-id>/
  manifest.json
  environment.json
  input/
  stdout.log
  stderr.log
  result.json
  notes.md
  seal.json
```

`manifest.json` 是原始材料清单。它在 `result.json` 和 `notes.md` 写入之前，给当时已经存在的文件计算 SHA-256。结论不把自己的哈希写进这张清单。

`seal.json` 在整包写完之后生成。它封存 manifest、environment、两份输入、stdout、stderr、result 和 notes。它不哈希自己。清单回答“原始材料是什么”；封存回答“写完之后这些最终文件有没有被静默改掉”。两者都要对上，组件准入才能保持。只改一边并同时改掉封存条目，文件级 SHA-256 看不出来；那需要签名，这一版不做。

清单和封存里的路径都必须留在该次运行目录内。文件缺失或哈希不一致时，组件准入不能是 admitted。

失败运行的 stdout 和 stderr 同样留在目录里。超时写的是超时前捕获到的输出，可能为空。

本目录在初始提交中没有证据包。`evidence/_scratch/` 供本地试跑，不进入 Git。已提交的证据包应当是真实运行，而不是手写的通过结论。

当前 runner 只会把 `VE-METHOD-001` 的自审写到这里。那些记录不是组件验证。
