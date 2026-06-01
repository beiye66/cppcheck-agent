# 代码检查报告 — ❌ FAIL

- 目标: `tests\samples\demo_bad.c`
- 失败阈值 (fail_on): error, warning
- 汇总: 共 11 项（error 4 / warning 3 / style 4）

| 严重级 | 规则 id | 文件:行 | 说明 |
|--------|---------|---------|------|
| error | arrayIndexOutOfBounds | demo_bad.c:11 | Array 'buf[10]' accessed at index 10, which is out of bounds. |
| error | bufferAccessOutOfBounds | demo_bad.c:12 | Buffer is accessed out of bounds: buf |
| error | memleak | demo_bad.c:14 | Memory leak: buf |
| error | uninitvar | demo_bad.c:18 | Uninitialized variable: x |
| warning | nullPointerOutOfMemory | demo_bad.c:11 | If memory allocation fails, then there is a possible null pointer dereference: buf |
| warning | nullPointerOutOfMemory | demo_bad.c:12 | If memory allocation fails, then there is a possible null pointer dereference: buf |
| warning | no-goto | demo_bad.c:19 | 禁止使用 goto（结构化编程规范 / MISRA Rule 15.1）。 |
| style | constParameterPointer | demo_bad.c:5 | Parameter 'p' can be declared as pointer to const |
| style | no-magic-number | demo_bad.c:10 | 疑似魔法数字，建议用具名常量/宏替代。 |
| style | no-magic-number | demo_bad.c:11 | 疑似魔法数字，建议用具名常量/宏替代。 |
| style | no-magic-number | demo_bad.c:22 | 疑似魔法数字，建议用具名常量/宏替代。 |
