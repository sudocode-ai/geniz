import json
import logging
import os

import gradio as gr
import ray
from sudocode.coder import (generate_code, generate_test,
                            get_test_and_candidate_info, refresh_all_data)

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

os.environ['RAY_IGNORE_UNHANDLED_ERRORS'] = '1'


if gr.NO_RELOAD:
    ray.init(include_dashboard=False, ignore_reinit_error=True)


def get_original_problem_prompt():
    with open('input.py', 'r') as f:
        code_file = f.read()
    return code_file


test_info, candidate_info = get_test_and_candidate_info()


_CSS = '''
.test_entry {background-color: red}
'''

with gr.Blocks(css=_CSS) as demo:
    candidate_info_state = gr.State(candidate_info)
    test_info_state = gr.State(test_info)

    def click_run_all_tests():
        test_info, candidate_info = get_test_and_candidate_info()
        return {
            candidate_info_state: candidate_info,
            test_info_state: test_info,
        }

    def click_gen_code():
        generate_code()
        test_info, candidate_info = get_test_and_candidate_info()
        return {
            candidate_info_state: candidate_info,
            test_info_state: test_info,
        }

    def click_gen_test():
        generate_test()
        test_info, candidate_info = get_test_and_candidate_info()
        return {
            candidate_info_state: candidate_info,
            test_info_state: test_info,
        }

    with gr.Row():
        with gr.Accordion(label='Problem Description', open=False):
            prompt_editor = gr.Code(
                value=get_original_problem_prompt,
                language='python',
                show_label=False,
                interactive=True,
            )
    with gr.Row():
        gen_code_button = gr.Button("Generate Code")
        gen_test_button = gr.Button("Generate Test")
        run_all_tests_button = gr.Button("Run All Tests")
    with gr.Row(equal_height=True):
        with gr.Column():
            @gr.render(inputs=[candidate_info_state])
            def render_candidate_data(input_0):
                for i, candidate_info in enumerate(input_0):
                    candidate = candidate_info['candidate']
                    score = candidate_info['score']
                    with gr.Accordion(label=f'{candidate.id}  [score: {score}]', open=(i == 0)):
                        code_editor = gr.Code(
                            value=candidate.clean_source_code,
                            language='python',
                            interactive=True,
                            show_label=False)
        with gr.Column():
            @gr.render(inputs=[test_info_state])
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
                        with gr.Row():
                            output_options = info['outputs']
                            output_radio_group = gr.Radio(
                                choices=output_options,
                                value=output_options[0],
                                container=False,
                                interactive=True,
                                label='Output')
                        lock_checkbox = gr.Checkbox(label='Lock')

                        def output_radio_group_trigger(input_0):
                            this_info = info
                            print(
                                f'output_radio_group_trigger: {input_0}, {this_info}')
                        output_radio_group.change(
                            output_radio_group_trigger, inputs=[output_radio_group])

                        def lock_checkbox_trigger(input_0):
                            this_info = info
                            print(
                                f'lock_check_trigger: {input_0}, {this_info}')
                        lock_checkbox.change(
                            lock_checkbox_trigger, inputs=[lock_checkbox])

    gen_code_button.click(click_gen_code, inputs=[], outputs=[
                          candidate_info_state, test_info_state])
    gen_test_button.click(click_gen_test, inputs=[], outputs=[
                          candidate_info_state, test_info_state])
    run_all_tests_button.click(
        click_run_all_tests, inputs=[], outputs=[candidate_info_state, test_info_state])
    # code_editor.change(code_editor_change, code_editor, None)
    # gr.on(triggers=None, fn=click_run_all_tests, inputs=[], every=2)
    # dep = demo.load(click_run_all_tests, inputs=[], outputs=[test_info_state], every=2)

if __name__ == "__main__":
    demo.launch()
