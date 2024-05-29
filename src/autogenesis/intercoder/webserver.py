import json
import logging
import os

import gradio as gr
import ray
from sudocode.coder import generate_code, generate_test, refresh_all_data, get_test_info

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


test_info = get_test_info()

with gr.Blocks() as demo:
    test_info_state = gr.State(test_info)

    def click_run_all_tests():
        print('click_run_all_tests')
        test_info = get_test_info()
        import random
        random.shuffle(test_info)
        return {
            test_info_state: test_info,
        }

    candidate_boxes = []
    test_boxes = []
    with gr.Row():
        with gr.Accordion(label='Problem Description', open=False):
            prompt_editor = gr.Code(
                value=get_prompt,
                language='python',
                show_label=False,
            )
    with gr.Row():
        gen_code_button = gr.Button("Generate Code")
        gen_test_button = gr.Button("Generate Test")
        run_all_tests_button = gr.Button("Run All Tests")
    with gr.Row(equal_height=True):
        with gr.Column():
            file_explorer = gr.FileExplorer(
                # every=2,
                glob='**/*.py',
                file_count='single',
                height=200)
            code_editor = gr.Code(
                # every=1,
                language='python',
                label="Code Editor",
                interactive=True,
                show_label=False,
                elem_id="code_editor",
                scale=3)
        with gr.Column():
            @gr.render(inputs=[test_info_state], triggers=[run_all_tests_button.click, gen_code_button.click, gen_test_button.click])
            def render_test_data(input_0):
                # with open('test_dist.json', 'r') as f:
                #     input_0 = json.load(f)
                if input_0 is None:
                    print('input_0 is None')
                    return
                for info in input_0:
                    with gr.Group():
                        with gr.Row():
                            test_box = gr.Textbox(
                                info['call_str'], show_label=False, interactive=True)
                            test_boxes.append(test_box)
                        with gr.Row():
                            output_options = info['outputs']
                            output_radio_group = gr.Radio(
                                choices=output_options,
                                value=output_options[0],
                                container=False,
                                interactive=True,
                                label='Output')
                        lock_checkbox = gr.Checkbox(label='Lock')

    gen_code_button.click(gen_code)
    gen_test_button.click(gen_test)
    run_all_tests_button.click(
        click_run_all_tests, inputs=[], outputs=[test_info_state])
    file_explorer.change(select_candidate_file, file_explorer, code_editor)
    # code_editor.change(code_editor_change, code_editor, None)
    # gr.on(triggers=None, fn=click_run_all_tests, inputs=[], every=2)
    # dep = demo.load(click_run_all_tests, inputs=[], outputs=[test_info_state], every=2)

if __name__ == "__main__":
    ray.init(include_dashboard=False, ignore_reinit_error=True)
    demo.launch()
