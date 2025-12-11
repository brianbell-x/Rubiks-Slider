"""Tests for column shift mechanics."""

import pytest
from core.puzzle import Puzzle


class TestColumnShiftUp:
    """Tests for shifting columns up."""

    def test_column_shift_up_first_column(self, puzzle_3x3):
        """Test shifting first column up."""
        # Initial: [1,2,3], [4,5,6], [7,8,9]
        # Column 0: 1,4,7 -> 4,7,1
        puzzle_3x3._shift_column(0, "up")
        assert puzzle_3x3.board[0][0] == "4"
        assert puzzle_3x3.board[1][0] == "7"
        assert puzzle_3x3.board[2][0] == "1"
        # Other columns unchanged
        assert puzzle_3x3.board[0][1] == "2"
        assert puzzle_3x3.board[1][1] == "5"
        assert puzzle_3x3.board[2][1] == "8"

    def test_column_shift_up_middle_column(self, puzzle_3x3):
        """Test shifting middle column up."""
        # Column 1: 2,5,8 -> 5,8,2
        puzzle_3x3._shift_column(1, "up")
        assert puzzle_3x3.board[0][1] == "5"
        assert puzzle_3x3.board[1][1] == "8"
        assert puzzle_3x3.board[2][1] == "2"

    def test_column_shift_up_last_column(self, puzzle_3x3):
        """Test shifting last column up."""
        # Column 2: 3,6,9 -> 6,9,3
        puzzle_3x3._shift_column(2, "up")
        assert puzzle_3x3.board[0][2] == "6"
        assert puzzle_3x3.board[1][2] == "9"
        assert puzzle_3x3.board[2][2] == "3"

    def test_column_shift_up_wraps_top_element(self, puzzle_3x3):
        """Test that top element wraps to bottom when shifting up."""
        original_top = puzzle_3x3.board[0][0]
        puzzle_3x3._shift_column(0, "up")
        assert puzzle_3x3.board[-1][0] == original_top

    def test_column_shift_up_2x2(self, puzzle_2x2):
        """Test column shift up on 2x2 grid."""
        # Column 0: 1,3 -> 3,1
        puzzle_2x2._shift_column(0, "up")
        assert puzzle_2x2.board[0][0] == "3"
        assert puzzle_2x2.board[1][0] == "1"

    def test_column_shift_up_full_cycle(self, puzzle_3x3):
        """Test that 3 up shifts return to original for 3x3."""
        original_col = [puzzle_3x3.board[r][0] for r in range(3)]
        for _ in range(3):
            puzzle_3x3._shift_column(0, "up")
        new_col = [puzzle_3x3.board[r][0] for r in range(3)]
        assert original_col == new_col

    def test_column_shift_up_preserves_elements(self, puzzle_3x3):
        """Test that all elements are preserved after shift."""
        original_elements = {puzzle_3x3.board[r][0] for r in range(3)}
        puzzle_3x3._shift_column(0, "up")
        new_elements = {puzzle_3x3.board[r][0] for r in range(3)}
        assert original_elements == new_elements


class TestColumnShiftDown:
    """Tests for shifting columns down."""

    def test_column_shift_down_first_column(self, puzzle_3x3):
        """Test shifting first column down."""
        # Column 0: 1,4,7 -> 7,1,4
        puzzle_3x3._shift_column(0, "down")
        assert puzzle_3x3.board[0][0] == "7"
        assert puzzle_3x3.board[1][0] == "1"
        assert puzzle_3x3.board[2][0] == "4"

    def test_column_shift_down_middle_column(self, puzzle_3x3):
        """Test shifting middle column down."""
        # Column 1: 2,5,8 -> 8,2,5
        puzzle_3x3._shift_column(1, "down")
        assert puzzle_3x3.board[0][1] == "8"
        assert puzzle_3x3.board[1][1] == "2"
        assert puzzle_3x3.board[2][1] == "5"

    def test_column_shift_down_last_column(self, puzzle_3x3):
        """Test shifting last column down."""
        # Column 2: 3,6,9 -> 9,3,6
        puzzle_3x3._shift_column(2, "down")
        assert puzzle_3x3.board[0][2] == "9"
        assert puzzle_3x3.board[1][2] == "3"
        assert puzzle_3x3.board[2][2] == "6"

    def test_column_shift_down_wraps_bottom_element(self, puzzle_3x3):
        """Test that bottom element wraps to top when shifting down."""
        original_bottom = puzzle_3x3.board[-1][0]
        puzzle_3x3._shift_column(0, "down")
        assert puzzle_3x3.board[0][0] == original_bottom

    def test_column_shift_down_2x2(self, puzzle_2x2):
        """Test column shift down on 2x2 grid."""
        # Column 1: 2,4 -> 4,2
        puzzle_2x2._shift_column(1, "down")
        assert puzzle_2x2.board[0][1] == "4"
        assert puzzle_2x2.board[1][1] == "2"

    def test_column_shift_down_full_cycle(self, puzzle_3x3):
        """Test that 3 down shifts return to original for 3x3."""
        original_col = [puzzle_3x3.board[r][0] for r in range(3)]
        for _ in range(3):
            puzzle_3x3._shift_column(0, "down")
        new_col = [puzzle_3x3.board[r][0] for r in range(3)]
        assert original_col == new_col


