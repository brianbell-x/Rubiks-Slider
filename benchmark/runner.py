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

from .providers import chat, UsageInfo
from .display import BenchmarkDashboard, console
from core.puzzle import Puzzle, parse_simple_move

# #region agent log
LOG_PATH = r"c:\dev\Rubiks-Slider-Lite\.cursor\debug.log"
def _log_debug(session_id, run_id, hypothesis_id, location, message, data):
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"sessionId": session_id, "runId": run_id, "hypothesisId": hypothesis_id, "location": location, "message": message, "data": data, "timestamp": time.time() * 1000}) + "\n")
    except Exception as e:
        pass
# #endregion

LOG_DIR = Path("benchmark/logs")
LOG_DIR.mkdir(exist_ok=True)
CONFIG_FILE = "benchmark/config.yaml"

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
        return {"models": [], "attempts": 1, "seed": None}
    cfg = read_yaml_file(config_path)
    if not cfg:
        return {"models": [], "attempts": 1, "seed": None}
    return {
        "models": cfg.get("models", []),
        "attempts": cfg.get("attempts", 1),
        "seed": cfg.get("seed")
    }


INSTRUCTIONS_TEXT_PHASE1 = """Your prediction must be where tile {prediction_tile} will be AFTER your move, not where it is now.

1. Decide on your next move.
2. Simulate that move mentally and determine where tile {prediction_tile} ends up.
3. Output your move in `<move>` tags and your prediction in `<prediction>` tags.

Example: If tile 3 is at R1C2 and you move R1 L, tile 3 moves to R1C1:
`<move>R1 L</move><prediction>R1C1</prediction>`

Output exactly one move per turn. No reasoning or explanations needed."""

INSTRUCTIONS_TEXT_PHASE2 = """Your prediction must be where tile {prediction_tile} will be AFTER your move(s), not where it is now.

1. Decide on your next move or sequence of moves.
2. Simulate the moves mentally and determine where tile {prediction_tile} ends up.
3. Output your move(s) in `<move>` tags and your prediction in `<prediction>` tags.

Example: `<move>R1 L; C2 U</move><prediction>R2C1</prediction>`

You may output multiple moves per turn, separated by semicolons (`;`). No reasoning or explanations needed."""


