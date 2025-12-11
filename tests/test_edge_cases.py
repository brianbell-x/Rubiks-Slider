"""Tests for edge cases and error handling."""

import pytest
import json
from core.puzzle import Puzzle, parse_simple_move


class TestMinimumGridSize:
    """Tests for 2x2 grid (minimum size)."""

    def test_2x2_all_moves(self, puzzle_2x2):
        """Test all possible moves on 2x2 grid."""
        # Row moves
        puzzle_2x2._shift_row(0, "left")
        assert puzzle_2x2.board[0] == ["2", "1"]

        puzzle_2x2._shift_row(0, "right")
        assert puzzle_2x2.board[0] == ["1", "2"]

        # Column moves
        puzzle_2x2._shift_column(0, "up")
        assert puzzle_2x2.board[0][0] == "3"

        puzzle_2x2._shift_column(0, "down")
        assert puzzle_2x2.board[0][0] == "1"

    def test_2x2_full_cycle(self, puzzle_2x2):
        """Test full cycle on 2x2 returns to solved."""
        puzzle_2x2._shift_row(0, "left")
        puzzle_2x2._shift_row(0, "left")
        assert puzzle_2x2.board[0] == ["1", "2"]

    def test_2x2_solve_after_shuffle(self):
        """Test solving 2x2 after shuffle."""
        puzzle = Puzzle(size=2, auto_shuffle=True, shuffle_moves=5)
        reversed_seq = Puzzle.reverse_sequence(puzzle.get_shuffle_key())
        for move in reversed_seq:
            puzzle.apply_move_from_json(json.dumps(move))
        assert puzzle.is_solved()


class TestWrapAroundBehavior:
    """Tests for wrap-around at grid boundaries."""

    def test_row_left_wraps_first_to_last(self, puzzle_3x3):
        """Test left shift wraps first element to last position."""
        puzzle_3x3._shift_row(0, "left")
        assert puzzle_3x3.board[0][-1] == "1"
        assert puzzle_3x3.board[0][0] == "2"

    def test_row_right_wraps_last_to_first(self, puzzle_3x3):
        """Test right shift wraps last element to first position."""
        puzzle_3x3._shift_row(0, "right")
        assert puzzle_3x3.board[0][0] == "3"
        assert puzzle_3x3.board[0][-1] == "2"

    def test_column_up_wraps_top_to_bottom(self, puzzle_3x3):
        """Test up shift wraps top element to bottom position."""
        puzzle_3x3._shift_column(0, "up")
        assert puzzle_3x3.board[-1][0] == "1"
        assert puzzle_3x3.board[0][0] == "4"

    def test_column_down_wraps_bottom_to_top(self, puzzle_3x3):
        """Test down shift wraps bottom element to top position."""
        puzzle_3x3._shift_column(0, "down")
        assert puzzle_3x3.board[0][0] == "7"
        assert puzzle_3x3.board[-1][0] == "4"


class TestConsecutiveIdenticalMoves:
    """Tests for repeated identical moves."""

    def test_n_left_shifts_cycle(self, puzzle_3x3):
        """Test that n left shifts on size n returns to original."""
        original = puzzle_3x3.board[0][:]
        for _ in range(3):
            puzzle_3x3._shift_row(0, "left")
        assert puzzle_3x3.board[0] == original

    def test_n_right_shifts_cycle(self, puzzle_3x3):
        """Test that n right shifts on size n returns to original."""
        original = puzzle_3x3.board[0][:]
        for _ in range(3):
            puzzle_3x3._shift_row(0, "right")
        assert puzzle_3x3.board[0] == original

    def test_n_up_shifts_cycle(self, puzzle_3x3):
        """Test that n up shifts on size n returns to original."""
        original_col = [puzzle_3x3.board[r][0] for r in range(3)]
        for _ in range(3):
            puzzle_3x3._shift_column(0, "up")
        new_col = [puzzle_3x3.board[r][0] for r in range(3)]
        assert original_col == new_col

    def test_n_down_shifts_cycle(self, puzzle_3x3):
        """Test that n down shifts on size n returns to original."""
        original_col = [puzzle_3x3.board[r][0] for r in range(3)]
        for _ in range(3):
            puzzle_3x3._shift_column(0, "down")
        new_col = [puzzle_3x3.board[r][0] for r in range(3)]
        assert original_col == new_col


class TestStateStringFormats:
    """Tests for state string output formats."""

    def test_get_state_string_format(self, puzzle_3x3):
        """Test get_state_string returns correct format."""
        state = puzzle_3x3.get_state_string()
        lines = state.strip().split("\n")
        assert len(lines) == 3
        assert "1 2 3" in lines[0]

    def test_get_labeled_state_string_has_headers(self, puzzle_3x3):
        """Test get_labeled_state_string has row/column headers."""
        state = puzzle_3x3.get_labeled_state_string()
        assert "C1" in state
        assert "C2" in state
        assert "C3" in state
        assert "R1" in state
        assert "R2" in state
        assert "R3" in state

    def test_get_labeled_state_string_has_values(self, puzzle_3x3):
        """Test get_labeled_state_string contains tile values."""
        state = puzzle_3x3.get_labeled_state_string()
        for i in range(1, 10):
            assert str(i) in state

    def test_state_string_after_move(self, puzzle_3x3):
        """Test state string updates after move."""
        puzzle_3x3._shift_row(0, "left")
        state = puzzle_3x3.get_state_string()
        lines = state.strip().split("\n")
        # First row should now be 2 3 1
        assert "2" in lines[0]
        assert "3" in lines[0]
        assert "1" in lines[0]


