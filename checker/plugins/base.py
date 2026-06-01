"""
可扩展检查框架的核心接口。

所有检查器（cppcheck 核心、MISRA addon、自定义正则规则、未来你自己写的检查器）
都实现 Checker 抽象类，产出统一的 Finding 列表。run_check.py 负责把多个检查器的
结果合并、归一化成同一份 JSON 契约返回给 Agent。

这样新增一种检查能力 = 新增一个 Checker 子类并注册，无需改动主流程。
"""
from __future__ import annotations

import dataclasses
from abc import ABC, abstractmethod
from typing import List


# cppcheck 的严重级，统一成这几档，便于 Agent 决策（error 必修，warning/style 视配置）
SEVERITY_ORDER = ["error", "warning", "performance", "portability", "style", "information"]


@dataclasses.dataclass
class Finding:
    """一条检查结果。字段构成 Agent 解析的稳定契约（见 json_schema.md）。"""
    id: str                 # 规则/检查项 id，如 "nullPointer" / "misra-c2012-15.5"
    severity: str           # error | warning | performance | portability | style | information
    file: str               # 文件路径
    line: int               # 行号（无则 0）
    column: int             # 列号（无则 0）
    message: str            # 人类可读描述
    checker: str            # 产出该结果的检查器名，如 "cppcheck" / "custom-regex"
    rule: str = ""          # 关联的编码规范条目（可选），如 "MISRA-15.5"
    cwe: str = ""           # CWE 编号（可选）

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class Checker(ABC):
    """检查器插件接口。实现 run() 即可被框架调度。"""

    name: str = "base"

    @abstractmethod
    def run(self, target: str, config: dict) -> List[Finding]:
        """对 target（文件或目录）执行检查，返回 Finding 列表。

        config: 来自 config.json 的配置子树，检查器自行解释（启用规则、严重级阈值等）。
        约定：不要抛异常打断整个流程；内部错误应转成一条 severity=information 的 Finding。
        """
        raise NotImplementedError


# ---- 检查器注册表：新增检查器在这里登记即可被 run_check.py 发现 ----
_REGISTRY: dict[str, type[Checker]] = {}


def register(checker_cls: type[Checker]) -> type[Checker]:
    """类装饰器：把一个 Checker 子类注册进框架。"""
    _REGISTRY[checker_cls.name] = checker_cls
    return checker_cls


def get_registered() -> dict[str, type[Checker]]:
    return dict(_REGISTRY)
