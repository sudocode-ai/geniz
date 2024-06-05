import copy
import logging
import os
from functools import partial

import gradio as gr
import ray
from sudocode.coder import (generate_code, generate_test,
                            get_test_and_candidate_info, load_locked_tests,
                            save_locked_tests)

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


test_info, candidate_info, locked_tests = get_test_and_candidate_info()


_CSS = '''
.locked {
    border-color: green;
}
'''

with gr.Blocks(css=_CSS) as demo:
    candidate_info_state = gr.State(candidate_info)
    test_info_state = gr.State(test_info)
    locked_tests_state = gr.State(locked_tests)

    def click_run_all_tests():
        test_info, candidate_info, locked_tests = get_test_and_candidate_info()
        return {
            candidate_info_state: candidate_info,
            test_info_state: test_info,
            locked_tests_state: locked_tests,
        }

    def click_gen_code():
        generate_code()
        test_info, candidate_info, locked_tests = get_test_and_candidate_info()
        return {
            candidate_info_state: candidate_info,
            test_info_state: test_info,
            locked_tests_state: locked_tests,
        }

    def click_gen_test():
        generate_test()
        test_info, candidate_info, locked_tests = get_test_and_candidate_info()
        return {
            candidate_info_state: candidate_info,
            test_info_state: test_info,
            locked_tests_state: locked_tests,
        }

    with gr.Row():
        with gr.Accordion(label='Problem Description', open=False):
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
                if input_0 is None:
                    print('input_0 is None')
                    return
                for info in input_0:
                    default_output_str = info['default_output_str']
                    default_call_str = info['default_call_str']
                    locked = info['locked']
                    elem_id = info['id']
                    elem_classes = []
                    if locked:
                        elem_classes.append('locked')
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

                        def output_radio_group_trigger(this_info, selected_output, locked_tests):
                            # TODO: color change for candidate boxes
                            output_info = this_info['outputs_info'].get(
                                selected_output, None)
                            if output_info is None or len(output_info) == 0:
                                return this_info['default_call_str'], locked_tests
                            if this_info['input'] in locked_tests:
                                if selected_output != locked_tests[this_info['input']]:
                                    locked_tests[this_info['input']] = selected_output
                                    save_locked_tests(locked_tests)
                            return output_info[0]['call_str'], locked_tests

                        output_radio_group.change(
                            partial(output_radio_group_trigger, copy.copy(info)),
                            inputs=[output_radio_group, locked_tests_state],
                            outputs=[test_box, locked_tests_state])

                        def lock_checkbox_trigger(this_info, true_or_false, selected_output, locked_tests):
                            if true_or_false is True:
                                locked_tests[this_info['input']] = selected_output
                            else:
                                locked_tests.pop(this_info['input'], None)
                            save_locked_tests(locked_tests)
                            return candidate_info, locked_tests

                        lock_checkbox.change(
                            partial(lock_checkbox_trigger, copy.copy(info)),
                            inputs=[lock_checkbox, output_radio_group, locked_tests_state],
                            outputs=[candidate_info_state, locked_tests_state],
                            js='''(x, y, z) => {
    var element = document.getElementById("''' + str(elem_id) + '''");
    if (x) {
        element.classList.add("locked");
    } else {
        element.classList.remove("locked");
    }
    return [x, y, z];
}
''')

    gen_code_button.click(click_gen_code, inputs=None, outputs=[
                          candidate_info_state, test_info_state, locked_tests_state])
    gen_test_button.click(click_gen_test, inputs=None, outputs=[
                          candidate_info_state, test_info_state, locked_tests_state])
    run_all_tests_button.click(
        click_run_all_tests, inputs=None, outputs=[candidate_info_state, test_info_state, locked_tests_state])
    # code_editor.change(code_editor_change, code_editor, None)
    # gr.on(triggers=None, fn=click_run_all_tests, inputs=[], every=2)
    # dep = demo.load(click_run_all_tests, inputs=[], outputs=[test_info_state], every=2)

if __name__ == "__main__":
    demo.launch(debug=True)
