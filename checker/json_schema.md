# JSON 输出契约（v1.0）

`run_check.py` 向 stdout 输出的 JSON 是 **Agent 与检查器之间的接口**。Agent 只依赖本契约，
不关心底层用了 cppcheck 还是别的检查器。契约要版本化、向后兼容（新增字段不删旧字段）。

```jsonc
{
  "schema_version": "1.0",
  "target": "tests/samples/rule_nullptr_bad.c",
  "passed": false,                 // 是否未触发 fail_on 阈值
  "fail_on": ["error", "warning"], // 哪些严重级会判定失败
  "summary": {
    "error": 1,
    "warning": 2,
    "style": 3,
    "total": 6
  },
  "findings": [
    {
      "id": "nullPointer",         // 规则/检查项 id
      "severity": "error",          // error|warning|performance|portability|style|information
      "file": "tests/samples/rule_nullptr_bad.c",
      "line": 12,
      "column": 5,
      "message": "Null pointer dereference: p",
      "checker": "cppcheck",        // 哪个检查器产出
      "rule": "",                   // 关联编码规范条目（可选）
      "cwe": "476"                  // CWE 编号（可选）
    }
  ]
}
```

## Agent 如何消费

1. 读 `passed`：true → 报告通过，结束循环。
2. false → 遍历 `findings`，按 `file`+`line` 定位代码，按 `severity` 决定优先级。
3. 对每条提出/应用修复（需用户确认），必要时为修复补测试用例。
4. 重新调用 `/check` → 直到 `passed=true` 或达到最大轮数（防无限循环）。

## 退出码

| code | 含义 |
|------|------|
| 0 | 通过（无 fail_on 级别问题） |
| 1 | 存在 fail_on 级别问题 |
| 2 | 用法错误 / 目标不存在 |
