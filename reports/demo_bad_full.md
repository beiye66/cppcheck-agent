# 代码检查报告 — ❌ FAIL

- 目标: `tests/samples/demo_bad.c`
- 失败阈值 (fail_on): error, warning
- 汇总: 共 12 项（error 4 / warning 7 / style 1）

| 严重级 | 规则 id | 文件:行 | 说明 |
|--------|---------|---------|------|
| error | arrayIndexOutOfBounds | demo_bad.c:11 | Array 'buf[10]' accessed at index 10, which is out of bounds. |
| error | bufferAccessOutOfBounds | demo_bad.c:12 | Buffer is accessed out of bounds: buf |
| error | memleak | demo_bad.c:14 | Memory leak: buf |
| error | uninitvar | demo_bad.c:18 | Uninitialized variable: x |
| warning | nullPointerOutOfMemory | demo_bad.c:11 | If memory allocation fails, then there is a possible null pointer dereference: buf |
| warning | clang-analyzer-security.ArrayBound | demo_bad.c:11 | Out of bound access to memory after the end of the heap area |
| warning | nullPointerOutOfMemory | demo_bad.c:12 | If memory allocation fails, then there is a possible null pointer dereference: buf |
| warning | unsafe-func | demo_bad.c:12 | 使用了不安全的库函数，建议改用带长度限制的安全版本。 |
| warning | clang-analyzer-security.insecureAPI.strcpy | demo_bad.c:12 | Call to function 'strcpy' is insecure as it does not provide bounding of the memory buffer. Replace unbounded copy functions with analogous functions that support length arguments such as 'strlcpy'. CWE-119 |
| warning | clang-analyzer-core.UndefinedBinaryOperatorResult | demo_bad.c:18 | The left operand of '>' is a garbage value |
| warning | no-goto | demo_bad.c:19 | 禁止使用 goto（MISRA Rule 15.1）。 |
| style | constParameterPointer | demo_bad.c:5 | Parameter 'p' can be declared as pointer to const |
