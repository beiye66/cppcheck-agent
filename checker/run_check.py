#!/usr/bin/env python3
"""
代码检查 Agent —— 检查器主程序（被 Claude Code 的 /check 命令调用的"exe"）。

职责：
  1. 加载配置（config.json）
  2. 调度所有启用的检查器插件（cppcheck 核心 + 自定义规则 + 未来扩展）
  3. 把各检查器的 Finding 合并、归一化成稳定的 JSON 契约
  4. 把 JSON 打到 stdout，供 Agent 解析后决定后续动作

用法：
    python run_check.py <file_or_dir> [--config config.json] [--report-md out.md]
退出码：
    0 = 无达到 fail_on 阈值的问题；1 = 有；2 = 用法/内部错误
JSON 契约见同目录 json_schema.md。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List

# 强制 stdout/stderr 为 UTF-8：Windows 控制台默认 cp936 会把中文 JSON 写成坏字节，
# 导致调用方（Agent）拿到的 JSON 无法正确解码。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # Python 3.7+
    except (AttributeError, ValueError):
        pass

# 允许以脚本方式直接运行（把本目录加入 sys.path 以导入 plugins 包）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from plugins import Finding, get_registered  # noqa: E402
from plugins.base import SEVERITY_ORDER  # noqa: E402

SCHEMA_VERSION = "1.0"


def _base_dir() -> str:
    """脚本所在目录；打包成 onefile exe 时 __file__ 指向临时解压目录，
    故冻结环境下改用 exe 实际所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def resolve_config_path(explicit: str | None) -> str | None:
    """按候选顺序定位 config.json：显式指定 > exe/脚本同目录 > 当前目录下 checker/。"""
    candidates = []
    if explicit:
        candidates.append(explicit)
    candidates.append(os.path.join(_base_dir(), "config.json"))
    candidates.append(os.path.join(os.getcwd(), "checker", "config.json"))
    candidates.append(os.path.join(os.getcwd(), "config.json"))
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def load_config(path: str | None) -> dict:
    if not path or not os.path.isfile(path):
        return {"enabled_checkers": ["cppcheck", "custom-regex"], "fail_on": ["error", "warning"]}
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def run_all(target: str, config: dict) -> List[Finding]:
    enabled = config.get("enabled_checkers", [])
    registry = get_registered()
    findings: List[Finding] = []
    for name in enabled:
        cls = registry.get(name)
        if cls is None:
            findings.append(Finding(id="unknown-checker", severity="information", file=target,
                                    line=0, column=0,
                                    message=f"配置启用了未注册的检查器: {name}", checker="run_check"))
            continue
        findings.extend(cls().run(target, config))
    return findings


def summarize(findings: List[Finding]) -> dict:
    counts = {s: 0 for s in SEVERITY_ORDER}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    counts["total"] = len(findings)
    return counts


def build_result(target: str, findings: List[Finding], config: dict) -> dict:
    # 按严重级、文件、行号排序，输出可预测
    # 归一化文件路径：不同检查器风格不一（clang-tidy 报绝对路径，cppcheck 报相对路径）。
    # 统一为相对 cwd 的正斜杠路径，保证 Agent 解析时同一文件的标识一致。
    cwd = os.getcwd()
    for f in findings:
        if os.path.isabs(f.file):
            try:
                rel = os.path.relpath(f.file, cwd)
                if not rel.startswith(".."):
                    f.file = rel
            except ValueError:
                pass  # 跨盘符等无法相对化时保留原值
        f.file = f.file.replace("\\", "/")
    order = {s: i for i, s in enumerate(SEVERITY_ORDER)}
    findings_sorted = sorted(findings, key=lambda f: (order.get(f.severity, 99), f.file, f.line))
    summary = summarize(findings_sorted)
    fail_on = set(config.get("fail_on", ["error"]))
    passed = all(summary.get(s, 0) == 0 for s in fail_on)
    return {
        "schema_version": SCHEMA_VERSION,
        "target": target.replace("\\", "/"),
        "passed": passed,
        "fail_on": sorted(fail_on),
        "summary": {k: v for k, v in summary.items() if v or k == "total"},
        "findings": [f.to_dict() for f in findings_sorted],
    }


def to_markdown(result: dict) -> str:
    s = result["summary"]
    status = "✅ PASS" if result["passed"] else "❌ FAIL"
    lines = [
        f"# 代码检查报告 — {status}",
        "",
        f"- 目标: `{result['target']}`",
        f"- 失败阈值 (fail_on): {', '.join(result['fail_on'])}",
        f"- 汇总: 共 {s.get('total', 0)} 项"
        f"（error {s.get('error', 0)} / warning {s.get('warning', 0)} / style {s.get('style', 0)}）",
        "",
        "| 严重级 | 规则 id | 文件:行 | 说明 |",
        "|--------|---------|---------|------|",
    ]
    for f in result["findings"]:
        loc = f"{os.path.basename(f['file'])}:{f['line']}"
        lines.append(f"| {f['severity']} | {f['id']} | {loc} | {f['message']} |")
    if not result["findings"]:
        lines.append("| — | — | — | 未发现问题 |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="代码检查 Agent 检查器")
    parser.add_argument("target", nargs="?", help="要检查的 C/C++ 文件或目录")
    parser.add_argument("--config", default=None, help="配置文件路径（默认自动定位 config.json）")
    parser.add_argument("--report-md", help="额外输出 Markdown 报告到该路径")
    parser.add_argument("--list-checkers", action="store_true",
                        help="列出所有已注册的检查器后退出")
    args = parser.parse_args(argv)

    if args.list_checkers:
        print(json.dumps({"registered_checkers": sorted(get_registered().keys())},
                         ensure_ascii=False, indent=2))
        return 0

    if not args.target:
        parser.error("缺少检查目标（或使用 --list-checkers）")

    if not os.path.exists(args.target):
        json.dump({"schema_version": SCHEMA_VERSION, "error": f"目标不存在: {args.target}"},
                  sys.stdout, ensure_ascii=False)
        print()
        return 2

    config = load_config(resolve_config_path(args.config))
    findings = run_all(args.target, config)
    result = build_result(args.target, findings, config)

    # 主输出：JSON 到 stdout（Agent 解析）
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if args.report_md:
        with open(args.report_md, "w", encoding="utf-8") as fh:
            fh.write(to_markdown(result))

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
