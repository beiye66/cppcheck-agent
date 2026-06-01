/* VAR-1 反例：使用未初始化变量，应触发 uninitvar */
int f(void) {
    int x;
    return x + 1;
}
