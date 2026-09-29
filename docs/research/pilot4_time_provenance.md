# Pilot #4 expectation provenance

执行前核对。预注册阻止按结果改尺子；它不证明尺子本来就是对的。

Commit：`f46d9578190b476b3501923ea8977d899e8db2cb`。

## 入口

`pyproject.toml` 的脚本 `mcp-server-time` 指向 `mcp_server_time:main`。`__init__.py` 的 `main` 解析 `--local-timezone`，再调用 `serve`。声明的启动是：

`mcp-server-time --local-timezone UTC`

因此 `get_local_tz` 使用传入的 `UTC`，不调用 `tzlocal.get_localzone_name()`。换算本身在两个时区参数都给出时也不读这个本地时区。

## S1

`serve` 构造 `Server("mcp-time")`。Python MCP SDK 1.29.0 里，`Server.__init__` 把这个名字存成 `self.name`，`version` 默认是 `None`。`create_initialization_options` 在 version 为空时用 `importlib.metadata.version("mcp")`。`session.py` 把 `server_name` / `server_version` 放进 `serverInfo`。`uv.lock` 把发行名 `mcp` 锁在 1.29.0。客户端提供的 `2025-03-26` 在 `SUPPORTED_PROTOCOL_VERSIONS` 里，initialize 原样回写 `protocolVersion`。

所以 S1 同时核对三件事：`protocolVersion` 是 `2025-03-26`，`serverInfo.name` 是 `mcp-time`，`serverInfo.version` 是 `1.29.0`。这是这条静态链，不是一次试跑。

## S2

`list_tools` 注册 `convert_time`。额外名字允许存在，包括 `get_current_time`。

## R1

调用 `convert_time`，参数是源码要求的三个字段：

- `source_timezone`: `UTC`
- `time`: `12:00`
- `target_timezone`: `Asia/Tokyo`

`call_tool` 调用 `TimeServer.convert_time`。它用 `datetime.strptime(time_str, "%H:%M")` 取时分，用 `datetime.now(source_timezone)` 只取日期，再算两端的 `utcoffset()`。差值的小时数如果是整数，格式是 `f"{hours_difference:+.1f}h"`。返回值经 `model_dump()` 和 `json.dumps(..., indent=2)` 放进一条 `type=text`。顶层键因此是两格缩进的 `"time_difference"`。

日期、星期和 `is_dst` 随运行当天变化。它们不是这条主张。`get_current_time` 也不是。

`time_difference` 的预期值来自锁文件里的 `tzdata` 2024.2，加上上面的格式。基础镜像自带 `/usr/share/zoneinfo`，CPython 会优先读它，那样偏移就不来自锁文件。配方在安装锁定依赖之后删除这个目录，让 `ZoneInfo` 使用已安装的 `tzdata` 2024.2。镜像 `sha256:f4cd3016ba9ee1e1fc2c94a75694e7a67a23d9882514372129c49ed04f0ef3b4` 在 MCP 运行前做过只读核对，没有发送 MCP。用户 65532，network none。`importlib.metadata` 读到 `mcp` 1.29.0 和 `tzdata` 2024.2。`/usr/share/zoneinfo` 不存在。2026-01-15 和 2026-07-15 的 UTC 偏移都是 0，Asia/Tokyo 都是 9 小时。按源码的整数格式，预期子串是 `  "time_difference": "+9.0h"`。

uv 默认把 CPython 放在 `/root` 下。沙箱用户 65532 不能穿过 `/root`。配方把 `UV_PYTHON_INSTALL_DIR` 设为 `/opt/uv-python`，并给该目录读和执行权限。这是镜像能按声明入口启动的条件，不是一次测量结果。

## 规则互斥

不同 `capability_status` 不共用同一条现实观察：

- P4-M1 要求协议、名字、版本三者都符合。P4-M3 是有可解析 initialize，但三者至少一项不符。P4-M2 是没有可解析响应。
- P4-M4 是名单里有 `convert_time`。P4-M5 是有名单但没有这个名字。名单解析失败走 P4-M2。
- P4-M7 要求可解析的 tool result、`isError` 不是 true、文本包含预注册子串。P4-M8 是有可解析 result，但这一条不成立。没有 content 的错误响应走 P4-M2。
- P4-M9 只表示等待超时。P4-M10 只表示进程启动前被边界拒绝。P4-M11 只表示前置不是 match，所以没有发送。

没有留下空编号的占位规则。
