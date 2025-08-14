"""Render aggregate run_log for a model to a single Video (MP4/H.264).
Usage: python -m benchmark.visualize <..._results.json> <output_directory> --fps 2
"""

import argparse
import json
import textwrap
import numpy as np
import matplotlib.pyplot as plt
import imageio
from pathlib import Path
import copy
import sys
import tempfile
import os
import re 

from core.puzzle import Puzzle, parse_simple_move
from .settings import sanitize_model_name

COLOR_MAP = {
    "A": "#e6194B",  # Red
    "B": "#4363d8",  # Blue
    "C": "#ffe119",  # Yellow
    "D": "#3cb44b",  # Green
    "E": "#f58231",  # Orange
    "F": "#911eb4",  # Purple
    "G": "#42d4f4"   # Cyan
}


def draw_board(ax, grid):
    n = len(grid)
    ax.set_facecolor("black") # Ensure background is black
    ax.clear()
    for y, row in enumerate(grid):
        for x, col_val in enumerate(row): # Renamed 'col' to 'col_val' to avoid conflict
            ax.add_patch(
                plt.Rectangle(
                    (x, n - y - 1),
                    1,
                    1,
                    facecolor=COLOR_MAP.get(col_val, "#777777"), # Default to gray
                    edgecolor="black",
                    lw=0.5,
                )
            )
            ax.text(
                x + 0.5,
                n - y - 0.5,
                col_val,
                ha="center",
                va="center",
                fontsize=32, # Consider adjusting based on grid size if too crowded
                color="black",
                weight="bold",
                family="DejaVu Sans", # Ensure font supports characters
            )
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_xticks([])
    ax.set_yticks([])


def extract_moves_from_run_data(run_data, grid_size):
    """
    Extracts moves and initial state from a single 'run' dictionary.
    """
    conversation = run_data.get("conversation", [])
    initial_state = None
    current_state_marker = "**Current State:**"

    # Try to find initial state in user messages first
    for turn in conversation:
        if turn["role"] == "user":
            content = turn["content"]
            marker_pos = content.find(current_state_marker)
            if marker_pos != -1:
                search_area = content[marker_pos + len(current_state_marker) :]
                # Regex to find the board within triple backticks
                m = re.search(
                    r"```\s*((?:[A-Z0-9 ]+\n)+?)\s*```", search_area, re.MULTILINE
                )
                if m:
                    board_str = m.group(1).strip(" \n")
                    board_lines = [
                        line.strip().replace(" ", "")
                        for line in board_str.splitlines()
                        if line.strip()
                    ]
                    if board_lines and all(len(line) == len(board_lines[0]) for line in board_lines):
                        initial_state = [list(row) for row in board_lines]
                        break # Found initial state
            if initial_state: # Break outer loop if found
                break
    
    if not initial_state:
        # Fallback: Try to get initial state from 'summary' if present (older logs might have it)
        summary = run_data.get("summary", {})
        initial_board_str = summary.get("initial_board_state_for_visualization")
        if initial_board_str:
             board_lines = [
                line.strip().replace(" ", "")
                for line in initial_board_str.splitlines()
                if line.strip()
            ]
             if board_lines and all(len(line) == len(board_lines[0]) for line in board_lines):
                initial_state = [list(row) for row in board_lines]

    if not initial_state:
        raise ValueError(
            f"Could not extract valid initial state for grid size {grid_size} from conversation or summary for the run."
        )
    
    if len(initial_state) != grid_size or not all(len(row) == grid_size for row in initial_state):
        raise ValueError(
            f"Extracted initial state dimensions ({len(initial_state)}x{len(initial_state[0]) if initial_state else 0}) "
            f"do not match expected grid size {grid_size}x{grid_size}."
        )


    moves_extracted = []
    puz = Puzzle(size=grid_size, auto_shuffle=False)
    puz.board = copy.deepcopy(initial_state)

    # Add initial state as the first "step"
    moves_extracted.append(
        {
            "state_before_move": copy.deepcopy(puz.board), # Not strictly needed for initial
            "state_after_move": copy.deepcopy(puz.board),
            "model_move": "Initial State",
            "model_reasoning": "Starting configuration of Rubiks Slider for this run.",
            "move_json": None,
        }
    )

    for turn_idx, turn in enumerate(conversation):
        if turn["role"] != "assistant":
            continue

        content = turn.get("content", "")
        move_match = re.search(
            r"<move>(.*?)</move>", content, re.DOTALL | re.IGNORECASE
        )
        reasoning_match = re.search(
            r"<reasoning>(.*?)</reasoning>", content, re.DOTALL | re.IGNORECASE
        )

        move_str = move_match.group(1).strip() if move_match else "No <move> tag found"
        
        if reasoning_match:
            reasoning_str = reasoning_match.group(1).strip()
        elif move_match: # Move found, reasoning missing
            # Try to get content outside the move tag as reasoning
            reasoning_str = re.sub(r"(?is)<move>.*?</move>", "", content).strip()
            if not reasoning_str:
                reasoning_str = "No <reasoning> tag or other text found."
        else: # No move tag, use full content as reasoning
            reasoning_str = content.strip()
            if not reasoning_str:
                reasoning_str = "Empty assistant message."


        state_before_this_move = copy.deepcopy(puz.board)
        move_json_parsed = None

        if move_match and move_str != "No <move> tag found":
            move_json_parsed_str, err = parse_simple_move(move_str, grid_size)
            if err:
                print(f"Warning: Run's move '{move_str}' is invalid: {err}. Board state will not change for this step.")
                # Keep puz.board as state_before_this_move
                puz.board = copy.deepcopy(state_before_this_move)
            else:
                try:
                    # apply_move_from_json returns (bool, message)
                    success, _msg = puz.apply_move_from_json(move_json_parsed_str)
                    if success:
                        move_json_parsed = json.loads(move_json_parsed_str) # Store the dict
                    else:
                        print(f"Warning: Run's move '{move_str}' failed to apply: {_msg}. Board state will not change.")
                        puz.board = copy.deepcopy(state_before_this_move)
                except Exception as e_apply:
                    print(f"Error applying move '{move_str}': {e_apply}. Board state will not change.")
                    puz.board = copy.deepcopy(state_before_this_move)
        else: # No valid move tag, board does not change
            puz.board = copy.deepcopy(state_before_this_move)

        state_after_this_move = copy.deepcopy(puz.board)

        moves_extracted.append(
            {
                "state_before_move": state_before_this_move,
                "state_after_move": state_after_this_move,
                "model_move": move_str,
                "model_reasoning": reasoning_str,
                "move_json": move_json_parsed,
            }
        )
    return moves_extracted, initial_state


