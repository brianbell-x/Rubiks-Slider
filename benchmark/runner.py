"""
Run with python -m benchmark.runner
"""

import json
import re
import yaml
import os
import sys
import time
import argparse
import pathlib
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict

from .providers import chat
from core.puzzle import Puzzle, parse_simple_move

LOG_DIR = Path("benchmark/logs")
LOG_DIR.mkdir(exist_ok=True)
CONFIG_FILE = "benchmark/benchmark_config.yaml"

def now_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _random_shuffle_count(size: int) -> int:
    min_moves = size
    max_moves = size * size * 2
    return random.randint(min_moves, max_moves)

def generate_shuffle_sequence(size, moves=None):
    moves = moves if moves is not None else _random_shuffle_count(size)
    seq = []
    for _ in range(moves):
        move_type = random.choice(["row", "column"])
        idx = random.randint(1, size)
        direction = random.choice(["left", "right"]) if move_type == "row" else random.choice(["up", "down"])
        seq.append({"type": move_type, "index": idx, "direction": direction})
    return seq

def get_shuffle_sequence(size: int) -> List[Dict]:
    return generate_shuffle_sequence(size)

def sanitize_model_name(model):
    model_str = str(model) if model is not None else "default"
    return model_str.replace("/", "_").replace(" ", "_").replace(":", "_")


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)


def read_yaml_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_json_file(data, path):
    ensure_directory(os.path.dirname(path))
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def read_benchmarks_config():
    config_path = pathlib.Path(CONFIG_FILE)
    if not config_path.exists():
        return []
    cfg = read_yaml_file(config_path)
    return cfg.get("benchmarks", []) if cfg else []


INSTRUCTIONS_TEXT = """- Output your next move or sequence of moves (e.g., `R1 L`, `C2 U`, or `R1 L; C2 U; R3 R`) inside `<move>` tags.
- Example: `<move>R1 L; C2 U</move>`
- Do NOT include any reasoning or explanations. Only output your move(s) in the required format.
- You must respond with at least one move inside `<move>` tags."""


def build_prompt(mode: str, puzzle: Puzzle, grid_size: int, move_count: int) -> str:
    base_state_block = f"```\n{puzzle.get_state_string()}\n```"

    if mode == "initial":
        solved_board_str = "\n".join(" ".join(row) for row in puzzle.solved_board)
        return f"""# Welcome to Rubiks Slider!

**Instructions:**

{INSTRUCTIONS_TEXT}

**How to play:**

- You can shift rows left (L) or right (R).
  - Example: `R1 L` shifts row 1 left.
    ```
A B C
D E F
G H I
    ```
    becomes:
    ```
B C A
D E F
G H I
    ```
- You can shift columns up (U) or down (D).
  - Example: `C2 D` shifts column 2 down.
    ```
A B C
D E F
G H I
    ```
    becomes:
    ```
A H C
D B F
G E I
    ```
- You may output multiple moves per turn, separated by semicolons (`;`).

**Goal:** Return Rubiks Slider to the solved state:

```
{solved_board_str}
```

**Current State:**

{base_state_block}

**Moves made:** 0"""

    if mode == "failed_parse":
        return f"""## Your previous move(s) could not be parsed.

Please carefully output your next move or sequence of moves using the following format:

- Enclose your move(s) in <move>...</move> tags.
- Each move should be in the form `R1 L`, `C2 U`, etc. (e.g., `R1 L; C2 U; R3 R` for multiple moves, separated by semicolons).
- Example: `<move>R1 L; C2 U</move>`
- Do not include any other formatting or explanations inside the <move> tags.

## Current State ({grid_size}x{grid_size})

{base_state_block}

**Moves made:** {move_count}"""

    return f"""## Current State ({grid_size}x{grid_size})

{base_state_block}

**Moves made:** {move_count}

**Instructions:**

{INSTRUCTIONS_TEXT}"""


def invoke_model(messages, model):
    start = time.time()
    reply, reasoning = chat(messages, model)
    return reply, reasoning, time.time() - start


