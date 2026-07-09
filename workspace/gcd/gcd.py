def gcd(a: int, b: int) -> int:
    """计算两个整数的最大公因数 (Greatest Common Divisor)"""
    a, b = abs(a), abs(b)
    while b != 0:
        a, b = b, a % b
    return a