import logging
import os

import gradio as gr
import ray
from sudocode import auto_import, get_round_info, run_all_code_agents
from sudocode.coder import code_gen
from sudocode.round_info import get_round_info

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

os.environ['RAY_IGNORE_UNHANDLED_ERRORS'] = '1'

auto_import()


value = '''
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
'''


def gen_code():
    code_gen()


def gen_test():
    pass


def fake_gen():
    with open('candidate_dfSAs_0.py', 'r') as f:
        code_file = f.read()
    return code_file


with gr.Blocks() as demo:
    with gr.Row():
        gen_code_button = gr.Button("Generate Code", scale=0)
        gen_test_button = gr.Button("Generate Test", scale=0)
    with gr.Row():
        code_editor = gr.Code(
            value=value,
            language='python',
            label="Generated images",
            show_label=False,
            elem_id="code_editor")

    gen_code_button.click(gen_code)
    gen_test_button.click(gen_test)

if __name__ == "__main__":
    demo.launch()
