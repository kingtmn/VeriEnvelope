# VeriEnvelope

Working project name: **VeriEnvelope**。

这是 Evidence-bound Tool Verification 的 v0.1。VeriEnvelope verifies specific claims under declared conditions. It does not decide overall product quality or fitness for use。它不是软件排名，也不是认证机构。发布说明在 [docs/release/V0_1_RELEASE_CANDIDATE.md](docs/release/V0_1_RELEASE_CANDIDATE.md)。源码已经公开在 `kingtmn/VeriEnvelope`；静态网站部署状态以 [CURRENT_STATE.md](CURRENT_STATE.md) 为准。

名称尚未做商标和域名尽调。正式发布前至少还要检查 USPTO、WIPO、EUIPO、CNIPA、GitHub、域名，以及公司或产品名冲突。本仓库不宣称这项清查已经完成。

## 它回答什么

针对一个固定下来的软件组件版本，回答五件事：

1. 在什么版本和环境下，实际证明了它能做什么？
2. 为什么这个结论可以被暂时相信？
3. 结论在什么边界停止成立？
4. 原始证据在哪里？
5. 如果结论后来变了，历史还在不在？

不回答“这个软件好不好”，也不给出总分。

## 三层，不能混

| 层 | 位置 | 是什么 |
| --- | --- | --- |
| Method Specification | `methods/` | 公开方法。第三方可以不用本仓库代码，按方法自行复现。 |
| Reference Implementation | `runner/` | 该方法的一种参考实现。不是唯一裁判。 |
| Verification Result | 一次运行写出的 `result.json` | 某次测量的结论。第三方结果不会自动变成官方结论。 |

`VE-METHOD-001` 只审计测量管线本身。当前范围是 Tool。五条现行语义主张和它们的证据列在 [docs/release/PUBLICATION_AUDIT_V0_1.md](docs/release/PUBLICATION_AUDIT_V0_1.md)。其中 Playwright MCP 的 `browser_navigate` 是 not_demonstrated。这不是认证。

## 当前边界

- 数据模型可以表示 tool 和 mcp_server。
- 参考 runner 的 `run_case` **拒绝**执行第三方组件验证。Everything 的三次运行走的是单独的容器路径，不是 `run_case`。不在宿主机上安装陌生代码。
- 组件登记状态没有 `admitted`。验证结果里的 `admission=admitted` 不是发布，也不是认证。Historical Project GATE 1 已通过。v0.1 发布审计是 READY，但还没有 Publication Authorization。GATE 2 锁定。
- 本地查看器只渲染已有记录，不重新裁决。

宪法在 [CONSTITUTION.md](CONSTITUTION.md)。思想来源在 [METHODOLOGY_LINEAGE.md](METHODOLOGY_LINEAGE.md)。现在做到哪一步，以 [CURRENT_STATE.md](CURRENT_STATE.md) 为准。

## 运行

要求 Python 3.11+。

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
```

跑一次管线自审，并生成单页 HTML：

```bash
.venv/bin/python -m verienvelope run \
  --method methods/VE-METHOD-001 \
  --case methods/VE-METHOD-001/cases/echo_match.json \
  --out evidence/_scratch

.venv/bin/python -m verienvelope view \
  --result evidence/_scratch/fixture.method001/0.0.0/*/result.json \
  --out viewer/preview/index.html
```

`evidence/_scratch/` 和 `viewer/preview/` 被 gitignore。进程退出码 0 只表示这次观察为 match，不表示任何组件被准入。

## 公开网站

`site/` 是只读展示层，从五个现行封存结果生成静态 HTML。它不重跑组件，也不重新裁决。GitHub 始终是事实来源。

```bash
python3 site/build.py
python3 site/verify_public.py
```

Cloudflare Pages 的配置和输出目录见 [site/README.md](site/README.md)。首次公开前的检查结果见 [docs/release/PUBLICATION_HYGIENE_V0_1.md](docs/release/PUBLICATION_HYGIENE_V0_1.md)。

## 明确不做

用户系统、评论、排名、支付、广告、SEO 站、项目方自助提交、批量抓取打分、Agent / Multi-Agent 标准、企业认证、全球统一标准、用模型自动裁决。也不使用“重新定义标准”“全球首个”“权威认证”这类说法。
