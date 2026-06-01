/* CTRL-1 反例：使用 goto，应触发自定义规则 no-goto */
int f(int n) {
    if (n < 0) {
        goto fail;
    }
    return n;
fail:
    return -1;
}
