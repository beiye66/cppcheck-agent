#!/usr/bin/env python3
"""
测试 runner：对每个样例运行检查器，断言"该检出的检出、不该检出的没检出"。

这同时是规则的回归测试——验证 coding rule 确实被检查器有效落地。
用法：
    python tests/run_tests.py
退出码：0 全部通过；1 有失败。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")  # 避免 Windows 控制台中文乱码
except (AttributeError, ValueError):
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_CHECK = os.path.join(ROOT, "checker", "run_check.py")
EXPECT = os.path.join(ROOT, "tests", "expectations.json")


def run_checker(target: str, config: str | None = None) -> dict:
    cmd = [sys.executable, RUN_CHECK, target]
    if config:
        cmd += ["--config", config]
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", cwd=ROOT,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"_parse_error": True, "stdout": proc.stdout, "stderr": proc.stderr}


def main() -> int:
    with open(EXPECT, "r", encoding="utf-8") as fh:
        spec = json.load(fh)

    passed = 0
    failed = 0
    for case in spec["cases"]:
        target = case["file"]
        result = run_checker(target, case.get("config"))
        if result.get("_parse_error"):
            print(f"[FAIL] {target}: 检查器输出不是合法 JSON")
            print(result.get("stderr", "")[:500])
            failed += 1
            continue

        findings = result.get("findings", [])
        ids = {f["id"] for f in findings}
        checkers = {f["checker"] for f in findings}
        ok = True
        reasons = []
        for must in case.get("must_contain", []):
            if must not in ids:
                ok = False
                reasons.append(f"缺少应检出的规则 '{must}'")
        for forbid in case.get("must_not_contain", []):
            if forbid in ids:
                ok = False
                reasons.append(f"误报了不应检出的规则 '{forbid}'")
        for ck in case.get("must_contain_checker", []):
            if ck not in checkers:
                ok = False
                reasons.append(f"结果中未出现检查器 '{ck}'（实际: {sorted(checkers)}）")

        if ok:
            print(f"[PASS] {target}")
            passed += 1
        else:
            print(f"[FAIL] {target}: {'; '.join(reasons)} (实际检出: {sorted(ids)})")
            failed += 1

    total = passed + failed
    print(f"\n=== 测试结果: {passed}/{total} 通过, {failed} 失败 ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
