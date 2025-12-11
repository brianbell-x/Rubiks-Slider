"""Tests for solved state detection."""

import pytest
import json
from core.puzzle import Puzzle


class TestIsSolved:
    """Tests for is_solved method."""

    def test_unshuffled_puzzle_is_solved(self, puzzle_3x3):
        """Test that an unshuffled puzzle is solved."""
        assert puzzle_3x3.is_solved() is True

    def test_shuffled_puzzle_is_not_solved(self):
        """Test that a shuffled puzzle is not solved."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=10)
        assert puzzle.is_solved() is False

    def test_single_move_makes_unsolved(self, puzzle_3x3):
        """Test that a single move makes puzzle unsolved."""
        puzzle_3x3.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')
        assert puzzle_3x3.is_solved() is False

    def test_reversing_move_makes_solved(self, puzzle_3x3):
        """Test that reversing a move returns to solved state."""
        puzzle_3x3.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')
        puzzle_3x3.apply_move_from_json('{"type": "row", "index": 1, "direction": "right"}')
        assert puzzle_3x3.is_solved() is True

    def test_full_cycle_returns_to_solved(self, puzzle_3x3):
        """Test that cycling through all positions returns to solved."""
        # 3 left moves on row 1 = full cycle
        for _ in range(3):
            puzzle_3x3.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')
        assert puzzle_3x3.is_solved() is True

    def test_is_solved_2x2(self, puzzle_2x2):
        """Test is_solved works for 2x2."""
        assert puzzle_2x2.is_solved() is True
        puzzle_2x2.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')
        assert puzzle_2x2.is_solved() is False

    def test_is_solved_4x4(self, puzzle_4x4):
        """Test is_solved works for 4x4."""
        assert puzzle_4x4.is_solved() is True
        puzzle_4x4.apply_move_from_json('{"type": "column", "index": 2, "direction": "up"}')
        assert puzzle_4x4.is_solved() is False

    def test_custom_target_board_solved(self):
        """Test is_solved with custom target board."""
        custom = [["A", "B"], ["C", "D"]]
        puzzle = Puzzle(size=2, auto_shuffle=False, target_board=custom)
        assert puzzle.is_solved() is True

    def test_custom_target_board_unsolved(self):
        """Test is_solved with custom target board after move."""
        custom = [["A", "B"], ["C", "D"]]
        puzzle = Puzzle(size=2, auto_shuffle=False, target_board=custom)
        puzzle._shift_row(0, "left")
        # Now board is [["B", "A"], ["C", "D"]]
        assert puzzle.is_solved() is False


class TestSolvedComparison:
    """Tests for how solved comparison works."""

    def test_solved_compares_board_to_solved_board(self, puzzle_3x3):
        """Test that is_solved compares board to solved_board."""
        # Manually verify the comparison
        assert puzzle_3x3.board == puzzle_3x3.solved_board

    def test_identical_boards_are_solved(self, puzzle_3x3):
        """Test that identical boards return True for is_solved."""
        puzzle_3x3.board = [row[:] for row in puzzle_3x3.solved_board]
        assert puzzle_3x3.is_solved() is True

    def test_different_boards_are_not_solved(self, puzzle_3x3):
        """Test that different boards return False for is_solved."""
        puzzle_3x3.board[0][0] = "X"
        assert puzzle_3x3.is_solved() is False

    def test_swapped_elements_not_solved(self, puzzle_3x3):
        """Test that swapping two elements makes puzzle unsolved."""
        puzzle_3x3.board[0][0], puzzle_3x3.board[0][1] = puzzle_3x3.board[0][1], puzzle_3x3.board[0][0]
        assert puzzle_3x3.is_solved() is False


class TestSolvingPuzzle:
    """Tests for actually solving a shuffled puzzle."""

    def test_reverse_shuffle_solves_puzzle(self):
        """Test that reversing shuffle sequence solves puzzle."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=10)
        shuffle_seq = puzzle.get_shuffle_key()

        # Apply reversed sequence
        reversed_seq = Puzzle.reverse_sequence(shuffle_seq)
        for move in reversed_seq:
            puzzle.apply_move_from_json(json.dumps(move))

        assert puzzle.is_solved() is True

    def test_solving_with_known_moves(self, puzzle_3x3):
        """Test solving with a known sequence of moves."""
        # Make a known sequence
        puzzle_3x3.apply_move_from_json('{"type": "row", "index": 1, "direction": "left"}')
        puzzle_3x3.apply_move_from_json('{"type": "column", "index": 2, "direction": "up"}')

        assert puzzle_3x3.is_solved() is False

        # Reverse the sequence
        puzzle_3x3.apply_move_from_json('{"type": "column", "index": 2, "direction": "down"}')
        puzzle_3x3.apply_move_from_json('{"type": "row", "index": 1, "direction": "right"}')

        assert puzzle_3x3.is_solved() is True

    def test_solving_larger_puzzle(self):
        """Test solving a larger shuffled puzzle."""
        puzzle = Puzzle(size=4, auto_shuffle=True, shuffle_moves=15)
        shuffle_seq = puzzle.get_shuffle_key()

        reversed_seq = Puzzle.reverse_sequence(shuffle_seq)
        for move in reversed_seq:
            puzzle.apply_move_from_json(json.dumps(move))

        assert puzzle.is_solved() is True