def build_prompt(mode: str, puzzle: Puzzle, grid_size: int, move_count: int, phase: int, prediction_tile: int) -> str:
    base_state_block = f"```\n{puzzle.get_labeled_state_string()}\n```"
    
    # #region agent log
    current_tile_pos = puzzle.get_tile_position(prediction_tile)
    current_pos_str = f"R{current_tile_pos[0]}C{current_tile_pos[1]}" if current_tile_pos else None
    board_state_str = puzzle.get_labeled_state_string()
    _log_debug("debug-session", "run1", "A", "runner.py:109", "Prompt build - current tile position", {"prediction_tile": prediction_tile, "current_position": current_pos_str, "mode": mode, "move_count": move_count, "board_state": board_state_str})
    # #endregion
    
    instructions_template = INSTRUCTIONS_TEXT_PHASE1 if phase == 1 else INSTRUCTIONS_TEXT_PHASE2
    instructions = instructions_template.format(prediction_tile=prediction_tile)
    
    prediction_text = f"""**Prediction Task:**

Predict where tile {prediction_tile} will be AFTER you apply your move(s), not where it is now.

Example:
- Tile 5 is at R2C1, you move C1 U (column 1 up)
- After C1 U: tile 5 moves from R2C1 → R1C1
- Predict R1C1 (the position after the move)

Process:
1. Note where tile {prediction_tile} currently is
2. Decide your move(s)
3. Simulate the move(s) and find where tile {prediction_tile} ends up
4. Report that new position

Format: <prediction>R#C#</prediction>"""
    
    # #region agent log
    _log_debug("debug-session", "run1", "C", "runner.py:110", "Prediction text wording", {"prediction_text": prediction_text, "contains_currently": "currently showing" in prediction_text, "contains_after": "After your move(s)" in prediction_text})
    # #endregion

    if mode == "initial":
        solved_board_str = "\n".join(" ".join(row) for row in puzzle.solved_board)
        return f"""# Welcome to Rubiks Slider!

**How to play:**

- You can shift rows left (L) or right (R).
  - Example: `R1 L` shifts row 1 left.
    ```
       C1 C2 C3
    R1  1  2  3
    R2  4  5  6
    R3  7  8  9
    ```
    becomes:
    ```
       C1 C2 C3
    R1  2  3  1
    R2  4  5  6
    R3  7  8  9
    ```
- You can shift columns up (U) or down (D).
  - Example: `C2 D` shifts column 2 down.
    ```
       C1 C2 C3
    R1  1  2  3
    R2  4  5  6
    R3  7  8  9
    ```
    becomes:
    ```
       C1 C2 C3
    R1  1  8  3
    R2  4  2  6
    R3  7  5  9
    ```

**Understanding Tiles:** Each cell contains a numbered tile. In a 3x3 puzzle, tiles are numbered 1-9. When you move a row or column, the tiles in that row/column shift together.

**Goal:** Return Rubiks Slider to the solved state:

```
{solved_board_str}
```

**Board State (Before Your Move):**

{base_state_block}

**Moves made:** 0

{prediction_text}

**Instructions:**

{instructions}"""

    if mode == "failed_parse":
        return f"""## Your previous response could not be parsed.

Please carefully output your next move(s) and prediction using the following format:

- Enclose your move(s) in <move>...</move> tags.
- Enclose your prediction in <prediction>...</prediction> tags.
- Example: 
<move>R1 L</move>
<prediction>R1C3</prediction>

## Board State (Before Your Move) ({grid_size}x{grid_size})

{base_state_block}

**Moves made:** {move_count}

{prediction_text}"""

    return f"""**Moves made:** {move_count}

{prediction_text}

## Board State (Before Your Move) ({grid_size}x{grid_size})

{base_state_block}

**Instructions:**

{instructions}"""


def invoke_model(messages, model):
    start = time.time()
    reply, reasoning, usage_info = chat(messages, model)
    return reply, reasoning, time.time() - start, usage_info


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


