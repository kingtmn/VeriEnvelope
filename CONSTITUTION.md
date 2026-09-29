# VeriEnvelope Constitution

工作名称：VeriEnvelope。本文件是项目约束，不是介绍。

当维护 VeriEnvelope 的声誉与维护事实冲突时，事实优先。声誉包括：项目叙事、已发布结论、方法作者的面子、以及“不要公开改口”的压力。

## 1. Evidence before conclusion

证据先于结论。没有可定位的原始记录，就没有能力结论。声明、文档和流行度不是能力证据。

## 2. Unknown stays unknown

不知道就是不知道。未运行、未复现、无法归因的结果，状态只能是 UNKNOWN 或 INSUFFICIENT。禁止用猜测填成已验证。

没有观察到错误，只表示在已经执行的条件和观察窗口里没有观察到错误。不能由此推出安全、可靠、无缺陷或可以投产。

观察不是解释。一次超时、一次非零退出或一次输出不一致，不能自动写成组件、runner、环境或方法中的某一个原因，除非另有证据支持这个归因。

## 3. Scope is part of truth

适用范围和边界是结论的一部分。缺少边界的通过，不是通过。

## 4. Errors remain visible

错误、误判和更正不得静默删除。可以追加更正，不能改写历史使旧结论看起来从未存在。

## 5. Reality can veto us

真实反例可以推翻结论、方法、参考实现和 Schema。模型不优先于观察。

## 6. Trust cannot be bought

商业利益、热度、作者身份、Star、下载量、融资和背书不得购买或替代验证结论。

## 7. Method and measurement tools are themselves auditable

VeriEnvelope 的方法和检测工具必须能被审计、被反例击中、被重新验证。参考实现不是终审。方法规格必须公开到第三方可以不使用本仓库代码而尝试复现。
