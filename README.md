# 代码检查 Agent（cppcheck + Agent 扩展）

一个把 **cppcheck 静态分析**封装成 **Agent 可调用工具**的可扩展代码检查框架，并通过
Claude Code 的自定义命令 `/check` 实现 **「检查 → 解析 JSON → 自主修复 → 重检查」** 的闭环。

本项目同时落地两个题目：
- **第 3 题（扩展 Agent 控制功能）**：自定义命令调用一个返回 JSON 的程序，Agent 解析后执行后续动作。
- **第 1 题（cppcheck 套件）**：cppcheck 检查、AI 生成 coding rule、AI 生成测试用例、基于 cppcheck 的可扩展检查框架。

---

## 1. 整体架构

```
Claude Code (Agent 大脑)
   │  /check <file> [--fix]   ← .claude/commands/check.md 定义的自定义命令
   ▼
checker/run_check.py  (被调用的"exe"，可 pyinstaller 打包)
   │  调度已注册的检查器插件
   ├── CppcheckChecker     → 调 cppcheck，解析 XML
   └── CustomRegexChecker  → 正则规则（goto/魔法数字/不安全函数…）
   │  合并 + 归一化
   ▼
统一 JSON 契约 (stdout)  → Agent 解析 → 决策：汇报 / 修复(Edit) / 重检查
```

这正是 ReAct 范式：`Action(/check) → Observation(JSON) → Thought(修哪条) → Action(Edit/重检查)`，
直到 `passed=true` 或达到最大轮数。

## 2. 目录结构

```
code-check-agent/
├── .claude/
│   ├── commands/check.md      # /check 自定义命令（第3题核心）
│   └── settings.json          # 预授权运行检查器命令
├── checker/
│   ├── run_check.py           # 检查器主程序（编排 + JSON 输出）
│   ├── config.json            # 默认配置（启停检查器、规则集）
│   ├── config.misra.json      # 启用 MISRA addon 的配置档
│   ├── json_schema.md         # JSON 输出契约（Agent 解析接口）
│   ├── rules/coding_rules.md  # AI 生成的编码规范（MISRA + 常见，第1题）
│   ├── addons/                # cppcheck 官方 MISRA addon（misra.py 等）
│   └── plugins/               # 可扩展检查框架
│       ├── base.py            #   Checker 接口 + Finding + 注册表
│       ├── cppcheck_checker.py
│       ├── custom_regex_checker.py
│       └── README.md          #   如何新增检查器
├── tests/
│   ├── samples/               # AI 生成的测试用例（每条规则反例/正例）
│   ├── expectations.json      # 测试期望清单
│   └── run_tests.py           # 测试 runner（回归验证规则有效）
└── reports/                   # 检查报告输出
```

## 3. 使用方法

```bash
# 直接用检查器（命令行）
python checker/run_check.py tests/samples/demo_bad.c --report-md reports/demo.md

# 列出已注册检查器
python checker/run_check.py --list-checkers

# 启用 MISRA addon
python checker/run_check.py <target> --config checker/config.misra.json

# 跑回归测试（验证规则落地）
python tests/run_tests.py
```

在 **Claude Code** 里（于本目录启动）：
```
/check tests/samples/demo_bad.c          # 只检查 + 汇报 + 给修复建议
/check tests/samples/loop_demo.c --fix   # 进入自主修复闭环（最多 5 轮）
```

## 4. 检查结果与报告

### 4.1 综合样例 demo_bad.c（11 项）

| 严重级 | 数量 | 代表问题 |
|--------|------|---------|
| error | 4 | 数组越界、缓冲区溢出、内存泄漏、未初始化变量 |
| warning | 3 | malloc 未判空（可能空指针）、goto |
| style | 4 | 魔法数字、参数可声明 const |

完整报告见 [reports/demo_bad.md](reports/demo_bad.md)。

### 4.2 Agent 自主修复闭环 loop_demo.c

