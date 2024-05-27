# Autogenesis multi-agentic code-gen framework

Self-bootstrap the generated code folder.

## Docker

```bash
cd sudocode-core
docker build . -f Dockerfile.autogenesis -t autogenesis
```


## HumanEval benchmark

GPT-4 turbo, full set
```bash
python benchmark.py --dataset=humaneval --output=test_latest_gpt4_turbo_1 --parallel=20 --trials=1 --im
age=autogenesis:latest-gpt4-turbo
```

GPT-4, full set
```bash
python benchmark.py --dataset=humaneval --output=test_agentcoder_v0_gpt4_1 --parallel=20 --trials=1 --image=autogenesis:latest-gpt4
```

Only 10 hard cases
```bash
python benchmark.py --dataset=humaneval --output=test_agentcoder_v0_hard --parallel=10 --trials=1 --hard
```

Only 10 hard cases, each runs 10 times
```bash
python benchmark.py --dataset=humaneval --output=test_agentcoder_v0_hard --parallel=30 --trials=10 --hard
```

ningcoder Agent

```bash
python benchmark.py --dataset=humaneval --agent=ningcoder --output=test_ningcoder_hard --parallel=1 --trials=1 --hard
```