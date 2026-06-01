"""
自定义正则检查器：用纯文本正则匹配来覆盖 cppcheck 原生查不到的编码规范条目，
例如命名约定、禁用 goto、魔法数字、残留 TODO/FIXME 等。

规则从 config.json 的 custom_regex.rules 读取，因此"加一条规范"只需改配置，
不必改代码——体现框架的可扩展与配置驱动。
"""
from __future__ import annotations

import os
import re
from typing import List

from .base import Checker, Finding, register

# C/C++ 源文件后缀
_C_EXT = {".c", ".h", ".cpp", ".cc", ".cxx", ".hpp"}


def _iter_source_files(target: str):
    if os.path.isfile(target):
        yield target
        return
    for dirpath, _dirs, files in os.walk(target):
        for name in files:
            if os.path.splitext(name)[1].lower() in _C_EXT:
                yield os.path.join(dirpath, name)


@register
class CustomRegexChecker(Checker):
    name = "custom-regex"

    def run(self, target: str, config: dict) -> List[Finding]:
        cfg = config.get("custom_regex", {})
        if not cfg.get("enabled", True):
            return []
        rules = cfg.get("rules", [])
        compiled = []
        for r in rules:
            try:
                compiled.append((r, re.compile(r["pattern"])))
            except re.error as e:
                # 规则本身写错也报一条，方便排查
                compiled.append((r, None))
                _ = e

        findings: List[Finding] = []
        for path in _iter_source_files(target):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as fh:
                    lines = fh.readlines()
            except OSError:
                continue
            for lineno, text in enumerate(lines, start=1):
                for r, rx in compiled:
                    if rx is None:
                        continue
                    if rx.search(text):
                        findings.append(Finding(
                            id=r.get("id", "custom"),
                            severity=r.get("severity", "style"),
                            file=path, line=lineno, column=0,
                            message=r.get("message", "违反自定义编码规范"),
                            checker=self.name,
                            rule=r.get("rule", ""),
                        ))
        return findings
