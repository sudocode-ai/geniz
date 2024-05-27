"""Main entrance and also a simple planner agent."""

import logging
import os

from sudocode import get_round_info, run_all_code_agents, auto_import
from sudocode.round_info import get_round_info

import ray

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

os.environ['RAY_IGNORE_UNHANDLED_ERRORS'] = '1'

auto_import()

if __name__ == '__main__':
    ray.init(include_dashboard=False, ignore_reinit_error=True)
    round_info = get_round_info()
    round_info.save()  # for the first round init.
    logging.info(f'### Round {round_info.round} start ###')
    if run_all_code_agents():
        round_info = get_round_info()
        round_info.round = 100
        round_info.save()
    logging.info(f'### Round {round_info.round} end ###')
    round_info = get_round_info()
    round_info.round += 1
    round_info.save()
