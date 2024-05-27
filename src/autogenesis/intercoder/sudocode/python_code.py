import ast
from typing import Optional

from pydantic import BaseModel


_CODE_AGENT_DECORATOR = ast.Call(
    func=ast.Attribute(
        value=ast.Name(id='sudocode', ctx=ast.Load()),
        attr='CodeAgent',
        ctx=ast.Load()),
    args=[],
    keywords=[])


_DEBUG_AGENT_DECORATOR = ast.Call(
    func=ast.Attribute(
        value=ast.Name(id='sudocode', ctx=ast.Load()),
        attr='DebugAgent',
        ctx=ast.Load()),
    args=[],
    keywords=[])


def maybe_add_decorators(tree: ast.Module, function_name: Optional[str] = None) -> bool:
    has_func_def = False
    tree.body.insert(0, ast.Import(names=[ast.alias(name='sudocode')]))
    for statement in reversed(tree.body):
        if isinstance(statement, ast.FunctionDef):
            if statement.name.startswith('test_'):
                statement.decorator_list = [_DEBUG_AGENT_DECORATOR]
            else:
                if function_name:
                    if statement.name == function_name:
                        has_func_def = True
                        statement.decorator_list = [_CODE_AGENT_DECORATOR]
    return has_func_def


def find_longest_code_block(text, function_name: Optional[str] = None, require_func_def = False):
    # May generate several code blocks, alwasy choose the longest.
    code_block_starters = text.split('```python')
    code_blocks = []
    for starter in code_block_starters:
        try:
            code_block = starter.split('```')[0]
            # Valid only if be able to parse it.
            # We assume only to generate function for now.
            tree = ast.parse(code_block)
            has_func_def = maybe_add_decorators(tree, function_name)
            if require_func_def:
                if not has_func_def:
                    continue
            code_block = ast.unparse(tree)
        except:
            continue
        code_blocks.append(code_block)
    return max(code_blocks, key=lambda x: len(x))


class PythonCode(BaseModel):
    # Code snippet.
    code_text: Optional[str] = None
    # Exception string if error from parsing
    parsing_error: Optional[str] = None

    def valid(self) -> bool:
        return self.code_text is not None

    @classmethod
    def extract_main_program_code_block_from_full_reply(
        cls,
        full_reply: str,
        function_name: Optional[str] = None
    ) -> "PythonCode":
        """Extract and validate the code block from replied texts."""
        try:
            code_gen_section = full_reply
            # May generate several code blocks, alwasy choose the longest.
            code_block_text = find_longest_code_block(
                code_gen_section, function_name=function_name, require_func_def=True)
            return cls(code_text=code_block_text)
        except Exception as e:
            return cls(code_text=None, parsing_error=str(e))

    @classmethod
    def extract_test_case_code_block_from_full_reply(
        cls,
        full_reply: str,
        function_name: Optional[str] = None
    ) -> "PythonCode":
        """Extract and validate test case code block from replied texts."""
        try:
            # May generate several code blocks, alwasy choose the longest.
            code_block_text = find_longest_code_block(
                full_reply, function_name=function_name)
            return cls(code_text=code_block_text)
        except Exception as e:
            return cls(code_text=None, parsing_error=str(e))


_TEST_CODE = '''
def make_palindrome(string: str) -> str:
    """ Find the shortest palindrome that begins with a supplied string.
    Algorithm idea is simple:
    - Find the longest postfix of supplied string that is a palindrome.
    - Append to the end of the string reverse of a string prefix that comes before the palindromic suffix.
    >>> make_palindrome('')
    ''
    >>> make_palindrome('cat')
    'catac'
    >>> make_palindrome('cata')
    'catac'
    """
    postfix = string[::-1]  # Reverse the string
    for i in range(len(string)):
        if string[:len(string)-i] == postfix[i:]:
            return string + string[:i][::-1]
    return ''

print(make_palindrome(""))
print(make_palindrome("cat"))
print(make_palindrome("cata"))
'''


def test_parse_and_add_decorator():
    tree = ast.parse(_TEST_CODE)
    maybe_add_decorators(tree)
    print(ast.unparse(tree))


if __name__ == '__main__':
    test_parse_and_add_decorator()
