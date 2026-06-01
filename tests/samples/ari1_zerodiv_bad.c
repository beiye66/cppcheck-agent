/* ARI-1 反例：除以零，应触发 zerodiv */
int f(void) {
    int x = 10;
    int y = 0;
    return x / y;
}
