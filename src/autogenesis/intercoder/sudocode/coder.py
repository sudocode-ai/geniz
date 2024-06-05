from collections import defaultdict
import functools
import inspect
import json
import logging
import os
import pickle
import random
from pathlib import Path
from typing import Callable, List, Optional
from unittest.mock import MagicMock

import isort
import ray
from pydantic import BaseModel

from .auto_import import auto_import
from .data_collector import (DataPoint, calculate_candidates_stats_scores,
                             get_candidate_input_output, get_data_collector,
                             get_test_dist, is_data_collection_mode, get_data_dist,
                             reduce_to_most_frequent_answer, datapoint_to_input_output_str)
from .debugger import get_all_test_cases
from .llm import ChatMessage, query_llm
from .python_code import PythonCode
from .round_info import get_round_info
from .test_designer import create_test_file
from .util import (PersistStateToFile, alphanumeric_uuid, entropy_list,
                   load_prompt, make_function_call_statement_str,
                   shorten_answer, shorten_list)
from .data_collector import DATA_DIST



_INPUT = 'input.py'
_OUTPUT = 'output.py'

_REGISTRY = dict()

PROGRAMMER_PROMPT = load_prompt(
    os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "prompts/programmer_prompt_simple.yaml",
    )
)


@ray.remote
def _execute_remote(function_obj, candidate_id, *args, **kwargs):
    print(f'remotely execute {candidate_id}, input={shorten_answer(args)}')
    try:
        ret = function_obj(*args, **kwargs)
    except Exception as e:
        ret = e
    dp = DataPoint(input=args, output=ret, candidate=candidate_id)

    # Check serializable.
    try:
        ray.put(dp)
        return dp
    except:
        pass
    return None


class CodeAgentState(BaseModel, PersistStateToFile):
    function_obj: Callable
    source_code: str
    source_filename: str
    function_name: str

    @property
    def id(self) -> str:
        return f'{self.function_name}({self.source_filename})'

    @property
    def clean_source_code(self) -> str:
        """Without decorator."""
        clean_source_code = self.source_code
        clean_source_code = clean_source_code.replace(
            '@sudocode.CodeAgent()', '')
        clean_source_code = clean_source_code.replace(
            '@sudocode.CodeAgent', '')
        clean_source_code = clean_source_code.replace(
            '@sudocode.DebugAgent()', '')
        clean_source_code = clean_source_code.replace(
            '@sudocode.DebugAgent', '')
        return clean_source_code

    @property
    def module_name(self) -> str:
        return self.source_filename.removesuffix('.py')

    def load_previous_history(self) -> List[ChatMessage]:
        history_filename = Path(f'{self.source_filename}.history.pickle')
        if history_filename.exists():
            return pickle.loads(history_filename.read_bytes())
        return []

    def debug_str(self):
        return self.id

    def debug_oracle_pass(self):
        """Eval if passing against the dataset ground-truth.

        CAUTION: only print in logging to help development. Use this information to code-gen is CHEATING.
        """
        try:
            import eval_output
            eval_output.check(self.function_obj)
        except:
            return False
        return True

    def call_and_record_data_remotely(self, *args, **kwargs):
        return _execute_remote.remote(self.function_obj, self.id, *args, *kwargs)

    def is_genesis(self) -> bool:
        return self.source_filename == _INPUT

    def delete(self):
        logging.info(f'=== Delete {self.id}')
        os.system(f'rm {self.source_filename}*')

    def submit(self):
        final_source_code = f'''# Submitted from {self.id}
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from {self.module_name} import *

{self.clean_source_code}

final_answer = {self.function_name}
'''
        with open(_OUTPUT, 'w') as f:
            f.write(final_source_code)

    def query_llm_and_save_candidate(self, message, system_message=PROGRAMMER_PROMPT.format()) -> Optional[List[str]]:
        previous_history = self.load_previous_history()
        new_id = str(alphanumeric_uuid()[-5:])
        output_filename = f'candidate_{new_id}.py'
        replys, histories = query_llm(
            message, system_message=system_message, previous_history=previous_history, filename=output_filename)

        wrote_filenames = []
        for i, reply in enumerate(replys):
            candidate = PythonCode.extract_main_program_code_block_from_full_reply(
                reply, function_name=self.function_name)
            if candidate.valid():
                final_code = f'''# Mutation from '{self.source_filename}'
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

import sudocode

{candidate.code_text}
'''
                new_candidate_filename = f'candidate_{new_id}_{i}.py'
                with open(new_candidate_filename, 'w') as f:
                    f.write(final_code)
                    logging.info(f'Wrote to {new_candidate_filename}')
                isort.file(new_candidate_filename)
                new_history_filename = f'{new_candidate_filename}.history.pickle'
                with open(new_history_filename, 'wb') as f:
                    pickle.dump(histories[i], f)
                    logging.info(f'Wrote to {new_history_filename}')
                wrote_filenames.append(new_candidate_filename)
        return wrote_filenames

    def generate_test_case(self) -> bool:
        return create_test_file(self.source_filename,
                                self.function_name, self.clean_source_code)

    def generate_seed_candidate(self) -> bool:
        message = f'''
```python
{self.clean_source_code}
```

Generate '{self.function_name}'.
'''
        return bool(self.query_llm_and_save_candidate(message))

    def generate_candidate_by_execution_result(self, execution_results: str) -> bool:
        message = f'''Check the correctness based on execution results.
```
{execution_results}
```

If you found the function {self.function_name} is not correct, re-generate it.
'''
        return bool(self.query_llm_and_save_candidate(message))


def get_all_agents() -> List[CodeAgentState]:
    return [agent for agent in _REGISTRY.values() if not agent.is_genesis()]


