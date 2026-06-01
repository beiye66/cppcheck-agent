/* PTR-2 反例：数组越界访问，应触发 arrayIndexOutOfBounds */
void f(void) {
    int a[4];
    a[4] = 0;   /* 合法下标是 0..3 */
}
