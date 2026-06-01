/* MEM-1 正例：正确释放内存，不应触发 memleak */
#include <stdlib.h>

void f(void) {
    int *p = (int *)malloc(sizeof(int) * 4);
    if (p == NULL) {
        return;
    }
    p[0] = 1;
    free(p);
}
