# Mutation from 'input.py'
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

import sudocode


def is_palindrome(s):
    """Check if a string is a palindrome."""
    return s == s[::-1]

def find_max_palindrome_suffix(s):
    """Find the longest palindromic suffix of the string from both ends."""
    start, end = (0, len(s) - 1)
    success_state = False
    while start <= end:
        str_expansion = start + 1 < end and is_palindrome(s[start:end + 1])
        rev_str_expansion = start - 1 >= 0 and is_palindrome(s[end:start - 1:-1])
        if str_expansion:
            end = end - 1
        else:
            start = start + 1
        if rev_str_expansion:
            start = start + 1
            end = end + 1
        success_state = str_expansion and (not rev_str_expansion) or success_state
    return s[start:end + 1]

@sudocode.CodeAgent()
def make_palindrome(s):
    """Create the shortest palindrome beginning with the given string."""
    if is_palindrome(s):
        return s
    suffix = find_max_palindrome_suffix(s)
    prefix_index = s.index(suffix)
    prefix = s[:prefix_index]
    reversed_prefix = prefix[::-1]
    result = reversed_prefix + suffix
    return result
assert make_palindrome('') == ''
assert make_palindrome('cat') == 'catac'
assert make_palindrome('cata') == 'catac'
assert make_palindrome('raceacar') == 'raceacarace'
