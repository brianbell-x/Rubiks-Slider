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
from typing import List, Dict, Optional, Tuple

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


INSTRUCTIONS_TEXT_PHASE1 = """- Output your next move inside `<move>` tags.
- Example: `<move>R1 L</move>`
- You must output exactly ONE move per turn.
- Do NOT include any reasoning or explanations. Only output your move and prediction in the required format."""

INSTRUCTIONS_TEXT_PHASE2 = """- Output your next move or sequence of moves (e.g., `R1 L`, `C2 U`, or `R1 L; C2 U; R3 R`) inside `<move>` tags.
- Example: `<move>R1 L; C2 U</move>`
- You may output multiple moves per turn, separated by semicolons (`;`).
- Do NOT include any reasoning or explanations. Only output your move(s) and prediction in the required format."""


def build_prompt(mode: str, puzzle: Puzzle, grid_size: int, move_count: int, phase: int, prediction_tile: int) -> str:
    base_state_block = f"```\n{puzzle.get_labeled_state_string()}\n```"
    
    instructions = INSTRUCTIONS_TEXT_PHASE1 if phase == 1 else INSTRUCTIONS_TEXT_PHASE2
    
    prediction_text = f"""**Prediction Challenge:**
After submitting your move(s), you must predict where a specific tile will end up.
Format your prediction as: <prediction>R#C#</prediction>

For this turn: Where will tile {prediction_tile} be after your move(s)?"""

    if mode == "initial":
        solved_board_str = "\n".join(" ".join(row) for row in puzzle.solved_board)
        return f"""# Welcome to Rubiks Slider!

**How to play:**

- You can shift rows left (L) or right (R).
  - Example: `R1 L` shifts row 1 left.
    ```
    C1 C2 C3
 R1  A  B  C
 R2  D  E  F
 R3  G  H  I
    ```
    becomes:
    ```
    C1 C2 C3
 R1  B  C  A
 R2  D  E  F
 R3  G  H  I
    ```
- You can shift columns up (U) or down (D).
  - Example: `C2 D` shifts column 2 down.
    ```
    C1 C2 C3
 R1  A  B  C
 R2  D  E  F
 R3  G  H  I
    ```
    becomes:
    ```
    C1 C2 C3
 R1  A  H  C
 R2  D  B  F
 R3  G  E  I
    ```

**Goal:** Return Rubiks Slider to the solved state:

```
{solved_board_str}
```

**Current State:**

{base_state_block}

**Moves made:** 0

**Instructions:**

{instructions}

{prediction_text}"""

    if mode == "failed_parse":
        return f"""## Your previous response could not be parsed.

Please carefully output your next move(s) and prediction using the following format:

- Enclose your move(s) in <move>...</move> tags.
- Enclose your prediction in <prediction>...</prediction> tags.
- Example: 
<move>R1 L</move>
<prediction>R1C3</prediction>

## Current State ({grid_size}x{grid_size})

{base_state_block}

**Moves made:** {move_count}

{prediction_text}"""

    return f"""## Current State ({grid_size}x{grid_size})

{base_state_block}

**Moves made:** {move_count}

**Instructions:**

{instructions}

{prediction_text}"""


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

