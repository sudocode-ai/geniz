# Mutation from 'input.py'
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

import sudocode

@sudocode.CodeAgent()
def make_palindrome(s: str) -> str:

    def expandAroundCenter(left, right):
        while left >= 0 and right < len(s) and (s[left] == s[right]):
            left -= 1
            right += 1
        return right - left - 1
    mid = expandAroundCenter(0, 1)
    extra = expandAroundCenter(0, len(s) - 1)
    if mid <= 0 or (extra + mid) // 2 < 1:
        return s
    left_half_length = (extra + mid) // 2
    return s[:left_half_length] + s[::-1]
if __name__ == '__main__':
    print(make_palindrome(''))
    print(make_palindrome('cat'))
    print(make_palindrome('cata'))
