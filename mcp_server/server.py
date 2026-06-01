#!/usr/bin/env python3
"""
代码检查 Agent —— MCP server（手写轻量实现）。

把检查器以 **Model Context Protocol** 标准工具的形式暴露给任意 MCP 客户端
（Claude Code / Claude Desktop 等），相比 /check 自定义命令更"正统"：模型用
function-calling 方式调用结构化工具，且跨客户端可复用。

为什么手写而不用官方 mcp SDK：官方 `mcp` 包要求 Python >=3.10，本机为 3.9，
故按协议手写。MCP 的 stdio 传输 = 按行分隔的 JSON-RPC 2.0 消息（stdin 收 / stdout 发），
日志一律走 stderr，避免污染协议流。

复用：直接 import 现有 run_check 的 run_all/build_result，零重复逻辑——
体现"框架核心与接入层解耦"。
"""
from __future__ import annotations

import json
import os
import sys

# 让本脚本能 import 到 checker/ 下的 run_check 与 plugins 包
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "checker"))

import run_check  # noqa: E402  复用核心逻辑

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "cppcheck-agent"
SERVER_VERSION = "1.0.0"


def log(msg: str) -> None:
    """日志走 stderr，绝不写 stdout（stdout 专供 JSON-RPC）。"""
    print(f"[mcp-server] {msg}", file=sys.stderr, flush=True)


# ---- 工具定义：暴露给客户端的 check_code ----
CHECK_CODE_TOOL = {
    "name": "check_code",
    "description": (
        "对 C/C++ 文件或目录运行静态代码检查（封装 cppcheck + 自定义编码规范规则）。"
        "返回结构化结果：summary 汇总、findings 列表（含规则 id、严重级、文件行号、说明）、"
        "passed 是否通过。用于发现内存泄漏、越界、未初始化、不安全函数、goto、魔法数字等问题。"
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "target": {
                "type": "string",
                "description": "要检查的 C/C++ 文件或目录路径（相对或绝对）。",
            },
            "config": {
                "type": "string",
                "description": "可选：配置文件路径。缺省时自动定位 config.json。",
            },
        },
        "required": ["target"],
    },
}


def run_check_code(arguments: dict) -> dict:
    """执行一次检查，返回与 run_check 完全一致的 JSON 结果（复用核心逻辑）。"""
    target = arguments.get("target")
    if not target:
        return {"error": "缺少必填参数 target"}
    if not os.path.exists(target):
        return {"schema_version": run_check.SCHEMA_VERSION, "error": f"目标不存在: {target}"}

    config_path = run_check.resolve_config_path(arguments.get("config"))
    config = run_check.load_config(config_path)
    findings = run_check.run_all(target, config)
    return run_check.build_result(target, findings, config)


# ---- JSON-RPC 分发 ----
def make_result(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def make_error(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_request(msg: dict):
    """处理一条 JSON-RPC 消息。通知（无 id）返回 None（不回包）。"""
    method = msg.get("method")
    req_id = msg.get("id")
    params = msg.get("params", {}) or {}

    # 通知：initialized 等，无需响应
    if req_id is None:
        log(f"通知: {method}")
        return None

    if method == "initialize":
        return make_result(req_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })

    if method == "ping":
        return make_result(req_id, {})

    if method == "tools/list":
        return make_result(req_id, {"tools": [CHECK_CODE_TOOL]})

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {}) or {}
        if name != "check_code":
            return make_error(req_id, -32602, f"未知工具: {name}")
        try:
            result = run_check_code(arguments)
        except Exception as e:  # 工具内部异常 → 作为 isError 结果返回，而非崩溃
            log(f"check_code 异常: {e}")
            return make_result(req_id, {
                "content": [{"type": "text", "text": f"检查执行失败: {e}"}],
                "isError": True,
            })
        return make_result(req_id, {
            "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}],
            "isError": False,
        })

    return make_error(req_id, -32601, f"未实现的方法: {method}")


def main() -> int:
    # stdin/stdout 用 UTF-8，且 stdout 不缓冲（逐行回包）
    try:
        sys.stdin.reconfigure(encoding="utf-8")
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    log(f"启动 {SERVER_NAME} v{SERVER_VERSION}，协议 {PROTOCOL_VERSION}")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            log(f"非法 JSON: {e}")
            continue

        response = handle_request(msg)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    log("stdin 关闭，退出。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
