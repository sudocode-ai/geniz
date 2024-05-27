import sudocode
from input import make_palindrome


@sudocode.DebugAgent()
def test_make_palindrome():
    assert make_palindrome('') == ''
    assert make_palindrome('cat') == 'catac'
    assert make_palindrome('ai') == 'iai'
    assert make_palindrome('Hello') == 'HellolleH'
    assert make_palindrome('A!') == 'A!'
    assert make_palindrome('1#!') == '1#!1#'
    assert make_palindrome('hello world!') == '!ollehdlrowolleh'
    assert make_palindrome('a') == 'a'
    assert make_palindrome('aba') == 'ababa'
    import random
    import string
    long_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=50))
    palindrome_length = len(long_str) // 4
    assert make_palindrome(long_str) == long_str[:palindrome_length] + long_str[::-1]
test_make_palindrome()