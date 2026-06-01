"""
clang-tidy 检查器：把 LLVM clang-tidy 接入本框架的第二个静态分析引擎。

与 cppcheck 互补——clang-tidy 基于 Clang AST，偏"编译级"分析，擅长 bugprone/cert/
modernize 等检查；cppcheck 不需编译、误报低。两者结果在同一 JSON 契约下合并。

本插件完全走既有 Checker 接口：实现 run() + @register 即可被框架调度，主流程无改动，
体现"加新检查器不改主流程"的可扩展性。
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import List

from .base import Checker, Finding, register

_C_EXT = {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp"}

# 解析 clang-tidy 文本诊断：  <file>:<line>:<col>: warning|error: <msg> [check-name]
# 注意 Windows 路径含盘符冒号（C:\...），故首段用非贪婪并要求其后是数字。
_DIAG_RE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?P<col>\d+):\s+"
    r"(?P<sev>warning|error):\s+(?P<msg>.*?)"
    r"(?:\s+\[(?P<check>[^\]]+)\])?$"
)


def find_clang_tidy() -> str | None:
    exe = shutil.which("clang-tidy")
    if exe:
        return exe
    for cand in (
        r"C:\Program Files\LLVM\bin\clang-tidy.exe",
        r"C:\Program Files (x86)\LLVM\bin\clang-tidy.exe",
    ):
        if os.path.isfile(cand):
            return cand
    return None


def _iter_source_files(target: str):
    if os.path.isfile(target):
        yield target
        return
    for dirpath, _dirs, files in os.walk(target):
        for name in files:
            if os.path.splitext(name)[1].lower() in _C_EXT:
                yield os.path.join(dirpath, name)


@register
class ClangTidyChecker(Checker):
    name = "clang-tidy"

    def run(self, target: str, config: dict) -> List[Finding]:
        exe = find_clang_tidy()
        if not exe:
            return [Finding(
                id="clang-tidy-not-found", severity="information", file=target, line=0, column=0,
                message="未找到 clang-tidy，请安装 LLVM 或将其加入 PATH。", checker=self.name,
            )]

        cfg = config.get("clang-tidy", {})
        checks = cfg.get("checks", "clang-analyzer-*,bugprone-*,cert-*")
        std = cfg.get("std", "c11")
        includes = cfg.get("includes", [])
        timeout = cfg.get("timeout", 120)

        findings: List[Finding] = []
        for path in _iter_source_files(target):
            cmd = [exe, path, f"-checks=-*,{checks}", "--quiet", "--"]
            cmd.append(f"-std={std}")
            for inc in includes:
                cmd.append(f"-I{inc}")
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      encoding="utf-8", errors="replace", timeout=timeout)
            except subprocess.TimeoutExpired:
                findings.append(Finding(id="clang-tidy-timeout", severity="information",
                                        file=path, line=0, column=0,
                                        message="clang-tidy 执行超时。", checker=self.name))
                continue
            findings.extend(self._parse(proc.stdout + "\n" + proc.stderr, path))
        return self._dedupe(findings)

    def _parse(self, text: str, target: str) -> List[Finding]:
        out: List[Finding] = []
        for line in text.splitlines():
            m = _DIAG_RE.match(line.strip())
            if not m:
                continue
            check = m.group("check") or "clang-tidy"
            # cert-* 检查关联 CERT C 规则，记到 rule 字段
            rule = check if check.startswith("cert-") else ""
            out.append(Finding(
                id=check,
                severity=m.group("sev"),
                file=m.group("file"),
                line=int(m.group("line")),
                column=int(m.group("col")),
                message=m.group("msg").strip(),
                checker=self.name,
                rule=rule,
            ))
        return out

    @staticmethod
    def _dedupe(findings: List[Finding]) -> List[Finding]:
        # clang-tidy 对同一问题可能在不同 TU 重复报告，去重
        seen = set()
        uniq = []
        for f in findings:
            key = (f.id, f.file, f.line, f.column, f.message)
            if key not in seen:
                seen.add(key)
                uniq.append(f)
        return uniq
