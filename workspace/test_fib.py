import pytest
from fib import fib


class TestFib:
    def test_fib_0(self):
        assert fib(0) == 0

    def test_fib_1(self):
        assert fib(1) == 1

    def test_fib_2(self):
        assert fib(2) == 1

    def test_fib_5(self):
        assert fib(5) == 5

    def test_fib_10(self):
        assert fib(10) == 55

    def test_fib_negative_raises(self):
        with pytest.raises(ValueError):
            fib(-1)