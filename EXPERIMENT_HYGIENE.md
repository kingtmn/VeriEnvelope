# 实验卫生

这些规则约束候选选择和外部运行。它们不给组件打分，也不把失败当成目标。

Failure is data. Failure-seeking is bias.

## 1. 先选候选，再看结果

候选必须在运行之前定下来。不能因为“这个可能会通过”或“这个可能容易出错”而挑选。

## 2. 热门是选择信息，不是证据

Star、Fork、下载量、用户量和官方身份只说明值不值得花验证成本。它们不能进入 Capability、Assurance 或 Admission。

Popularity 不是质量，也不是验证证据。

## 3. 预注册

每个 Pilot 在执行前固定：Identity、Claims、Method、Expected Observations、Decision Rules、Explicit Non-Claims、Envelope、Execution Artifact。

观察不能反过来修改同一版本方法。

## Expected observations need provenance

关键 Expected Observation 必须在运行前冻结，并且能追溯。至少要回答：值从哪里来；它为什么对应被断言的字段；来源是 source、protocol spec、declared metadata，还是 fixture。

Pre-registration controls outcome-driven change; it does not establish correctness of the measuring rule.

这属于方法质量，不是新的一层。JSON 标点和无关日志不要求完整来源。

## 4. 不重复直到通过

第一次真实失败、mismatch、blocked 或 timeout 必须先留下 evidence。不能为了得到 PASS 再跑一次。

重复必须说明原因，并写成新的 run authorization。

## 5. 不悄悄排除

build failure、sandbox 不兼容、许可证不够清楚、不可控的外部依赖、需要鉴权、方法写不出来、preflight 失败，都要留下选择记录和原因。

Not measured、Not demonstrated、Failed 是三件不同的事。

## 6. 一次运行一个主测量

一个 external run 只有一个 primary claim。前置 claim 可以再次观察，但不能变成这次的主测量。

## 7. 先观察，再诊断

顺序是 Observation，然后 Claim Status，然后 Diagnosis，然后 Cause。不能从观察直接跳到原因。

## 8. 保留反面证据

失败日志、异常输出、timeout、blocked、method defect、runner defect、evaluation defect 都保留。不只保存 PASS。

## 9. 诊断时一次改一个关键条件

出现 mismatch 之后，如果要诊断，一次只改变一个关键条件。不要同时换版本、Runner、环境、协议和方法，然后宣布修好了。

## 10. 环境身份

每次至少记录 source、artifact、runtime、sandbox、protocol、network policy、相关环境、timestamp。

外部服务存在时，把它记成不能完全固定的外部变量。

## 11. 随机和非确定

对象如果依赖 random、时间、网络、模型或外部状态，先固定能固定的变量。不能固定的进入 Assurance 或 Envelope，不把它写成 deterministic。

## 12. 方法版本

方法修订留下历史。修改方法不等于错误。静默修改才是问题。

## 13. 失败有信息

失败不是项目失败。它可能暴露组件边界、方法、runner、环境、假设或评估的缺陷。不为了维持通过率而改数据。

## 14. 也不追求失败率

VeriEnvelope 不追求高失败率。目标是高信息增益，并且解释歧义低。

不为了制造错误而选择对象，也不为了制造错误而修改实验。