| 轮次 | 结果 |
|------|------|
| 第 1 轮 | 4 项：error 1（uninitvar）+ warning 3（malloc 未判空 / strcpy 不安全 / uninitvar） |
| 修复 | 初始化变量、检查 malloc 返回值、用 memcpy 替换 strcpy |
| 第 2 轮 | **0 项，passed=true**，闭环收敛 ✅ |

修复后报告见 [reports/loop_demo_after.md](reports/loop_demo_after.md)。

### 4.3 回归测试

`python tests/run_tests.py` → **7/7 通过**：每条规则的反例都被正确检出，正例不误报。

## 5. 整个过程考虑了哪些问题

1. **检查器 ↔ Agent 的接口契约**：用版本化 JSON（`schema_version`）作为唯一接口，Agent 不关心
   底层是 cppcheck 还是别的工具；新增字段不删旧字段，保证向后兼容。
2. **编码/跨平台**：Windows 控制台默认 cp936 会让中文 JSON 变坏字节 → 强制 stdout 为 UTF-8；
   不同检查器路径分隔符不一（`/` vs `\`）→ 统一归一化为 `/`。
3. **误报与噪声控制**：高危且可精确判断的（内存/越界）交给 cppcheck（误报率低）；只能近似判断的
   （魔法数字）用正则并设较低严重级；用 `fail_on` 控制哪些级别判定失败。
4. **闭环安全与可控**（对应研究报告里的"护栏"）：
   - 默认只汇报、给建议，**只有显式 `--fix` 才改代码**（human-in-the-loop）；
   - 修复循环设**最多 5 轮**上限，防止"修复又引入新问题"的无限循环；
   - 命令权限在 `settings.json` 里最小化预授权。
5. **可扩展性**：插件接口 + 注册表 + 配置驱动，三种扩展路径（加正则规则 / 启用 cppcheck 能力 /
   写新插件）成本递增，新增能力不改主流程。
6. **可验证性**：用 expectations 清单 + test runner 做回归，保证"规范确实被检查器有效落地"，
   也防止后续改动让规则失效。
7. **MISRA 版权**：MISRA 规则原文受版权保护，addon 仅按规则编号报告，不内置规则文本。

## 6. 最终框架包含的内容

- **检查引擎层**：cppcheck（核心静态分析）+ 官方 MISRA addon + 自定义正则检查器。
- **框架层**：统一 `Checker` 插件接口、`Finding` 数据模型、检查器注册表、配置驱动的规则集、
  统一 JSON 契约、Markdown 报告生成、自省（`--list-checkers`）。
- **规范层**：AI 生成的 C 编码规范文档（MISRA + 常见规则），并映射到具体检查能力。
- **测试层**：每条规则的反例/正例样例、期望清单、回归测试 runner。
- **Agent 集成层**：Claude Code 自定义命令 `/check`、权限配置，实现检查→修复→重检查闭环。

## 7. 打包成 exe（已完成，满足"调用 exe 程序"）

已用 PyInstaller 打包为单文件 `dist/run_check.exe`（约 6 MB，无需 Python 环境即可运行）。
一键复现：

```powershell
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

该脚本会：① 装 pyinstaller；② `--onefile` 打包（`--paths checker` 解决 plugins 包发现，
`--hidden-import` 带上各检查器）；③ 把 config 复制到 exe 同目录。

**冻结环境处理**：onefile exe 里 `__file__` 指向临时解压目录，故 `run_check.py` 用
`_base_dir()`（冻结时取 exe 实际目录）+ 多候选 `resolve_config_path()` 来定位 config.json，
保证 exe 从任意工作目录都能找到配置。已验证：从 `%TEMP%` 用绝对路径调用 exe 检测正常。

用法与 Python 版完全一致，JSON 契约相同：

```bash
dist/run_check.exe <target> [--config ...] [--report-md ...] [--list-checkers]
```

`/check` 命令已改为优先用 `dist/run_check.exe`，不存在时回退到 `python checker/run_check.py`。

## 依赖

- Python 3.7+
- cppcheck（本项目用 2.20.0，安装在 `C:\Program Files\Cppcheck\`，检查器会自动定位）
