#!/bin/bash

nohup python run.py --world test_humaneval/test_10 --agent agentcoder_v0 --rounds=21 --benchmark=HumanEval/10 &
nohup python run.py --world test_humaneval/test_33 --agent agentcoder_v0 --rounds=21 --benchmark=HumanEval/33 &
nohup python run.py --world test_humaneval/test_64 --agent agentcoder_v0 --rounds=21 --benchmark=HumanEval/64 &
nohup python run.py --world test_humaneval/test_65 --agent agentcoder_v0 --rounds=21 --benchmark=HumanEval/65 &
nohup python run.py --world test_humaneval/test_83 --agent agentcoder_v0 --rounds=21 --benchmark=HumanEval/83 &
nohup python run.py --world test_humaneval/test_115 --agent agentcoder_v0 --rounds=21 --benchmark=HumanEval/115 &
nohup python run.py --world test_humaneval/test_130 --agent agentcoder_v0 --rounds=21 --benchmark=HumanEval/130 &
nohup python run.py --world test_humaneval/test_132 --agent agentcoder_v0 --rounds=21 --benchmark=HumanEval/132 &
nohup python run.py --world test_humaneval/test_145 --agent agentcoder_v0 --rounds=21 --benchmark=HumanEval/145 &
nohup python run.py --world test_humaneval/test_163 --agent agentcoder_v0 --rounds=21 --benchmark=HumanEval/163 &