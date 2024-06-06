import argparse
import json
import os
import shutil
import traceback
import uuid
from pathlib import Path
from time import sleep
from typing import List, Optional

import docker
from docker.errors import NotFound
from docker.models.containers import Container

_IMAGE = 'autogenesis'


def _wait_for_ready(container: Container, timeout: int = 60, stop_time: float = 0.1) -> None:
    elapsed_time = 0
    while container.status != "running" and elapsed_time < timeout:
        sleep(stop_time)
        elapsed_time += stop_time
        container.reload()
        continue
    if container.status != "running":
        raise ValueError("Container failed to start")


def _attach_or_create_container(container_name: str, world_folder: Path, docker_image: str = _IMAGE, model: str = 'Phi-3-mini-128k-instruct') -> Container:
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        return container
    except NotFound:
        container = client.containers.create(
            docker_image,
            name=container_name,
            entrypoint="/bin/sh",
            tty=True,
            auto_remove=True,
            volumes={
                '/var/run/docker.sock': {'bind': '/var/run/docker.sock', 'mode': 'rw'},
                str(world_folder.resolve()): {"bind": "/workspace", "mode": "rw"}
            },
            network_mode='host',
            working_dir="/workspace",
        )
        container.start()
        return container


def _stop_container(container_name: str):
    client = docker.from_env()
    try:
        container = client.containers.get(container_name)
        container.stop()
    except:
        return


def stop(world_folder: Path):
    docker_name_file = Path(os.path.join(world_folder, 'container_name.txt'))
    if docker_name_file.exists():
        container_name = docker_name_file.read_text()
        _stop_container(container_name)


def init_world_folder(world_folder: Path, source_agent_folder: Path):
    """init world folder with a pre-configuared example."""
    shutil.copytree(source_agent_folder, world_folder)


def run(world_folder: Path, cmd: List[str] = ['python', 'main.py'], timeout: float = 1200, save_log_to_file: bool = False, image: str = _IMAGE, model: str = 'Phi-3-mini-128k-instruct'):
    docker_name_file = Path(os.path.join(world_folder, 'container_name.txt'))
    task_id = Path(os.path.join(world_folder, 'task_id.txt'))
    log_file = Path(os.path.join(world_folder, 'stdout.log'))

    if not docker_name_file.exists():
        if task_id.exists():
            normalized_task_id = task_id.read_text().replace('/', '-')
            container_name = f'autogenesis-{normalized_task_id}-{str(uuid.uuid4())[-5:]}'
        else:
            container_name = f'autogenesis-{uuid.uuid4()}'
        docker_name_file.write_text(container_name)
    container_name = docker_name_file.read_text()

    container = _attach_or_create_container(
        container_name, world_folder, image, model)
    _wait_for_ready(container)

    command = ["timeout", str(timeout)] + cmd
    result = container.exec_run(command, stream=True, environment={'AUTOGENESIS_MODEL': model})
    output_stream = result.output
    for chunk in output_stream:
        if save_log_to_file:
            with open(log_file, 'ab') as f:
                f.write(chunk)
        print(chunk.decode('utf-8'), flush=True)
    return result


def check_stop_criteria(world_folder: Path, rounds: Optional[int] = None, save_log_to_file: bool = False, image: str = _IMAGE):
    submitted_file = Path(os.path.join(world_folder, 'output.py'))
    pass_file = Path(os.path.join(world_folder, 'output.pass'))
    if submitted_file.exists():
        run(world_folder, cmd=['python', 'eval_output.py'],
            save_log_to_file=save_log_to_file, image=image)
        if pass_file.exists():
            passed = pass_file.read_text()
            print(f'{world_folder} passed: {passed}')
        else:
            stop(world_folder)
            dirname, basename = os.path.split(world_folder)
            dest_path = os.path.join(dirname, f'{basename}.abnormal')
            shutil.rmtree(dest_path, ignore_errors=True)
            world_folder.replace(dest_path)
            print(f'{world_folder} abnormal')
        return True

    if rounds is not None:
        roundinfo_file = Path(os.path.join(world_folder, 'RoundInfo.json'))
        if roundinfo_file.exists():
            roundinfo = json.loads(roundinfo_file.read_text())
            current_round = int(roundinfo['round'])
            if current_round >= rounds:
                print(f'Reach max rounds {rounds}, stop')
                return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Autogenesis Runner")
    parser.add_argument("--world", type=str, default="./world_folder",
                        help="The world folder.")
    parser.add_argument("--agent", type=str, default="./agentcoder_v0",
                        help="Source agent.")
    parser.add_argument("--image", type=str, default="autogenesis",
                        help="Docker image")
    parser.add_argument("--model", type=str, default="Phi-3-mini-128k-instruct",
                        help="LLM model")
    parser.add_argument("--rounds", type=int, default=1, help="Max rounds")
    parser.add_argument("--save_log_to_file", action='store_true',
                        help="Also save terminal log to 'stdout.log' in the world folder.")
    parser.add_argument("--init_only", action='store_true',
                        help="Only init the world folder without run.")
    args = parser.parse_args()

    world_folder_path = Path(args.world)
    if not world_folder_path.exists():
        try:
            init_world_folder(world_folder_path, Path(args.agent))
        except:
            print('Init failed.')
            traceback.print_exc()
            shutil.rmtree(world_folder_path, ignore_errors=True)
            exit(1)

    if args.init_only:
        exit(0)

    for _ in range(args.rounds):
        try:
            run(world_folder_path,
                save_log_to_file=args.save_log_to_file,
                image=args.image,
                model=args.model)
            if check_stop_criteria(world_folder_path, args.rounds, save_log_to_file=args.save_log_to_file, image=args.image):
                break
        except:
            traceback.print_exc()
            break
    stop(world_folder_path)


if __name__ == '__main__':
    main()
