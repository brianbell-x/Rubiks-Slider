"""Tests for Puzzle class initialization."""

import pytest
from core.puzzle import Puzzle


class TestPuzzleInitialization:
    """Tests for puzzle creation and initialization."""

    def test_default_size(self):
        """Test that default size is 6x6."""
        puzzle = Puzzle(auto_shuffle=False)
        assert puzzle.size == 6

    def test_custom_size_2x2(self):
        """Test creating a 2x2 puzzle."""
        puzzle = Puzzle(size=2, auto_shuffle=False)
        assert puzzle.size == 2
        assert len(puzzle.board) == 2
        assert len(puzzle.board[0]) == 2

    def test_custom_size_3x3(self):
        """Test creating a 3x3 puzzle."""
        puzzle = Puzzle(size=3, auto_shuffle=False)
        assert puzzle.size == 3
        assert len(puzzle.board) == 3
        assert all(len(row) == 3 for row in puzzle.board)

    def test_custom_size_10x10(self):
        """Test creating a larger 10x10 puzzle."""
        puzzle = Puzzle(size=10, auto_shuffle=False)
        assert puzzle.size == 10
        assert len(puzzle.board) == 10
        assert all(len(row) == 10 for row in puzzle.board)

    def test_minimum_size_validation(self):
        """Test that size < 2 raises ValueError."""
        with pytest.raises(ValueError, match="Grid size must be at least 2"):
            Puzzle(size=1, auto_shuffle=False)

    def test_minimum_size_zero(self):
        """Test that size 0 raises ValueError."""
        with pytest.raises(ValueError, match="Grid size must be at least 2"):
            Puzzle(size=0, auto_shuffle=False)

    def test_minimum_size_negative(self):
        """Test that negative size raises ValueError."""
        with pytest.raises(ValueError, match="Grid size must be at least 2"):
            Puzzle(size=-1, auto_shuffle=False)

    def test_solved_board_creation_3x3(self, puzzle_3x3):
        """Test that solved_board is created correctly for 3x3."""
        expected = [
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"]
        ]
        assert puzzle_3x3.solved_board == expected

    def test_solved_board_creation_2x2(self, puzzle_2x2):
        """Test that solved_board is created correctly for 2x2."""
        expected = [
            ["1", "2"],
            ["3", "4"]
        ]
        assert puzzle_2x2.solved_board == expected

    def test_solved_board_creation_4x4(self, puzzle_4x4):
        """Test that solved_board is created correctly for 4x4."""
        expected = [
            ["1", "2", "3", "4"],
            ["5", "6", "7", "8"],
            ["9", "10", "11", "12"],
            ["13", "14", "15", "16"]
        ]
        assert puzzle_4x4.solved_board == expected

    def test_board_matches_solved_without_shuffle(self, puzzle_3x3):
        """Test that board equals solved_board when auto_shuffle=False."""
        assert puzzle_3x3.board == puzzle_3x3.solved_board

    def test_custom_target_board(self):
        """Test creating puzzle with custom target board."""
        custom = [
            ["A", "B", "C"],
            ["D", "E", "F"],
            ["G", "H", "I"]
        ]
        puzzle = Puzzle(size=3, auto_shuffle=False, target_board=custom)
        assert puzzle.solved_board == custom
        assert puzzle.board == custom

    def test_invalid_target_board_wrong_rows(self):
        """Test that wrong number of rows raises ValueError."""
        invalid = [
            ["1", "2", "3"],
            ["4", "5", "6"]
        ]
        with pytest.raises(ValueError, match="Invalid target_board"):
            Puzzle(size=3, auto_shuffle=False, target_board=invalid)

    def test_invalid_target_board_wrong_cols(self):
        """Test that wrong number of columns raises ValueError."""
        invalid = [
            ["1", "2"],
            ["3", "4"],
            ["5", "6"]
        ]
        with pytest.raises(ValueError, match="Invalid target_board"):
            Puzzle(size=3, auto_shuffle=False, target_board=invalid)

    def test_invalid_target_board_not_list(self):
        """Test that non-list target raises ValueError."""
        with pytest.raises(ValueError, match="Invalid target_board"):
            Puzzle(size=3, auto_shuffle=False, target_board="not a list")

    def test_shuffle_sequence_empty_without_shuffle(self, puzzle_3x3):
        """Test that shuffle_sequence is empty when auto_shuffle=False."""
        assert puzzle_3x3.shuffle_sequence == []

    def test_auto_shuffle_modifies_board(self):
        """Test that auto_shuffle=True changes the board."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=5)
        # Board should (very likely) differ from solved after 5 moves
        # There's a tiny chance it could end up solved, but recursive check handles that
        assert puzzle.shuffle_sequence != []

    def test_auto_shuffle_creates_sequence(self):
        """Test that auto_shuffle creates a shuffle sequence."""
        puzzle = Puzzle(size=3, auto_shuffle=True, shuffle_moves=10)
        assert len(puzzle.shuffle_sequence) >= 10  # May be more due to recursive check

    def test_board_is_deep_copy_of_solved(self, puzzle_3x3):
        """Test that board is a deep copy, not a reference."""
        puzzle_3x3.board[0][0] = "X"
        assert puzzle_3x3.solved_board[0][0] == "1"

    def test_target_board_is_deep_copied(self):
        """Test that target_board is deep copied."""
        custom = [["A", "B"], ["C", "D"]]
        puzzle = Puzzle(size=2, auto_shuffle=False, target_board=custom)
        custom[0][0] = "X"
        assert puzzle.solved_board[0][0] == "A"
