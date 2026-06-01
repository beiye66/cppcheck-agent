/* 演示用：故意包含多类问题的 C 文件，用于验证检查器。 */
#include <stdlib.h>
#include <string.h>

int read_value(int *p) {
    return *p;            /* 可能空指针解引用（调用方可能传 NULL） */
}

void leak_and_oob(void) {
    char *buf = (char *)malloc(10);
    buf[10] = 'x';        /* 数组越界写 */
    strcpy(buf, "this string is definitely longer than ten bytes"); /* 缓冲区溢出 */
    /* 忘记 free(buf) —— 内存泄漏 */
}

int use_uninit(void) {
    int x;
    if (x > 0) {          /* 使用未初始化变量 */
        goto done;        /* 违反 no-goto 规范 */
    }
done:
    return x + 12345;     /* 魔法数字 */
}
