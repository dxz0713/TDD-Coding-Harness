import pytest
from gcd import gcd


def test_gcd_basic():
    assert gcd(12, 8) == 4
    assert gcd(8, 12) == 4
    assert gcd(100, 25) == 25


def test_gcd_coprime():
    assert gcd(7, 13) == 1
    assert gcd(17, 19) == 1


def test_gcd_same_number():
    assert gcd(10, 10) == 10
    assert gcd(7, 7) == 7


def test_gcd_with_zero():
    assert gcd(0, 5) == 5
    assert gcd(5, 0) == 5
    assert gcd(0, 0) == 0


def test_gcd_with_one():
    assert gcd(1, 5) == 1
    assert gcd(5, 1) == 1


def test_gcd_negative():
    assert gcd(-12, 8) == 4
    assert gcd(12, -8) == 4
    assert gcd(-12, -8) == 4


def test_gcd_large_numbers():
    assert gcd(123456, 7890) == 6
    assert gcd(10**9, 10**6) == 10**6