"""Tests for move parsing and application from JSON."""

import pytest
import json
from core.puzzle import Puzzle, parse_simple_move


class TestParseSimpleMove:
    """Tests for parse_simple_move function."""

    def test_parse_row_left(self):
        """Test parsing row left move."""
        result, error = parse_simple_move("R1 L", 3)
        assert error is None
        move = json.loads(result)
        assert move["type"] == "row"
        assert move["index"] == 1
        assert move["direction"] == "left"

    def test_parse_row_right(self):
        """Test parsing row right move."""
        result, error = parse_simple_move("R2 R", 3)
        assert error is None
        move = json.loads(result)
        assert move["type"] == "row"
        assert move["index"] == 2
        assert move["direction"] == "right"

    def test_parse_column_up(self):
        """Test parsing column up move."""
        result, error = parse_simple_move("C1 U", 3)
        assert error is None
        move = json.loads(result)
        assert move["type"] == "column"
        assert move["index"] == 1
        assert move["direction"] == "up"

    def test_parse_column_down(self):
        """Test parsing column down move."""
        result, error = parse_simple_move("C3 D", 3)
        assert error is None
        move = json.loads(result)
        assert move["type"] == "column"
        assert move["index"] == 3
        assert move["direction"] == "down"

    def test_parse_lowercase(self):
        """Test parsing with lowercase input."""
        result, error = parse_simple_move("r1 l", 3)
        assert error is None
        move = json.loads(result)
        assert move["type"] == "row"
        assert move["direction"] == "left"

    def test_parse_mixed_case(self):
        """Test parsing with mixed case input."""
        result, error = parse_simple_move("c2 D", 3)
        assert error is None
        move = json.loads(result)
        assert move["type"] == "column"
        assert move["direction"] == "down"

    def test_parse_with_whitespace(self):
        """Test parsing with extra whitespace."""
        result, error = parse_simple_move("  R1 L  ", 3)
        assert error is None
        move = json.loads(result)
        assert move["type"] == "row"

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        result, error = parse_simple_move("invalid", 3)
        assert result is None
        assert "Invalid format" in error

    def test_parse_index_out_of_bounds_high(self):
        """Test parsing with index too high."""
        result, error = parse_simple_move("R4 L", 3)
        assert result is None
        assert "out of bounds" in error

    def test_parse_index_out_of_bounds_zero(self):
        """Test parsing with index 0 (should fail - 1-indexed)."""
        result, error = parse_simple_move("R0 L", 3)
        assert result is None
        assert "out of bounds" in error

    def test_parse_row_with_up_direction(self):
        """Test parsing row with invalid up direction."""
        result, error = parse_simple_move("R1 U", 3)
        assert result is None
        assert "Invalid direction" in error

    def test_parse_row_with_down_direction(self):
        """Test parsing row with invalid down direction."""
        result, error = parse_simple_move("R1 D", 3)
        assert result is None
        assert "Invalid direction" in error

    def test_parse_column_with_left_direction(self):
        """Test parsing column with invalid left direction."""
        result, error = parse_simple_move("C1 L", 3)
        assert result is None
        assert "Invalid direction" in error

    def test_parse_column_with_right_direction(self):
        """Test parsing column with invalid right direction."""
        result, error = parse_simple_move("C1 R", 3)
        assert result is None
        assert "Invalid direction" in error

    def test_parse_larger_grid(self):
        """Test parsing for larger grid sizes."""
        result, error = parse_simple_move("R10 L", 10)
        assert error is None
        move = json.loads(result)
        assert move["index"] == 10

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        result, error = parse_simple_move("", 3)
        assert result is None
        assert "Invalid format" in error


