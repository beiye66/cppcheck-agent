"""
cppcheck 检查器：封装 cppcheck 命令行，解析其 XML 输出为统一 Finding。

cppcheck 是静态分析器，不需要编译即可检查 C/C++ 源码。这里调用：
    cppcheck --enable=<...> --xml --xml-version=2 [--addon=misra] [--rule-file=custom.xml] <target>
cppcheck 把结果（XML）写到 stderr，我们解析它。
"""
from __future__ import annotations

import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from typing import List

from .base import Checker, Finding, register


def find_cppcheck() -> str | None:
    """定位 cppcheck 可执行文件：先看 PATH，再看常见安装目录。"""
    exe = shutil.which("cppcheck")
    if exe:
        return exe
    for cand in (
        r"C:\Program Files\Cppcheck\cppcheck.exe",
        r"C:\Program Files (x86)\Cppcheck\cppcheck.exe",
    ):
        if os.path.isfile(cand):
            return cand
    return None


@register
class CppcheckChecker(Checker):
    name = "cppcheck"

    def run(self, target: str, config: dict) -> List[Finding]:
        exe = find_cppcheck()
        if not exe:
            return [Finding(
                id="cppcheck-not-found", severity="information", file=target, line=0, column=0,
                message="未找到 cppcheck，可执行文件不在 PATH 或常见安装目录中。", checker=self.name,
            )]

        cfg = config.get("cppcheck", {})
        enable = cfg.get("enable", "warning,style,performance,portability")
        cmd = [exe, f"--enable={enable}", "--xml", "--xml-version=2", "--inline-suppr"]

        # 可选：标准、include 路径
        if cfg.get("std"):
            cmd.append(f"--std={cfg['std']}")
        for inc in cfg.get("includes", []):
            cmd.append(f"-I{inc}")

        # 可选：自定义正则规则文件（属于"基于 cppcheck 的可扩展规则"）
        rule_file = cfg.get("rule_file")
        if rule_file and os.path.isfile(rule_file):
            cmd.append(f"--rule-file={rule_file}")

        # 可选：MISRA addon（cppcheck 自带 misra.py）
        if cfg.get("misra_addon"):
            cmd.append(f"--addon={cfg['misra_addon']}")

        cmd.append(target)

        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=cfg.get("timeout", 120))
        except subprocess.TimeoutExpired:
            return [Finding(id="cppcheck-timeout", severity="information", file=target,
                            line=0, column=0, message="cppcheck 执行超时。", checker=self.name)]

        # cppcheck 把 XML 报告写到 stderr
        return self._parse_xml(proc.stderr, target)

    def _parse_xml(self, xml_text: str, target: str) -> List[Finding]:
        findings: List[Finding] = []
        if not xml_text.strip():
            return findings
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            return [Finding(id="cppcheck-xml-parse-error", severity="information", file=target,
                            line=0, column=0, message=f"解析 cppcheck XML 失败: {e}", checker=self.name)]

        for err in root.iter("error"):
            eid = err.get("id", "")
            sev = err.get("severity", "information")
            msg = err.get("msg", "")
            cwe = err.get("cwe", "") or ""
            loc = err.find("location")
            f = loc.get("file", target) if loc is not None else target
            line = int(loc.get("line", "0")) if loc is not None else 0
            col = int(loc.get("column", "0")) if loc is not None else 0
            # cppcheck 用 id 形如 misra-c2012-15.5 标注 MISRA 规则
            rule = eid if eid.startswith("misra") else ""
            findings.append(Finding(id=eid, severity=sev, file=f, line=line, column=col,
                                    message=msg, checker=self.name, rule=rule, cwe=cwe))
        return findings