def get_genesis() -> CodeAgentState:
    return [agent for agent in _REGISTRY.values() if agent.is_genesis()][0]


def find_agent(candidate_id: str) -> Optional[CodeAgentState]:
    return _REGISTRY.get(candidate_id, None)


def CodeAgent(method=None, **kwargs):
    def _harness(method):
        source_code = inspect.getsource(method)
        source_filename = os.path.basename(method.__code__.co_filename)
        code_agent_state = CodeAgentState(
            function_obj=method, source_code=source_code, source_filename=source_filename, function_name=method.__name__)
        _REGISTRY[code_agent_state.id] = code_agent_state

        @functools.wraps(method)
        def _wrapper(*args, **kwargs):
            # Mock to avoid any test errors (e.g. `assert ==`).
            always_true = MagicMock()
            always_true.__eq__.return_value = True
            always_true.__gt__.return_value = True
            always_true.__lt__.return_value = True

            if is_data_collection_mode():
                call_refs = [agent.call_and_record_data_remotely(
                    *args, **kwargs) for agent in get_all_agents()]
                readys, unreadys = ray.wait(
                    call_refs, num_returns=len(call_refs), timeout=5)
                for task in unreadys:
                    ray.cancel(task, force=True)
                datapoints = ray.get(readys)
                collector = get_data_collector()
                for dp in datapoints:
                    if dp is not None:
                        collector.record(dp)
                return always_true
            else:
                # TODO: non data collection mode
                # return code_agent_state.call_and_maybe_fix_exception(*args, **kwargs)
                return always_true

        setattr(_wrapper, '__code_agent_state__', code_agent_state)
        return _wrapper

    if method is not None:
        return _harness(method)
    return _harness


def print_candidate_rank(ranked_candidate):
    if not ranked_candidate:
        return
    print('\nCandidate rank:')
    for score, candidate_id in ranked_candidate:
        agent = find_agent(candidate_id)
        if agent is not None:
            if agent.debug_oracle_pass():
                oracle_pass = '✔'
            else:
                oracle_pass = '✖'
        else:
            oracle_pass = 'N/A'
        print(f'{score:8}: {candidate_id:50} - {oracle_pass}')


def load_locked_tests():
    if not os.path.exists('locked_tests.json'):
        return {}
    with open('locked_tests.json', 'r') as f:
        return json.load(f)


def save_locked_tests(locked_tests):
    with open('locked_tests.json', 'w') as f:
        json.dump(locked_tests, f, indent=2)


def refresh_all_data():
    DATA_DIST.clear()
    auto_import()
    all_test_cases = get_all_test_cases()
    for test in all_test_cases:
        test()


def generate_code():
    auto_import()
    genesis = get_genesis()
    genesis.generate_seed_candidate()


def generate_test():
    auto_import()
    genesis = get_genesis()
    genesis.generate_test_case()
    refresh_all_data()
    all_test_cases = get_all_test_cases()
    for test in all_test_cases:
        test()


def get_test_and_candidate_info():
    refresh_all_data()
    genesis = get_genesis()
    function_name = genesis.function_name

    locked_tests = load_locked_tests()

    candidate_to_passed_locked_tests = defaultdict(list)
    test_info = []
    candidate_to_input_output = get_candidate_input_output()
    test_dist = get_test_dist()
    for input, dist_with_output in test_dist.items():
        dist = [x[0] for x in dist_with_output]
        outputs = [x[1] for x in dist_with_output]
        most_frequent_output = outputs[0]
        print(
            f'=== {shorten_answer(input)} -> {most_frequent_output}, entropy: {entropy_list(dist):.2f}, dist: {shorten_list(dist)}')
        
        outputs_info = defaultdict(list)
        for candidate_id, input_to_datapoint_dict in candidate_to_input_output.items():
            for _, datapoint in input_to_datapoint_dict.items():
                try:
                    input_str, output_str = datapoint_to_input_output_str(datapoint)
                except:
                    continue
                if input_str != input:
                    continue
                
                call_str = make_function_call_statement_str(datapoint.input, datapoint.output, function_name, limit=1000)
                outputs_info[output_str].append({
                    'datapoint': datapoint,
                    'call_str': call_str,
                    'candidate_id': candidate_id,
                })

        default_output_str = most_frequent_output
        locked_output = locked_tests.get(input, None)
        locked = False
        if (locked_output is not None) and (locked_output in outputs):
            default_output_str = locked_output
            locked = True

        this_test_id = alphanumeric_uuid()
        if locked:
            correct_info_list = outputs_info[default_output_str]
            for info in correct_info_list:
                candidate_to_passed_locked_tests[info['candidate_id']].append(this_test_id)

        test_info.append({
            'id': this_test_id,
            'input': input,
            'default_output_str': default_output_str,
            'default_call_str': outputs_info[default_output_str][0]['call_str'],
            'outputs': outputs,  # in rank order.
            'outputs_info': outputs_info,
            'locked': locked,
        })

    all_candidates = get_all_agents()
    all_candidate_ids = [c.id for c in all_candidates]

    candidate_to_stats_scores = calculate_candidates_stats_scores(all_candidate_ids)
    candidate_info = [{
            'candidate_id': candidate_id,
            'candidate': find_agent(candidate_id),
            'stats_score': stats_score,
            'tests_score': len(candidate_to_passed_locked_tests[candidate_id]),
            'passed_tests': candidate_to_passed_locked_tests[candidate_id],
        } for candidate_id, stats_score in candidate_to_stats_scores.items()]
    
    test_info = sorted(test_info, key=lambda x:x['locked'], reverse=True)
    candidate_info = sorted(candidate_info, key=lambda x:(x['tests_score'], x['stats_score']), reverse=True)
    return test_info, candidate_info, locked_tests
