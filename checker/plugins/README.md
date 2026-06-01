# 检查器插件框架 —— 如何扩展

本框架的设计目标：**新增一种检查能力，不改主流程**。三种扩展方式，按成本从低到高：

## 方式 1：加一条正则规范（零代码）

编辑 `checker/config.json` 的 `custom_regex.rules`，追加一条：

```json
{ "id": "no-system-call", "rule": "SEC-1", "severity": "warning",
  "pattern": "(^|[^A-Za-z0-9_])system\\s*\\(",
  "message": "禁止调用 system()，存在命令注入风险。" }
```

保存即生效，无需改代码。适合靠文本模式可识别的规范。

## 方式 2：启用 cppcheck 的能力（改配置）

- 调 `cppcheck.enable` 打开更多检查类别。
- 在 `cppcheck.misra_addon` 填 `checker/addons/misra.py` 启用 MISRA 规则。
- 用 `cppcheck.rule_file` 加载 cppcheck 自定义正则规则文件。

## 方式 3：写一个新的检查器插件（加代码）

适合需要语义分析、调用外部工具（如 clang-tidy、自研分析器）的场景。

1. 在 `checker/plugins/` 新建 `my_checker.py`：

   ```python
   from .base import Checker, Finding, register

   @register
   class MyChecker(Checker):
       name = "my-checker"

       def run(self, target, config):
           cfg = config.get("my-checker", {})
           findings = []
           # ... 做你的分析，产出 Finding ...
           findings.append(Finding(
               id="my-rule-1", severity="warning",
               file=target, line=1, column=0,
               message="...", checker=self.name))
           return findings
   ```

2. 在 `checker/plugins/__init__.py` 增加 `from . import my_checker`。
3. 在 `config.json` 的 `enabled_checkers` 加入 `"my-checker"`。
4. `python checker/run_check.py --list-checkers` 应能看到它。

所有检查器的输出都会被框架合并、归一化成同一份 JSON 契约（见 `json_schema.md`），
Agent 端无需关心底层用了哪种检查器——这就是框架可扩展的关键。
