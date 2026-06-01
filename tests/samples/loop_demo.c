/* 闭环演示文件：含若干问题，由 Agent 自动检查并修复。 */
#include <stdlib.h>
#include <string.h>

char *make_copy(const char *src) {
    size_t len = strlen(src) + 1;
    char *dst = (char *)malloc(len);
    if (dst == NULL) {          /* 修复: 检查 malloc 返回值 */
        return NULL;
    }
    memcpy(dst, src, len);      /* 修复: 用 memcpy 替代不安全的 strcpy */
    return dst;
}

int sum_first_n(const int *arr, int n) {
    int total = 0;              /* 修复: 初始化 */
    for (int i = 0; i < n; i++) {
        total += arr[i];
    }
    return total;
}
