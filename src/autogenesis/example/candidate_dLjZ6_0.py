# Mutation from 'input.py'
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

import geniz


@geniz.CodeAgent()
def make_palindrome(s):
    """
    Generates the shortest palindrome by appending the reverse of the prefix to the given string with its longest palindromic suffix.
    
    Parameters:
    s (str): The input string.
    
    Returns:
    str: The resulting shortest palindrome.
    
    Example:
    >>> make_palindrome('')
    ''
    >>> make_palindrome('cat')
    'catac'
    """
    rev_tail = s[::-1]
    for i in range(len(s), 0, -1):
        if rev_tail[:i] == rev_tail[i - 1::-1]:
            palindromic_suffix = rev_tail[:i]
            remaining_prefix = s[len(palindromic_suffix):]
            return palindromic_suffix + remaining_prefix[::-1]
if __name__ == '__main__':
    print(make_palindrome(''))
    print(make_palindrome('cat'))
    print(make_palindrome('cata'))
