import traceback
from collections import defaultdict
from contextlib import contextmanager
from threading import Lock
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel

from .util import shorten_answer

_lock = Lock()
DATA_DIST = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

COLLECTION_MODE = False
CURRENT_COLLECTOR = None


class DataPoint(BaseModel):
    input: Tuple
    output: Any
    candidate: str = ''
    test_case: str = ''

    def debug_str(self):
        msg = f'DataPoint\n  input: {str(self.input)[:50]}\n  output: {str(self.output)[:50]}\n  candidate: {self.candidate}\n  test_case: {self.test_case}'
        return msg


def datapoint_to_input_output_str(datapoint):
    input_str = str(datapoint.input)
    if isinstance(datapoint.output, Exception):
        e = datapoint.output
        output_str = f'Exception({type(e).__name__}: {e})'
    else:
        output_str = str(datapoint.output)
    return input_str, output_str

class DataCollector(BaseModel):
    test_case: str
    data_points: List[DataPoint] = []

    def record(self, datapoint: DataPoint):
        # Skip invalid executions.
        # if datapoint.output is None or isinstance(datapoint.output, Exception):
        #     return
        datapoint.test_case = self.test_case
        self.data_points.append(datapoint)
        # print(f'Record {datapoint.debug_str()}')

    def merge(self):
        _lock.acquire()
        for datapoint in self.data_points:
            try:
                input_str, output_str = datapoint_to_input_output_str(datapoint)
                DATA_DIST[input_str][output_str][datapoint.candidate].append(
                    datapoint)
            except:
                pass
        _lock.release()


class ReenterException(Exception):
    pass


def _enter_collection_mode(collector: DataCollector):
    global COLLECTION_MODE, CURRENT_COLLECTOR
    if COLLECTION_MODE is True:
        raise ReenterException('re-enter collection mode')
    COLLECTION_MODE = True
    CURRENT_COLLECTOR = collector


def _leave_collection_mode():
    global COLLECTION_MODE, CURRENT_COLLECTOR
    if COLLECTION_MODE is False:
        print('Warning leave collection mode without entering')
    COLLECTION_MODE = False
    CURRENT_COLLECTOR = None


def is_data_collection_mode() -> bool:
    return COLLECTION_MODE


def get_data_collector() -> DataCollector:
    return CURRENT_COLLECTOR  # type: ignore


def reduce_to_most_frequent_answer() -> Dict[Tuple, str]:
    most_frequent = dict()
    for input, output_dist in DATA_DIST.items():
        if not output_dist:
            continue
        answer = max(output_dist.items(), key=lambda x: len(x[1]))
        most_frequent[input] = shorten_answer(answer[0])
    return most_frequent


def calculate_candidates_stats_scores(all_candidates: List[str] = []) -> Dict[str, int]:
    candidate_to_score = defaultdict(int)
    for c in all_candidates:
        candidate_to_score[c] = 0
    for _, output_dist in DATA_DIST.items():
        if not output_dist:
            continue
        sort_by_frequency = sorted(
            output_dist.items(), reverse=True, key=lambda x: len(x[1]))
        # Find the first valid output to credit candidates score.
        bounty = 3
        for _, candidate_dist in sort_by_frequency:
            for candidate in candidate_dist:
                candidate_to_score[candidate] += bounty
            bounty -= 1
            if bounty == 0:
                break
    return candidate_to_score


def get_test_dist() -> Dict[Tuple, Any]:
    test_dist = dict()
    for input, output_dist in DATA_DIST.items():
        dist = sorted([(len(points), output)
                      for output, points in output_dist.items()], reverse=True, key=lambda x: x[0])
        test_dist[input] = dist
    return test_dist


def get_candidate_input_output() -> Dict[str, Dict[str, DataPoint]]:
    candidate_input_output = defaultdict(dict)
    for input, output_dist in DATA_DIST.items():
        for _, candidate_dist in output_dist.items():
            for candidate_id, datapoints in candidate_dist.items():
                candidate_input_output[candidate_id][input] = datapoints[0]
    return candidate_input_output


def get_data_dist():
    return DATA_DIST


@contextmanager
def data_collection_mode(test_case):
    collector = DataCollector(test_case=test_case)
    try:
        _enter_collection_mode(collector)
        yield collector
    except Exception as e:
        print(f'  suppress exception: {e}')
        traceback.print_exc()
    finally:
        collector.merge()
        _leave_collection_mode()
