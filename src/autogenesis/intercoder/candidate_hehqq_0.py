# Mutation from 'input.py'
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

import sudocode


def find_longest_palindromic_suffix(s: str) -> (str, int):
    """Finds the longest palindromic suffix of the given string."""
    for length in range(len(s), -1, -1):
        if is_palindrome(s[:length]):
            return (s[:length], length)
    return ('', 0)

@sudocode.CodeAgent()
def make_palindrome(s: str) -> str:
    """Make the shortest palindrome beginning with the given string."""
    suffix, suffix_length = find_longest_palindromic_suffix(s)
    return s + suffix[::-1] if suffix_length > 0 else s

def is_palindrome(s: str) -> bool:
    """Check if the given string is a palindrome."""
    return s == s[::-1]
if __name__ == '__main__':
    assert make_palindrome('') == ''
    assert make_palindrome('cat') == 'catac'
    assert make_palindrome('cata') == 'cata'
    assert make_palindrome('racecar') == 'racecar'
    print('All tests passed!')