class TestColumnShiftInverse:
    """Tests for up/down being inverse operations."""

    def test_up_down_inverse(self, puzzle_3x3):
        """Test that up followed by down returns to original."""
        original_col = [puzzle_3x3.board[r][0] for r in range(3)]
        puzzle_3x3._shift_column(0, "up")
        puzzle_3x3._shift_column(0, "down")
        new_col = [puzzle_3x3.board[r][0] for r in range(3)]
        assert original_col == new_col

    def test_down_up_inverse(self, puzzle_3x3):
        """Test that down followed by up returns to original."""
        original_col = [puzzle_3x3.board[r][0] for r in range(3)]
        puzzle_3x3._shift_column(0, "down")
        puzzle_3x3._shift_column(0, "up")
        new_col = [puzzle_3x3.board[r][0] for r in range(3)]
        assert original_col == new_col

    def test_multiple_inverse_operations(self, puzzle_3x3):
        """Test multiple inverse operations on column."""
        original_col = [puzzle_3x3.board[r][1] for r in range(3)]
        puzzle_3x3._shift_column(1, "up")
        puzzle_3x3._shift_column(1, "up")
        puzzle_3x3._shift_column(1, "down")
        puzzle_3x3._shift_column(1, "down")
        new_col = [puzzle_3x3.board[r][1] for r in range(3)]
        assert original_col == new_col


class TestColumnShiftLargerGrids:
    """Tests for column shifts on larger grids."""

    def test_4x4_column_shift_up(self, puzzle_4x4):
        """Test column shift up on 4x4."""
        # Column 0: 1,5,9,13 -> 5,9,13,1
        puzzle_4x4._shift_column(0, "up")
        assert puzzle_4x4.board[0][0] == "5"
        assert puzzle_4x4.board[1][0] == "9"
        assert puzzle_4x4.board[2][0] == "13"
        assert puzzle_4x4.board[3][0] == "1"

    def test_4x4_column_shift_down(self, puzzle_4x4):
        """Test column shift down on 4x4."""
        # Column 0: 1,5,9,13 -> 13,1,5,9
        puzzle_4x4._shift_column(0, "down")
        assert puzzle_4x4.board[0][0] == "13"
        assert puzzle_4x4.board[1][0] == "1"
        assert puzzle_4x4.board[2][0] == "5"
        assert puzzle_4x4.board[3][0] == "9"

    def test_6x6_column_shift_up(self, puzzle_6x6):
        """Test column shift up on 6x6."""
        # Column 0: 1,7,13,19,25,31 -> 7,13,19,25,31,1
        puzzle_6x6._shift_column(0, "up")
        assert puzzle_6x6.board[0][0] == "7"
        assert puzzle_6x6.board[5][0] == "1"

    def test_6x6_column_full_cycle(self, puzzle_6x6):
        """Test that 6 shifts return to original on 6x6."""
        original_col = [puzzle_6x6.board[r][0] for r in range(6)]
        for _ in range(6):
            puzzle_6x6._shift_column(0, "up")
        new_col = [puzzle_6x6.board[r][0] for r in range(6)]
        assert original_col == new_col


class TestMixedRowColumnOperations:
    """Tests for combinations of row and column operations."""

    def test_row_then_column_independence(self, puzzle_3x3):
        """Test that row and column operations on different indices are independent."""
        # Shift row 0 left: [2,3,1], [4,5,6], [7,8,9]
        puzzle_3x3._shift_row(0, "left")
        # Shift column 1 down: [2,8,1], [4,3,6], [7,5,9]
        puzzle_3x3._shift_column(1, "down")

        assert puzzle_3x3.board[0] == ["2", "8", "1"]
        assert puzzle_3x3.board[1] == ["4", "3", "6"]
        assert puzzle_3x3.board[2] == ["7", "5", "9"]

    def test_column_then_row(self, puzzle_3x3):
        """Test column operation followed by row operation."""
        # Shift column 0 up: [4,2,3], [7,5,6], [1,8,9]
        puzzle_3x3._shift_column(0, "up")
        # Shift row 2 right: [4,2,3], [7,5,6], [9,1,8]
        puzzle_3x3._shift_row(2, "right")

        assert puzzle_3x3.board[0] == ["4", "2", "3"]
        assert puzzle_3x3.board[1] == ["7", "5", "6"]
        assert puzzle_3x3.board[2] == ["9", "1", "8"]

    def test_multiple_operations_on_same_element(self, puzzle_3x3):
        """Test element moves correctly through multiple operations."""
        # Track where "5" (center) ends up
        # Start: [1,2,3], [4,5,6], [7,8,9] - "5" at R2C2

        # Shift row 1 left: [1,2,3], [5,6,4], [7,8,9] - "5" at R2C1
        puzzle_3x3._shift_row(1, "left")
        pos = puzzle_3x3.get_tile_position(5)
        assert pos == (2, 1)

        # Shift column 0 up: [5,2,3], [7,6,4], [1,8,9] - "5" at R1C1
        puzzle_3x3._shift_column(0, "up")
        pos = puzzle_3x3.get_tile_position(5)
        assert pos == (1, 1)