class TestApplyMoveFromJson:
    """Tests for apply_move_from_json method."""

    def test_apply_row_left(self, puzzle_3x3):
        """Test applying row left move via JSON."""
        json_move = '{"type": "row", "index": 1, "direction": "left"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is True
        assert puzzle_3x3.board[0] == ["2", "3", "1"]

    def test_apply_row_right(self, puzzle_3x3):
        """Test applying row right move via JSON."""
        json_move = '{"type": "row", "index": 1, "direction": "right"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is True
        assert puzzle_3x3.board[0] == ["3", "1", "2"]

    def test_apply_column_up(self, puzzle_3x3):
        """Test applying column up move via JSON."""
        json_move = '{"type": "column", "index": 1, "direction": "up"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is True
        assert puzzle_3x3.board[0][0] == "4"
        assert puzzle_3x3.board[1][0] == "7"
        assert puzzle_3x3.board[2][0] == "1"

    def test_apply_column_down(self, puzzle_3x3):
        """Test applying column down move via JSON."""
        json_move = '{"type": "column", "index": 1, "direction": "down"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is True
        assert puzzle_3x3.board[0][0] == "7"
        assert puzzle_3x3.board[1][0] == "1"
        assert puzzle_3x3.board[2][0] == "4"

    def test_apply_invalid_json(self, puzzle_3x3):
        """Test applying invalid JSON."""
        success, msg = puzzle_3x3.apply_move_from_json("not valid json")
        assert success is False
        assert "Invalid JSON" in msg

    def test_apply_missing_type(self, puzzle_3x3):
        """Test applying move with missing type."""
        json_move = '{"index": 1, "direction": "left"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is False
        assert "Missing required keys" in msg

    def test_apply_missing_index(self, puzzle_3x3):
        """Test applying move with missing index."""
        json_move = '{"type": "row", "direction": "left"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is False
        assert "Missing required keys" in msg

    def test_apply_missing_direction(self, puzzle_3x3):
        """Test applying move with missing direction."""
        json_move = '{"type": "row", "index": 1}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is False
        assert "Missing required keys" in msg

    def test_apply_index_too_high(self, puzzle_3x3):
        """Test applying move with index > grid size."""
        json_move = '{"type": "row", "index": 4, "direction": "left"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is False
        assert "Invalid index" in msg

    def test_apply_index_too_low(self, puzzle_3x3):
        """Test applying move with index < 1."""
        json_move = '{"type": "row", "index": 0, "direction": "left"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is False
        assert "Invalid index" in msg

    def test_apply_negative_index(self, puzzle_3x3):
        """Test applying move with negative index."""
        json_move = '{"type": "row", "index": -1, "direction": "left"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is False
        assert "Invalid index" in msg

    def test_apply_string_index(self, puzzle_3x3):
        """Test applying move with string index."""
        json_move = '{"type": "row", "index": "1", "direction": "left"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is False
        assert "Invalid index" in msg

    def test_apply_row_with_invalid_direction(self, puzzle_3x3):
        """Test applying row move with column direction."""
        json_move = '{"type": "row", "index": 1, "direction": "up"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is False
        assert "Invalid move type or direction" in msg

    def test_apply_column_with_invalid_direction(self, puzzle_3x3):
        """Test applying column move with row direction."""
        json_move = '{"type": "column", "index": 1, "direction": "left"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is False
        assert "Invalid move type or direction" in msg

    def test_apply_invalid_type(self, puzzle_3x3):
        """Test applying move with invalid type."""
        json_move = '{"type": "diagonal", "index": 1, "direction": "left"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert success is False

    def test_apply_success_message(self, puzzle_3x3):
        """Test that success message contains move details."""
        json_move = '{"type": "row", "index": 2, "direction": "right"}'
        success, msg = puzzle_3x3.apply_move_from_json(json_move)
        assert "row 2" in msg.lower()
        assert "right" in msg.lower()

    def test_apply_multiple_moves_sequential(self, puzzle_3x3):
        """Test applying multiple moves sequentially."""
        puzzle_3x3.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')
        puzzle_3x3.apply_move_from_json('{"type": "column", "index": 2, "direction": "down"}')

        # R1 L: [2,3,1], [4,5,6], [7,8,9]
        # C2 D: [2,9,1], [4,3,6], [7,5,9] - wait, let me recalculate
        # After R1 L: row0=[2,3,1], row1=[4,5,6], row2=[7,8,9]
        # C2 is index 1 (0-indexed). Values: 3,5,8 -> down: 8,3,5
        # Result: row0=[2,8,1], row1=[4,3,6], row2=[7,5,9]

        assert puzzle_3x3.board[0][1] == "8"
        assert puzzle_3x3.board[1][1] == "3"
        assert puzzle_3x3.board[2][1] == "5"


class TestMoveIndexConversion:
    """Tests for 1-indexed to 0-indexed conversion."""

    def test_row_1_maps_to_internal_0(self, puzzle_3x3):
        """Test that row index 1 affects board[0]."""
        json_move = '{"type": "row", "index": 1, "direction": "left"}'
        puzzle_3x3.apply_move_from_json(json_move)
        assert puzzle_3x3.board[0] == ["2", "3", "1"]
        assert puzzle_3x3.board[1] == ["4", "5", "6"]  # unchanged

    def test_row_3_maps_to_internal_2(self, puzzle_3x3):
        """Test that row index 3 affects board[2]."""
        json_move = '{"type": "row", "index": 3, "direction": "left"}'
        puzzle_3x3.apply_move_from_json(json_move)
        assert puzzle_3x3.board[0] == ["1", "2", "3"]  # unchanged
        assert puzzle_3x3.board[2] == ["8", "9", "7"]

    def test_column_1_maps_to_internal_0(self, puzzle_3x3):
        """Test that column index 1 affects column 0."""
        json_move = '{"type": "column", "index": 1, "direction": "up"}'
        puzzle_3x3.apply_move_from_json(json_move)
        # Column 0 changed
        assert puzzle_3x3.board[0][0] == "4"
        # Column 1 unchanged
        assert puzzle_3x3.board[0][1] == "2"

    def test_column_3_maps_to_internal_2(self, puzzle_3x3):
        """Test that column index 3 affects column 2."""
        json_move = '{"type": "column", "index": 3, "direction": "up"}'
        puzzle_3x3.apply_move_from_json(json_move)
        # Column 2 changed
        assert puzzle_3x3.board[0][2] == "6"
        # Column 1 unchanged
        assert puzzle_3x3.board[0][1] == "2"
