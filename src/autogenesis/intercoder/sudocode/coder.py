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
from .data_collector import (DataPoint, calculate_candidates_scores,
                             get_candidate_input_output, get_data_collector,
                             get_test_dist, is_data_collection_mode,
                             reduce_to_most_frequent_answer)
from .debugger import get_all_test_cases
from .llm import ChatMessage, query_llm
from .python_code import PythonCode
from .round_info import get_round_info
from .test_designer import create_test_file
from .util import (PersistStateToFile, alphanumeric_uuid, entropy_list,
                   load_prompt, make_function_call_statement_str,
                   shorten_answer, shorten_list)

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


def generate_code():
    auto_import()
    genesis = get_genesis()
    genesis.generate_seed_candidate()
    auto_import()


def generate_test():
    auto_import()
    genesis = get_genesis()
    genesis.generate_test_case()
    auto_import()
    all_test_cases = get_all_test_cases()
    for test in all_test_cases:
        test()


def code_gen():
    all_candidates = get_all_agents()
    all_candidate_ids = [c.id for c in all_candidates]
    all_test_cases = get_all_test_cases()
    candidates = len(all_candidates)
    genesis = get_genesis()
    function_name = genesis.function_name

    for test in all_test_cases:
        test()
    test_dist = get_test_dist()
    with open('test_dist.json', 'w') as f:
        json.dump(test_dist, f, indent=2)


def run_all_code_agents() -> bool:
    round_info = get_round_info()
    if os.path.exists(_OUTPUT):
        logging.info(f'Day {round_info.round}: already have {_OUTPUT}')
        return True

    all_candidates = get_all_agents()
    all_candidate_ids = [c.id for c in all_candidates]
    all_test_cases = get_all_test_cases()
    candidates = len(all_candidates)
    genesis = get_genesis()
    function_name = genesis.function_name

    for test in all_test_cases:
        test()

    test_dist = get_test_dist()
    with open('test_dist.json', 'w') as f:
        json.dump(test_dist, f, indent=2)

    test_inputs = list(test_dist.keys())
    candidate_to_scores = calculate_candidates_scores(all_candidate_ids)
    ranked_candidate = sorted(
        [(s, c) for c, s in candidate_to_scores.items() if find_agent(c)], reverse=True)
    for input, dist_with_output in test_dist.items():
        most_frequent_output = dist_with_output[0][1]
        dist = [x[0] for x in dist_with_output]
        print(
            f'=== {shorten_answer(input)} -> {most_frequent_output}, entropy: {entropy_list(dist):.2f}, dist: {shorten_list(dist)}')
    print_candidate_rank(ranked_candidate)

    logging.info(f'Total candidates: {candidates}')
    logging.info(f'Total test cases: {len(test_inputs)}')

    return False

    # Seed
    if round_info.round < 10:
        logging.info(
            f'Day {round_info.round}: generate seed candidates and seed tests.')
        if candidates < 10:
            genesis.generate_seed_candidate()
        if len(test_inputs) < 5:
            genesis.generate_test_case()

        if candidates >= 10 and len(test_inputs) >= 5:
            round_info.round = 10
            round_info.save()
        return False

    if round_info.round >= 20:
        logging.info(
            f'Day {round_info.round}: force to submit.')
        if candidates > 0:
            best_candidate = all_candidates[0]
            logging.info(
                f'Give up, submit random candidate: {best_candidate.debug_str()}')
            best_candidate.submit()
        else:
            logging.info('Give up, no candidate to submit!')
            genesis.submit()
        return True

    # Submit
    if round_info.round >= 14:
        logging.info(
            f'Day {round_info.round}: rank and submit best candidate.')
        if len(ranked_candidate) > 0:
            best_candidate_id = ranked_candidate[0][1]
            best_candidate = [
                agent for agent in all_candidates if agent.id == best_candidate_id][0]
            logging.info(
                f'Submit the best candidate: {best_candidate.debug_str()}')
            best_candidate.submit()
            return True

    # Feedback-fix-augment
    if 10 <= round_info.round:
        logging.info(
            f'Day {round_info.round}: generate more test cases and feedback-fix-candidates')

        if candidates < 10:
            genesis.generate_seed_candidate()
        if len(test_inputs) < 5:
            genesis.generate_test_case()

        candidate_input_output = get_candidate_input_output()
        if not candidate_input_output:
            return False

        to_be_fixed_candidates = list(candidate_input_output.keys())
        random.shuffle(to_be_fixed_candidates)
        quota = 5
        for candidate_id in to_be_fixed_candidates:
            if quota <= 0:
                break
            input_output_dist = candidate_input_output[candidate_id]

            agent = find_agent(candidate_id)
            if agent is None or agent.is_genesis():
                continue

            call_strs = []
            for input, datapoint in input_output_dist.items():
                # Skip large test for now
                if len(input) > 50:
                    continue

                call_str = make_function_call_statement_str(
                    datapoint.input, datapoint.output, function_name, limit=100)
                if not call_str:
                    continue
                call_strs.append(call_str)

            execution_result = '\n'.join(call_strs)
            print(
                f'=== Exercising {candidate_id}:\n{execution_result}')
            born_new = agent.generate_candidate_by_execution_result(
                execution_result)
            if born_new:
                agent.delete()
                quota -= 1

        return False
    return False
