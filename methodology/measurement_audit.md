# 测量审计

VeriEnvelope 的 runner 也是被测对象。审计时至少核对下面几项。

## 规则没有被实现私自改写

方法文件里的规则编号顺序和集合，必须与 runner 声明实现的编号一致。结论类别从方法文件读取。测试使用独立于 YAML 的期望值，避免把方法文件改一改测试就跟着放过。

`when` 字段是规格文字。真正的条件在 `runner/verienvelope/rules.py`。审计时读这段代码，并用方法目录里的 fixture 运行，不要只读 YAML。

## 不得伪造通过

- 没有发生输出比较时，能力状态不得为 `demonstrated`。
- `pipeline_self_test` 不得被准入。
- schema 校验失败时，进程以错误结束，不得把这次运行口头称为通过。
- 组件文件的 `status` 不得是 `admitted`。那个词只用于验证结果里的 `admission`。`admission=admitted` 是政策决定，可以留在证据里，但它不是发布状态，也不是认证。

## 执行边界

审计 runner 时确认：

- 子进程不是 shell
- 工作目录不在仓库内
- 绝对路径和 `..` 不会被读取后执行
- 超时有上限
- 子进程环境是允许名单，而不是“删掉几个看起来像密钥的变量”

`secret_probe` fixture 在父进程持有 `VE_TEST_SECRET` 时仍应输出 `clean`。这只证明该变量没有被传进去。它不证明网络已断开，也不证明 PATH 是安全的。

## 证据能被另一个人打开

证据包里要有清单、环境、输入副本、stdout、stderr、结果和 notes。清单上的观察和结果类别必须与 `result.json` 一致。清单中的 SHA-256 必须对得上包内文件。

## v0.1 的方法—runner 一致性

当前没有规则引擎。`methods/VE-METHOD-001/cases/` 里的 match、mismatch、nonzero、timeout、secret_probe，加上路径拒绝测试，就是这一版参考 runner 对这一版方法的一致性测试。

测试期望值写在测试里，不从 YAML 读出来再当成标准答案。规则编号集合必须与方法文件一致。结论类别从方法文件读取。

这只覆盖 VE-METHOD-001。它不能证明另一个 runner 也忠实，也不能证明下一版方法。第二份实现出现时，应共用同一批 fixture 和期望观察，而不是先做 DSL。

## 方法本身可以被改

如果 fixture 测试表明分类规则把现实压扁了，改方法版本，保留旧证据，追加历史。不要为了让旧结论继续好看而改写规则含义却不升版本。
