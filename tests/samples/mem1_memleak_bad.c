/* MEM-1 反例：分配内存后未释放，应触发 memleak */
#include <stdlib.h>

void f(void) {
    int *p = (int *)malloc(sizeof(int) * 4);
    p[0] = 1;
    /* 缺少 free(p) */
}