def parse_moves(response_text: str, grid_size: int):
    match = re.search(r"<move>(.*?)</move>", response_text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    move_block = match.group(1).strip()
    if not move_block:
        return None
    move_strs = [m.strip() for m in re.split(r"[;\n]", move_block) if m.strip()]
    move_dicts = []
    for simple_move_str in move_strs:
        json_move_str, error_msg = parse_simple_move(simple_move_str, grid_size)
        if error_msg:
            return None
        move_dicts.append(json.loads(json_move_str))
    return move_dicts if move_dicts else None


def apply_shuffle_sequence(puzzle: Puzzle, shuffle_sequence, grid_size: int):
    for move in shuffle_sequence:
        if 1 <= move.get("index", -1) <= grid_size:
            puzzle.apply_move_from_json(json.dumps(move))


def run_benchmark_scenario(grid_size, model, shuffle_sequence):
    puzzle = Puzzle(size=grid_size, auto_shuffle=False)
    apply_shuffle_sequence(puzzle, shuffle_sequence, grid_size)

    if puzzle.is_solved():
        return {
            "solved": True,
            "api_calls": 0,
            "moves": 0,
            "time_spent": 0.0,
            "conversation": [],
            "termination_reason": "Already Solved",
        }

    move_count = 0
    api_calls = 0
    conversation = []
    total_time = 0.0
    failed_parse_last = False

    while not puzzle.is_solved():
        print(f"    > Attempting call {api_calls + 1} ...")

        if failed_parse_last:
            mode = "failed_parse"
        elif not conversation:
            mode = "initial"
        else:
            mode = "followup"

        prompt = build_prompt(mode, puzzle, grid_size, move_count)
        messages = conversation + [{"role": "user", "content": prompt}]

        reply, reasoning, wall_time = invoke_model(messages, model)
        total_time += wall_time
        api_calls += 1

        conversation.append({"role": "user", "content": prompt})
        conversation.append({"role": "assistant", "content": reply, "reasoning": reasoning})

        extracted_moves = parse_moves(reply, grid_size)
        if extracted_moves is None:
            if not failed_parse_last:
                failed_parse_last = True
                continue
            return {
                "solved": False,
                "api_calls": api_calls,
                "moves": move_count,
                "time_spent": total_time,
                "conversation": conversation,
                "termination_reason": "Invalid Move/Response Format",
            }

        failed_parse_last = False

        for move_dict in extracted_moves:
            success, _ = puzzle.apply_move_from_json(json.dumps(move_dict))
            if success:
                move_count += 1
                if puzzle.is_solved():
                    break
            else:
                return {
                    "solved": False,
                    "api_calls": api_calls,
                    "moves": move_count,
                    "time_spent": total_time,
                    "conversation": conversation,
                    "termination_reason": "Invalid Move Applied",
                }

    return {
        "solved": True,
        "api_calls": api_calls,
        "moves": move_count,
        "time_spent": total_time,
        "conversation": conversation,
        "termination_reason": "Solved",
    }


def save_incremental_log(model, results, timestamp, run_dir):
    model_id = f"openrouter_{sanitize_model_name(model)}"
    max_solved = max((r["size"] for r in results if r["solved"]), default=0)
    log_data = {
        "provider": "openrouter",
        "model": model,
        "attempts": results,
        "timestamp": timestamp,
        "max_solved_size": max_solved,
    }
    model_dir = os.path.join(run_dir, model_id)
    write_json_file(log_data, os.path.join(model_dir, f"{model_id}_results.json"))
    print(f"    > Incremental results saved")


def run_benchmark():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-size", type=int, default=3, help="Starting grid size")
    ap.add_argument("--shuffle-moves", type=int, default=10, help="Number of shuffle moves")
    args = ap.parse_args()

    print("--- Rubiks Slider Benchmark ---")

    benchmark_configs = read_benchmarks_config()
    if not benchmark_configs:
        print("No benchmark configurations found. Exiting.")
        sys.exit(1)

    timestamp = now_timestamp()
    run_dir = os.path.join(LOG_DIR, timestamp)
    ensure_directory(run_dir)
    print(f"[*] Log directory: {run_dir}")

    models = []
    for cfg in benchmark_configs:
        model = cfg.get("model")
        if model:
            models.append(model)

    if not models:
        print("No valid models found in config. Exiting.")
        sys.exit(1)

    model_results = defaultdict(list)
    active_models = set(models)
    current_size = args.start_size

    while active_models and current_size <= 7:
        print(f"\n--- Grid Size: {current_size}x{current_size} ---")
        shuffle = get_shuffle_sequence(current_size)
        print(f"  > Using {len(shuffle)} shuffle moves")

        succeeded = set()

        for model in list(active_models):
            print(f"\n  --- Testing openrouter/{model} ---")

            result = run_benchmark_scenario(current_size, model, shuffle)
            
            run_data = {
                "size": current_size,
                "moves": result["moves"],
                "solved": result["solved"],
                "conversation": result["conversation"],
                "time_spent": result["time_spent"],
                "api_calls_made": result["api_calls"],
            }
            if not result["solved"]:
                run_data["stop_reason"] = result["termination_reason"]

            model_results[model].append(run_data)
            save_incremental_log(model, model_results[model], timestamp, run_dir)

            status = "solved" if result["solved"] else result["termination_reason"]
            print(f"    > Result: api_calls={result['api_calls']}, moves={result['moves']}, {status}")

            if result["solved"]:
                succeeded.add(model)

        if not succeeded:
            print(f"\n--- No models succeeded at size {current_size}. Stopping. ---")
            break

        current_size += 1

    print("\n--- Benchmark Complete ---")
    for model, results in model_results.items():
        max_solved = max((r["size"] for r in results if r["solved"]), default=0)
        print(f"  openrouter/{model}: Max solved = {max_solved or 'None'}")


if __name__ == "__main__":
    run_benchmark()