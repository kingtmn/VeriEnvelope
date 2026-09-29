# 设计原则

这些原则约束怎么设计和审计 VeriEnvelope。它们不是运行时规则引擎，也没有被编码成 15 个抽象层级。

1. **Reality Calibration**
   先看真实组件能怎样被固定和执行，再决定方法写什么。不先假设一份标准会有用。

2. **Problem Reduction**
   第一阶段只处理低层、可测试的组件。当前执行面更窄：只跑方法自带的 fixture。

3. **Direction First**
   质量先于数量，证据先于宣传，真实先于声誉，边界先于漂亮结论。

4. **Phenomenon First**
   先测量一个具体对象，再考虑要不要抽象成更宽的方法。`VE-METHOD-001` 不假装已经是组件标准。

5. **Counterexample First**
   主动保留失败输出、超时和拒绝执行的记录。方法要写明什么样的结果说明方法本身该改。

6. **Evidence First**
   README、作者声明、Star 和热度可以当背景信息，不能自动变成能力证据。Schema 不接收 popularity、stars、downloads。

7. **Measurement Audit**
   测量工具自己要被测。秘密环境变量不得进入子进程；没有比较发生时不得写成 demonstrated。

8. **Simplicity First**
   现有 Identity、Capability、Assurance、Envelope、Evidence、History 能表达的，就不增加 L3。新字段必须说明它解决的具体缺口。

9. **Prediction First**
   方法在运行前写明：什么观察支持当前做法，什么观察说明该修改方法或 runner。

10. **Perturbation**
    不只保留输出一致的用例。方法内包含输出不一致、非零退出和超时。

11. **Multiple Windows**
    作者声明、源码、本仓库测试、第三方报告和用户反馈是不同窗口。多个模型的相同说法不是独立证据。证据来源用 `source_type` 区分，不做成等级制度。

12. **三个验证维度**
    能力是否被观察到、为什么暂时相信、结论能声称到哪里，是三个问题。它们不是成熟度等级。不用一个总分压平。

13. **Dynamic Boundary**
    通过总是绑定组件版本、方法版本、runner 版本、环境和 fixture。版本一变，旧准入不继承。

14. **Researcher Self-Audit**
    历史事件允许记下 evaluation_defect 和随后的 fixed 或 revalidated。项目必须能留下“以前判断错了”。

15. **Failure Value**
    失败输出写入证据包并保留。失败不是待清理的垃圾，也不是公开榜上的惩罚。
