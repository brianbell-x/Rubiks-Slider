import random
import json
import copy
import re
from collections import deque
from typing import List, Dict, Any, Optional, Tuple

class Puzzle:
    """Rubiks Slider with row/column shifts."""

    def __init__(
        self,
        size: int = 6,
        auto_shuffle: bool = True,
        shuffle_moves: Optional[int] = None,
        target_board: Optional[List[List[str]]] = None,
    ):
        if size < 2:
            raise ValueError("Grid size must be at least 2.")
        self.size = size

        if target_board:
            if not isinstance(target_board, list) or len(target_board) != size:
                raise ValueError(f"Invalid target_board: Must be a list of {size} rows.")
            for r_idx, row in enumerate(target_board):
                if not isinstance(row, list) or len(row) != size:
                    raise ValueError(
                        f"Invalid target_board: Row {r_idx+1} must be a list of {size} elements."
                    )
            self.solved_board = copy.deepcopy(target_board)
        else:
            self.solved_board = self._create_solved_board()

        self.board = copy.deepcopy(self.solved_board)
        self.shuffle_sequence: List[Dict[str, Any]] = []

        if auto_shuffle:
            moves_to_apply = shuffle_moves if shuffle_moves is not None else random.randint(self.size, self.size * self.size * 2)
            self._shuffle_board(moves_to_apply)

    def _create_solved_board(self) -> List[List[str]]:
        return [[str(r * self.size + c + 1) for c in range(self.size)] for r in range(self.size)]

    def get_tile_position(self, tile_number: int) -> Optional[Tuple[int, int]]:
        """
        Find the current row and column of a tile by its number.
        Returns (row, col) as 1-indexed values, or None if not found.
        """
        target = str(tile_number)
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == target:
                    return (r + 1, c + 1)
        return None

    def validate_prediction(self, tile_number: int, predicted_position: str) -> bool:
        """
        Check if the predicted position matches the actual position of the tile.
        predicted_position format: "R#C#" (e.g., "R2C3")
        Returns True if prediction is correct, False otherwise.
        """
        actual_pos = self.get_tile_position(tile_number)
        if not actual_pos:
            return False
        
        match = re.match(r"R(\d+)C(\d+)", predicted_position)
        if not match:
            return False
            
        pred_row, pred_col = map(int, match.groups())
        return (pred_row, pred_col) == actual_pos

    def get_labeled_state_string(self) -> str:
        """
        Return board state with grid labels for prompts.
        Format:
            C1 C2 C3
        R1   1  2  3
        R2   4  5  6
        R3   7  8  9
        """
        # Calculate column width based on max number length and column label length
        max_num_len = len(str(self.size * self.size))
        max_col_label_len = len(str(self.size)) + 1 # "C" + number
        col_width = max(max_num_len, max_col_label_len)
        
        # Header
        header = "   " + " ".join(f"C{c+1}".rjust(col_width) for c in range(self.size))
        
        rows = []
        for r in range(self.size):
            row_label = f"R{r+1}".ljust(2)
            row_content = " ".join(cell.rjust(col_width) for cell in self.board[r])
            rows.append(f"{row_label} {row_content}")
            
        return header + "\n" + "\n".join(rows)

    def _shuffle_board(self, moves: int = 10):
        self.shuffle_sequence = []
        for _ in range(moves):
            move_type = random.choice(["row", "column"])
            internal_index = random.randint(0, self.size - 1)
            direction = (
                random.choice(["left", "right"])
                if move_type == "row"
                else random.choice(["up", "down"])
            )
            move_dict = {
                "type": move_type,
                "index": internal_index + 1,
                "direction": direction,
            }
            self.shuffle_sequence.append(move_dict)
            self._apply_move_internal(move_type, internal_index, direction)
        if self.is_solved():
            self._shuffle_board(moves + 5)

    def get_shuffle_key(self) -> List[Dict[str, Any]]:
        return copy.deepcopy(self.shuffle_sequence)

    @staticmethod
    def _reverse_move(move: Dict[str, Any]) -> Dict[str, Any]:
        inverted_move = copy.deepcopy(move)
        direction = inverted_move["direction"]
        opposites = {"left": "right", "right": "left", "up": "down", "down": "up"}
        inverted_move["direction"] = opposites[direction]
        return inverted_move

    @staticmethod
    def reverse_sequence(sequence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [Puzzle._reverse_move(move) for move in reversed(sequence)]

    def display_board(self):
        for row in self.board:
            print(" ".join(row))

    def _shift_row(self, row_index: int, direction: str):
        row_deque = deque(self.board[row_index])
        row_deque.rotate(-1 if direction == "left" else 1)
        self.board[row_index] = list(row_deque)

    def _shift_column(self, col_index: int, direction: str):
        column_deque = deque(self.board[r][col_index] for r in range(self.size))
        column_deque.rotate(-1 if direction == "up" else 1)
        for r in range(self.size):
            self.board[r][col_index] = column_deque[r]

    def _apply_move_internal(self, move_type: str, index: int, direction: str):
        if move_type == "row":
            self._shift_row(index, direction)
        else:
            self._shift_column(index, direction)

    def apply_move_from_json(self, json_string: str):
        try:
            move_data = json.loads(json_string)
        except json.JSONDecodeError:
            return False, "Invalid JSON format."

        required_keys = {"type", "index", "direction"}
        if not required_keys.issubset(move_data.keys()):
            return False, f"Missing required keys. Need: {required_keys}"

        move_type = move_data.get("type")
        direction = move_data.get("direction")
        index = move_data.get("index")
        if not isinstance(index, int) or not (1 <= index <= self.size):
            return (
                False,
                f"Invalid index. Must be an integer between 1 and {self.size}.",
            )
        internal_index = index - 1

        if move_type == "row" and direction in ["left", "right"]:
            self._apply_move_internal(move_type, internal_index, direction)
            return True, f"Moved row {index} {direction}."
        elif move_type == "column" and direction in ["up", "down"]:
            self._apply_move_internal(move_type, internal_index, direction)
            return True, f"Moved column {index} {direction}."
        else:
            return False, "Invalid move type or direction."

    def is_solved(self) -> bool:
        return self.board == self.solved_board

    def get_state_string(self) -> str:
        return "\n".join(" ".join(row) for row in self.board)

def parse_simple_move(input_str: str, grid_size: int):
    input_str = input_str.strip().upper()
    match = re.match(r"^(R|C)(\d+)\s+(L|R|U|D)$", input_str)
    if not match:
        return None, "Invalid format. Use 'R# L/R' or 'C# U/D' (e.g., R1 L, C2 U)."

    type_char, index_str, direction_char = match.groups()
    index = int(index_str)
    if not (1 <= index <= grid_size):
        return None, f"Index {index} out of bounds (must be 1-{grid_size})."

    move_type = "row" if type_char == "R" else "column"
    direction_map = {"L": "left", "R": "right", "U": "up", "D": "down"}
    direction = direction_map.get(direction_char)
    if (type_char == "R" and direction_char not in ["L", "R"]) or (
        type_char == "C" and direction_char not in ["U", "D"]
    ):
        return None, f"Invalid direction for {move_type} move."

    move_dict = {"type": move_type, "index": index, "direction": direction}
    return json.dumps(move_dict), None
