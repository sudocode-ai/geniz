import copy
import json
import logging
import os
from functools import partial

import gradio as gr
import ray

from geniz.coder import (generate_code, generate_test,
                         get_test_and_candidate_info, save_locked_tests)

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

os.environ['RAY_IGNORE_UNHANDLED_ERRORS'] = '1'

if os.path.exists('keys.json'):
    with open('keys.json', 'r') as f:
        cfg = json.load(f)
        for i in cfg:
            os.environ[i] = cfg[i]


if gr.NO_RELOAD:
    ray.init(include_dashboard=False, ignore_reinit_error=True)


def get_original_problem_prompt():
    with open('input.py', 'r') as f:
        code_file = f.read()
    return code_file


initial_app_state = get_test_and_candidate_info()


_CSS = '''
.test_case_container {
    border-width: medium;
}

.test_case_locked {
    border-color: green;
}
'''

with gr.Blocks(css=_CSS, title='Geniz') as demo:
    app_state = gr.State(initial_app_state)

    def click_run_all_tests():
        return get_test_and_candidate_info()

    def click_gen_code():
        generate_code()
        return get_test_and_candidate_info()

    def click_gen_test():
        generate_test()
        return get_test_and_candidate_info()

    with gr.Row():
        with gr.Accordion(label='LLM settings', open=True):
            with gr.Row():
                api_base_box = gr.Textbox(
                    os.getenv('API_BASE', 'https://geniz.ai/v1'), label='API_BASE', interactive=True)
                api_key_box = gr.Textbox(
                    os.getenv('API_KEY', ''), label='API_KEY', type='password', interactive=True)
                model_box = gr.Textbox(
                    os.getenv('MODEL', 'openai/Phi-3-mini-128k-instruct-a100'), label='MODEL', interactive=True)
                batch_inference_n = gr.Dropdown(
                    [1, 3, 5, 10], value=3, label='Batch Inference', interactive=True)

            def change_api_base(input):
                os.environ['API_BASE'] = input
            api_base_box.input(change_api_base, inputs=[api_base_box])

            def change_api_key(input):
                os.environ['API_KEY'] = input
            api_key_box.input(change_api_key, inputs=[api_key_box])

            def change_model(input):
                os.environ['MODEL'] = input
            model_box.input(change_model, inputs=[model_box])

            def change_batch_inference(input):
                os.environ['BATCH_INFERENCE_N'] = input
            batch_inference_n.input(
                change_batch_inference, inputs=[batch_inference_n])

    with gr.Row():
        with gr.Accordion(label='Problem Description', open=True):
            prompt_editor = gr.Code(
                value=get_original_problem_prompt,
                language='python',
                show_label=False,
                interactive=True,
            )

    gr.Markdown("---")
    with gr.Row():
        gen_code_button = gr.Button("Generate Code")
        gen_test_button = gr.Button("Generate Test")
        run_all_tests_button = gr.Button("Run All Tests")

    @gr.render(inputs=[app_state])
    def render_app(this_app_state):
        with gr.Row(equal_height=True):
            with gr.Column():
                all_candidate_info = this_app_state['candidate_info']
                for i, candidate_info in enumerate(all_candidate_info):
                    candidate_id = candidate_info['candidate_id']
                    candidate = candidate_info['candidate']
                    tests_score = candidate_info['tests_score']
                    stars = '⭐' * tests_score
                    with gr.Accordion(label=f'{candidate_id} {stars}',
                                      open=False):
                        with gr.Row():
                            code_editor = gr.Code(
                                value=candidate.clean_source_code,
                                language='python',
                                interactive=True,
                                show_label=False)
                        for test_id, test_call_str in candidate_info['passed_tests'].items():
                            with gr.Row():
                                gr.Text(f'✅ {test_call_str}', show_label=False)
                        for test_id, test_call_str in candidate_info['failed_tests'].items():
                            with gr.Row():
                                gr.Text(f'❌ {test_call_str}', show_label=False)
                        with gr.Row():
                            delete_button = gr.Button('Delete', scale=0)

                            def click_delete_button(this_candidate_info, this_app_state):
                                this_candidate_id = this_candidate_info['candidate_id']
                                this_candidate = this_candidate_info['candidate']
                                this_candidate.delete()
                                all_candidate_info = this_app_state['candidate_info']
                                this_app_state['candidate_info'] = [c for c in all_candidate_info if c['candidate_id'] != this_candidate_id]
                                return this_app_state
                            delete_button.click(partial(click_delete_button, copy.copy(candidate_info)),
                                                inputs=[app_state], outputs=app_state)
            with gr.Column():
                for info in this_app_state['test_info']:
                    default_output_str = info['default_output_str']
                    default_call_str = info['default_call_str']
                    locked = info['locked']
                    elem_id = info['id']
                    elem_classes = ['test_case_container']
                    if locked:
                        elem_classes.append('test_case_locked')
                    with gr.Group(elem_id=elem_id, elem_classes=elem_classes):
                        with gr.Row():
                            test_box = gr.Textbox(
                                default_call_str, show_label=False, interactive=True)
                        with gr.Row():
                            output_options = info['outputs']
                            output_radio_group = gr.Radio(
                                choices=output_options,
                                value=default_output_str,
                                container=False,
                                interactive=True,
                                label='Output Values')
                        lock_checkbox = gr.Checkbox(label='Lock', value=locked)

                        def output_radio_group_trigger(this_info, selected_output, this_app_state):
                            locked_tests = this_app_state['locked_tests']
                            output_info = this_info['outputs_info'].get(
                                selected_output, None)
                            if output_info is None or len(output_info) == 0:
                                return this_info['default_call_str'], this_app_state
                            if this_info['input'] in locked_tests:
                                if selected_output != locked_tests[this_info['input']]:
                                    locked_tests[this_info['input']
                                                 ] = selected_output
                                    save_locked_tests(locked_tests)
                            return output_info[0]['call_str'], this_app_state

                        output_radio_group.change(
                            partial(output_radio_group_trigger,
                                    copy.copy(info)),
                            inputs=[output_radio_group, app_state],
                            outputs=[test_box, app_state])

                        def lock_checkbox_trigger(this_info, true_or_false, selected_output):
                            locked_tests =  this_app_state['locked_tests']
                            if true_or_false is True:
                                locked_tests[this_info['input']
                                             ] = selected_output
                                save_locked_tests(locked_tests)
                            else:
                                locked_tests.pop(this_info['input'], None)
                                save_locked_tests(locked_tests)

                        lock_checkbox.change(
                            partial(lock_checkbox_trigger, copy.copy(info)),
                            inputs=[lock_checkbox, output_radio_group],
                            outputs=None,
                            js='''(x, y) => {
    var element = document.getElementById("''' + str(elem_id) + '''");
    if (x) {
        element.classList.add("test_case_locked");
    } else {
        element.classList.remove("test_case_locked");
    }
    return [x, y];
}
''')

    gen_code_button.click(click_gen_code, inputs=None, outputs=app_state)
    gen_test_button.click(click_gen_test, inputs=None, outputs=app_state)
    run_all_tests_button.click(click_run_all_tests, inputs=None, outputs=app_state)
    # code_editor.change(code_editor_change, code_editor, None)
    # gr.on(triggers=None, fn=click_run_all_tests, inputs=[], every=2)
    # dep = demo.load(click_run_all_tests, inputs=[], outputs=[test_info_state], every=2)

if __name__ == "__main__":
    demo.launch(debug=True)
