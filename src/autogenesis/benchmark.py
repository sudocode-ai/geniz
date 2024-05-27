"""Code-agent test-bench

Pre-requisite:
> pip install -e .
"""

import argparse
import asyncio
import glob
import os
from collections import defaultdict
from pathlib import Path
import shutil
from subprocess import check_output
from typing import Optional

import ray
from datasets import load_dataset
from tqdm import tqdm
from utils.logging import PrintColor, format_color


os.environ['RAY_DEDUP_LOGS'] = '0'


def calculate_score(output: str):
    total = defaultdict(int)
    positive = defaultdict(int)

    overral_score = 0
    for output_file_path in glob.glob(f'{output}/**/output.pass', recursive=True):
        output_file = Path(output_file_path)
        if not output_file.exists():
            continue
        passed = int(output_file.read_text())
        world_folder = os.path.dirname(output_file)
        task_id_file = Path(os.path.join(world_folder, 'task_id.txt'))
        task_id = task_id_file.read_text()

        total[task_id] += 1
        positive[task_id] += passed

    for task_id, sum in sorted(total.items(), key=lambda x: int(x[0].split('/')[1])):
        pos = positive[task_id]
        if pos > 0:
            color = PrintColor.GREEN
            overral_score += 1
        else:
            color = PrintColor.RED
        print(format_color(
            f'{task_id}: {pos}/{sum} ({100*pos/sum:.1f}%)', color))
    print()
    if len(total) > 0:
        print(
            f'Overall score: {overral_score}/{len(total)} ({100*overral_score/len(total):.1f}%)')


def init_benchmark_scaffolding(world_folder: Path, entry, agent):
    task_id = entry['task_id']
    assert task_id.startswith('HumanEval/')
    prompt = entry['prompt']
    test = entry['test']
    entry_point = entry['entry_point']

    if agent in ['ningcoder', 'opencoder', 'baseline']:
        with open(os.path.join(world_folder, 'input.py'), 'w') as f:
            source_lines = prompt.split('\n')
            for i, line in enumerate(source_lines):
                if line.startswith(f'def {entry_point}'):
                    source_lines.insert(i, '@sudocode.CodeAgent()')
                    break
            final_prompt = '\n'.join(source_lines)
            final_prompt = 'import sudocode\n' + final_prompt
            f.write(final_prompt)
    else:
        with open(os.path.join(world_folder, 'input.txt'), 'w') as f:
            polished_prompt = f'{prompt}\n# The main function (entry point) is {entry_point}'
            f.write(polished_prompt)
    with open(os.path.join(world_folder, 'task_id.txt'), 'w') as f:
        f.write(task_id)

    eval_code = f'''
{prompt}

{test}

if __name__ == '__main__':
    try:
        import output
        check(output.final_answer)
        with open('output.pass', 'w') as f:
            f.write('1')
    except:
        import traceback
        with open('output.error', 'w') as f:
            f.write(traceback.format_exc())
        with open('output.pass', 'w') as f:
            f.write('0')
'''
    with open(os.path.join(world_folder, 'eval_output.py'), 'w') as f:
        f.write(eval_code)


@ray.remote
def run_eval_case(trial: str, entry, output: str, rerun_failures: bool = False, image: str = 'autogenesis', agent: str = 'ningcoder', model: str = 'Phi-3-mini-128k-instruct'):
    world_path = Path(os.path.join(output, trial))
    pass_file = Path(os.path.join(world_path, 'output.pass'))
    if pass_file.exists():
        passed = pass_file.read_text()
        if rerun_failures and passed != '1':
            shutil.rmtree(world_path, ignore_errors=True)
        else:
            return world_path, passed
    else:
        shutil.rmtree(world_path, ignore_errors=True)

    init_cmd = ['python', 'run.py',
                f'--world={world_path}', f'--agent={agent}', '--init_only']
    print(' '.join(init_cmd))
    check_output(init_cmd)

    init_benchmark_scaffolding(world_path, entry, agent)

    if agent in ['ningcoder']:
        max_rounds = 11
    if agent in ['opencoder']:
        max_rounds = 30
    else:
        max_rounds = 23

    run_cmd = ['python', 'run.py', f'--world={world_path}', f'--agent={agent}',
               f'--rounds={max_rounds}', '--save_log_to_file', f'--image={image}',
               f'--model={model}']
    print(' '.join(run_cmd))
    retry = 0
    while retry < 2:
        retry += 1
        try:
            check_output(run_cmd)
            if pass_file.exists():
                return world_path, pass_file.read_text()
        except KeyboardInterrupt:
            return world_path, '0'
        except:
            continue
    return world_path, '0'