def parse_prediction(response_text: str) -> str | None:
    """Extract prediction from <prediction>R#C#</prediction> tags"""
    match = re.search(r"<prediction>(.*?)</prediction>", response_text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    prediction = match.group(1).strip()
    if not re.match(r"^R\d+C\d+$", prediction):
        return None
    return prediction

def apply_shuffle_sequence(puzzle: Puzzle, shuffle_sequence, grid_size: int):
    for move in shuffle_sequence:
        if 1 <= move.get("index", -1) <= grid_size:
            puzzle.apply_move_from_json(json.dumps(move))


def run_benchmark_scenario(grid_size, model, shuffle_sequence, phase: int):
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
            "predictions_total": 0,
            "predictions_correct": 0,
            "prediction_accuracy": 0.0
        }

    move_count = 0
    api_calls = 0
    conversation = []
    total_time = 0.0
    failed_parse_last = False
    consecutive_wrong_predictions = 0
    predictions_total = 0
    predictions_correct = 0

    while not puzzle.is_solved():
        print(f"    > Attempting call {api_calls + 1} ...")

        if failed_parse_last:
            mode = "failed_parse"
            # Keep same prediction tile for retry
        elif not conversation:
            mode = "initial"
            prediction_tile = random.randint(1, grid_size * grid_size)
        else:
            mode = "followup"
            prediction_tile = random.randint(1, grid_size * grid_size)

        prompt = build_prompt(mode, puzzle, grid_size, move_count, phase, prediction_tile)
        messages = conversation + [{"role": "user", "content": prompt}]

        reply, reasoning, wall_time = invoke_model(messages, model)
        total_time += wall_time
        api_calls += 1

        conversation.append({"role": "user", "content": prompt})
        conversation.append({"role": "assistant", "content": reply, "reasoning": reasoning})

        extracted_moves = parse_moves(reply, grid_size)
        extracted_prediction = parse_prediction(reply)

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
                "predictions_total": predictions_total,
                "predictions_correct": predictions_correct,
                "prediction_accuracy": (predictions_correct / predictions_total * 100) if predictions_total > 0 else 0.0
            }

        # Check if prediction is missing or invalid format (counts as wrong prediction)
        if extracted_prediction is None:
            consecutive_wrong_predictions += 1
            predictions_total += 1
            print(f"      > Prediction missing or invalid format. Consecutive wrong: {consecutive_wrong_predictions}")
        else:
            # Apply moves first to check prediction against new state
            # But we need to be careful not to modify the puzzle if we are going to fail due to invalid moves
            # So we'll use a temporary puzzle or apply/reverse. 
            # Actually, we can just apply moves, and if they are valid, check prediction.
            # If moves are invalid, we fail anyway.
            
            # Validate moves first
            moves_valid = True
            temp_puzzle = Puzzle(size=grid_size, auto_shuffle=False)
            temp_puzzle.board = [row[:] for row in puzzle.board] # Deep copy board
            
            for move_dict in extracted_moves:
                success, _ = temp_puzzle.apply_move_from_json(json.dumps(move_dict))
                if not success:
                    moves_valid = False
                    break
            
            if not moves_valid:
                 return {
                    "solved": False,
                    "api_calls": api_calls,
                    "moves": move_count,
                    "time_spent": total_time,
                    "conversation": conversation,
                    "termination_reason": "Invalid Move Applied",
                    "predictions_total": predictions_total,
                    "predictions_correct": predictions_correct,
                    "prediction_accuracy": (predictions_correct / predictions_total * 100) if predictions_total > 0 else 0.0
                }

            # Moves are valid, check prediction on temp_puzzle (which has moves applied)
            is_correct = temp_puzzle.validate_prediction(prediction_tile, extracted_prediction)
            predictions_total += 1
            
            if is_correct:
                consecutive_wrong_predictions = 0
                predictions_correct += 1
                print(f"      > Prediction Correct! ({extracted_prediction})")
            else:
                consecutive_wrong_predictions += 1
                print(f"      > Prediction Wrong. Predicted {extracted_prediction}, Actual {temp_puzzle.get_tile_position(prediction_tile)}. Consecutive wrong: {consecutive_wrong_predictions}")

        if consecutive_wrong_predictions >= 3:
             return {
                "solved": False,
                "api_calls": api_calls,
                "moves": move_count,
                "time_spent": total_time,
                "conversation": conversation,
                "termination_reason": "Unable to predict consequences",
                "predictions_total": predictions_total,
                "predictions_correct": predictions_correct,
                "prediction_accuracy": (predictions_correct / predictions_total * 100) if predictions_total > 0 else 0.0
            }

        failed_parse_last = False

        # Apply moves to actual puzzle
        for move_dict in extracted_moves:
            puzzle.apply_move_from_json(json.dumps(move_dict))
            move_count += 1
            if puzzle.is_solved():
                break
    
    return {
        "solved": True,
        "api_calls": api_calls,
        "moves": move_count,
        "time_spent": total_time,
        "conversation": conversation,
        "termination_reason": "Solved",
        "predictions_total": predictions_total,
        "predictions_correct": predictions_correct,
        "prediction_accuracy": (predictions_correct / predictions_total * 100) if predictions_total > 0 else 0.0
    }


def save_incremental_log(model, results, timestamp, run_dir):
    model_id = f"openrouter_{sanitize_model_name(model)}"
    # max_solved logic might need update if we want to track phases, but for now keeping it simple
    # We can track max phase passed maybe?
    log_data = {
        "provider": "openrouter",
        "model": model,
        "attempts": results,
        "timestamp": timestamp,
    }
    model_dir = os.path.join(run_dir, model_id)
    write_json_file(log_data, os.path.join(model_dir, f"{model_id}_results.json"))
    print(f"    > Incremental results saved")


