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
test_make_palindrome()