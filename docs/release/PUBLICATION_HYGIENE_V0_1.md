# Publication Hygiene v0.1

日期：2026-09-28。

这次检查只覆盖首次公开发布与静态展示层。没有重新运行组件，没有改 Method，没有改历史 evidence，没有扩大 registry，GATE 2 仍锁定。

## 已确认

1. 本地仓库是 `/Users/<user>/Desktop/VeriEnvelope`，分支是 `main`，检查开始时工作区干净，HEAD 是 `10183be`。
2. GitHub 远端 `kingtmn/VeriEnvelope` 实时显示为 Public；隐私安全的公开快照已经 push 到 `main`，未公开旧的本地 Git 历史。
3. 当前树共 360 个已跟踪文件。没有已跟踪的 `.env`、私钥文件、数据库文件或证书文件。
4. 当前树和全部 Git commit 做过高置信度 secret shape 检查。没有命中私钥头、GitHub token、OpenAI-style key、Cloudflare API token assignment 或 Bearer token。
5. 当前树里的个人绝对路径已改成 `/Users/<user>/...`。容器里的 `/home/node` 是公开镜像用户路径，不是宿主用户信息。
6. 全部本地 Markdown 链接通过存在性检查。公开网站生成后的内部 `href` / `src` 也通过存在性检查。
7. 根目录有 MIT LICENSE。网站没有复制第三方图片、字体或脚本，也没有新增依赖。
8. 五个公开案例只读取现行封存 `result.json`。构建时会检查 primary capability 和状态：Everything demonstrated、Playwright not_demonstrated、Filesystem demonstrated、Time demonstrated、Memory demonstrated。
9. 网站是只读展示层。它显示 Claim、Result、Method、Evidence、Envelope、History，不计算总分，不重新裁决，不把 admission 写成认证。
10. Cloudflare 构建命令为 `python3 site/build.py && python3 site/verify_public.py`，输出目录为 `site/dist`。生成目录不进入 Git。
11. 桌面和 390px 移动视口已人工查看首页与 Playwright 案例页。浏览器控制台没有 error 或 warning。
12. 不需要 Docker 的 146 项测试通过。完整测试集合另外有 10 failed、7 errors，均发生在 Docker/Colima integration tests，直接错误是当前受控环境无权访问 `/Users/<user>/.colima/default/docker.sock`。没有把这些项记成通过，也没有为本次发布重跑外部组件。

## 公开历史与隐私处理

Git 历史不能仅靠修改当前 HEAD 擦除。现有私有历史里仍能看到：

- 旧版 `docs/research/prior_work_audit.md` 中的宿主用户名和若干本机项目路径；
- Git author 名称与邮箱；
- 已封存的历史文档、诊断和 evidence。

用户已明确要求隐藏本机用户名和本机项目路径，同时允许完整公开 Git author 邮箱，并要求首页提供邮箱反馈入口。

因此公开仓库采用一个不带 parent 的隐私安全根提交：树内容来自完成脱敏和校验后的本地 HEAD，但不发布旧 Git commit 链。本机原仓库和完整历史保持不动，没有改写历史，也没有删除 evidence。所有 Method、Evidence 包以及文件内记录的 History 仍包含在公开快照中。公开仓库的取舍是：不显示 v0.1 首次公开之前的 Git commit lineage。

首页和全站 footer 使用用户指定邮箱 `kingtmn1@gmail.com` 作为反馈地址。Git author 邮箱仍按原提交元数据公开，不做改写。

## 名称检查边界

一次有限的精确名称网页、GitHub 与官方数据库索引搜索没有发现 `VeriEnvelope` 的明显公开冲突。这不是正式商标清查，也不能证明 USPTO、WIPO、EUIPO、CNIPA 或未被搜索引擎索引的登记中不存在冲突。因此 v0.1 继续明确称为 working project name，不主张商标权利。

## 当前结论

发布准备：AUTHORIZED FOR PUBLIC SNAPSHOT。

用户在 2026-09-28 已明确授权：

1. 隐藏本机用户名和本机项目路径；
2. 完整公开 Git author 邮箱，并在网站首页留下该邮箱；
3. 把脱敏后的公开快照 push 到公共仓库 `kingtmn/VeriEnvelope`；
4. 操作 Cloudflare Dashboard，创建 Pages 项目并上线。

GitHub OAuth / GitHub App 的实际授权页面仍属于账户权限变更；到达该按钮前再次停下做 action-time confirmation。

## 上线结果

- GitHub：`https://github.com/kingtmn/VeriEnvelope`
- Cloudflare Pages：`https://verienvelope.pages.dev/`
- GitHub App 已收紧为仅选择 `kingtmn/VeriEnvelope`；Cloudflare Pages 项目只绑定该仓库的 `main` 分支。
- 首次 Cloudflare 构建完成并上传 14 个静态文件；线上首页、反馈邮箱和案例详情页已验证可访问。
