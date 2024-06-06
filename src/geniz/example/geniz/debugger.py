import functools
import os

from .data_collector import data_collection_mode, is_data_collection_mode

_REGISTRY = []


def DebugAgent(**kwargs):
    def _harness(method):
        @functools.wraps(method)
        def _wrapper(*args, **kwargs):
            name = method.__name__
            source_filename = os.path.basename(method.__code__.co_filename)
            test_case = f'{name}({source_filename})'
            if is_data_collection_mode():
                print(
                    f'>>> Skip test case {test_case}, nested data collection mode')
                return
            print(
                f'>>> Run test case {test_case} in data collection mode')
            with data_collection_mode(test_case=test_case):
                method(*args, **kwargs)

        _REGISTRY.append(_wrapper)
        return _wrapper

    return _harness


def get_all_test_cases():
    return _REGISTRY