class TestCustomTargetBoard:
    """Tests for custom target boards."""

    def test_custom_letters_board(self, custom_3x3_board):
        """Test puzzle with letter tiles."""
        puzzle = Puzzle(size=3, auto_shuffle=False, target_board=custom_3x3_board)
        assert puzzle.board[0][0] == "A"
        assert puzzle.is_solved()

    def test_custom_board_shift(self, custom_3x3_board):
        """Test shift works with custom tiles."""
        puzzle = Puzzle(size=3, auto_shuffle=False, target_board=custom_3x3_board)
        puzzle._shift_row(0, "left")
        assert puzzle.board[0] == ["B", "C", "A"]

    def test_custom_board_not_solved_after_move(self, custom_3x3_board):
        """Test custom board becomes unsolved after move."""
        puzzle = Puzzle(size=3, auto_shuffle=False, target_board=custom_3x3_board)
        puzzle._shift_row(0, "left")
        assert not puzzle.is_solved()


class TestJsonEdgeCases:
    """Tests for JSON parsing edge cases."""

    def test_json_with_extra_fields(self, puzzle_3x3):
        """Test JSON move with extra fields is accepted."""
        json_move = '{"type": "row", "index": 1, "direction": "left", "extra": "field"}'
        success, _ = puzzle_3x3.apply_move_from_json(json_move)
        assert success

    def test_json_with_float_index(self, puzzle_3x3):
        """Test JSON move with float index (should fail)."""
        json_move = '{"type": "row", "index": 1.5, "direction": "left"}'
        success, _ = puzzle_3x3.apply_move_from_json(json_move)
        assert not success

    def test_json_with_null_values(self, puzzle_3x3):
        """Test JSON move with null values."""
        json_move = '{"type": "row", "index": null, "direction": "left"}'
        success, _ = puzzle_3x3.apply_move_from_json(json_move)
        assert not success


class TestDisplayBoard:
    """Tests for display_board method."""

    def test_display_board_no_exception(self, puzzle_3x3, capsys):
        """Test display_board doesn't raise exception."""
        puzzle_3x3.display_board()
        captured = capsys.readouterr()
        assert "1" in captured.out


class TestDeepCopyBehavior:
    """Tests for deep copy behavior of puzzle state."""

    def test_modifying_board_doesnt_affect_solved(self, puzzle_3x3):
        """Test modifying board doesn't change solved_board."""
        puzzle_3x3.board[0][0] = "X"
        assert puzzle_3x3.solved_board[0][0] == "1"

    def test_shuffle_sequence_is_independent(self):
        """Test shuffle sequence modification doesn't affect puzzle."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=5)
        seq = puzzle.get_shuffle_key()
        seq[0]["direction"] = "modified"
        assert puzzle.shuffle_sequence[0]["direction"] != "modified"


class TestLargeGridOperations:
    """Tests for operations on larger grids."""

    def test_10x10_initialization(self):
        """Test 10x10 grid initialization."""
        puzzle = Puzzle(size=10, auto_shuffle=False)
        assert puzzle.size == 10
        assert len(puzzle.board) == 10
        assert len(puzzle.board[0]) == 10
        assert puzzle.board[9][9] == "100"

    def test_10x10_tile_positions(self):
        """Test tile positions on 10x10."""
        puzzle = Puzzle(size=10, auto_shuffle=False)
        assert puzzle.get_tile_position(1) == (1, 1)
        assert puzzle.get_tile_position(100) == (10, 10)
        assert puzzle.get_tile_position(55) == (6, 5)

    def test_10x10_moves(self):
        """Test moves work on 10x10."""
        puzzle = Puzzle(size=10, auto_shuffle=False)
        puzzle._shift_row(0, "left")
        assert puzzle.board[0][0] == "2"
        assert puzzle.board[0][9] == "1"

    def test_10x10_solve_after_shuffle(self):
        """Test solving 10x10 after shuffle."""
        puzzle = Puzzle(size=10, auto_shuffle=True, shuffle_moves=20)
        reversed_seq = Puzzle.reverse_sequence(puzzle.get_shuffle_key())
        for move in reversed_seq:
            puzzle.apply_move_from_json(json.dumps(move))
        assert puzzle.is_solved()


class TestParseSimpleMoveEdgeCases:
    """Tests for parse_simple_move edge cases."""

    def test_multiple_spaces_between_parts(self):
        """Test handling multiple spaces - regex accepts \\s+ so this works."""
        result, error = parse_simple_move("R1   L", 3)
        # The regex uses \s+ which accepts multiple spaces
        assert result is not None
        assert error is None

    def test_no_space_between_parts(self):
        """Test handling no space between parts."""
        result, error = parse_simple_move("R1L", 3)
        assert result is None

    def test_special_characters(self):
        """Test handling special characters."""
        result, error = parse_simple_move("R1@L", 3)
        assert result is None

    def test_numeric_only(self):
        """Test handling numeric only input."""
        result, error = parse_simple_move("123", 3)
        assert result is None
