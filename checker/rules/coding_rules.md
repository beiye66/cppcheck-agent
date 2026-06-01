# C 语言编码规范（Coding Rules）

> 本规范由 AI 辅助整理，融合 **MISRA C:2012** 的代表性规则与业界常见 C 编码规范
> （CERT C、Linux kernel style、Google C++ 部分适用于 C 的条目等）。
>
> 每条规则标注：**编号 / 类别 / 严重级 / 检查方式**。检查方式分三类：
> - `cppcheck` —— cppcheck 原生能检测（给出对应 id）
> - `misra-addon` —— 由 cppcheck 的 MISRA addon (`addons/misra.py`) 检测
> - `custom-regex` —— 由本框架的自定义正则检查器检测（规则定义在 `config.json`）
>
> 这种"规则 → 检查能力"的映射，正是把"编码规范"落地成"自动化检查"的关键。

---

## 一、内存与资源管理（Memory & Resource）

| 编号 | 规则 | 严重级 | 检查方式 | 对应 id |
|------|------|--------|---------|---------|
| MEM-1 | 动态分配的内存必须释放，避免内存泄漏 | error | cppcheck | `memleak` |
| MEM-2 | 禁止使用已释放的内存（use-after-free） | error | cppcheck | `useAfterFree` |
| MEM-3 | 禁止重复释放同一指针（double free） | error | cppcheck | `doubleFree` |
| MEM-4 | `malloc` 等分配后必须检查返回值是否为 NULL | warning | cppcheck | `nullPointerOutOfMemory` |
| MEM-5 | 资源（文件句柄等）使用后必须关闭 | error | cppcheck | `resourceLeak` |

## 二、指针与数组（Pointer & Array）

| 编号 | 规则 | 严重级 | 检查方式 | 对应 id |
|------|------|--------|---------|---------|
| PTR-1 | 解引用指针前应确保非空 | error | cppcheck | `nullPointer` |
| PTR-2 | 数组访问不得越界 | error | cppcheck | `arrayIndexOutOfBounds` |
| PTR-3 | 缓冲区操作不得越界（如 strcpy 溢出） | error | cppcheck | `bufferAccessOutOfBounds` |
| PTR-4 | MISRA 18.1：指针算术只能在数组范围内 | warning | misra-addon | `misra-c2012-18.1` |

## 三、变量与初始化（Variable & Init）

| 编号 | 规则 | 严重级 | 检查方式 | 对应 id |
|------|------|--------|---------|---------|
| VAR-1 | 使用前必须初始化变量 | error | cppcheck | `uninitvar` |
| VAR-2 | 不应存在未使用的变量 | style | cppcheck | `unusedVariable` |
| VAR-3 | MISRA 8.9：只在单个函数用到的对象应定义在块作用域 | style | misra-addon | `misra-c2012-8.9` |
| VAR-4 | 指针参数若不修改所指内容，应声明为 `const` | style | cppcheck | `constParameterPointer` |

## 四、控制流与结构（Control Flow）

| 编号 | 规则 | 严重级 | 检查方式 | 对应 id |
|------|------|--------|---------|---------|
| CTRL-1 | 禁止使用 `goto`（MISRA 15.1） | warning | custom-regex | `no-goto` |
| CTRL-2 | `if/else if` 链应有 `else` 结尾（MISRA 15.7） | style | misra-addon | `misra-c2012-15.7` |
| CTRL-3 | `switch` 必须有 `default`（MISRA 16.4） | warning | misra-addon | `misra-c2012-16.4` |
| CTRL-4 | 不应存在永真/永假的条件、不可达代码 | warning | cppcheck | `knownConditionTrueFalse` |
| CTRL-5 | 循环/条件体必须使用大括号（MISRA 15.6） | style | misra-addon | `misra-c2012-15.6` |

## 五、运算与类型（Arithmetic & Type）

| 编号 | 规则 | 严重级 | 检查方式 | 对应 id |
|------|------|--------|---------|---------|
| ARI-1 | 禁止除以零 | error | cppcheck | `zerodiv` |
| ARI-2 | 避免有符号整数溢出 | warning | cppcheck | `integerOverflow` |
| ARI-3 | 避免有符号/无符号混用比较 | warning | cppcheck | `signConversion` |
| ARI-4 | MISRA 10.x：禁止不当的隐式类型转换 | warning | misra-addon | `misra-c2012-10.*` |

## 六、API 与标准库（API Usage）

| 编号 | 规则 | 严重级 | 检查方式 | 对应 id |
|------|------|--------|---------|---------|
| API-1 | `printf/scanf` 格式串与参数类型必须匹配 | warning | cppcheck | `invalidPrintfArgType_*` |
| API-2 | 优先使用带长度限制的安全函数（snprintf 等） | style | custom-regex | `unsafe-func` |

## 七、风格与可维护性（Style & Maintainability）

| 编号 | 规则 | 严重级 | 检查方式 | 对应 id |
|------|------|--------|---------|---------|
| STYLE-1 | 使用空格缩进，不使用 Tab | style | custom-regex | `no-tab-indent` |
| COMMON-2 | 避免魔法数字，使用具名常量/宏 | style | custom-regex | `no-magic-number` |
| COMMON-3 | 提交代码不应残留 TODO/FIXME 标记 | information | custom-regex | `leftover-todo` |
| NAME-1 | 宏名应全大写、变量名小写下划线（命名约定） | style | custom-regex | `naming-macro` |

---

## 落地说明

1. **cppcheck 原生**覆盖了大部分内存/指针/初始化/运算类**高危**问题，开箱即用、误报率低。
2. **MISRA addon** 覆盖 MISRA C:2012 的结构化/类型/可移植性规则。启用方式：在 `config.json`
   的 `cppcheck.misra_addon` 填入 `checker/addons/misra.py` 的路径（规则原文受版权保护，
   addon 仅按规则编号报告）。
3. **custom-regex** 覆盖 cppcheck 难以静态判断、但靠文本模式可识别的规范（goto、魔法数字、
   命名、Tab 缩进等）。新增规范只需在 `config.json` 的 `custom_regex.rules` 加一条，**无需改代码**。

> 设计取舍：能交给静态分析器精确判断的（内存/越界）交给 cppcheck；只能近似判断的（魔法数字）
> 用正则并设较低严重级，避免误报干扰；强规范（goto）用 warning 级提醒。
