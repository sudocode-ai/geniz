# Mutation from 'input.py'
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

import sudocode


@sudocode.CodeAgent()
def make_palindrome(s: str) -> str:
    """
    Finds the shortest palindrome starting with the given string.
    
    The approach used is to append the reverse of the remaining part of the string, if any, to itself.
    This way, the resulting string is guaranteed to be a palindrome.

    Example:
    >>> make_palindrome('cat')
    'catactac'

    Notes:
    - For null string, it returns an empty string.
    - If the input is already a palindrome, it is returned as is.
    
    Args:
    s (str): Input string.

    Returns:
    str: The shortest palindrome starting with the given string.
    """
    if s == s[::-1]:
        return s
    else:
        return s + (s[::-1] if s != '' else '')
print(make_palindrome(''))
print(make_palindrome('cat'))
print(make_palindrome('cata'))