def run_benchmark():
    ap = argparse.ArgumentParser()
    # Grid size is fixed to 3x3 for this benchmark version
    ap.add_argument("--shuffle-moves", type=int, default=10, help="Number of shuffle moves")
    args = ap.parse_args()

    print("--- Rubiks Slider Benchmark v2 (Prediction Based) ---")

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
    
    # Fixed grid size for this benchmark
    grid_size = 3
    
    print(f"\n--- Grid Size: {grid_size}x{grid_size} ---")
    shuffle = get_shuffle_sequence(grid_size)
    print(f"  > Using {len(shuffle)} shuffle moves")

    for model in models:
        print(f"\n  --- Testing openrouter/{model} ---")
        
        # Phase 1: Qualifying Round
        print("  > Starting Phase 1 (Qualifying Round)...")
        result_p1 = run_benchmark_scenario(grid_size, model, shuffle, phase=1)
        
        run_data = {
            "phase": 1,
            "size": grid_size,
            "moves": result_p1["moves"],
            "solved": result_p1["solved"],
            "conversation": result_p1["conversation"],
            "time_spent": result_p1["time_spent"],
            "api_calls_made": result_p1["api_calls"],
            "predictions_total": result_p1["predictions_total"],
            "predictions_correct": result_p1["predictions_correct"],
            "prediction_accuracy": result_p1["prediction_accuracy"],
            "termination_reason": result_p1["termination_reason"]
        }
        model_results[model].append(run_data)
        save_incremental_log(model, model_results[model], timestamp, run_dir)
        
        status_p1 = "PASSED" if result_p1["solved"] else f"FAILED ({result_p1['termination_reason']})"
        print(f"    > Phase 1 Result: {status_p1}")
        print(f"      Stats: api_calls={result_p1['api_calls']}, moves={result_p1['moves']}, accuracy={result_p1['prediction_accuracy']:.1f}%")

        if result_p1["solved"]:
            # Phase 2: Full Benchmark
            print("  > Starting Phase 2 (Full Benchmark)...")
            # Use same shuffle for consistency or new one? 
            # Usually benchmarks might use same problem or harder. 
            # Task says "Phase 2 (Full Benchmark)... Purpose: Test compound action reasoning"
            # Implies we should probably use the same starting state but allow multi-moves.
            # Or maybe a fresh shuffle to avoid memory? 
            # Let's use the same shuffle to see if they can solve it faster/better with multi-moves, 
            # OR a new shuffle to test generalizability. 
            # Given "Pass Criteria: Solve puzzle", let's use a fresh shuffle to ensure it's a robust test.
            shuffle_p2 = get_shuffle_sequence(grid_size)
            result_p2 = run_benchmark_scenario(grid_size, model, shuffle_p2, phase=2)
            
            run_data_p2 = {
                "phase": 2,
                "size": grid_size,
                "moves": result_p2["moves"],
                "solved": result_p2["solved"],
                "conversation": result_p2["conversation"],
                "time_spent": result_p2["time_spent"],
                "api_calls_made": result_p2["api_calls"],
                "predictions_total": result_p2["predictions_total"],
                "predictions_correct": result_p2["predictions_correct"],
                "prediction_accuracy": result_p2["prediction_accuracy"],
                "termination_reason": result_p2["termination_reason"]
            }
            model_results[model].append(run_data_p2)
            save_incremental_log(model, model_results[model], timestamp, run_dir)
            
            status_p2 = "PASSED" if result_p2["solved"] else f"FAILED ({result_p2['termination_reason']})"
            print(f"    > Phase 2 Result: {status_p2}")
            print(f"      Stats: api_calls={result_p2['api_calls']}, moves={result_p2['moves']}, accuracy={result_p2['prediction_accuracy']:.1f}%")
        else:
            print("    > Skipping Phase 2 (Phase 1 Failed)")

    print("\n--- Benchmark Complete ---")
    for model, results in model_results.items():
        passed_p1 = any(r["phase"] == 1 and r["solved"] for r in results)
        passed_p2 = any(r["phase"] == 2 and r["solved"] for r in results)
        print(f"  openrouter/{model}: Phase 1={'PASS' if passed_p1 else 'FAIL'}, Phase 2={'PASS' if passed_p2 else 'FAIL' if passed_p1 else 'N/A'}")


if __name__ == "__main__":
    run_benchmark()