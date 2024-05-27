import logging
import os
import pickle

import isort

from .llm import query_llm
from .python_code import PythonCode
from .util import alphanumeric_uuid, load_prompt

TEST_DESIGNER_PROMPT = load_prompt(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "prompts/test_designer_prompt_simple.yaml",
    )
)


def create_test_file(source_filename, function_name, source_code) -> bool:
    source_error_filename = f'{source_filename}.error'
    module_name = source_filename.removesuffix('.py')
    new_id = str(alphanumeric_uuid()[-5:])
    output_filename = f'{module_name}_{new_id}_test.py'

    # Skip the submitted result.
    if source_filename == 'output.py':
        return False
    # Skip if original program already contains error
    # Maybe add another fixer here.
    if os.path.exists(source_error_filename):
        os.system(f'rm {source_error_filename}*')
        return False
    if os.path.exists(output_filename):
        return False

    logging.info(
        f'TestDesigner: generating {output_filename} for {function_name} in {source_filename}...')

    system_message = TEST_DESIGNER_PROMPT.format(
        function_name=function_name, input_code_snippet=source_code)
    message = f'''Please generate test cases for following code, and add "from {module_name} import {function_name}" in top and assume {function_name} is already defined in {module_name}.
```python
{source_code}
```

Test case is like:
```python
def test_{function_name}():
  assert xxxx
  assert xxxx
  ...
```
'''
    replys, histories = query_llm(message, system_message=system_message, filename=output_filename)
    for i, reply in enumerate(replys):
        test_code = PythonCode.extract_test_case_code_block_from_full_reply(
            reply, function_name=function_name)
        if not test_code.valid():
            logging.info(f'Test case is invalid:\n\n{test_code.code_text}')
            return False
        test_case_filename = f'{module_name}_{new_id}_{i}_test.py'
        with open(test_case_filename, 'w') as f:
            code_text = f'from {module_name} import {function_name}\n{test_code.code_text}'
            f.write(code_text)
            logging.info(f'Wrote to {test_case_filename}')
        isort.file(test_case_filename)
        new_history_filename = f'{test_case_filename}.history.pickle'
        with open(new_history_filename, 'wb') as f:
            pickle.dump(histories[i], f)
            logging.info(f'Wrote to {new_history_filename}')
    return True
