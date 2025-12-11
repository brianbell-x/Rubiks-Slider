"""Tests for row shift mechanics."""

import pytest
from core.puzzle import Puzzle


class TestRowShiftLeft:
    """Tests for shifting rows left."""

    def test_row_shift_left_first_row(self, puzzle_3x3):
        """Test shifting first row left."""
        puzzle_3x3._shift_row(0, "left")
        assert puzzle_3x3.board[0] == ["2", "3", "1"]
        # Other rows unchanged
        assert puzzle_3x3.board[1] == ["4", "5", "6"]
        assert puzzle_3x3.board[2] == ["7", "8", "9"]

    def test_row_shift_left_middle_row(self, puzzle_3x3):
        """Test shifting middle row left."""
        puzzle_3x3._shift_row(1, "left")
        assert puzzle_3x3.board[0] == ["1", "2", "3"]
        assert puzzle_3x3.board[1] == ["5", "6", "4"]
        assert puzzle_3x3.board[2] == ["7", "8", "9"]

    def test_row_shift_left_last_row(self, puzzle_3x3):
        """Test shifting last row left."""
        puzzle_3x3._shift_row(2, "left")
        assert puzzle_3x3.board[0] == ["1", "2", "3"]
        assert puzzle_3x3.board[1] == ["4", "5", "6"]
        assert puzzle_3x3.board[2] == ["8", "9", "7"]

    def test_row_shift_left_wraps_first_element(self, puzzle_3x3):
        """Test that first element wraps to end when shifting left."""
        original_first = puzzle_3x3.board[0][0]
        puzzle_3x3._shift_row(0, "left")
        assert puzzle_3x3.board[0][-1] == original_first

    def test_row_shift_left_2x2(self, puzzle_2x2):
        """Test row shift left on 2x2 grid."""
        puzzle_2x2._shift_row(0, "left")
        assert puzzle_2x2.board[0] == ["2", "1"]

    def test_row_shift_left_full_cycle(self, puzzle_3x3):
        """Test that 3 left shifts return to original for 3x3."""
        original = [row[:] for row in puzzle_3x3.board]
        for _ in range(3):
            puzzle_3x3._shift_row(0, "left")
        assert puzzle_3x3.board == original

    def test_row_shift_left_preserves_elements(self, puzzle_3x3):
        """Test that all elements are preserved after shift."""
        original_elements = set(puzzle_3x3.board[0])
        puzzle_3x3._shift_row(0, "left")
        new_elements = set(puzzle_3x3.board[0])
        assert original_elements == new_elements


class TestRowShiftRight:
    """Tests for shifting rows right."""

    def test_row_shift_right_first_row(self, puzzle_3x3):
        """Test shifting first row right."""
        puzzle_3x3._shift_row(0, "right")
        assert puzzle_3x3.board[0] == ["3", "1", "2"]
        # Other rows unchanged
        assert puzzle_3x3.board[1] == ["4", "5", "6"]
        assert puzzle_3x3.board[2] == ["7", "8", "9"]

    def test_row_shift_right_middle_row(self, puzzle_3x3):
        """Test shifting middle row right."""
        puzzle_3x3._shift_row(1, "right")
        assert puzzle_3x3.board[0] == ["1", "2", "3"]
        assert puzzle_3x3.board[1] == ["6", "4", "5"]
        assert puzzle_3x3.board[2] == ["7", "8", "9"]

    def test_row_shift_right_last_row(self, puzzle_3x3):
        """Test shifting last row right."""
        puzzle_3x3._shift_row(2, "right")
        assert puzzle_3x3.board[0] == ["1", "2", "3"]
        assert puzzle_3x3.board[1] == ["4", "5", "6"]
        assert puzzle_3x3.board[2] == ["9", "7", "8"]

    def test_row_shift_right_wraps_last_element(self, puzzle_3x3):
        """Test that last element wraps to front when shifting right."""
        original_last = puzzle_3x3.board[0][-1]
        puzzle_3x3._shift_row(0, "right")
        assert puzzle_3x3.board[0][0] == original_last

    def test_row_shift_right_2x2(self, puzzle_2x2):
        """Test row shift right on 2x2 grid."""
        puzzle_2x2._shift_row(1, "right")
        assert puzzle_2x2.board[1] == ["4", "3"]

    def test_row_shift_right_full_cycle(self, puzzle_3x3):
        """Test that 3 right shifts return to original for 3x3."""
        original = [row[:] for row in puzzle_3x3.board]
        for _ in range(3):
            puzzle_3x3._shift_row(0, "right")
        assert puzzle_3x3.board == original


class TestRowShiftInverse:
    """Tests for left/right being inverse operations."""

    def test_left_right_inverse(self, puzzle_3x3):
        """Test that left followed by right returns to original."""
        original = puzzle_3x3.board[0][:]
        puzzle_3x3._shift_row(0, "left")
        puzzle_3x3._shift_row(0, "right")
        assert puzzle_3x3.board[0] == original

    def test_right_left_inverse(self, puzzle_3x3):
        """Test that right followed by left returns to original."""
        original = puzzle_3x3.board[0][:]
        puzzle_3x3._shift_row(0, "right")
        puzzle_3x3._shift_row(0, "left")
        assert puzzle_3x3.board[0] == original

    def test_multiple_inverse_operations(self, puzzle_3x3):
        """Test multiple inverse operations."""
        original = puzzle_3x3.board[1][:]
        puzzle_3x3._shift_row(1, "left")
        puzzle_3x3._shift_row(1, "left")
        puzzle_3x3._shift_row(1, "right")
        puzzle_3x3._shift_row(1, "right")
        assert puzzle_3x3.board[1] == original


class TestRowShiftLargerGrids:
    """Tests for row shifts on larger grids."""

    def test_4x4_row_shift_left(self, puzzle_4x4):
        """Test row shift left on 4x4."""
        puzzle_4x4._shift_row(0, "left")
        assert puzzle_4x4.board[0] == ["2", "3", "4", "1"]

    def test_4x4_row_shift_right(self, puzzle_4x4):
        """Test row shift right on 4x4."""
        puzzle_4x4._shift_row(0, "right")
        assert puzzle_4x4.board[0] == ["4", "1", "2", "3"]

    def test_6x6_row_shift_left(self, puzzle_6x6):
        """Test row shift left on 6x6."""
        puzzle_6x6._shift_row(0, "left")
        assert puzzle_6x6.board[0] == ["2", "3", "4", "5", "6", "1"]

    def test_6x6_row_full_cycle(self, puzzle_6x6):
        """Test that 6 shifts return to original on 6x6."""
        original = puzzle_6x6.board[0][:]
        for _ in range(6):
            puzzle_6x6._shift_row(0, "left")
        assert puzzle_6x6.board[0] == original