def generate_model_video(model_id: str, all_attempts_data: list, video_out_path: Path, fps: int):
    """
    Generates a single video for all attempts of a given model.
    """
    if not str(video_out_path).lower().endswith(".mp4"):
        print("Warning: Output file does not end with .mp4. Forcing MP4/H.264 output.")
        video_out_path = video_out_path.with_suffix(".mp4")

    model_frames = []
    
    # Figure setup (consider making this adaptive or configurable)
    fig_w_inches, fig_h_inches, fig_dpi = 12, 6.5, 200 # Slightly taller for suptitle
    fig = plt.figure(figsize=(fig_w_inches, fig_h_inches), facecolor="black", dpi=fig_dpi)
    
    # Add a super title for the Model ID (without "Model: " prefix)
    fig.suptitle(f"{model_id}", color="white", fontsize=16, weight="bold", y=0.97)

    # GridSpec for board and text areas
    # Adjust top parameter in GridSpec to make space for suptitle
    # Give more space to the reasoning text on the right
    outer = fig.add_gridspec(1, 2, width_ratios=[0.35, 0.65], wspace=0.2, left=0.05, right=0.95, bottom=0.05, top=0.85)
    ax_board = fig.add_subplot(outer[0])
    ax_txt = fig.add_subplot(outer[1])

    ax_board.set_aspect("equal", adjustable="box")
    ax_board.set_facecolor("black")
    ax_txt.set_facecolor("black")
    ax_txt.axis("off") # Turn off axis lines and ticks for text area

    total_attempts_for_model = len(all_attempts_data)

    # --- Helper function for formatting moves ---
    def _format_move_for_display(move_str: str) -> str:
        """Converts compact move notation to human-readable format."""
        if not move_str or move_str in ["Initial State", "No <move> tag found"]:
            return move_str

        match = re.match(r"([RC])(\d+)\s+([LRUD])", move_str, re.IGNORECASE)
        if not match:
            return move_str # Return original if parsing fails

        type_char, index_str, direction_char = match.groups()
        
        try:
            index = int(index_str)
        except ValueError:
             return f"{move_str} (Invalid Index)" # Handle non-integer index

        type_full = "Row" if type_char.upper() == 'R' else "Column"
        
        direction_map = {'L': 'Left', 'R': 'Right', 'U': 'Up', 'D': 'Down'}
        direction_full = direction_map.get(direction_char.upper())

        if not direction_full:
             return f"{move_str} (Invalid Dir Char)" # Invalid direction character

        # Basic validation of direction based on type
        if type_full == "Row" and direction_full not in ["Left", "Right"]:
            return f"{move_str} (Invalid Row Dir)"
        if type_full == "Column" and direction_full not in ["Up", "Down"]:
             return f"{move_str} (Invalid Col Dir)"

        return f"{type_full} {index} {direction_full}"
    # --- End Helper ---

    for attempt_idx, attempt_data in enumerate(all_attempts_data):
        attempt_number_in_video = attempt_idx + 1
        grid_size = attempt_data.get("size")

        if grid_size is None:
            print(f"Warning: Attempt {attempt_number_in_video} for model {model_id} is missing 'size'. Skipping this attempt.")
            continue
        
        print(f"Processing Model '{model_id}', Attempt {attempt_number_in_video}/{total_attempts_for_model} (Size: {grid_size})")

        try:
            steps, _ = extract_moves_from_run_data(attempt_data, grid_size)
        except ValueError as e:
            print(f"Skipping visualization for Attempt {attempt_number_in_video} (Model: {model_id}) due to error: {e}")
            # Optionally, add a frame indicating this attempt was skipped/error
            # For now, just skip to next attempt in the video
            continue
        
        if not steps:
            print(f"No valid steps found for Attempt {attempt_number_in_video} (Model: {model_id}). Skipping.")
            continue

        summary = attempt_data.get("summary", {})
        solved_status = summary.get("solved_status", attempt_data.get("solved", False)) # Check top-level 'solved' too

        # Try to get termination_reason from summary, then from top-level 'reason'
        termination_reason = summary.get("termination_reason")
        if not termination_reason or termination_reason == "N/A":
            termination_reason = attempt_data.get("reason")
        
        if not termination_reason: # If still not found, default to "N/A"
            termination_reason = "N/A"
            
        attempt_outcome_text = "PASS" if solved_status else f"FAIL ({termination_reason})"

        # Render frames for each step in the current attempt
        for step_idx, step_details in enumerate(steps):
            ax_board.clear()
            ax_txt.clear()
            fig.texts.clear() # Clear previous figure-level texts
            # Re-apply suptitle after clearing fig.texts
            fig.suptitle(f"{model_id}", color="white", fontsize=16, weight="bold", y=0.97)

            current_board_state = step_details["state_after_move"]
            draw_board(ax_board, current_board_state)

            # Add Attempt/Size info to bottom-right of the figure
            fig.text(0.98, 0.02, f"Attempt {attempt_number_in_video}/{total_attempts_for_model} (Size {grid_size})", 
                     color="grey", fontsize=9, ha="right", va="bottom", transform=fig.transFigure)

            move_text = step_details["model_move"]
            # Combine Move number and LLM move into a single caption below the board
            if step_idx == 0 and move_text == "Initial State":
                move_caption = "Initial State"
            else:
                # Format the move_text using the new helper
                formatted_move = _format_move_for_display(move_text)
                move_caption = f"Move {step_idx}: {formatted_move}" # Use formatted move here
            
            ax_board.text(0.5, -0.08, move_caption, transform=ax_board.transAxes,
                          ha="center", va="top", color="lightgrey", fontsize=10, weight="bold")

            # Added padding for reasoning title and text
            ax_txt.text(0.03, 0.97, "Reasoning:", color="white", fontsize=10, weight="bold",
                        va="top", transform=ax_txt.transAxes)
            
            cleaned_reasoning = step_details.get("model_reasoning", "N/A").replace(":", ":\n") # Basic reformat
            # Increased textwrap width to utilize more horizontal space
            wrapped_reasoning = "\n" + textwrap.fill(cleaned_reasoning, width=115) 
            reasoning_fontsize = 7 if len(cleaned_reasoning) > 500 else 8 # Adjusted threshold slightly
            # Adjusted y-position for padding and to be relative to title
            ax_txt.text(0.03, 0.97 - 0.07, wrapped_reasoning, color="white", fontsize=reasoning_fontsize,
                        va="top", linespacing=1.3, transform=ax_txt.transAxes, wrap=True)

            fig.canvas.draw()
            frame_rgba = np.asarray(fig.canvas.renderer.buffer_rgba())
            frame_rgb = frame_rgba[:, :, :3]
            model_frames.append(frame_rgb.copy())

        # Add summary frames for the current attempt
        summary_duration_frames = fps * 3  # 3 seconds for attempt summary
        for _ in range(summary_duration_frames):
            fig.texts.clear() # Clear previous figure-level texts (like Attempt/Size info)
            # Re-apply suptitle after clearing fig.texts
            fig.suptitle(f"{model_id}", color="white", fontsize=16, weight="bold", y=0.97)
            # Board shows the last state of the attempt, text area shows summary
            ax_txt.clear()
            ax_txt.text(0.5, 0.5, f"Attempt {attempt_number_in_video} Result:\n{attempt_outcome_text}",
                        color="#77DD77" if solved_status else "#FF6961", # Pastel Green / Pastel Red
                        fontsize=16, weight="bold",
                        va="center", ha="center", transform=ax_txt.transAxes, wrap=True,
                        bbox=dict(boxstyle="round,pad=0.5", fc="black", ec="grey", lw=1))
            
            fig.canvas.draw()
            frame_rgba = np.asarray(fig.canvas.renderer.buffer_rgba())
            frame_rgb = frame_rgba[:, :, :3]
            model_frames.append(frame_rgb.copy())

    plt.close(fig) # Close the figure after all frames are generated

    if not model_frames:
        print(f"No frames generated for model {model_id}. Video will not be created.")
        return

    video_out_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing {len(model_frames)} frames for model '{model_id}' to {video_out_path} at {fps} FPS...")
    try:
        imageio.mimwrite(video_out_path, model_frames, fps=fps, codec="libx264", quality=9, pixelformat="yuv420p")
        print(f"[visualize] Successfully wrote video to {video_out_path}")
    except Exception as e:
        print(f"\nError writing video file for model '{model_id}': {e}")
        print("Ensure ffmpeg is installed and accessible by imageio.")
        print("You might need to install it via your system's package manager")
        print("or install the Python package: pip install imageio[ffmpeg]")
        # Not re-raising here to allow other models to process if in a batch
        
