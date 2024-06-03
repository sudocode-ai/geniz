# Mutation from 'input.py'
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

import sudocode


@sudocode.CodeAgent()
def make_palindrome(s: str) -> str:
    """Find the shortest palindrome that begins with a supplied string."""
    if s == '' or s == ' ' or s == ' ':
        return ''
    if len(s) < 2:
        return s + s[::-1][1:]
    n = len(s)
    rev_suf = s[::-1]
    l = 1
    while l < n - 1:
        if s[l] == rev_suf[n - 1 - l]:
            l += 1
        else:
            break
    p = s[:l]
    front_start = l
    reverse_needed_portion = s[l:]
    return p + reverse_needed_portion[::-1] if reverse_needed_portion else s
print(make_palindrome(''))
print(make_palindrome('cat'))
print(make_palindrome('cata'))