def run_benchmark_scenario(grid_size, model, shuffle_sequence, phase: int,
                           attempt: int = 1, total_attempts: int = 1):
    """Run a single benchmark scenario with live dashboard."""
    puzzle = Puzzle(size=grid_size, auto_shuffle=False)
    apply_shuffle_sequence(puzzle, shuffle_sequence, grid_size)

    if puzzle.is_solved():
        return {
            "solved": True,
            "turns": 0,
            "moves": 0,
            "time_spent": 0.0,
            "conversation": [],
            "termination_reason": "Already Solved",
            "predictions_total": 0,
            "predictions_correct": 0,
            "predictions_wrong": 0,
            "prediction_accuracy": 0.0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost": 0.0
        }

    # Initialize dashboard
    dashboard = BenchmarkDashboard(
        model=model,
        phase=phase,
        attempt=attempt,
        total_attempts=total_attempts
    )
    dashboard.grid_size = grid_size
    dashboard.start()

    try:
        turns = 0
        move_count = 0
        conversation = []
        total_time = 0.0
        failed_parse_last = False
        consecutive_wrong_predictions = 0
        predictions_total = 0
        predictions_correct = 0
        predictions_wrong = 0
        prediction_tile = None
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_cost = 0.0

        while not puzzle.is_solved():
            dashboard.increment_turn()

            # Store board state before move
            before_board = [row[:] for row in puzzle.board]

            if failed_parse_last:
                mode = "failed_parse"
                # Keep same prediction tile for retry
            elif not conversation:
                mode = "initial"
                prediction_tile = random.randint(1, grid_size * grid_size)
            else:
                mode = "followup"
                prediction_tile = random.randint(1, grid_size * grid_size)

            # #region agent log
            current_tile_pos = puzzle.get_tile_position(prediction_tile)
            _log_debug("debug-session", "run1", "E", "runner.py:290", "Before prompt build - current tile position", {"prediction_tile": prediction_tile, "current_position": f"R{current_tile_pos[0]}C{current_tile_pos[1]}" if current_tile_pos else None, "board_state": [row[:] for row in puzzle.board], "turn": turns + 1, "conversation_length": len(conversation)})
            # #endregion

            # Update dashboard with prediction target
            dashboard.set_prediction_target(prediction_tile)

            prompt = build_prompt(mode, puzzle, grid_size, move_count, phase, prediction_tile)
            # #region agent log
            current_state_blocks_in_history = sum(1 for msg in conversation if "Current State" in msg.get("content", "") or "Board State" in msg.get("content", ""))
            _log_debug("debug-session", "post-fix", "B", "runner.py:340", "Conversation history analysis", {"history_length": len(conversation), "current_state_blocks_count": current_state_blocks_in_history, "has_multiple_states": current_state_blocks_in_history > 1, "last_user_msg_has_state": "Board State" in (conversation[-1].get("content", "") if conversation else "")})
            _log_debug("debug-session", "post-fix", "C", "runner.py:341", "Prompt structure check", {"prompt_contains_board_state": "Board State" in prompt, "prompt_contains_before_move": "Before Your Move" in prompt, "prompt_contains_after": "AFTER" in prompt or "after" in prompt.lower(), "prompt_contains_simulate": "SIMULATE" in prompt or "simulate" in prompt.lower(), "prompt_contains_warning": "WARNING" in prompt or "Do NOT report" in prompt, "prediction_text_first": prompt.find("PREDICTION") < prompt.find("Instructions") if "Instructions" in prompt else True, "mode": mode})
            # #endregion
            messages = conversation + [{"role": "user", "content": prompt}]
            
            # #region agent log
            _log_debug("debug-session", "post-fix", "PROMPT", "runner.py:354", "Full prompt being sent to API", {"total_messages": len(messages), "full_prompt": prompt, "conversation_history_length": len(conversation), "last_conversation_msg": conversation[-1] if conversation else None})
            # #endregion

            dashboard.set_thinking(True)
            reply, reasoning, wall_time, usage_info = invoke_model(messages, model)
            dashboard.set_thinking(False)
            
            # #region agent log
            _log_debug("debug-session", "post-fix", "RESPONSE", "runner.py:361", "Full API response received", {"full_reply": reply, "reasoning": reasoning, "wall_time": wall_time, "usage_info": {"prompt_tokens": usage_info.prompt_tokens, "completion_tokens": usage_info.completion_tokens, "total_tokens": usage_info.total_tokens, "cost": usage_info.cost}})
            # #endregion

            total_time += wall_time
            total_prompt_tokens += usage_info.prompt_tokens
            total_completion_tokens += usage_info.completion_tokens
            total_cost += usage_info.cost
            dashboard.update_usage(total_prompt_tokens, total_completion_tokens, total_cost)
            turns += 1

            conversation.append({"role": "user", "content": prompt})
            conversation.append({"role": "assistant", "content": reply, "reasoning": reasoning})

            extracted_moves = parse_moves(reply, grid_size)
            extracted_prediction = parse_prediction(reply)

            # #region agent log
            current_tile_pos_before_move = puzzle.get_tile_position(prediction_tile)
            current_pos_before_str = f"R{current_tile_pos_before_move[0]}C{current_tile_pos_before_move[1]}" if current_tile_pos_before_move else None
            move_decided_first = extracted_moves is not None and extracted_prediction is not None
            prediction_before_move = extracted_prediction is not None and extracted_moves is None
            _log_debug("debug-session", "post-fix", "PARSE", "runner.py:383", "Response parsing results", {"extracted_prediction": extracted_prediction, "extracted_moves": extracted_moves, "move_decided_first": move_decided_first, "prediction_before_move": prediction_before_move, "current_tile_position_before_move": current_pos_before_str, "prediction_matches_current": extracted_prediction == current_pos_before_str})
            # #endregion

            if extracted_moves is None:
                if not failed_parse_last:
                    failed_parse_last = True
                    continue
                dashboard.stop()
                return {
                    "solved": False,
                    "turns": turns,
                    "moves": move_count,
                    "time_spent": total_time,
                    "conversation": conversation,
                    "termination_reason": "Invalid Move/Response Format",
                    "predictions_total": predictions_total,
                    "predictions_correct": predictions_correct,
                    "predictions_wrong": predictions_wrong,
                    "prediction_accuracy": (predictions_correct / predictions_total * 100) if predictions_total > 0 else 0.0,
                    "total_prompt_tokens": total_prompt_tokens,
                    "total_completion_tokens": total_completion_tokens,
                    "total_cost": total_cost
                }

            # Check if prediction is missing or invalid format (counts as wrong prediction)
            if extracted_prediction is None:
                consecutive_wrong_predictions += 1
                predictions_total += 1
                predictions_wrong += 1
                dashboard.record_prediction_result(
                    f"Where will tile {prediction_tile} be?",
                    "(missing/invalid)",
                    False
                )
            else:
                # Validate moves first
                moves_valid = True
                temp_puzzle = Puzzle(size=grid_size, auto_shuffle=False)
                temp_puzzle.board = [row[:] for row in puzzle.board]

                for move_dict in extracted_moves:
                    success, _ = temp_puzzle.apply_move_from_json(json.dumps(move_dict))
                    if not success:
                        moves_valid = False
                        break

                if not moves_valid:
                    dashboard.stop()
                    return {
                        "solved": False,
                        "turns": turns,
                        "moves": move_count,
                        "time_spent": total_time,
                        "conversation": conversation,
                        "termination_reason": "Invalid Move Applied",
                        "predictions_total": predictions_total,
                        "predictions_correct": predictions_correct,
                        "predictions_wrong": predictions_wrong,
                        "prediction_accuracy": (predictions_correct / predictions_total * 100) if predictions_total > 0 else 0.0,
                        "total_prompt_tokens": total_prompt_tokens,
                        "total_completion_tokens": total_completion_tokens,
                        "total_cost": total_cost
                    }

                # Moves are valid, check prediction on temp_puzzle (which has moves applied)
                # #region agent log
                future_tile_pos = temp_puzzle.get_tile_position(prediction_tile)
                current_tile_pos_for_validation = puzzle.get_tile_position(prediction_tile)
                current_pos_str_for_val = f"R{current_tile_pos_for_validation[0]}C{current_tile_pos_for_validation[1]}" if current_tile_pos_for_validation else None
                future_pos_str = f"R{future_tile_pos[0]}C{future_tile_pos[1]}" if future_tile_pos else None
                _log_debug("debug-session", "run1", "A", "runner.py:430", "Prediction validation - all positions", {"prediction_tile": prediction_tile, "predicted_position": extracted_prediction, "current_position_before_move": current_pos_str_for_val, "actual_future_position": future_pos_str, "moves_applied": [json.dumps(m) for m in extracted_moves], "prediction_equals_current": extracted_prediction == current_pos_str_for_val, "prediction_equals_future": extracted_prediction == future_pos_str, "is_correct_prediction": extracted_prediction == future_pos_str})
                _log_debug("debug-session", "run1", "E", "runner.py:431", "State comparison - tile movement", {"before_board": [row[:] for row in puzzle.board], "after_board": [row[:] for row in temp_puzzle.board], "tile_moved": current_pos_str_for_val != future_pos_str, "tile_current_pos": current_pos_str_for_val, "tile_future_pos": future_pos_str})
                # #endregion
                is_correct = temp_puzzle.validate_prediction(prediction_tile, extracted_prediction)
                predictions_total += 1

                if is_correct:
                    consecutive_wrong_predictions = 0
                    predictions_correct += 1
                else:
                    consecutive_wrong_predictions += 1
                    predictions_wrong += 1

                # Update dashboard with boards and prediction result
                after_board = [row[:] for row in temp_puzzle.board]
                move_str = "; ".join(
                    f"{'R' if m['type'] == 'row' else 'C'}{m['index']} {m['direction'][0].upper()}"
                    for m in extracted_moves
                )
                dashboard.set_boards(before_board, after_board, move_str)
                dashboard.record_prediction_result(
                    f"Where will tile {prediction_tile} be?",
                    extracted_prediction,
                    is_correct
                )

            if consecutive_wrong_predictions >= 3:
                dashboard.stop()
                return {
                    "solved": False,
                    "turns": turns,
                    "moves": move_count,
                    "time_spent": total_time,
                    "conversation": conversation,
                    "termination_reason": "Unable to predict consequences",
                    "predictions_total": predictions_total,
                    "predictions_correct": predictions_correct,
                    "predictions_wrong": predictions_wrong,
                    "prediction_accuracy": (predictions_correct / predictions_total * 100) if predictions_total > 0 else 0.0,
                    "total_prompt_tokens": total_prompt_tokens,
                    "total_completion_tokens": total_completion_tokens,
                    "total_cost": total_cost
                }

            failed_parse_last = False

            # Apply moves to actual puzzle
            for move_dict in extracted_moves:
                puzzle.apply_move_from_json(json.dumps(move_dict))
                move_count += 1
                if puzzle.is_solved():
                    break

            dashboard.add_moves(len(extracted_moves))

        dashboard.stop()
        return {
            "solved": True,
            "turns": turns,
            "moves": move_count,
            "time_spent": total_time,
            "conversation": conversation,
            "termination_reason": "Solved",
            "predictions_total": predictions_total,
            "predictions_correct": predictions_correct,
            "predictions_wrong": predictions_wrong,
            "prediction_accuracy": (predictions_correct / predictions_total * 100) if predictions_total > 0 else 0.0,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_cost": total_cost
        }

    finally:
        # Ensure dashboard is stopped even on exceptions
        if dashboard.live:
            dashboard.stop()


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

    console.print("[bold blue]--- Rubiks Slider Benchmark v2 (Prediction Based) ---[/]")

    config = read_benchmarks_config()
    models = config["models"]
    attempts = config["attempts"]
    seed = config["seed"]

    if not models:
        console.print("[red]No models found in config. Exiting.[/]")
        sys.exit(1)

    # Seed the random generator if configured
    if seed is not None:
        random.seed(seed)
        console.print(f"[dim][*] Using seed: {seed} (all models will get the same shuffles)[/]")

    timestamp = now_timestamp()
    run_dir = os.path.join(LOG_DIR, timestamp)
    ensure_directory(run_dir)
    console.print(f"[dim][*] Log directory: {run_dir}[/]")

    model_configs = [{"model": model, "attempts": attempts} for model in models]

    model_results = defaultdict(list)

    # Fixed grid size for this benchmark
    grid_size = 3

    # Pre-generate all shuffle sequences so all models get the same boards
    console.print(f"\n[bold]--- Generating shuffle sequences ---[/]")
    shuffle_p1 = get_shuffle_sequence(grid_size)
    shuffle_p2_3x3 = get_shuffle_sequence(grid_size)
    shuffle_p2_4x4 = get_shuffle_sequence(4)
    console.print(f"  [dim]> Phase 1 (3x3): {len(shuffle_p1)} moves[/]")
    console.print(f"  [dim]> Phase 2 (3x3): {len(shuffle_p2_3x3)} moves[/]")
    console.print(f"  [dim]> Phase 2 (4x4): {len(shuffle_p2_4x4)} moves[/]")

    for model_cfg in model_configs:
        model = model_cfg["model"]
        total_attempts = model_cfg["attempts"]
        console.print(f"\n  [bold cyan]--- Testing openrouter/{model} ---[/]")

        # Phase 1: Qualifying Round
        console.print("  [yellow]> Starting Phase 1 (Qualifying Round)...[/]")
        result_p1 = run_benchmark_scenario(grid_size, model, shuffle_p1, phase=1, attempt=1, total_attempts=total_attempts)

        run_data = {
            "phase": 1,
            "size": grid_size,
            "moves": result_p1["moves"],
            "solved": result_p1["solved"],
            "conversation": result_p1["conversation"],
            "time_spent": result_p1["time_spent"],
            "turns": result_p1["turns"],
            "predictions_total": result_p1["predictions_total"],
            "predictions_correct": result_p1["predictions_correct"],
            "predictions_wrong": result_p1["predictions_wrong"],
            "prediction_accuracy": result_p1["prediction_accuracy"],
            "termination_reason": result_p1["termination_reason"],
            "total_prompt_tokens": result_p1["total_prompt_tokens"],
            "total_completion_tokens": result_p1["total_completion_tokens"],
            "total_cost": result_p1["total_cost"]
        }
        model_results[model].append(run_data)
        save_incremental_log(model, model_results[model], timestamp, run_dir)

        if result_p1["solved"]:
            console.print(f"    [bold green]> Phase 1 Result: PASSED[/]")
        else:
            console.print(f"    [bold red]> Phase 1 Result: FAILED ({result_p1['termination_reason']})[/]")
        total_tokens_p1 = result_p1['total_prompt_tokens'] + result_p1['total_completion_tokens']
        console.print(f"      [dim]Stats: turns={result_p1['turns']}, moves={result_p1['moves']}, accuracy={result_p1['prediction_accuracy']:.1f}%[/]")
        console.print(f"      [dim]Tokens: prompt={result_p1['total_prompt_tokens']}, completion={result_p1['total_completion_tokens']}, total={total_tokens_p1}, cost=${result_p1['total_cost']:.4f}[/]")

        if result_p1["solved"]:
            # Phase 2: Full Benchmark
            console.print("  [yellow]> Starting Phase 2 (Full Benchmark)...[/]")
            result_p2 = run_benchmark_scenario(grid_size, model, shuffle_p2_3x3, phase=2, attempt=1, total_attempts=total_attempts)

            run_data_p2 = {
                "phase": 2,
                "size": grid_size,
                "moves": result_p2["moves"],
                "solved": result_p2["solved"],
                "conversation": result_p2["conversation"],
                "time_spent": result_p2["time_spent"],
                "turns": result_p2["turns"],
                "predictions_total": result_p2["predictions_total"],
                "predictions_correct": result_p2["predictions_correct"],
                "predictions_wrong": result_p2["predictions_wrong"],
                "prediction_accuracy": result_p2["prediction_accuracy"],
                "termination_reason": result_p2["termination_reason"],
                "total_prompt_tokens": result_p2["total_prompt_tokens"],
                "total_completion_tokens": result_p2["total_completion_tokens"],
                "total_cost": result_p2["total_cost"]
            }
            model_results[model].append(run_data_p2)
            save_incremental_log(model, model_results[model], timestamp, run_dir)

            if result_p2["solved"]:
                console.print(f"    [bold green]> Phase 2 (3x3) Result: PASSED[/]")
            else:
                console.print(f"    [bold red]> Phase 2 (3x3) Result: FAILED ({result_p2['termination_reason']})[/]")
            total_tokens_p2 = result_p2['total_prompt_tokens'] + result_p2['total_completion_tokens']
            console.print(f"      [dim]Stats: turns={result_p2['turns']}, moves={result_p2['moves']}, accuracy={result_p2['prediction_accuracy']:.1f}%[/]")
            console.print(f"      [dim]Tokens: prompt={result_p2['total_prompt_tokens']}, completion={result_p2['total_completion_tokens']}, total={total_tokens_p2}, cost=${result_p2['total_cost']:.4f}[/]")

            if result_p2["solved"]:
                # Phase 2 (4x4): Extended Benchmark
                grid_size_4x4 = 4
                console.print("  [yellow]> Starting Phase 2 (4x4 Extended Benchmark)...[/]")
                result_p2_4x4 = run_benchmark_scenario(grid_size_4x4, model, shuffle_p2_4x4, phase=2, attempt=1, total_attempts=total_attempts)

                run_data_p2_4x4 = {
                    "phase": 2,
                    "size": grid_size_4x4,
                    "moves": result_p2_4x4["moves"],
                    "solved": result_p2_4x4["solved"],
                    "conversation": result_p2_4x4["conversation"],
                    "time_spent": result_p2_4x4["time_spent"],
                    "turns": result_p2_4x4["turns"],
                    "predictions_total": result_p2_4x4["predictions_total"],
                    "predictions_correct": result_p2_4x4["predictions_correct"],
                    "predictions_wrong": result_p2_4x4["predictions_wrong"],
                    "prediction_accuracy": result_p2_4x4["prediction_accuracy"],
                    "termination_reason": result_p2_4x4["termination_reason"],
                    "total_prompt_tokens": result_p2_4x4["total_prompt_tokens"],
                    "total_completion_tokens": result_p2_4x4["total_completion_tokens"],
                    "total_cost": result_p2_4x4["total_cost"]
                }
                model_results[model].append(run_data_p2_4x4)
                save_incremental_log(model, model_results[model], timestamp, run_dir)

                if result_p2_4x4["solved"]:
                    console.print(f"    [bold green]> Phase 2 (4x4) Result: PASSED[/]")
                else:
                    console.print(f"    [bold red]> Phase 2 (4x4) Result: FAILED ({result_p2_4x4['termination_reason']})[/]")
                total_tokens_p2_4x4 = result_p2_4x4['total_prompt_tokens'] + result_p2_4x4['total_completion_tokens']
                console.print(f"      [dim]Stats: turns={result_p2_4x4['turns']}, moves={result_p2_4x4['moves']}, accuracy={result_p2_4x4['prediction_accuracy']:.1f}%[/]")
                console.print(f"      [dim]Tokens: prompt={result_p2_4x4['total_prompt_tokens']}, completion={result_p2_4x4['total_completion_tokens']}, total={total_tokens_p2_4x4}, cost=${result_p2_4x4['total_cost']:.4f}[/]")
            else:
                console.print("    [dim]> Skipping Phase 2 (4x4) (Phase 2 3x3 Failed)[/]")
        else:
            console.print("    [dim]> Skipping Phase 2 (Phase 1 Failed)[/]")

    console.print("\n[bold blue]--- Benchmark Complete ---[/]")
    for model, results in model_results.items():
        passed_p1 = any(r["phase"] == 1 and r["solved"] for r in results)
        passed_p2_3x3 = any(r["phase"] == 2 and r["size"] == 3 and r["solved"] for r in results)
        passed_p2_4x4 = any(r["phase"] == 2 and r["size"] == 4 and r["solved"] for r in results)
        p1_status = "[green]PASS[/]" if passed_p1 else "[red]FAIL[/]"
        p2_3x3_status = "[green]PASS[/]" if passed_p2_3x3 else ("[red]FAIL[/]" if passed_p1 else "[dim]N/A[/]")
        p2_4x4_status = "[green]PASS[/]" if passed_p2_4x4 else ("[red]FAIL[/]" if passed_p2_3x3 else "[dim]N/A[/]")
        console.print(f"  openrouter/{model}: Phase 1={p1_status}, Phase 2 (3x3)={p2_3x3_status}, Phase 2 (4x4)={p2_4x4_status}")


if __name__ == "__main__":
    run_benchmark()