def run_self_test():
    print("Running embedded self-test for benchmark.visualize (single video per model)...")

    EMBEDDED_AGGREGATE_LOG_DATA = """{
  "provider": "embedded_test_provider",
  "model": "test_model_log_v2",
  "attempts": [
    {
      "size": 3,
      "moves": 1,
      "solved": true, 
      "reason": "Solved via top-level", 
      "conversation": [
        {"role": "user", "content": "Initial prompt for attempt 1. **Current State:**\\n```\\nA B C\\nD E F\\nG H I\\n```\\nMake a move."},
        {"role": "assistant", "content": "<reasoning>This is reasoning for attempt 1, move 1.</reasoning><move>R1 L</move>"}
      ],
      "run_errors": []
    },
    {
      "size": 2,
      "moves": 5,
      "conversation": [
        {"role": "user", "content": "Initial prompt for attempt 2. **Current State:**\\n```\\nX Y\\nZ W\\n```\\nMake a move."},
        {"role": "assistant", "content": "<reasoning>This is reasoning for attempt 2, move 1.</reasoning><move>C1 U</move>"},
        {"role": "assistant", "content": "<reasoning>This is reasoning for attempt 2, move 2. This reasoning is a bit longer to test text wrapping and see how it fits into the allocated space for the visualization panel, ensuring that it does not overflow or become unreadable due to excessive length or small font size. We need to check if the text wraps correctly and remains legible.</reasoning><move>R2 R</move>"}
      ],
      "summary": {
        "solved_status": false, 
        "termination_reason": "Max moves exceeded (from summary)"
      },
      "run_errors": ["Example error if any"]
    }
  ],
  "timestamp": "20250101_000000",
  "max_solved_size": 3
}"""
    
    temp_log_file_path = None
    with tempfile.TemporaryDirectory(prefix="cline_vis_test_") as tmp_output_dir_str:
        tmp_output_dir = Path(tmp_output_dir_str)
        
        try:
            # Create a temporary log file with the embedded data
            with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".json", encoding="utf-8", dir=tmp_output_dir) as tmp_f:
                tmp_f.write(EMBEDDED_AGGREGATE_LOG_DATA)
                temp_log_file_path = Path(tmp_f.name)
            
            # Call the main processing function that now generates one video per model
            process_aggregate_log(temp_log_file_path, tmp_output_dir, fps=1)

            # Verification: Expect one video for "embedded_test_provider_test_model_log_v2"
            expected_video_filename = sanitize_model_name("embedded_test_provider_test_model_log_v2") + ".mp4"
            expected_video_file = tmp_output_dir / expected_video_filename
            
            if not expected_video_file.exists():
                print(f"[FAIL] Expected video file was not created: {expected_video_file}")
                return False
            if expected_video_file.stat().st_size == 0:
                print(f"[FAIL] Expected video file is empty: {expected_video_file}")
                return False
            
            print(f"[PASS] Embedded test: Video '{expected_video_file.name}' created in {tmp_output_dir}")
            return True

        except Exception as e:
            print(f"[FAIL] Embedded test failed during visualization: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if temp_log_file_path and temp_log_file_path.exists():
                try:
                    os.remove(temp_log_file_path)
                except Exception as e_rem:
                    print(f"Warning: Could not remove temporary log file {temp_log_file_path}: {e_rem}")

def process_aggregate_log(aggregate_log_path: Path, output_dir_path: Path, fps: int):
    """
    Processes an aggregate log file, generating a single video for the model described in the log.
    """
    if not aggregate_log_path.exists():
        raise FileNotFoundError(f"Aggregate log file not found at {aggregate_log_path}")

    try:
        with open(aggregate_log_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error reading aggregate log file {aggregate_log_path}: Invalid JSON - {e}")

    all_attempts_data = data.get("attempts")
    if not all_attempts_data or not isinstance(all_attempts_data, list):
        raise ValueError(f"Log file {aggregate_log_path.name} does not contain a valid 'attempts' array or is empty.")

    # Determine model_id
    provider = data.get("provider")
    model_name_from_log = data.get("model") # Renamed to avoid conflict with 'model' module
    
    model_id_parts = []
    if provider:
        model_id_parts.append(provider)
    if model_name_from_log:
        model_id_parts.append(model_name_from_log)
    
    if not model_id_parts: # Fallback to filename if provider/model not in JSON
        base_name = aggregate_log_path.name
        if base_name.endswith("_results.json"):
            model_id_from_filename = base_name[:-len("_results.json")]
        else:
            model_id_from_filename = base_name.rsplit('.', 1)[0] if '.' in base_name else base_name
        model_id = sanitize_model_name(model_id_from_filename)
        print(f"Warning: Could not find provider/model in JSON, using filename-derived ID: {model_id}")
    else:
        model_id = sanitize_model_name("_".join(model_id_parts))

    output_dir_path.mkdir(parents=True, exist_ok=True)
    video_filename = f"{model_id}.mp4" # Single video per model
    video_out_path = output_dir_path / video_filename
    
    print(f"\nProcessing all attempts for Model '{model_id}' from {aggregate_log_path.name} -> {video_out_path}")
    try:
        generate_model_video(model_id, all_attempts_data, video_out_path, fps)
    except Exception as e:
        # Log error but don't necessarily stop if part of a larger batch process
        print(f"Error generating video for Model '{model_id}': {e}")
        import traceback
        traceback.print_exc()


def main():
    if len(sys.argv) == 1:
        print("No arguments provided. Running embedded self-test...")
        result = run_self_test()
        sys.exit(0 if result else 1)

    ap = argparse.ArgumentParser(
        description="Render Rubiks Slider aggregate log to a single MP4 video for the model."
    )
    ap.add_argument("log", help="Path to the input aggregate log file (e.g., model_id_results.json)")
    ap.add_argument("out_dir", help="Path to the output directory for the video file.")
    ap.add_argument("--fps", type=int, default=2, help="Frames per second for the output video.")
    args = ap.parse_args()

    try:
        process_aggregate_log(Path(args.log), Path(args.out_dir), args.fps)
    except Exception as e:
        print(f"[ERROR] Top-level error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
