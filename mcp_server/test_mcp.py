#!/usr/bin/env python3
"""
MCP server 冒烟测试：以子进程启动 server.py，按 MCP 握手顺序发 JSON-RPC，校验响应。
用法： python mcp_server/test_mcp.py
退出码：0 全部通过；1 有失败。
"""
import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")  # 避免 Windows 控制台中文乱码
except (AttributeError, ValueError):
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(ROOT, "mcp_server", "server.py")


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, SERVER],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", cwd=ROOT, bufsize=1,
    )

    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "test", "version": "0"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},  # 通知，无响应
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "check_code",
                    "arguments": {"target": "tests/samples/ari1_zerodiv_bad.c"}}},
    ]
    payload = "".join(json.dumps(r) + "\n" for r in requests)
    out, err = proc.communicate(payload, timeout=120)

    # 解析 stdout 中的所有响应行
    responses = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        responses[msg.get("id")] = msg

    failures = []

    # 校验 initialize
    init = responses.get(1)
    if not init or init.get("result", {}).get("serverInfo", {}).get("name") != "cppcheck-agent":
        failures.append("initialize 响应不正确")
    else:
        print("[PASS] initialize ->", init["result"]["serverInfo"])

    # 校验通知不产生响应（id=None 不应出现在 responses，除非 server 误回）
    # (通知没有 id，server 不应回包；这里无需断言具体内容)

    # 校验 tools/list
    tl = responses.get(2)
    tools = tl.get("result", {}).get("tools", []) if tl else []
    names = [t["name"] for t in tools]
    if "check_code" not in names:
        failures.append(f"tools/list 未包含 check_code，实际: {names}")
    else:
        print("[PASS] tools/list ->", names)

    # 校验 tools/call
    tc = responses.get(3)
    if not tc or "result" not in tc:
        failures.append("tools/call 无 result")
    else:
        text = tc["result"]["content"][0]["text"]
        result = json.loads(text)
        ids = sorted({f["id"] for f in result.get("findings", [])})
        if "zerodiv" not in ids:
            failures.append(f"tools/call 未检出 zerodiv，实际: {ids}")
        else:
            print(f"[PASS] tools/call -> passed={result['passed']} ids={ids}")

    if failures:
        print("\n=== 失败 ===")
        for f in failures:
            print(" -", f)
        print("\n--- server stderr ---\n" + err[:1000])
        return 1
    print("\n=== MCP server 冒烟测试全部通过 ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
