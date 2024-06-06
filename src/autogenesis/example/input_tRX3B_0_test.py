import geniz
from input import make_palindrome


@geniz.DebugAgent()
def test_make_palindrome():
    assert make_palindrome('') == ''
    assert make_palindrome('cat') == 'catac'
    assert make_palindrome('tac') == 'tac'
    assert make_palindrome('abba') == 'abbaab'
    assert make_palindrome('abcd') == 'dccba'
    assert make_palindrome('abccba') == 'abccbac'
    assert make_palindrome('race') == 'ecarace'
    assert make_palindrome('programming') == 'mnangrommargopgnir'
    assert make_palindrome('noon') == 'noonno'
    assert make_palindrome('cyclist') == 'ticsyrclitcy'
    assert make_palindrome('123454321') == '1234532431'
    assert make_palindrome('education') == 'noitoracedu'
    assert make_palindrome('a') == 'a'
    assert make_palindrome('ab') == 'baab'
    assert make_palindrome('break') == 'ekiribarb'
    assert make_palindrome('ballet') == 'elttalabeltabel'
    assert make_palindrome('abcdef') == 'fedcbaabcdef'
    assert make_palindrome('aabsnrvsd') == 'vsdrnsabarsn'
    print('All test cases passed!')
from input import make_palindrome

test_make_palindrome()
