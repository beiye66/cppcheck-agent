"""检查器插件包。导入各检查器模块以触发其 @register 注册。"""
from . import cppcheck_checker  # noqa: F401
from . import custom_regex_checker  # noqa: F401
from . import clangtidy_checker  # noqa: F401
from .base import Checker, Finding, get_registered, register  # noqa: F401
