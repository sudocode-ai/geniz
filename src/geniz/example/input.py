import geniz
from typing import List

@geniz.CodeAgent()
def longestPalindrome(s: str) -> str:
    """Given a string s, return the longest palindromic substring in s.
    
    Example 1:
      Input: s = "babad"
      Output: "bab"
      Explanation: "aba" is also a valid answer.
      
    Example 2:
      Input: s = "cbbd"
      Output: "bb"

    Constraints:
      1 <= s.length <= 1000
      s consist of only digits and English letters.
    """