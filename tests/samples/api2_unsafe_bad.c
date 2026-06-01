/* API-2 反例：使用不安全的 strcpy，应触发自定义规则 unsafe-func */
#include <string.h>

void f(char *dst, const char *src) {
    strcpy(dst, src);
}
