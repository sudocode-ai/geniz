import sudocode
from input import make_palindrome


@sudocode.DebugAgent()
def test_make_palindrome():
    assert make_palindrome('') == ''
    print('Test with empty string passed.')
    assert make_palindrome('a') == 'aa'
    print('Test with single character string passed.')
    assert make_palindrome('racecar') == 'racecar'
    print('Test with a palindrome itself passed.')
    assert make_palindrome('ingoimm') == 'ginoming'
    print('Test with a non-palindrome string and its regular form passed.')
    assert make_palindrome('wel') == 'welwel'
    print('Test with simple concatenation case passed.')
    assert make_palindrome('he') == 'heh'
    print('Test with a palindrome of length 2 passed.')
    assert make_palindrome('d') == 'd'
    print('Test with single-character string resulting in palindrome upon append passed.')
    print('All tests passed.')
test_make_palindrome()