def humaneval_bench(output: str,
                    max_rows: int = 200,
                    rerun_failures: bool = False,
                    hard: bool = False,
                    parallel: int = 1,
                    against_one_case: Optional[int] = None,
                    trials: int = 1,
                    image: str = 'autogenesis',
                    agent: str = 'ningcoder',
                    model: str = 'Phi-3-mini-128k-instruct'):
    calculate_score(output)

    dataset = load_dataset("openai_humaneval")
    dataset_len = len(dataset["test"])
    if against_one_case is not None:
        eval_cases = [against_one_case]
    else:
        if hard:
            # Average passing rate:
            #  10: 30%
            #  33: 30%
            #  64: 80%
            #  65:  0%
            #  83:  0%
            # 115: 80%
            # 130: 10%
            # 132:  0%
            # 145:  0%
            # 163:  0%
            eval_cases = [10, 33, 64, 65, 83, 115, 130, 132, 145, 163]
        else:
            eval_cases = list(range(dataset_len))
        eval_cases = eval_cases[:max_rows]

    eval_tasks = [(f'{case_id}_{trial}', dataset['test'][case_id], output, rerun_failures, image, agent, model)
                  for case_id in eval_cases for trial in range(trials)]

    running_refs = []
    for task in tqdm(eval_tasks, desc='Benchmarking...'):
        if len(running_refs) >= parallel:
            # update result_refs to only track the remaining tasks.
            ready_refs, running_refs = ray.wait(running_refs, num_returns=1)
            results = ray.get(ready_refs)
            if len(results) > 0:
                world_folder, passed = results[0]
                if passed == '1':
                    color = PrintColor.GREEN
                else:
                    color = PrintColor.RED
                print(format_color(
                    f'Finished: {passed} - {world_folder}', color))

        running_refs.append(run_eval_case.remote(*task))
    ray.get(running_refs)

    calculate_score(output)


async def mbpp_bench(output: str, max_rows: int = 10, rerun_failures: bool = False, hard: bool = False):
    raise RuntimeError('TODO: migrate to call Autogenesis framework')


def main():
    ray.init()

    parser = argparse.ArgumentParser(description="Benchmark code-gen agent")
    parser.add_argument("--dataset", type=str, default="humaneval",
                        help="The dataset to benchmark.")
    parser.add_argument("--max_rows", type=int, default=200,
                        help="Max rows to test")
    parser.add_argument("--output", type=str,
                        default="./output", help="Output folder")
    parser.add_argument("--rerun_failures", action='store_true',
                        help="Only re-run the failed cases")
    parser.add_argument("--hard", action='store_true',
                        help="Run a small subset of tests (if it exists) that tend to fail often. If we get these csases right, it's a great chance to beat SOTA.")
    parser.add_argument("--parallel", type=int, default=1,
                        help="Max concurrent running eval cases")
    parser.add_argument("--against_one_case", type=int, default=None,
                        help="case number. Test only one.")
    parser.add_argument("--trials", type=int, default=1,
                        help="How many independent trails for one case. (Test flakiness)")
    parser.add_argument("--image", type=str,
                        default="autogenesis", help="docker image")
    parser.add_argument("--agent", type=str, default="ningcoder",
                        help="The agent to use.")
    parser.add_argument("--model", type=str, default="Phi-3-mini-128k-instruct",
                        help="The LLM model.")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    if args.dataset == 'humaneval':
        humaneval_bench(args.output, args.max_rows, args.rerun_failures,
                        args.hard, args.parallel, args.against_one_case, args.trials, args.image, args.agent,
                        args.model)
    if args.dataset == 'mbpp':
        asyncio.run(mbpp_bench(args.output + "_mbpp",
                    args.max_rows, args.rerun_failures, args.hard))


if __name__ == '__main__':
    main()
