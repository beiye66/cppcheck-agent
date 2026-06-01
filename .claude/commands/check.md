---
description: 对 C/C++ 文件或目录运行代码检查（cppcheck + 自定义规则），解析 JSON 结果并按需修复
argument-hint: <文件或目录路径> [--fix]
allowed-tools: Bash(python:*), Read, Edit
---

# /check —— 代码检查 Agent

你是一个代码检查 Agent。用户要检查的目标是：`$ARGUMENTS`

## 执行步骤

1. **运行检查器**（它封装了 cppcheck + 自定义规则，输出 JSON 到 stdout）。
   优先用打包好的 exe，没有则回退到 Python：

   ```bash
   # 若存在 dist/run_check.exe 则用它（无需 Python 环境）：
   dist/run_check.exe <目标路径> --report-md reports/last_check.md
   # 否则：
   python checker/run_check.py <目标路径> --report-md reports/last_check.md
   ```

   - 把 `<目标路径>` 替换为 `$ARGUMENTS` 中的路径部分（去掉 `--fix` 等开关）。
   - 退出码：0=通过，1=有问题，2=用法错误。

2. **解析 JSON**（契约见 [checker/json_schema.md](../../checker/json_schema.md)）：
   - 读 `summary` 和 `passed`。
   - 若 `passed == true`：报告"✅ 检查通过"，结束。
   - 否则：按 `severity`（error > warning > style）整理 `findings`，用清晰的中文表格汇报：严重级 / 规则 id / 文件:行 / 说明。

3. **决定后续动作**：
   - 默认**只汇报**问题，并对每条给出**修复建议**（不直接改代码）。
   - 仅当用户在参数里带了 `--fix` 时，才进入**自主修复闭环**：
     a. 对每条 finding，用 Read 打开对应 `file` 的 `line` 附近代码确认上下文；
     b. 用 Edit 做最小必要修复（修复前向用户说明改动，遵循 human-in-the-loop）；
     c. 修复完成后**重新运行检查器**确认问题消失；
     d. 重复，直到 `passed == true` **或**达到 **最多 5 轮**（防止无限循环），到达上限则停止并汇报剩余问题。

4. **产出**：最终给出本轮检查结论摘要，并指向 `reports/last_check.md` 报告文件。

## 注意

- 不要捏造 findings；一切以检查器输出的 JSON 为准。
- error 级必须优先处理；style 级可按用户偏好选择是否修。
- 若 JSON 里出现 `id: cppcheck-not-found`，提示用户 cppcheck 未安装或路径不对。
