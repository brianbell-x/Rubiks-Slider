"""
Run with python -m benchmark.runner
"""

import json
import os
import sys
import time
import argparse
import pathlib
from collections import defaultdict

from .providers import chat
from core.puzzle import Puzzle, parse_simple_move
from .settings import (
    LOG_DIR,
    CONFIG_FILE,
    now_timestamp,
    get_shuffle_sequence,
    sanitize_model_name,
)

# -------------------- Utility Functions --------------------

def ensure_directory(path):
    """Ensure a directory exists."""
    os.makedirs(path, exist_ok=True)

def read_json_file(path):
    """Load a JSON file and return its contents, or None on error."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not read or parse JSON file {path}: {e}")
        return None

def write_json_file(data, path):
    """Save data as JSON to a file, ensuring the directory exists."""
    try:
        ensure_directory(os.path.dirname(path))
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving JSON to {path}: {e}")

# -------------------- Config Loading --------------------

def read_benchmarks_config():
    """Load benchmark run configurations from the config file."""
    config_path = pathlib.Path(CONFIG_FILE)
    if config_path.exists():
        cfg = read_json_file(config_path)
        if not cfg:
            return []
        bench_list = cfg.get("benchmarks", [])
        if not isinstance(bench_list, list):
            print(f"Warning: 'benchmarks' in {CONFIG_FILE} is not a list. Using empty run list.")
            return []
        return bench_list
    print(f"Config not found → {CONFIG_FILE}. Using empty run list.")
    return []

# -------------------- Prompt Construction --------------------

INSTRUCTIONS_TEXT = """- Output your next move or sequence of moves (e.g., `R1 L`, `C2 U`, or `R1 L; C2 U; R3 R`) inside `<move>` tags.
- Example: `<move>R1 L; C2 U</move>`
- Do NOT include any reasoning or explanations. Only output your move(s) in the required format.
- You must respond with at least one move inside `<move>` tags."""

def build_prompt(mode: str, puzzle: Puzzle, grid_size: int, move_count: int) -> str:
    """
    Build a user prompt. Modes:
      - "initial": full instructions + examples + **Current State:** marker
      - "followup": current state + instructions
      - "failed_parse": previous move(s) could not be parsed + current state + instructions
    """
    base_state_block = "\n".join([
        "```",
        puzzle.get_state_string(formatted=False),
        "```",
    ])

    if mode == "initial":
        solved_board_str = "\n".join(" ".join(row) for row in puzzle.solved_board)
        ex_board_before_row_str = "A B C\nD E F\nG H I"
        ex_board_after_row_str = "B C A\nD E F\nG H I"
        ex_board_before_col_str = "A B C\nD E F\nG H I"
        ex_board_after_col_str = "A H C\nD B F\nG E I"
        lines = [
            "# Welcome to Rubiks Slider!",
            "",
            "**Instructions:**",
            "",
            INSTRUCTIONS_TEXT,
            "",
            "**How to play:**",
            "",
            "- You can shift rows left (L) or right (R).",
            "  - Example: `R1 L` shifts row 1 left.",
            "    ```",
            f"{ex_board_before_row_str}",
            "    ```",
            "    becomes:",
            "    ```",
            f"{ex_board_after_row_str}",
            "    ```",
            "- You can shift columns up (U) or down (D).",
            "  - Example: `C2 D` shifts column 2 down.",
            "    ```",
            f"{ex_board_before_col_str}",
            "    ```",
            "    becomes:",
            "    ```",
            f"{ex_board_after_col_str}",
            "    ```",
            "- You may output multiple moves per turn, separated by semicolons (`;`).",
            "",
            "**Goal:** Return Rubiks Slider to the solved state:",
            "",
            "```",
            solved_board_str,
            "```",
            "",
            "**Current State:**",
            "",
            base_state_block,
            "",
            "**Moves made:** 0",
        ]
        return "\n".join(lines)

    if mode == "failed_parse":
        return "\n".join([
            "## Your previous move(s) could not be parsed.",
            "",
            "Please carefully output your next move or sequence of moves using the following format:",
            "",
            "- Enclose your move(s) in <move>...</move> tags.",
            "- Each move should be in the form `R1 L`, `C2 U`, etc. (e.g., `R1 L; C2 U; R3 R` for multiple moves, separated by semicolons).",
            "- Example: `<move>R1 L; C2 U</move>`",
            "- Do not include any other formatting or explanations inside the <move> tags.",
            "",
            f"## Current State ({grid_size}x{grid_size})",
            "",
            base_state_block,
            "",
            f"**Moves made:** {move_count}",
        ])

    # followup
    return "\n".join([
        f"## Current State ({grid_size}x{grid_size})",
        "",
        base_state_block,
        "",
        f"**Moves made:** {move_count}",
        "",
        "**Instructions:**",
        "",
        INSTRUCTIONS_TEXT,
    ])

# -------------------- LLM Call + Parsing --------------------

def invoke_model(messages, provider, model, model_config):
    """
    Call provider.chat and return (reply, reasoning, wall_time, run_errors).
    On failure, reply is None and run_errors contains a single error dict.
    """
    start = time.time()
    try:
        reply, reasoning = chat(messages, provider, model, model_config)
    except RuntimeError as e:
        return None, None, 0.0, [{"type": "API Error", "details": f"API Error: {str(e)}"}]
    except Exception as e:
        return None, None, 0.0, [{"type": "API Call Exception", "details": f"API Call Exception: {str(e)}"}]
    wall = time.time() - start
    if reply is None:
        return None, None, wall, [{"type": "API Error", "details": "API call failed or returned None."}]
    return reply, reasoning, wall, []

def parse_moves(response_text: str, grid_size: int):
    """
    Extract and parse one or more moves from the LLM's response.
    Returns a list of move dicts, or None on error.
    """
    import re
    match = re.search(r"<move>(.*?)</move>", response_text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    move_block = match.group(1).strip()
    if not move_block:
        return None
    # Split on semicolons or newlines, allow for multiple moves
    move_strs = [m.strip() for m in re.split(r"[;\n]", move_block) if m.strip()]
    move_dicts = []
    for simple_move_str in move_strs:
        json_move_str, error_msg = parse_simple_move(simple_move_str, grid_size)
        if error_msg:
            return None
        try:
            move_dict = json.loads(json_move_str)
            move_dicts.append(move_dict)
        except Exception:
            return None
    if not move_dicts:
        return None
    return move_dicts

def append_conversation_turn(prompt: str, reply: str, reasoning: str | None):
    """Create conversation history entries for user prompt and assistant reply."""
    return [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": reply, "reasoning": reasoning},
    ]

# -------------------- Scenario Helpers --------------------

def apply_shuffle_sequence(puzzle: Puzzle, shared_shuffle_sequence, grid_size: int):
    """
    Apply a validated shuffle sequence to the Rubiks Slider board.
    Returns (ok: bool, error_message: str | None, move_json: str | None).
    """
    valid_shuffle_sequence = [
        move for move in shared_shuffle_sequence
        if 1 <= move.get("index", -1) <= grid_size
    ]
    for move in valid_shuffle_sequence:
        move_json = json.dumps(move)
        success, message = puzzle.apply_move_from_json(move_json)
        if not success:
            return False, f"Shared Shuffle Error: {message}", move_json
    return True, None, None

def build_run_result(
    termination_reason,
    solved,
    puzzle,
    api_calls_made,
    total_individual_moves_applied,
    llm_move_sequence,
    error_message,
    time_spent,
    conversation_history,
    run_errors,
):
    """Construct the benchmark result dictionary."""
    return {
        "summary": {
            "termination_reason": termination_reason,
            "error_message": error_message,
            "solved": solved,
            "api_calls_made": api_calls_made,
            "total_individual_moves_applied": total_individual_moves_applied,
            "final_board_state": puzzle.get_state_string(formatted=False),
            "llm_move_sequence": llm_move_sequence,
            "time_spent": time_spent,
        },
        "conversation_history": conversation_history,
        "run_errors": run_errors,
    }

# -------------------- Benchmark Scenario --------------------

def run_benchmark_scenario(
    grid_size,
    provider,
    model,
    shared_shuffle_sequence,
    model_config=None,
):
    """Run a single benchmark scenario for a given model and Rubiks Slider configuration."""
    puzzle = Puzzle(size=grid_size, auto_shuffle=False)

    ok, shuffle_err, shuffle_move_json = apply_shuffle_sequence(puzzle, shared_shuffle_sequence, grid_size)
    if not ok:
        print(f"ERROR applying shared shuffle move: {shuffle_err} - {shuffle_move_json}")
        return build_run_result(
            termination_reason="Internal Shuffle Error",
            solved=False,
            puzzle=puzzle,
            api_calls_made=0,
            total_individual_moves_applied=0,
            llm_move_sequence=[],
            error_message=shuffle_err,
            time_spent=0.0,
            conversation_history=[],
            run_errors=[{"type": "Shuffle Error", "details": shuffle_err}],
        )

    if puzzle.is_solved():
        return build_run_result(
            termination_reason="Already Solved",
            solved=True,
            puzzle=puzzle,
            api_calls_made=0,
            total_individual_moves_applied=0,
            llm_move_sequence=[],
            error_message=None,
            time_spent=0.0,
            conversation_history=[],
            run_errors=[],
        )

    return run_game_loop(
        puzzle=puzzle,
        grid_size=grid_size,
        provider=provider,
        model=model,
        shared_shuffle_sequence=shared_shuffle_sequence,
        model_config=model_config,
    )

def run_game_loop(
    puzzle,
    grid_size,
    provider,
    model,
    shared_shuffle_sequence,
    model_config,
):
    """Main loop for LLM move generation and Rubiks Slider solving."""
    individual_move_counter = 0
    api_call_counter = 0
    llm_move_sequence = []
    termination_reason = ""
    conversation_history = []
    run_errors = []
    error_message = None
    total_time_spent = 0.0
    FIXED_LIMITS = {3: 50, 4: 100, 5: 200, 6: 400}
    max_moves_allowed = FIXED_LIMITS.get(grid_size, len(shared_shuffle_sequence))

    failed_parse_last_turn = False

    while not puzzle.is_solved():
        if individual_move_counter >= max_moves_allowed:
            termination_reason = "Exceeded Move Limit"
            break

        print(f"    > Attempting call {api_call_counter + 1} ...")

        # Determine prompt mode
        if failed_parse_last_turn:
            mode = "failed_parse"
        elif not conversation_history:  # first turn
            mode = "initial"
        else:
            mode = "followup"

        prompt = build_prompt(mode, puzzle, grid_size, individual_move_counter)
        api_messages = (conversation_history or []) + [{"role": "user", "content": prompt}]

        reply, reasoning, api_wall_time, api_errors = invoke_model(
            api_messages, provider, model, model_config
        )
        total_time_spent += api_wall_time
        api_call_counter += 1

        if api_errors:
            termination_reason = "API Error"
            error_message = api_errors[0].get("details")
            # annotate with api_call_number
            for err in api_errors:
                if "api_call_number" not in err:
                    err["api_call_number"] = api_call_counter
            run_errors.extend(api_errors)
            break

        # Record conversation only when we have a reply
        conversation_history.extend(append_conversation_turn(prompt, reply, reasoning))

        extracted_moves = parse_moves(reply, grid_size)
        if extracted_moves is None:
            if not failed_parse_last_turn:
                failed_parse_last_turn = True
                continue

            termination_reason = "Invalid Move/Response Format"
            error_message = "Failed to parse a valid move or moves from LLM response."
            last_response = conversation_history[-1]["content"] if conversation_history else ""
            run_errors.append({
                "type": "Parsing Failure",
                "api_call_number": api_call_counter,
                "response_content": last_response,
                "details": error_message
            })
            break
        else:
            failed_parse_last_turn = False

        for move_dict in extracted_moves:
            if individual_move_counter >= max_moves_allowed:
                termination_reason = "Exceeded Move Limit"
                break

            move_json_string = ""
            try:
                move_json_string = json.dumps(move_dict)
                success, message = puzzle.apply_move_from_json(move_json_string)
            except TypeError as e:
                termination_reason = "Move Serialization Error"
                error_message = f"Error serializing extracted move to JSON: {e}"
                run_errors.append({
                    "type": "Move Serialization Error",
                    "api_call_number": api_call_counter,
                    "move_dict": move_dict,
                    "details": error_message
                })
                break
            except Exception as apply_e:
                termination_reason = "Move Apply Exception"
                error_message = f"Move Apply Exception: {str(apply_e)}"
                run_errors.append({
                    "type": "Move Apply Exception",
                    "api_call_number": api_call_counter,
                    "move_json": move_json_string,
                    "details": error_message
                })
                break

            if success:
                llm_move_sequence.append(move_dict)
                individual_move_counter += 1
                if puzzle.is_solved():
                    break
            else:
                termination_reason = "Invalid Move Applied"
                error_message = f"Failed to apply LLM move: {message}"
                run_errors.append({
                    "type": "Invalid Move Applied",
                    "api_call_number": api_call_counter,
                    "move_json": move_json_string,
                    "details": error_message
                })
                break

        if termination_reason:
            break

    if not termination_reason:
        termination_reason = "Solved" if puzzle.is_solved() else "Unknown (Loop Exit)"

    solved_status = puzzle.is_solved()
    return build_run_result(
        termination_reason=termination_reason,
        solved=solved_status,
        puzzle=puzzle,
        api_calls_made=api_call_counter,
        total_individual_moves_applied=individual_move_counter,
        llm_move_sequence=llm_move_sequence,
        error_message=error_message,
        time_spent=total_time_spent,
        conversation_history=conversation_history,
        run_errors=run_errors,
    )

# -------------------- Incremental Logging --------------------

def save_incremental_log(provider, model, results, main_run_timestamp, main_run_dir):
    """Save the current results for a model incrementally."""
    model_id = f"{provider}_{sanitize_model_name(model)}"
    max_solved_size = max((lvl.get("size", 0) for lvl in results.get("attempts", []) if lvl.get("solved")), default=0)
    log_data = {
        "provider": provider,
        "model": model,
        "attempts": results.get("attempts", []),
        "timestamp": main_run_timestamp,
        "max_solved_size": max_solved_size,
    }
    model_dir = os.path.join(main_run_dir, model_id)
    log_file_path = os.path.join(model_dir, f"{model_id}_results.json")
    write_json_file(log_data, log_file_path)
    print(f"    > Incremental results saved: {log_file_path}")

# -------------------- Model Validation & Preparation --------------------

def prepare_model_runs(benchmark_configs):
    """Validate and prepare model configurations for the benchmark."""
    model_results = defaultdict(
        lambda: {
            "attempts": [],
            "active": True,
            "attempts_completed": 0,
            "config": {},
        }
    )
    all_models_to_run = []
    valid_configs = True
    for i, config_entry in enumerate(benchmark_configs):
        provider = config_entry.get("provider")
        model = config_entry.get("model")
        attempts = config_entry.get("attempts", 1)
        if not provider:
            print(f"Error: Config entry #{i+1} is missing mandatory 'provider'. Skipping entry: {config_entry}")
            valid_configs = False
            continue
        if not model:
            print(f"Error: Config entry #{i+1} for provider '{provider}' is missing mandatory 'model'. Skipping entry: {config_entry}")
            valid_configs = False
            continue
        model_key = (provider, model)
        all_models_to_run.append(model_key)
        model_results[model_key]["config"] = {"attempts": attempts}
        model_results[model_key]["active"] = True
    return model_results, all_models_to_run, valid_configs

# -------------------- Summary Printing --------------------

def print_summary(model_results):
    """Print a summary of the benchmark results for all models."""
    print("\n--- Benchmark Complete ---")
    for (provider, model), results in model_results.items():
        print(f"\n=== Final Summary for {provider}/{model or 'default'} ===")
        max_solved_size = max((lvl.get("size", 0) for lvl in results["attempts"] if lvl.get("solved")), default=0)
        print(f"  Max Size Solved: {max_solved_size if max_solved_size > 0 else 'None'}")
    print("\n--- Benchmark Execution Finished ---")

# -------------------- Main Benchmark Loop --------------------

def run_benchmark():
    """Main entrypoint for running the Rubiks Slider benchmark."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-size", type=int, default=3, help="Starting grid size (e.g., 3 for 3x3)")
    ap.add_argument("--shuffle-moves", type=int, default=10, help="Number of moves to shuffle the board")
    args = ap.parse_args()

    print("--- Rubiks Slider Benchmark ---")

    benchmark_configs = read_benchmarks_config()
    if not benchmark_configs:
        print("No benchmark configurations found in config file. Exiting.")
        sys.exit(1)

    main_run_timestamp = now_timestamp()
    main_run_dir = os.path.join(LOG_DIR, main_run_timestamp)
    ensure_directory(main_run_dir)
    print(f"[*] Main log directory: {main_run_dir}")

    model_results, all_models_to_run, valid_configs = prepare_model_runs(benchmark_configs)
    if not valid_configs:
        print("\nErrors found in benchmark_config.json. Please fix the mandatory 'provider' and 'model' fields. Exiting.")
        sys.exit(1)

    current_grid_size = args.start_size
    active_models_remaining = set(all_models_to_run)

    while active_models_remaining:
        if current_grid_size > 7:
            print("\n--- Reached max grid size limit (7). Stopping benchmark. ---")
            break

        print(f"\n--- Grid Size: {current_grid_size}×{current_grid_size} ---")
        current_shuffle = get_shuffle_sequence(current_grid_size)
        print(f"  > Using shuffle of {len(current_shuffle)} moves for {current_grid_size}x{current_grid_size}.")

        models_succeeded_this_size = set()
        models_to_test_this_size = list(active_models_remaining)

        for provider, model in models_to_test_this_size:
            model_key = (provider, model)
            model_config = model_results[model_key]["config"]
            attempts_for_model = model_config.get("attempts", 1)

            print(f"\n  --- Testing {provider}/{model or 'default'} ---")
            run_results_for_model_at_size = []
            model_succeeded_at_least_once = False

            for attempt_num in range(attempts_for_model):
                print(f"    * Attempt {attempt_num + 1}/{attempts_for_model}")
                scenario_result = run_benchmark_scenario(
                    grid_size=current_grid_size,
                    provider=provider,
                    model=model,
                    shared_shuffle_sequence=current_shuffle,
                    model_config=model_config,
                )
                summary = scenario_result["summary"]
                moves = summary["total_individual_moves_applied"]
                solved = summary["solved"]
                reason = summary["termination_reason"]
                conversation = scenario_result["conversation_history"]

                run_data = dict(
                    size=current_grid_size,
                    moves=moves,
                    solved=solved,
                    reason=reason,
                    conversation=conversation,
                    run_errors=scenario_result.get("run_errors", []),
                    time_spent=summary["time_spent"],
                    api_calls_made=summary["api_calls_made"],
                )
                run_results_for_model_at_size.append(run_data)
                api_calls = summary["api_calls_made"]
                print(f"    > Result (Attempt {attempt_num+1}): api_calls={api_calls}, moves={moves}, solved={solved}, reason={reason}")
                if solved:
                    model_succeeded_at_least_once = True

            model_results[model_key]["attempts"].extend(run_results_for_model_at_size)
            save_incremental_log(provider, model, model_results[model_key], main_run_timestamp, main_run_dir)

            if not model_succeeded_at_least_once:
                print(f"    > {provider}/{model or 'default'} failed on all attempts — stopping for this model.")
                active_models_remaining.remove(model_key)
            else:
                models_succeeded_this_size.add(model_key)

        if not models_succeeded_this_size:
            print(f"\n--- No models succeeded at size {current_grid_size}. Stopping benchmark. ---")
            break

        current_grid_size += 1

    print_summary(model_results)

# -------------------- Entrypoint --------------------

if __name__ == "__main__":
    run_benchmark()
