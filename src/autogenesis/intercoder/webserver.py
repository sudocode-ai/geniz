import logging
import os

import gradio as gr
import ray
from sudocode import auto_import, get_round_info, run_all_code_agents
from sudocode.coder import generate_code, generate_test
from sudocode.round_info import get_round_info

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

os.environ['RAY_IGNORE_UNHANDLED_ERRORS'] = '1'


def gen_code():
    generate_code()


def gen_test():
    generate_test()


def select_candidate_file(filepath):
    with open(filepath, 'r') as f:
        code_file = f.read()
    return code_file


def get_prompt():
    with open('input.py', 'r') as f:
        code_file = f.read()
    return code_file


with gr.Blocks() as demo:
    with gr.Row():
        with gr.Accordion(label='Problem Description', open=False):
            prompt_editor = gr.Code(
                value=get_prompt,
                language='python',
                show_label=False,
            )
    with gr.Row():
        gen_code_button = gr.Button("Generate Code", scale=0)
        gen_test_button = gr.Button("Generate Test", scale=0)
    with gr.Row():
        with gr.Column():
            file_explorer = gr.FileExplorer(
                every=2,
                glob='**/*.py',
                file_count='single',
                scale=0)
            code_editor = gr.Code(
                # every=1,
                language='python',
                label="Code Editor",
                interactive=True,
                show_label=False,
                elem_id="code_editor",
                scale=3)
        with gr.Column():
            textboxes = []
            for i in range(10):
                with gr.Group():
                    t = gr.Textbox(f"Textbox {i}", show_label=False)
                    textboxes.append(t)
                    c = gr.Checkbox()

    gen_code_button.click(gen_code)
    gen_test_button.click(gen_test)
    file_explorer.change(select_candidate_file, file_explorer, code_editor)
    # code_editor.change(code_editor_change, code_editor, None)

if __name__ == "__main__":
    ray.init(include_dashboard=False, ignore_reinit_error=True)
    demo.launch()
