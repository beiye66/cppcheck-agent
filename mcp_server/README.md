# MCP Server —— 把检查器暴露为标准 MCP 工具

本目录提供一个 **Model Context Protocol (MCP)** server，把代码检查器以标准工具
`check_code` 暴露给任意 MCP 客户端（Claude Code、Claude Desktop 等）。

## 为什么要 MCP（对比 /check 自定义命令）

| | `/check` 自定义命令 | MCP `check_code` 工具 |
|---|---|---|
| 本质 | 提示词模板触发脚本 | 结构化工具（带 inputSchema） |
| 调用方式 | 仅 Claude Code 内的 slash 命令 | 模型 function-calling，自动按需调用 |
| 复用范围 | 仅 Claude Code | **任何支持 MCP 的客户端通用** |
| 可靠性 | 依赖模型按提示执行 bash | 协议级结构化调用，参数受 schema 约束 |

MCP 是当前 Agent 工具生态的关键开放标准——一次实现，跨客户端复用。

## 实现说明

- **零依赖手写**：官方 `mcp` Python SDK 要求 Python ≥3.10，本机为 3.9，故按协议手写。
- **传输**：stdio + 按行分隔的 JSON-RPC 2.0（stdin 收 / stdout 发，日志走 stderr 避免污染协议）。
- **复用核心**：直接 `import run_check`，调用其 `run_all` / `build_result`，与 CLI / exe 共用同一套
  检查逻辑和 JSON 结果——核心与接入层解耦。
- **实现的方法**：`initialize`、`notifications/initialized`、`ping`、`tools/list`、`tools/call`。

## 工具：check_code

```jsonc
{
  "name": "check_code",
  "inputSchema": {
    "type": "object",
    "properties": {
      "target": { "type": "string", "description": "C/C++ 文件或目录路径" },
      "config": { "type": "string", "description": "可选：配置文件路径" }
    },
    "required": ["target"]
  }
}
```
返回 `content[0].text` 为 JSON 字符串，结构与 `checker/json_schema.md` 完全一致。

## 使用

### 1. 在 Claude Code 中（项目级注册）

项目根的 [.mcp.json](../.mcp.json) 已注册本 server。在本目录启动 `claude`，
确认信任该 MCP server 后，模型即可调用 `check_code` 工具。也可手动添加：

```bash
claude mcp add cppcheck-agent -- python mcp_server/server.py
```

### 2. 冒烟测试（不需要客户端）

```bash
python mcp_server/test_mcp.py
```
会以子进程启动 server 并完成 `initialize → tools/list → tools/call` 握手，
校验 `check_code` 能正确检出问题。

### 3. 手动对话（调试用）

向 server 的 stdin 逐行喂 JSON-RPC：
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"check_code","arguments":{"target":"tests/samples/demo_bad.c"}}}
```
